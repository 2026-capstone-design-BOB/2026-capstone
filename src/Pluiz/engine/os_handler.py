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

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class OSHandler(BaseController):
    def __init__(self):
        super().__init__()
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

    def _init_tts(self):
        if not self.tts_config.get("enabled", False):
            return None
        if pyttsx3 is None:
            self.logger.warning("pyttsx3 is not installed. TTS disabled.")
            return None

        if self._tts_engine is None:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", self.tts_config.get("rate", 185))
                self._tts_engine.setProperty("volume", self.tts_config.get("volume", 1.0))
            except Exception as e:
                self.logger.error(f"TTS Init Error: {e}")
                self._tts_engine = None
        return self._tts_engine

    def _speak(self, text):
        if not text or not self.tts_config.get("enabled", False):
            return

        if pyttsx3 is None:
            self.logger.warning("pyttsx3 is not installed. TTS disabled.")
            return

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.tts_config.get("rate", 185))
            engine.setProperty("volume", self.tts_config.get("volume", 1.0))
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            self.logger.error(f"TTS Speak Error: {e}")

    def _message(self, key, default_text):
        return self.tts_config.get("messages", {}).get(key, default_text)

    def _respond(self, status, reason=None, message=None, speak=False, **kwargs):
        result = {"status": status}
        if reason:
            result["reason"] = reason
        if message:
            result["message"] = message
        result.update(kwargs)

        if speak and message:
            self._speak(message)

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

        # 1. 앱 정보 매칭
        app_info, score = self._get_best_match(target)
        if not app_info:
            msg = self._message("app_not_found", "해당 프로그램을 찾지 못했어요.")
            return self._respond("fail", reason="not_found", message=msg, speak=True, score=score)

        # 2. 보안상 2차 차단
        is_blocked, blocked_reason = self._is_blocked_request(action, target, app_info, params)
        if is_blocked:
            self.logger.warning(f"Blocked by OSHandler: {blocked_reason}")
            msg = self._message("deny_unsafe", "이 요청은 보안상 실행할 수 없어요.")
            return self._respond("denied", reason=blocked_reason, message=msg, speak=True)

        actual_name = app_info["name"]
        path = app_info["path"]

        # 3. 액션 처리
        if action == "open":
            force_new = params.get("force_new", False)

            old_hwnds = self._get_all_hwnds(app_info)

            if not force_new and old_hwnds:
                self.logger.info(f"기존 '{actual_name}' 창을 사용합니다.")
                self.last_used_hwnd = old_hwnds[-1]
                self._force_focus(self.last_used_hwnd)

                msg = f"{actual_name} 창으로 이동했어요."
                speak_success = self.tts_config.get("speak_on_success", False)
                return self._respond(
                    "success",
                    reason="focus",
                    message=msg,
                    speak=speak_success,
                    mode="focus",
                    hwnd=self.last_used_hwnd
                )

            self.logger.info(f"'{actual_name}' 새 인스턴스 실행 중...")
            try:
                subprocess.Popen(f'start "" "{path}"', shell=True)
            except Exception as e:
                self.logger.error(f"Launch Error: {e}")
                msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
                return self._respond("fail", reason="launch_error", message=msg, speak=True)

            new_hwnd = None
            for _ in range(10):
                time.sleep(0.5)
                current_hwnds = self._get_all_hwnds(app_info)
                diff = [h for h in current_hwnds if h not in old_hwnds]
                if diff:
                    new_hwnd = diff[0]
                    break
                elif not old_hwnds and current_hwnds:
                    new_hwnd = current_hwnds[0]
                    break

            fallback_hwnds = self._get_all_hwnds(app_info)
            self.last_used_hwnd = new_hwnd or (fallback_hwnds[-1] if fallback_hwnds else None)

            if not self.last_used_hwnd:
                msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
                return self._respond("fail", reason="window_not_found", message=msg, speak=True)

            msg = f"{actual_name} 실행을 완료했어요."
            speak_success = self.tts_config.get("speak_on_success", False)
            return self._respond(
                "success",
                reason="launch",
                message=msg,
                speak=speak_success,
                mode="launch",
                hwnd=self.last_used_hwnd
            )

        elif action == "input":
            target_hwnd = self.last_used_hwnd
            win = self._find_window_by_hwnd(target_hwnd) if target_hwnd else None

            if not win:
                all_hwnds = self._get_all_hwnds(app_info)
                if all_hwnds:
                    target_hwnd = all_hwnds[-1]
                    win = self._find_window_by_hwnd(target_hwnd)

            if win:
                try:
                    self.logger.info(f"대상 창(HWND: {target_hwnd})에 텍스트를 입력합니다.")
                    self._force_focus(win._hWnd)
                    time.sleep(0.8)

                    text_to_input = params.get("text", "")
                    pyperclip.copy(text_to_input)
                    pyautogui.hotkey("ctrl", "v")
                    pyautogui.press("enter")

                    msg = self._message("action_done", "작업을 완료했어요.")
                    speak_success = self.tts_config.get("speak_on_success", False)
                    return self._respond("success", message=msg, speak=speak_success)
                except Exception as e:
                    self.logger.error(f"Input Error: {e}")
                    msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
                    return self._respond("fail", reason="input_error", message=msg, speak=True)
            else:
                msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
                return self._respond("fail", reason="window_not_found", message=msg, speak=True)

        elif action == "close":
            hwnds = self._get_all_hwnds(app_info)
            if not hwnds:
                msg = self._message("window_not_found", "대상 창을 찾지 못했어요.")
                return self._respond("fail", reason="window_not_found", message=msg, speak=True)

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
                speak_success = self.tts_config.get("speak_on_success", False)
                return self._respond(
                    "success",
                    message=msg,
                    speak=speak_success,
                    closed_count=closed_count
                )

            msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
            return self._respond("fail", reason="close_failed", message=msg, speak=True)

        msg = self._message("action_failed", "요청한 작업을 수행하지 못했어요.")
        return self._respond("fail", reason="unknown_action", message=msg, speak=True)

    def _get_best_match(self, target):
        choices = list(self.search_targets.keys())
        if not choices or not target:
            return None, 0

        best_match, score = process.extractOne(target, choices)
        return (self.search_targets[best_match], score) if score >= 60 else (None, score)