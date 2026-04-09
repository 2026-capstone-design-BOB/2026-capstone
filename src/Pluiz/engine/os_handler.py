# engine/os_handler.py
import subprocess
import pygetwindow as gw
import os
from engine.base import BaseController

class OSHandler(BaseController):
    def __init__(self):
        super().__init__()
        # 별칭(Alias) 매핑: 사용자가 말하는 이름 -> 실제 실행 파일명
        self.app_map = {
            "메모장": "notepad.exe",
            "계산기": "calc.exe",
            "그림판": "mspaint.exe",
            "명령 프롬프트": "cmd.exe",
            "명령프롬프트": "cmd.exe"
        }

    def execute(self, action: str, target: str, params: dict = None):
        self.logger.info(f"OS 실행 요청: {action} / {target}")

        if action == "open":
            return self._open_app(target)
        
        # 창 제어 (닫기, 최대화, 최소화)
        return self._control_window(action, target)

    def _open_app(self, target):
        executable = self.app_map.get(target, target)
        try:
            subprocess.Popen(f"start {executable}", shell=True)
            return True
        except Exception as e:
            self.logger.error(f"실행 에러: {e}")
            return False

    def _control_window(self, action, target):
        # 창 제목에서 유사한 것을 검색
        windows = gw.getWindowsWithTitle(target)
        if not windows:
            self.logger.warning(f"'{target}' 창을 찾을 수 없습니다.")
            return False

        win = windows[0]
        try:
            # 1. 종료 (Close)
            if action == "close":
                win.close()
            
            # 2. 최대화 (Maximize) - 전체 화면 ㅁ
            elif action in ["maximize", "최대화"]:
                win.maximize()
            
            # 3. 최소화 (Minimize) - 작업 표시줄로 숨기기 -
            elif action in ["minimize", "최소화"]:
                win.minimize()
                
            # 4. 이전 크기로 복원 (Restore) - ㅁ버튼(중간 크기)
            # LLM이 'restore'나 'resize' 혹은 '정규화' 등으로 보낼 때 처리
            elif action in ["restore", "복원", "resize"]:
                win.restore()
            
            return True
        except Exception as e:
            self.logger.error(f"창 제어 에러: {e}")
            return False