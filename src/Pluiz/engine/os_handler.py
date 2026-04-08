# engine/os_handler.py
import subprocess
from engine.base import BaseController

class OSHandler(BaseController):
    def __init__(self):
        super().__init__()
        # 간단한 시스템 앱 매핑
        self.system_apps = {
            "메모장": "notepad.exe",
            "계산기": "calc.exe",
            "그림판": "mspaint.exe"
        }

    def execute(self, action: str, target: str, params: dict = None):
        """
        Core로부터 전달받은 action, target을 바탕으로 명령 수행
        """
        self.logger.info(f"명령 실행 요청 - Action: {action}, Target: {target}")
        
        if action == "open":
            return self._open_logic(target, params)
        else:
            self.logger.warning(f"지원하지 않는 액션: {action}")
            return False

    def _open_logic(self, target, params):
        # 1. 우선 시스템 매핑 테이블 확인
        executable = self.system_apps.get(target)
        
        # 2. 만약 매핑 테이블에 없다면? 
        # (추후 이곳에 apps/ 폴더의 특수 스크립트를 로드하는 로직이 들어갈 자리입니다)
        if not executable:
            executable = target # 직접 실행 시도
            
        try:
            subprocess.Popen(executable, shell=True)
            self.logger.info(f"실행 성공: {executable}")
            return True
        except Exception as e:
            self.logger.error(f"실행 실패 ({target}): {e}")
            return False