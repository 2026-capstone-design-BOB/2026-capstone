# core/controller.py
import json
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from engine.os_handler import OSHandler
from utils.logger import get_logger

class PluizController:
    def __init__(self):
        self.logger = get_logger("PluizController")
        self.stt = STTEngine()
        self.interpreter = IntentInterpreter()
        self.os_handler = OSHandler()

    def process_voice_command(self):
        # 1. Listen
        audio = self.stt.listen()
        user_text = self.stt.transcribe(audio)
        
        if not user_text:
            print("   [STT] 소리가 들리지 않습니다...")
            return

        # --- 실시간 터미널 출력 ---
        print(f"\n🎤 인식된 목소리: {user_text}")
        print("🧠 AI 분석 중...", end="\r")

        # 2. Analyze
        intent_data = self.interpreter.analyze(user_text)
        if not intent_data:
            print("❌ 분석에 실패했습니다.")
            return

        # --- 실시간 터미널 출력 ---
        print("✅ 분석 완료!           ")
        print("-" * 30)
        print(f"📄 분석 결과 (JSON):\n{json.dumps(intent_data, indent=2, ensure_ascii=False)}")
        print("-" * 30)

        # 3. Dispatch
        intent = intent_data.get("intent")
        action = intent_data.get("action")
        target = intent_data.get("target")

        # 인텐트 처리 범위를 조금 더 유연하게 확장
        if intent in ["system", "apps", "open", "close_window"]:
            success = self.os_handler.execute(
                action=action,
                target=target,
                params=intent_data.get("params", {})
            )
            if success:
                print(f"🚀 실행 성공: {target} ({action})")
            else:
                print(f"⚠️ 실행 실패: {target}")
        else:
            print(f"💬 대화 모드: {intent} 타입은 아직 학습 중입니다.")