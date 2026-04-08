# core/interpreter.py
import ollama
import json
import re  # 정규표현식 추가
import config
from utils.logger import get_logger

class IntentInterpreter:
    def __init__(self):
        self.logger = get_logger("IntentInterpreter")
        self.model_name = config.LLM_MODEL_NAME

    def analyze(self, user_text, history=None):
        self.logger.info(f"의도 분석 시작: {user_text}")
        
        system_prompt = """
        당신은 AI 비서 'Pluiz'의 핵심 분석 모듈입니다.
        사용자의 명령을 분석하여 반드시 JSON 형식으로만 응답하세요.
        
        [필수 규칙]
        1. 결과에 아래 4개 키가 없으면 시스템이 붕괴됩니다: "intent", "action", "target", "params"
        2. 추가 데이터가 없더라도 "params": {} 를 반드시 포함하세요.
        3. 다른 부연 설명 없이 오직 JSON만 출력하세요.

        [출력 예시]
        {
            "intent": "system",
            "action": "open",
            "target": "메모장",
            "params": {}
        }
        """

        messages = [{'role': 'system', 'content': system_prompt}]
        if history:
            messages.extend(history)
        messages.append({'role': 'user', 'content': user_text})

        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            content = response['message']['content']
            self.logger.debug(f"LLM Raw Response: {content}")
            
            # 정규표현식을 사용하여 가장 바깥쪽 { } 내용을 추출 (수다 방지)
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(0)
                data = json.loads(json_str)
                
                # [방어 코드 추가] 필수 필드 누락 시 기본값 주입
                required = ["intent", "action", "target", "params"]
                for field in required:
                    if field not in data:
                        data[field] = {} if field == "params" else "unknown"
                return data
            
            else:
                self.logger.error(f"JSON 패턴을 찾을 수 없음: {content}")
                return None
                
        except Exception as e:
            self.logger.error(f"의도 분석 에러: {e}")
            # Ollama 서버 연결 문제인지 모델 문제인지 상세 로깅
            if "not found" in str(e):
                self.logger.error(f"모델 '{self.model_name}'이 설치되지 않았습니다. 'ollama pull {self.model_name}'을 실행하세요.")
            return None