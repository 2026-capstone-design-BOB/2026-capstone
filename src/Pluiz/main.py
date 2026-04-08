# main.py (수정 버전)
import json
import os
import datetime
from core.stt_engine import STTHandler
from core.llm_client import LLMHandler
from engine.os_controller import OSHandler
from engine.web_controller import WebHandler

os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class PluizAssistant:
    def __init__(self):
        print("--- Pluiz 시스템 초기화 중 ---")
        self.stt = STTHandler()
        self.llm = LLMHandler(model_name="llama3.1")
        self.os_ctrl = OSHandler()
        self.web_ctrl = WebHandler()
        print("--- 준비 완료! 명령을 내리세요. ---")

    def save_log(self, user_text, llm_response):
        """분석 결과를 logs 폴더에 저장합니다."""
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{now}]\n입력: {user_text}\n응답: {llm_response}\n{'-'*30}\n"
        with open("logs/llm_debug.log", "a", encoding="utf-8") as f:
            f.write(log_entry)

    def run(self):
        while True:
            user_text = self.stt.listen_and_transcribe()
            if not user_text or len(user_text) < 2:
                continue
            
            print(f"\n[나]: {user_text}")

            # 2. 분석 (LLM)
            response_json = self.llm.analyze_intent(user_text)
            
            # 분석 결과 즉시 출력 (디버깅용)
            print(f"== AI 분석 결과 ==\n{response_json}\n==================")
            self.save_log(user_text, response_json)

            if response_json is None:
                print("[Pluiz]: AI 엔진에 문제가 발생했습니다. Ollama 상태를 확인하세요.")
                continue

            try:
                # JSON 파싱 전 전처리 (AI가 딴소리 섞을 경우 대비)
                start_idx = response_json.find('{')
                end_idx = response_json.rfind('}') + 1
                if start_idx != -1 and end_idx != 0:
                    clean_json = response_json[start_idx:end_idx]
                    data = json.loads(clean_json)
                else:
                    raise ValueError("JSON 형식을 찾을 수 없습니다.")
                
                intent = data.get("intent")
                action = data.get("action")
                target = data.get("target")
                
                if intent == "apps" or intent == "file":
                    result = self.os_ctrl.execute(action, target)
                elif intent == "web":
                    result = self.web_ctrl.search(target)
                else:
                    result = "일반 대화 모드입니다."
                
                print(f"[Pluiz]: {result}")

            except Exception as e:
                print(f"[오류]: 파싱 실패. ({e})")

if __name__ == "__main__":
    assistant = PluizAssistant()
    assistant.run()