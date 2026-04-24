# core/controller.py

import json
import time
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from engine.os_handler import OSHandler
from engine.web_handler import WebHandler
from engine.speaker import Speaker
from utils.logger import get_logger


class PluizController:
    def __init__(self):
        self.logger = get_logger("Controller")
        self.stt = STTEngine()
        self.interpreter = IntentInterpreter()
        self.os_handler = OSHandler()
        self.web_handler = WebHandler()
        self.speaker = Speaker()

    def process_voice_command(self):
        """음성 인식을 시작하고 분석된 명령 시퀀스를 실행합니다."""
        audio = self.stt.listen()
        user_text = self.stt.transcribe(audio)

        if not user_text:
            print("   [STT] 소리가 들리지 않습니다...")
            return {
                "status": "no_input",
                "message": "소리가 들리지 않습니다.",
            }

        print(f"\n🎤 인식된 목소리: {user_text}")
        return self.process_text_command(user_text, speak_response=True)

    def process_text_command(self, user_text: str, speak_response: bool = True):
        """텍스트 명령을 분석하고 실행합니다. type/voice 공용 처리."""
        if not user_text or not str(user_text).strip():
            return {
                "status": "empty",
                "message": "입력이 비어 있습니다.",
            }

        user_text = str(user_text).strip()
        print("🧠 AI 분석 중...", end="\r")
        self.logger.info(f"의도 분석 시작: {user_text}")

        # 1. Analyze
        intent_data = self.interpreter.analyze(user_text)
        self.logger.debug(f"🤖 LLM 분석 결과: {json.dumps(intent_data, ensure_ascii=False)}")

        if not intent_data:
            print("⚠️ 분석 결과가 비어 있습니다.")
            final_tts = "분석 결과가 비어 있습니다."
            if speak_response:
                self.logger.info(f"[BEFORE TTS] {final_tts}")
                self.speaker.speak(final_tts)
            return {
                "status": "empty_intent",
                "message": final_tts,
            }

        status = intent_data.get("status", "unknown")
        message = intent_data.get("message", "")
        commands = intent_data.get("commands", [])

        print("✅ 분석 완료!            ")
        print("-" * 30)
        print(f"📄 분석 결과 (JSON):\n{json.dumps(intent_data, indent=2, ensure_ascii=False)}")
        print("-" * 30)

        # 2. 비실행 응답 처리
        if status == "clarify":
            final_tts = message or "질문을 다시 확인해주세요."
            print(f"🗣 재질문: {final_tts}")
            self.logger.info(f"Clarify response: {final_tts}")
            if speak_response:
                self.logger.info(f"[BEFORE TTS] {final_tts}")
                self.speaker.speak(final_tts)
            return {
                "status": "clarify",
                "message": final_tts,
            }

        if status == "denied":
            final_tts = message or "이 요청은 수행할 수 없습니다."
            print(f"🛑 요청 거절: {final_tts}")
            self.logger.warning(f"Denied response: {final_tts}")
            if speak_response:
                self.logger.info(f"[BEFORE TTS] {final_tts}")
                self.speaker.speak(final_tts)
            return {
                "status": "denied",
                "message": final_tts,
            }

        # 3. 정상 분석이 아니면 종료
        if status != "ok":
            final_tts = message or "명령을 이해하지 못했어요."
            print(f"⚠️ 알 수 없는 분석 상태: {status}")
            self.logger.warning(f"Unknown intent status: {status}")
            if speak_response:
                self.logger.info(f"[BEFORE TTS] {final_tts}")
                self.speaker.speak(final_tts)
            return {
                "status": "unknown",
                "message": final_tts,
            }

        # 4. 실행할 명령이 없는 경우
        if not commands:
            final_tts = message or "처리할 수 있는 명령이 없습니다."
            print(f"💬 {final_tts}")
            self.logger.info("No commands to execute.")
            if speak_response:
                self.logger.info(f"[BEFORE TTS] {final_tts}")
                self.speaker.speak(final_tts)
            return {
                "status": "no_commands",
                "message": final_tts,
            }

        self.logger.info(f"총 {len(commands)}개의 명령 실행 시작")

        spoken_messages = []
        stopped_early = False
        overall_status = "success"

        # 5. commands 리스트 순차 실행
        for idx, cmd in enumerate(commands, start=1):
            action = cmd.get("action")
            target = cmd.get("target")
            params = cmd.get("params", {})

            if idx > 1:
                prev_cmd = commands[idx - 2]
                if prev_cmd.get("action") == "open":
                    self.logger.info("⏳ 창이 뜨기를 기다립니다 (2초)...")
                    time.sleep(2.0)
                else:
                    time.sleep(0.5)

            self.logger.info(f"[{idx}/{len(commands)}] 명령 실행 중: {action} on {target}")
            self.logger.info(f"📡 송신 데이터 확인 -> 액션: {action}, 데이터: {params}")

            # 핸들러 선택
            if target and self.web_handler.is_mine(target):
                self.logger.info(f"🌐 Web 핸들러에게 위임: {target} ({action})")
                result = self.web_handler.execute(action, target, params)
            else:
                self.logger.info(f"💻 OS 핸들러에게 위임: {target} ({action})")
                result = self.os_handler.execute(action, target, params)

            result_status = result.get("status")
            result_message = result.get("message", "")
            result_reason = result.get("reason", "unknown")
            mode_str = f" [{result.get('mode')}]" if result.get("mode") else ""

            if result_status == "success":
                print(f"🚀 실행 성공: {target} -> {action}{mode_str}")
                if result_message:
                    print(f"   ↳ {result_message}")
                    spoken_messages.append(result_message)
                else:
                    spoken_messages.append(f"{target} {action} 작업을 완료했어요.")

            elif result_status == "denied":
                print(f"🛑 실행 거절: {target} ({action})")
                print(f"   ↳ {result_message or result_reason}")
                self.logger.warning(f"Execution denied: {target} ({action}) - {result_reason}")
                spoken_messages.append(result_message or "이 요청은 실행할 수 없어요.")
                stopped_early = True
                overall_status = "denied"
                break

            else:
                print(f"⚠️ 실행 실패: {target} (사유: {result_reason})")
                if result_message:
                    print(f"   ↳ {result_message}")
                    spoken_messages.append(result_message)
                else:
                    spoken_messages.append("요청한 작업을 수행하지 못했어요.")

                self.logger.warning(f"Execution failed: {target} ({action}) - {result_reason}")
                stopped_early = True
                overall_status = "failed"
                break

            time.sleep(0.5)

        # 6. 최종 TTS는 한 번만
        if spoken_messages:
            final_tts = " ".join(spoken_messages)
        elif stopped_early:
            final_tts = "요청한 작업을 끝까지 수행하지 못했어요."
        else:
            final_tts = "작업을 완료했어요."

        if speak_response:
            self.logger.info(f"[BEFORE TTS] {final_tts}")
            time.sleep(0.5)
            self.speaker.speak(final_tts)

        return {
            "status": overall_status,
            "message": final_tts,
            "stopped_early": stopped_early,
            "spoken_messages": spoken_messages,
            "intent_data": intent_data,
        }

    def shutdown(self):
        try:
            self.speaker.stop()
            self.logger.info("Controller shutdown complete.")
        except Exception as e:
            self.logger.warning(f"Shutdown warning: {e}")