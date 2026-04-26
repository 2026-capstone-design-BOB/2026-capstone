import json
import time
import os
import sys  # 종료를 위해 추가
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from core.security import SecurityManager
from engine.os_handler import OSHandler
from engine.web_handler import WebHandler
from engine.speaker import Speaker
from utils.logger import get_logger

class PluizController:
    def __init__(self):
        self.logger = get_logger("Controller")
        
        # 1. 엔진 및 모듈 초기화
        self.stt = STTEngine()
        self.interpreter = IntentInterpreter()
        self.os_handler = OSHandler()
        self.web_handler = WebHandler()
        self.speaker = Speaker()
        self.security = SecurityManager("assets/tts_security_config.json")

        # 2. TTS 멘트 로드 (assets/tts_config.json)
        self.tts_config_path = "assets/tts_config.json"
        self.tts_data = self._load_full_config()
        self.tts_msgs = self.tts_data.get("status_messages", {})
        self.tts_templates = self.tts_data.get("action_templates", {})

    def _load_full_config(self):
        """TTS 설정 파일의 전체 구조를 로드"""
        try:
            if os.path.exists(self.tts_config_path):
                with open(self.tts_config_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            return {}
        except Exception as e:
            self.logger.error(f"TTS 설정 로드 실패: {e}")
            return {}

    def process_voice_command(self):
        """음성 명령 처리 프로세스"""
        audio = self.stt.listen()
        user_text = self.stt.transcribe(audio)
        
        if not user_text:
            msg = self.tts_msgs.get("stt_unclear", "잘 듣지 못했어요.")
            self.speaker.speak(msg)
            return
            
        print(f"\n🎤 인식된 목소리: {user_text}")
        return self.process_text_command(user_text)

    def process_text_command(self, user_text: str):
        """텍스트 명령 분석 및 실행 (보안/해석/실행/TTS 통합)"""
        if not user_text.strip(): return

        # ==========================================================
        # [수정 핵심] 음성 종료 기능을 '최상단'으로 이동
        # AI(의도 분석)가 "이해 못했다"고 말하기 전에 먼저 가로챕니다.
        # ==========================================================
        exit_keywords = ["꺼줘", "종료해줘", "그만해", "잘 가", "종료"]
        if any(keyword in user_text for keyword in exit_keywords):
            print("\n👋 음성 명령으로 시스템을 종료합니다.")
            self.speaker.speak("알겠습니다. 플루이즈 서비스를 종료합니다. 이용해 주셔서 감사합니다.")
            
            # 인사가 끝날 때까지 대기 후 안전하게 종료
            time.sleep(2.5) 
            self.shutdown()
            sys.exit(0)
        # ==========================================================

        # --- [STEP 1: 보안 검사] ---
        is_safe, keyword = self.security.is_safe(user_text)
        if not is_safe:
            msg = self.tts_msgs.get("deny_unsafe", "보안상 실행할 수 없는 명령입니다.")
            self.logger.warning(f"🛑 보안 차단됨: {keyword}")
            self.speaker.speak(msg)
            return {"status": "denied", "message": msg}

        # --- [STEP 2: 의도 분석] ---
        self.logger.info(f"의도 분석 시작: {user_text}")
        intent_data = self.interpreter.analyze(user_text)
        
        if not intent_data or not intent_data.get("commands"):
            msg = self.tts_msgs.get("stt_unclear", "명령을 이해하지 못했어요.")
            self.speaker.speak(msg)
            return {"status": "fail", "message": "unknown_intent"}

        commands = intent_data.get("commands", [])
        
        # 새 창/새로 열기 의도 감지
        force_new_window = any(keyword in user_text for keyword in ["새로", "새 창", "새로운"])
        if force_new_window:
            self.logger.info("🆕 '새 창' 의도 감지됨")

        # --- [STEP 3: 순차 실행 및 결과 수집] ---
        spoken_responses = []
        overall_success = True

        for i, cmd in enumerate(commands):
            action = cmd.get("action")
            target = cmd.get("target")
            params = cmd.get("params", {})

            if force_new_window:
                params["force_new"] = True

            if i > 0:
                delay = 2.0 if commands[i-1].get("action") == "open" else 0.5
                time.sleep(delay)

            if self.web_handler.is_mine(target):
                self.logger.info(f"🌐 Web 위임: {target}")
                result = self.web_handler.execute(action, target, params)
            else:
                self.logger.info(f"💻 OS 위임: {target}")
                result = self.os_handler.execute(action, target, params)

            if result.get("status") == "success":
                mode_str = f" [{result.get('mode')}]" if result.get("mode") else ""
                print(f"🚀 실행 성공: {target} -> {action}{mode_str}")
                
                if result.get("message"):
                    spoken_responses.append(result["message"])
                elif action in self.tts_templates:
                    msg = self.tts_templates[action]
                    msg = msg.replace("{target}", str(target))
                    msg = msg.replace("{query}", str(params.get("query", "")))
                    msg = msg.replace("{departure}", str(params.get("departure", "현재 위치")))
                    msg = msg.replace("{destination}", str(params.get("destination", "")))
                    msg = msg.replace("{text}", str(params.get("text", "")))
                    spoken_responses.append(msg)
                else:
                    spoken_responses.append(self.tts_msgs.get("action_done", "완료했습니다."))
            else:
                overall_success = False
                reason = result.get('reason', 'unknown')
                print(f"⚠️ 실행 실패: {target} (사유: {reason})")
                break

        # --- [STEP 4: 최종 TTS 통합 피드백] ---
        if overall_success:
            final_msg = " ".join(spoken_responses) if spoken_responses else self.tts_msgs.get("action_done", "완료했습니다.")
        else:
            final_msg = self.tts_msgs.get("action_failed", "작업을 완료하지 못했어요.")
        
        print(f"DEBUG: 최종 전달될 메시지: '{final_msg}'")
        self.speaker.speak(final_msg)
        return {"status": "done", "messages": spoken_responses}

    def shutdown(self):
        """시스템 종료 전 자원 정리"""
        self.speaker.stop()
        self.logger.info("시스템이 안전하게 종료되었습니다.")