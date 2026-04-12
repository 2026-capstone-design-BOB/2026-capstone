# core/interpreter.py
import ollama
import json
import os
import re
import config
from utils.logger import get_logger

class IntentInterpreter:
    def __init__(self):
        self.logger = get_logger("IntentInterpreter")
        self.model_name = config.LLM_MODEL_NAME
        self.config_path = os.path.join("assets", "apps_config.json")
        self.apps_data = self._load_apps_config()

    def _load_apps_config(self):
        try:
            if not os.path.exists(self.config_path): return []
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f).get("apps", [])
        except: return []

    def _generate_system_prompt(self):
        # 앱 이름을 리스트업하여 LLM이 딴 이름을 지어내지 못하게 함
        valid_apps = ", ".join([app['name'] for app in self.apps_data])
        
        return f"""
당신은 사용자의 명령에서 핵심 키워드만 추출하는 도구입니다. 
반드시 다음 JSON 형식으로만 답변하세요.

[지원 앱 목록]
{valid_apps}

[추출 규칙]
1. target: 반드시 위 목록에 있는 앱 이름 중 하나를 고르세요. 없으면 가장 비슷한 것을 고르세요.
2. is_new: 사용자가 "새로", "하나 더", "또" 라는 표현을 썼다면 true, 아니면 false.
3. text: 입력하라는 내용이 있다면 그 내용만 추출하세요. 없으면 null.
4. action: 앱을 열거나 포커스하는 거라면 "open", 내용을 쓰는 거라면 "input", 닫는 거라면 "close".

[JSON 구조]
{{
  "target": "앱이름",
  "action": "open" | "input" | "close",
  "is_new": boolean,
  "text": "내용 또는 null"
}}
"""

    def analyze(self, user_text, history=None):
        system_prompt = self._generate_system_prompt()
        messages = [{'role': 'system', 'content': system_prompt}, {'role': 'user', 'content': user_text}]

        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            content = response['message']['content']
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                # LLM이 준 단순 데이터를 시스템용 명령 시퀀스로 변환하는 로직을 코드에서 처리
                raw_data = json.loads(json_match.group(0))
                return self._build_commands(raw_data)
            return None
        except Exception as e:
            self.logger.error(f"Analysis Error: {e}")
            return None

    def _build_commands(self, raw_data):
        """LLM의 단순 추출 데이터를 엄격한 실행 명령으로 변환 (Rule-base)"""
        commands = []
        target = raw_data.get("target", "메모장")
        
        # 1. 무조건 실행/포커스 명령을 첫 번째로 생성 (기본 규칙)
        commands.append({
            "intent": "system",
            "action": "open",
            "target": target,
            "params": {"force_new": raw_data.get("is_new", False)}
        })

        # 2. 텍스트가 있다면 입력 명령 추가
        if raw_data.get("text"):
            commands.append({
                "intent": "system",
                "action": "input",
                "target": target,
                "params": {"text": raw_data.get("text")}
            })
            
        return {"is_complex": len(commands) > 1, "commands": commands}