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

        # 2. Analyze
        intent_data = self.interpreter.analyze(user_text)
        if not intent_data:
            print("❌ 분석에 실패했습니다.            ")
            return

        status = intent_data.get("status", "unknown")
        message = intent_data.get("message", "")
        commands = intent_data.get("commands", [])

        # 분석 결과 출력
        print("✅ 분석 완료!            ")
        print("-" * 30)
        print(f"📄 분석 결과 (JSON):\n{json.dumps(intent_data, indent=2, ensure_ascii=False)}")
        print("-" * 30)

        # 3. 비실행 응답 처리 (재질문 / 거절)
        if status in ["clarify", "denied"]:
            if status == "clarify":
                print(f"🗣 재질문: {message}")
                self.logger.info(f"Clarify response: {message}")
            elif status == "denied":
                print(f"🛑 요청 거절: {message}")
                self.logger.warning(f"Denied response: {message}")
            return

        # 4. 정상 분석이 아니면 종료
        if status != "ok":
            print(f"⚠️ 알 수 없는 분석 상태: {status}")
            self.logger.warning(f"Unknown intent status: {status}")
            return

        # 5. 실행할 명령이 없는 경우
        if not commands:
            print("💬 처리할 수 있는 명령이 없습니다.")
            self.logger.info("No commands to execute.")
            return

        self.logger.info(f"총 {len(commands)}개의 명령 실행 시작")

        # 6. commands 리스트 순차 실행
        for idx, cmd in enumerate(commands, start=1):
            action = cmd.get("action")
            target = cmd.get("target")
            params = cmd.get("params", {})

            # 액션 전처리 (기존 로직 유지)
            if action in ["크기 줄여줘", "작게 해줘", "이전 크기", "normal"]:
                action = "restore"

            self.logger.info(f"[{idx}/{len(commands)}] 명령 실행 중: {action} on {target}")

            # 엔진(OSHandler)을 통한 실행
            result = self.os_handler.execute(action, target, params)

            result_status = result.get("status")
            result_message = result.get("message", "")
            result_reason = result.get("reason", "unknown")

            if result_status == "success":
                print(f"🚀 실행 성공: {target} ({action})")
                if result_message:
                    print(f"   ↳ {result_message}")

            elif result_status == "denied":
                print(f"🛑 실행 거절: {target} ({action})")
                print(f"   ↳ {result_message or result_reason}")
                self.logger.warning(f"Execution denied: {target} ({action}) - {result_reason}")
                break

            else:
                print(f"⚠️ 실행 실패: {target} (사유: {result_reason})")
                if result_message:
                    print(f"   ↳ {result_message}")
                self.logger.warning(f"Execution failed: {target} ({action}) - {result_reason}")

                # 실패 시 뒤 명령까지 진행하면 더 꼬일 수 있으니 중단
                break

            # 복합 명령 간 자연스러운 동작을 위한 미세 지연
            time.sleep(0.5)