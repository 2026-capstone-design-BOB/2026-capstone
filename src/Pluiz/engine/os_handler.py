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
import glob  # 최근 파일을 찾기 위해 추가
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

        # --- [액션 1: OPEN] ---
        if action == "open":
            is_new = params.get("is_new", False) or params.get("force_new", False)
            
            # 1. 엑셀 특수 처리: 바탕화면에서 가장 최근 .xlsx 파일을 찾아 실행
            if actual_name == "엑셀":
                try:
                    # 바탕화면 경로 가져오기
                    desktop_path = os.path.join(os.path.expanduser("~"), "Desktop")
                    # 모든 .xlsx 파일 리스트업
                    excel_files = glob.glob(os.path.join(desktop_path, "*.xlsx"))
                    
                    if excel_files:
                        # 가장 최근에 수정된 파일 선택
                        latest_file = max(excel_files, key=os.path.getmtime)
                        self.logger.info(f"📂 바탕화면의 최신 엑셀 파일 실행: {latest_file}")
                        
                        # 파일명을 인자로 넣어 실행 (이게 핵심입니다!)
                        subprocess.Popen(f'start "" "{latest_file}"', shell=True)
                        
                        # 창이 뜰 때까지 대기 및 핸들 확보
                        time.sleep(2.0) 
                        return {"status": "success", "mode": "launch_file", "file": latest_file}
                except Exception as e:
                    self.logger.error(f"엑셀 파일 찾기 중 에러: {e}")
                
                # 만약 파일 찾기에 실패하면 아래의 일반 실행 로직으로 넘어갑니다.

            # 2. 일반 앱 실행 로직 (메모장, 그림판 등 또는 엑셀 파일 못 찾았을 때)
            if not is_new and current_hwnds and actual_name != "엑셀":
                self.last_used_hwnd = current_hwnds[-1]
                self._force_focus(self.last_used_hwnd)
                return {"status": "success", "mode": "focus", "hwnd": self.last_used_hwnd}
            
            # 신규 실행
            old_hwnds = current_hwnds
            subprocess.Popen(f"start {path}", shell=True)
            
            new_hwnd = None
            for _ in range(10):
                time.sleep(0.5)
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

            # [1단계] 타겟 창 핸들 확보
            target_hwnd = self.last_used_hwnd
            if not target_hwnd or not win32gui.IsWindow(target_hwnd):
                for _ in range(5):  
                    hwnds = self._get_all_hwnds(actual_name)
                    if hwnds: 
                        target_hwnd = hwnds[-1]
                        break
                    time.sleep(0.5)
                self.last_used_hwnd = target_hwnd

            if target_hwnd:
                # [2단계] 창 포커싱
                self._force_focus(target_hwnd)
                time.sleep(1.0) 

                # [3단계] 클립보드 작업
                pyperclip.copy('') 
                pyperclip.copy(input_text)
                time.sleep(0.2) 

                # [4단계] 입력 실행
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