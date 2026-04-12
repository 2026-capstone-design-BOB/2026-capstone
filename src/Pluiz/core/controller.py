# core/controller.py
import json
import time
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from engine.os_handler import OSHandler
from utils.logger import get_logger

class PluizController:
    def __init__(self):
        self.logger = get_logger("Controller")
        self.stt = STTEngine()
        self.interpreter = IntentInterpreter()
        self.os_handler = OSHandler()

    def process_voice_command(self):
        """음성 인식을 시작하고 분석된 명령 시퀀스를 실행합니다."""
        # 1. Listen & Transcribe
        audio = self.stt.listen()
        user_text = self.stt.transcribe(audio)
        
        if not user_text:
            print("   [STT] 소리가 들리지 않습니다...")
            return

        # 실시간 터미널 출력
        print(f"\n🎤 인식된 목소리: {user_text}")
        print("🧠 AI 분석 중...", end="\r")

        # 2. Analyze (복합 명령 구조의 JSON 반환)
        intent_data = self.interpreter.analyze(user_text)
        if not intent_data:
            print("❌ 분석에 실패했습니다.            ")
            return

        # 분석 결과 출력
        print("✅ 분석 완료!            ")
        print("-" * 30)
        print(f"📄 분석 결과 (JSON):\n{json.dumps(intent_data, indent=2, ensure_ascii=False)}")
        print("-" * 30)

        # 3. Dispatch (commands 리스트 순차 실행)
        commands = intent_data.get("commands", [])
        if not commands:
            print("💬 처리할 수 있는 명령이 없습니다.")
            return

        self.logger.info(f"총 {len(commands)}개의 명령 실행 시작")

        for cmd in commands:
            action = cmd.get("action")
            target = cmd.get("target")
            params = cmd.get("params", {})

            # 액션 전처리 (기존 로직 유지)
            if action in ["크기 줄여줘", "작게 해줘", "이전 크기", "normal"]:
                action = "restore"

            self.logger.info(f"명령 실행 중: {action} on {target}")
            
            # 엔진(OSHandler)을 통한 실행
            result = self.os_handler.execute(action, target, params)
            
            if result.get("status") == "success":
                print(f"🚀 실행 성공: {target} ({action})")
            else:
                reason = result.get("reason", "unknown")
                print(f"⚠️ 실행 실패: {target} (사유: {reason})")
                # 실패 시 다음 명령을 계속할지 중단할지 여기서 결정 가능
            
            # 복합 명령 간의 자연스러운 동작을 위한 미세 지연
            time.sleep(0.5)