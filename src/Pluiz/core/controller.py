import json
import time
import os
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from core.security import SecurityManager  # 👈 신규 모듈
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

        # 초기화 직후 환영 인사 (필요 시)
        # self.speaker.speak(self.tts_msgs.get("welcome", "안녕하세요!"))
        
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
                    return json.load(f) # .get() 쓰지 말고 전체 리턴
            return {}
        except Exception as e:
            self.logger.error(f"TTS 설정 로드 실패: {e}")
            return {}

    def process_voice_command(self):
        """음성 명령 처리 프로세스"""
        # 1. 청취 및 인식
        audio = self.stt.listen()
        user_text = self.stt.transcribe(audio)
        
        if not user_text:
            msg = self.tts_msgs.get("stt_unclear", "잘 듣지 못했어요.")
            self.speaker.speak(msg)
            return
            
        # 2. 텍스트 명령 프로세스로 위임
        print(f"\n🎤 인식된 목소리: {user_text}")
        return self.process_text_command(user_text)

    def process_text_command(self, user_text: str):
        """텍스트 명령 분석 및 실행 (보안/해석/실행/TTS 통합)"""
        if not user_text.strip(): return

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
        
        # 새 창/새로 열기 의도 감지 (질문자님 기존 로직)
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

            # 새 창 의도 주입
            if force_new_window:
                params["force_new"] = True

            # 실행 전 딜레이 (명령 간 간격)
            if i > 0:
                delay = 2.0 if commands[i-1].get("action") == "open" else 0.5
                time.sleep(delay)

            # 핸들러 배정 및 실행
            if self.web_handler.is_mine(target):
                self.logger.info(f"🌐 Web 위임: {target}")
                result = self.web_handler.execute(action, target, params)
            else:
                self.logger.info(f"💻 OS 위임: {target}")
                result = self.os_handler.execute(action, target, params)

            # 결과 처리
            # --- [결과 처리 및 TTS 문장 생성] ---
            if result.get("status") == "success":
                mode_str = f" [{result.get('mode')}]" if result.get("mode") else ""
                print(f"🚀 실행 성공: {target} -> {action}{mode_str}")
                
                # 1순위: 핸들러가 준 메시지
                if result.get("message"):
                    spoken_responses.append(result["message"])
                
                # 2순위: 템플릿 엔진 (더 안전한 버전)
                elif action in self.tts_templates:
                    msg = self.tts_templates[action]
                    
                    # 안전한 치환 데이터 준비
                    # 템플릿에 {target}, {query} 등이 있으면 실제 값으로 교체합니다.
                    msg = msg.replace("{target}", str(target))
                    msg = msg.replace("{query}", str(params.get("query", "")))
                    msg = msg.replace("{departure}", str(params.get("departure", "현재 위치")))
                    msg = msg.replace("{destination}", str(params.get("destination", "")))
                    msg = msg.replace("{text}", str(params.get("text", "")))
                    
                    spoken_responses.append(msg)
                else:
                    # 템플릿이 아예 없는 경우
                    spoken_responses.append(self.tts_msgs.get("action_done", "완료했습니다."))
            else:
                overall_success = False
                reason = result.get('reason', 'unknown')
                print(f"⚠️ 실행 실패: {target} (사유: {reason})")
                break # 하나라도 실패하면 체인 중단 (팀원의 Chaining 의도 반영)

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
        