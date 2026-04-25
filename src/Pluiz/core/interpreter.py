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
        
        # OS 및 Web 설정 경로
        self.apps_config_path = os.path.join("assets", "apps_config.json")
        self.webs_config_path = os.path.join("assets", "webs_config.json")

    def _load_config_names(self, path):
        """설정 파일에서 이름들을 가져옵니다."""
        try:
            if not os.path.exists(path): return []
            with open(path, "r", encoding="utf-8") as f:
                apps = json.load(f).get("apps", [])
                return [app['name'] for app in apps]
        except: return []

    def _generate_system_prompt(self):
        apps = self._load_config_names(self.apps_config_path)
        webs = self._load_config_names(self.webs_config_path)
        valid_targets = ", ".join(apps + webs)
        
        return f"""
당신은 사용자의 명령을 JSON 명령 시퀀스로 변환하는 전문가입니다. 다른 설명 없이 JSON만 출력하세요.
대상 목록: {valid_targets}

[액션 및 파라미터 규칙]
1. "open": 앱 실행 또는 사이트 이동
   - 사용자가 "새로", "또", "하나 더", "새로운" 이라는 표현을 쓰면 반드시 params에 {{ "is_new": true }}를 포함하세요.
2. "input": 텍스트 입력 (params: {{ "text": "내용" }})
   - **텍스트 보존 원칙**: 사용자가 입력하라고 한 문구(인용구)를 토씨 하나 틀리지 말고 그대로 추출하세요.
   - 절대 요약하거나 말을 바꾸지 마세요. (예: '안녕' -> '고가세요' 금지)
3. "maximize", "minimize", "close": 창 조절 및 종료

[입력 추출 핵심 규칙]
- "~라고 써줘", "~ 입력해줘" 앞의 문구를 그대로 가져오세요.
- 예: "메모장 새로 열고 안녕 써줘" -> 'open'에 is_new: true 추가 후 'input' 생성.

[응답 형식 예시]
입력: "메모장 새로 열어줘"
출력:
{{
  "commands": [
    {{ "action": "open", "target": "메모장", "params": {{ "is_new": true }} }}
  ]
}}

입력: "메모장 열고 이제 오류 없었으면 좋겠다 써줘"
출력:
{{
  "commands": [
    {{ "action": "open", "target": "메모장", "params": {{}} }},
    {{ "action": "input", "target": "메모장", "params": {{ "text": "이제 오류 없었으면 좋겠다" }} }}
  ]
}}

[Web 검색 규칙]
- "X에서 Y 검색해줘" -> {{ "action": "web_search", "target": "X", "params": {{ "query": "Y" }} }}
- 특정 사이트 없으면 target은 "google"입니다.

[스마트 지도 검색 규칙]
- 지도 검색 시에는 오직 map_search 액션만 생성하세요
1. 경로 검색 액션: "A에서 B 가는 법", "A에서 B로 검색해줘" 등 경로 요청 시 반드시 아래 형식을 생성하세요.
   - action: "map_search", target: "naver_map"
   - params: {{ "departure": "A", "destination": "B" }}

2. **데이터 추출 원칙 (필독)**: 
   - 사용자가 말한 지명(A, B)을 절대 요약하거나 임의로 '현재 위치'로 바꾸지 마세요.
   - 예: "서울에서 강남역" -> departure: "서울", destination: "강남역" (O)
   - 예: "서울에서 강남역" -> departure: "현재 위치", destination: "강남역" (X)
   - 오직 사용자가 출발지를 **아예 언급하지 않았을 때만** (예: "강남역 어떻게 가?") departure를 "현재 위치"로 설정하세요.

3. **고유 명사 보존**: 
   - 사용자가 "서울"이라고만 했으면 "서울"을, "서울역"이라고 했으면 "서울역"을 그대로 추출하세요. 
   - "강남"과 "강남역"도 엄격히 구분하여 사용자가 말한 텍스트 그대로를 파라미터에 넣으세요.

[TTS 템플릿 연동 규칙 - 중요]
- 모든 액션은 params에 템플릿에 필요한 데이터를 포함해야 합니다.
- "X에서 Y 검색해줘" -> action: "web_search", target: "X", params: {{ "query": "Y" }}
- "A에서 B 가는법" -> action: "map_search", target: "naver_map", params: {{ "departure": "A", "destination": "B" }}
- 출발지 언급 없으면 departure: "현재 위치"

반드시 JSON 형식으로만 답변하세요.
"""

    def analyze(self, user_text):
        """이 메서드가 반드시 IntentInterpreter 클래스 안에 있어야 합니다!"""
        system_prompt = self._generate_system_prompt()
        messages = [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_text}
        ]

        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            content = response['message']['content']
            
            # JSON만 추출하는 견고한 정규식
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                raw_data = json.loads(json_match.group(0))
                # ❗ 중요: 이제 _build_commands가 리스트를 그대로 반환합니다.
                return self._build_commands(raw_data)
            
            self.logger.warning("응답에서 JSON을 찾을 수 없습니다.")
            return None
        except Exception as e:
            self.logger.error(f"Analysis Error: {e}")
            return None

    def _build_commands(self, raw_data):
        """LLM이 생성한 commands 리스트를 검증하고 반환합니다."""
        commands = raw_data.get("commands", [])
        
        # 하드코딩된 'open' 로직을 제거하고 LLM의 결정을 존중합니다.
        for cmd in commands:
            if "params" not in cmd:
                cmd["params"] = {}
        
        return {
            "is_complex": len(commands) > 1,
            "commands": commands
        }