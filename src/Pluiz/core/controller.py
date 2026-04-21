import json
import time
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from engine.os_handler import OSHandler
from engine.web_handler import WebHandler
from utils.logger import get_logger

class PluizController:
    def __init__(self):
        self.logger = get_logger("Controller")
        self.stt = STTEngine()
        self.interpreter = IntentInterpreter()
        self.os_handler = OSHandler()
        self.web_handler = WebHandler()

    def process_voice_command(self):
        # 1. 청취 및 인식 (STT 단계 로그는 STTEngine 내부에서 INFO로 찍힘)
        audio = self.stt.listen()
        user_text = self.stt.transcribe(audio)
        if not user_text: return

        # 2. 의도 분석 시작 로그 (기획자님 스타일)
        self.logger.info(f"의도 분석 시작: {user_text}")
        
        # interpreter.analyze 내부에서 DEBUG 레벨로 LLM Raw Response를 찍도록 유지해주세요.
        intent_data = self.interpreter.analyze(user_text)
        self.logger.debug(f"🤖 LLM 분석 결과: {json.dumps(intent_data, ensure_ascii=False)}")
        if not intent_data: 
            return

        commands = intent_data.get("commands", [])
        
        # 3. 순차적 명령 실행
        for i, cmd in enumerate(commands):
            action = cmd.get("action")
            target = cmd.get("target")
            params = cmd.get("params", {})

            # [핵심] 명령 간 연결 박자 조절
            # 이전 명령이 'open'이었다면 창이 뜨는 물리적 시간을 위해 더 오래 쉽니다.
            # [수정] open 직후에는 무조건 쉬어가도록 보장
            if i > 0:
                prev_cmd = commands[i-1]
                if prev_cmd.get("action") == "open":
                    self.logger.info("⏳ 창이 뜨기를 기다립니다 (2초)...")
                    time.sleep(2.0)
                else:
                    time.sleep(0.5)

            # 실행 전 데이터 최종 확인 로그
            self.logger.info(f"📡 송신 데이터 확인 -> 액션: {action}, 데이터: {params}")

            if self.web_handler.is_mine(target):
                result = self.web_handler.execute(action, target, params)
            else:
                result = self.os_handler.execute(action, target, params)
            # ... (뒷부분 동일) ...

            # 핸들러 배정 및 실행
            if self.web_handler.is_mine(target):
                self.logger.info(f"🌐 Web 핸들러에게 위임: {target} ({action})")
                result = self.web_handler.execute(action, target, params)
            else:
                self.logger.info(f"💻 OS 핸들러에게 위임: {target} ({action})")
                result = self.os_handler.execute(action, target, params)

            # 결과 화면 출력 (사용자 확인용)
            if result.get("status") == "success":
                mode_str = f" [{result.get('mode')}]" if result.get("mode") else ""
                print(f"🚀 실행 성공: {target} -> {action}{mode_str}")
            else:
                reason = result.get('reason')
                print(f"⚠️ 실행 실패: {target} (사유: {reason})")
                self.logger.error(f"실행 에러 ({target}): {reason}")