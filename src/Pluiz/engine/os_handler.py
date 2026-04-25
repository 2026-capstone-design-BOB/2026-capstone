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
from utils.logger import get_logger, trace_action # trace_action 추가

class OSHandler(BaseController):
    def __init__(self):
        super().__init__()
        self.config_path = os.path.join("assets", "apps_config.json")
        self.apps_data = self._load_config()
        self.search_targets = self._prepare_search_targets()
        # logger
        self.logger = get_logger("OSHandler")
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
        # [수정] 실행 시점에 모든 인자를 한 줄로 요약해서 출력
        self.logger.info(f"🚀 [OS_START] 액션: {action} | 타겟: {target} | 데이터: {params}")
        # 1. 앱 정보 매칭
        app_info, _ = self._get_best_match(target)
        if not app_info: return {"status": "fail", "reason": "not_found"}
        
        actual_name = app_info["name"]
        path = app_info["path"]
        params = params or {}
        current_hwnds = self._get_all_hwnds(actual_name)

        # engine/os_handler.py 내 open 부분

        # --- [액션 1: OPEN] ---
        if action == "open":
            # params에서 is_new가 있는지 확실히 체크
            is_new = params.get("is_new", False) or params.get("force_new", False)
            
            # 새로 여는 것이 아니고 이미 창이 있다면
            if not is_new and current_hwnds:
                self.last_used_hwnd = current_hwnds[-1]
                self._force_focus(self.last_used_hwnd)
                return {"status": "success", "mode": "focus", "hwnd": self.last_used_hwnd}
            
            # --- 여기서부터 신규 실행 로직 ---
            old_hwnds = current_hwnds
            subprocess.Popen(f"start {path}", shell=True)
            
            new_hwnd = None
            for _ in range(10):
                time.sleep(0.5)
                # 제가 제안한 고속 검색 함수(_get_fast_hwnd)가 있다면 그걸 쓰시는 게 좋습니다.
                updated_hwnds = self._get_all_hwnds(actual_name) 
                diff = [h for h in updated_hwnds if h not in old_hwnds]
                if diff:
                    new_hwnd = diff[0]
                    break
            
            self.last_used_hwnd = new_hwnd or (updated_hwnds[-1] if updated_hwnds else None)
            return {"status": "success", "mode": "launch", "hwnd": self.last_used_hwnd}
        # --- [액션 2: INPUT] ---
        elif action == "input":
            input_text = params.get('text', '')
            self.logger.info(f"🚀 [OS_START] 액션: input | 타겟: {actual_name} | 텍스트: '{input_text}'")

            # [1단계] 타겟 창 핸들 확보 (없으면 찾을 때까지 잠시 대기)
            target_hwnd = self.last_used_hwnd
            if not target_hwnd or not win32gui.IsWindow(target_hwnd):
                for _ in range(5):  # 최대 2.5초간 창 찾기 시도
                    target_hwnd = self._get_fast_hwnd(actual_name)
                    if target_hwnd: break
                    time.sleep(0.5)
                self.last_used_hwnd = target_hwnd

            if target_hwnd:
                # [2단계] 창을 최상단으로 올리고 '입력 가능 상태'가 될 때까지 대기
                self._force_focus(target_hwnd)
                
                # 핵심: 창이 활성화되어 포커스를 완전히 잡을 때까지의 물리적 시간 확보
                # 로그상 0.04초만에 실행되는 것을 방지하기 위해 강제로 0.8초~1초 대기
                time.sleep(1.0) 

                # [3단계] 클립보드 작업 (데이터 오염 방지)
                pyperclip.copy('') 
                pyperclip.copy(input_text)
                time.sleep(0.2) # 클립보드 데이터 안착 시간

                # [4단계] 입력 실행 (이미 활성화된 창에 안전하게 붙여넣기)
                pyautogui.keyDown('ctrl')
                pyautogui.press('v')
                time.sleep(0.1)
                pyautogui.keyUp('ctrl')
                
                if params.get('send_enter', False):
                    time.sleep(0.1)
                    pyautogui.press('enter')
                    
                return {"status": "success"}
            
            return {"status": "fail", "reason": "window_not_found"}
        # --- [액션 3: 창 제어 (최대/최소/복원)] ---
        elif action in ["maximize", "minimize", "restore"]:
            target_hwnd = self.last_used_hwnd if self.last_used_hwnd and win32gui.IsWindow(self.last_used_hwnd) else (current_hwnds[-1] if current_hwnds else None)
            
            if not target_hwnd: return {"status": "fail", "reason": "window_not_found"}
            
            if action == "maximize":
                win32gui.ShowWindow(target_hwnd, win32con.SW_MAXIMIZE)
            elif action == "minimize":
                win32gui.ShowWindow(target_hwnd, win32con.SW_MINIMIZE)
            elif action == "restore":
                win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
            
            self._force_focus(target_hwnd)
            return {"status": "success", "mode": action}

        # --- [액션 4: CLOSE] ---
        elif action == "close":
            target_hwnd = current_hwnds[-1] if current_hwnds else None
            if not target_hwnd: return {"status": "fail", "reason": "window_not_found"}
            
            win32gui.PostMessage(target_hwnd, win32con.WM_CLOSE, 0, 0)
            return {"status": "success", "mode": "close"}

        return {"status": "fail", "reason": f"unknown_action: {action}"}

    def _get_best_match(self, target):
        choices = list(self.search_targets.keys())
        best_match, score = process.extractOne(target, choices)
        return (self.search_targets[best_match], score) if score >= 60 else (None, score)