# engine/os_handler.py
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

class OSHandler(BaseController):
    def __init__(self):
        super().__init__()
        self.config_path = os.path.join("assets", "apps_config.json")
        self.apps_data = self._load_config()
        self.search_targets = self._prepare_search_targets()
        # 시퀀스 내에서 타겟 창을 유지하기 위한 변수
        self.last_used_hwnd = None

    def _load_config(self):
        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)["apps"]
        except: return []

    def _prepare_search_targets(self):
        targets = {}
        for app in self.apps_data:
            targets[app["name"]] = app
            for alias in app.get("aliases", []):
                targets[alias] = app
        return targets

    def _get_all_hwnds(self, name):
        """특정 이름을 가진 모든 창의 핸들 리스트를 반환합니다."""
        all_windows = gw.getAllWindows()
        return [w._hWnd for w in all_windows if name.lower() in w.title.lower()]

    def _find_window_by_hwnd(self, hwnd):
        """핸들(HWND)을 통해 창 객체를 찾습니다."""
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
        except: return False

    def execute(self, action: str, target: str, params: dict = None):
        # 1. 앱 정보 매칭
        app_info, _ = self._get_best_match(target)
        if not app_info: return {"status": "fail", "reason": "not_found"}
        
        actual_name = app_info["name"]
        path = app_info["path"]
        params = params or {}

        # 2. 액션 처리
        if action == "open":
            force_new = params.get("force_new", False)
            
            # 기존 창들 목록 확보 (신규 창 검증용)
            old_hwnds = self._get_all_hwnds(actual_name)
            
            if not force_new and old_hwnds:
                self.logger.info(f"기존 '{actual_name}' 창을 사용합니다.")
                self.last_used_hwnd = old_hwnds[-1]
                self._force_focus(self.last_used_hwnd)
                return {"status": "success", "mode": "focus", "hwnd": self.last_used_hwnd}
            
            # 새 창 실행
            self.logger.info(f"'{actual_name}' 새 인스턴스 실행 중...")
            subprocess.Popen(f"start {path}", shell=True)
            
            # 신규 창이 리스트에 나타날 때까지 대기 (최대 5초)
            new_hwnd = None
            for _ in range(10):
                time.sleep(0.5)
                current_hwnds = self._get_all_hwnds(actual_name)
                diff = [h for h in current_hwnds if h not in old_hwnds]
                if diff:
                    new_hwnd = diff[0]
                    break
                elif not old_hwnds and current_hwnds: # 아예 없다가 생긴 경우
                    new_hwnd = current_hwnds[0]
                    break
            
            self.last_used_hwnd = new_hwnd or (self._get_all_hwnds(actual_name)[-1] if self._get_all_hwnds(actual_name) else None)
            return {"status": "success", "mode": "launch", "hwnd": self.last_used_hwnd}

        elif action == "input":
            # 시퀀스 내에서 저장된 핸들이 있는지 먼저 확인
            target_hwnd = self.last_used_hwnd
            win = self._find_window_by_hwnd(target_hwnd) if target_hwnd else None
            
            # 핸들로 못 찾으면 이름으로 재검색 (방어 로직)
            if not win:
                all_hwnds = self._get_all_hwnds(actual_name)
                if all_hwnds:
                    target_hwnd = all_hwnds[-1]
                    win = self._find_window_by_hwnd(target_hwnd)

            if win:
                self.logger.info(f"대상 창(HWND: {target_hwnd})에 텍스트를 입력합니다.")
                self._force_focus(win._hWnd)
                time.sleep(0.8)
                pyperclip.copy(params.get("text", ""))
                pyautogui.hotkey('ctrl', 'v')
                pyautogui.press('enter')
                return {"status": "success"}
            else:
                return {"status": "fail", "reason": "window_not_found"}

        return {"status": "fail", "reason": "unknown_action"}

    def _get_best_match(self, target):
        choices = list(self.search_targets.keys())
        best_match, score = process.extractOne(target, choices)
        return (self.search_targets[best_match], score) if score >= 60 else (None, score)