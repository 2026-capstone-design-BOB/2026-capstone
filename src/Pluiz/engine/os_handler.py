import subprocess
import pygetwindow as gw
import json
import os
import time
import pyautogui
import pyperclip
import win32gui
import win32con
from fuzzywuzzy import process
from engine.base import BaseController
from utils.logger import get_logger, trace_action


class OSHandler(BaseController):
    def __init__(self):
        super().__init__()
        self.logger = get_logger("OSHandler")
        self.config_path = os.path.join("assets", "apps_config.json")

        self.raw_config = self._load_raw_config()
        self.apps_data = self.raw_config.get("apps", [])
        self.tts_config = self.raw_config.get("tts", {})
        self.security_config = self.raw_config.get("security", {})

        self.search_targets = self._prepare_search_targets()
        self.last_used_hwnd = None

    def _load_raw_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config Load Error: {e}")
            return {}

    def _prepare_search_targets(self):
        targets = {}
        for app in self.apps_data:
            targets[app["name"]] = app
            for alias in app.get("aliases", []):
                targets[alias] = app
        return targets

    def _message(self, key, default_text):
        return self.tts_config.get("messages", {}).get(key, default_text)

    def _respond(self, status, reason=None, message=None, **kwargs):
        result = {"status": status}
        if reason:
            result["reason"] = reason
        if message:
            result["message"] = message
        result.update(kwargs)
        return result

    def _get_window_keywords(self, app_info):
        keywords = app_info.get("window_keywords", [])
        if not keywords:
            keywords = [app_info.get("name", "")]
        return [k for k in keywords if k]

    def _get_all_hwnds(self, app_info):
        keywords = [k.lower() for k in self._get_window_keywords(app_info)]
        all_windows = gw.getAllWindows()

        matched = []
        for w in all_windows:
            title = (w.title or "").lower()
            if any(keyword in title for keyword in keywords):
                matched.append(w._hWnd)
        return matched

    def _find_window_by_hwnd(self, hwnd):
        all_windows = gw.getAllWindows()
        for w in all_windows:
            if w._hWnd == hwnd:
                return w
        return None

    def _force_focus(self, hwnd):
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False

    def _is_blocked_request(self, action, target, app_info, params=None):
        params = params or {}
        blocked_keywords = [str(x).lower() for x in self.security_config.get("blocked_keywords", [])]
        blocked_apps = [str(x).lower() for x in self.security_config.get("blocked_apps", [])]

        joined_text = " ".join([
            str(action or ""),
            str(target or ""),
            str(app_info.get("name", "") if app_info else ""),
            str(app_info.get("path", "") if app_info else ""),
            str(params.get("text", ""))
        ]).lower()

        if app_info and str(app_info.get("path", "")).lower() in blocked_apps:
            return True, "blocked_app"

        for keyword in blocked_keywords:
            if keyword in joined_text:
                return True, f"blocked_keyword:{keyword}"

        return False, None

    def execute(self, action: str, target: str, params: dict = None):
        params = params or {}
        self.logger.info(f"🚀 [OS_START] 액션: {action} | 타겟: {target} | 데이터: {params}")

        # 1. 앱 정보 매칭
        app_info, score = self._get_best_match(target)
        if not app_info:
            msg = self._message("app_not_found", "해당 프로그램을 찾지 못했어요.")
            return self._respond("fail", reason="not_found", message=msg, score=score)

        # 2. 보안 차단
        is_blocked, blocked_reason = self._is_blocked_request(action, target, app_info, params)
        if is_blocked:
            self.logger.warning(f"Blocked by OSHandler: {blocked_reason}")
            msg = self._message("deny_unsafe", "이 요청은 보안상 실행할 수 없어요.")
            return self._respond("denied", reason=blocked_reason, message=msg)

        actual_name = app_info["name"]
        path = app_info["path"]
        current_hwnds = self._get_all_hwnds(app_info)

        # 3. 액션 처리
        if action == "open":
            is_new = params.get("is_new", False) or params.get("force_new", False)

            # 이미 창이 있고 새로 여는 요청이 아니면 해당 창으로 포커스
            if not is_new and current_hwnds:
                self.last_used_hwnd = current_hwnds[-1]
                self._force_focus(self.last_used_hwnd)

                msg = f"{actual_name} 창으로 이동했어요."
                return self._respond(
                    "success",
                    reason="focus",
                    message=msg,
                    mode="focus",
                    hwnd=self.last_used_hwnd
                )

            # 새 실행
            old_hwnds = current_hwnds
            try:
                subprocess.Popen(f'start "" "{path}"', shell=True)
            except Exception as e:
                self.logger.error(f"Launch Error: {e}")
                msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
                return self._respond("fail", reason="launch_error", message=msg)

            new_hwnd = None
            updated_hwnds = old_hwnds[:]

            for _ in range(10):
                time.sleep(0.5)
                updated_hwnds = self._get_all_hwnds(app_info)
                diff = [h for h in updated_hwnds if h not in old_hwnds]
                if diff:
                    new_hwnd = diff[0]
                    break
                elif not old_hwnds and updated_hwnds:
                    new_hwnd = updated_hwnds[0]
                    break

            self.last_used_hwnd = new_hwnd or (updated_hwnds[-1] if updated_hwnds else None)

            if not self.last_used_hwnd:
                msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
                return self._respond("fail", reason="window_not_found", message=msg)

            msg = f"{actual_name} 실행을 완료했어요."
            return self._respond(
                "success",
                reason="launch",
                message=msg,
                mode="launch",
                hwnd=self.last_used_hwnd
            )

        elif action == "input":
            input_text = params.get("text", "")
            send_enter = params.get("send_enter", True)

            target_hwnd = self.last_used_hwnd
            win = self._find_window_by_hwnd(target_hwnd) if target_hwnd else None

            if not win:
                all_hwnds = self._get_all_hwnds(app_info)
                if all_hwnds:
                    target_hwnd = all_hwnds[-1]
                    win = self._find_window_by_hwnd(target_hwnd)
                    self.last_used_hwnd = target_hwnd

            if win:
                try:
                    self.logger.info(f"대상 창(HWND: {target_hwnd})에 텍스트를 입력합니다.")
                    self._force_focus(win._hWnd)
                    time.sleep(1.0)

                    pyperclip.copy("")
                    pyperclip.copy(input_text)
                    time.sleep(0.2)

                    pyautogui.keyDown("ctrl")
                    pyautogui.press("v")
                    time.sleep(0.1)
                    pyautogui.keyUp("ctrl")

                    if send_enter:
                        time.sleep(0.1)
                        pyautogui.press("enter")

                    msg = self._message("action_done", "작업을 완료했어요.")
                    return self._respond("success", message=msg)

                except Exception as e:
                    self.logger.error(f"Input Error: {e}")
                    msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
                    return self._respond("fail", reason="input_error", message=msg)

            msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
            return self._respond("fail", reason="window_not_found", message=msg)

        elif action in ["maximize", "minimize", "restore"]:
            target_hwnd = None

            if self.last_used_hwnd and win32gui.IsWindow(self.last_used_hwnd):
                target_hwnd = self.last_used_hwnd
            elif current_hwnds:
                target_hwnd = current_hwnds[-1]

            if not target_hwnd:
                msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
                return self._respond("fail", reason="window_not_found", message=msg)

            try:
                if action == "maximize":
                    win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)
                elif action == "minimize":
                    win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
                elif action == "restore":
                    win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)

                self._force_focus(target_hwnd)
                return self._respond("success", mode=action, message=f"{actual_name} 창을 {action} 했어요.")

            except Exception as e:
                self.logger.error(f"Window Control Error: {e}")
                msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
                return self._respond("fail", reason="window_control_error", message=msg)

        elif action == "close":
            hwnds = self._get_all_hwnds(app_info)
            if not hwnds:
                msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
                return self._respond("fail", reason="window_not_found", message=msg)

            closed_count = 0
            for hwnd in hwnds:
                try:
                    win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    closed_count += 1
                except Exception as e:
                    self.logger.error(f"Close Error (HWND {hwnd}): {e}")

            if closed_count > 0:
                if self.last_used_hwnd in hwnds:
                    self.last_used_hwnd = None

                msg = f"{actual_name} 창을 닫았어요."
                return self._respond(
                    "success",
                    message=msg,
                    closed_count=closed_count,
                    mode="close"
                )

            msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
            return self._respond("fail", reason="close_failed", message=msg)

        msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
        return self._respond("fail", reason="unknown_action", message=msg)

    def _get_best_match(self, target):
        choices = list(self.search_targets.keys())
        if not choices or not target:
            return None, 0

        best_match, score = process.extractOne(target, choices)
        return (self.search_targets[best_match], score) if score >= 60 else (None, score)