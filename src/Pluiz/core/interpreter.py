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

        self.apps_config_path = os.path.join("assets", "apps_config.json")
        self.webs_config_path = os.path.join("assets", "webs_config.json")

        self.apps_raw = self._load_raw_config(self.apps_config_path)
        self.webs_raw = self._load_raw_config(self.webs_config_path)

        self.apps_data = self.apps_raw.get("apps", [])
        self.webs_data = self.webs_raw.get("apps", [])

        self.tts_config = self.apps_raw.get("tts", {})
        self.security_config = self.apps_raw.get("security", {})

        self._alias_to_name = self._build_alias_map()

    def _load_raw_config(self, path):
        try:
            if not os.path.exists(path):
                return {}
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config Load Error ({path}): {e}")
            return {}

    def _build_alias_map(self):
        alias_map = {}

        for app in self.apps_data:
            name = app.get("name", "").strip()
            if not name:
                continue
            alias_map[name.lower()] = name
            for alias in app.get("aliases", []):
                alias_map[str(alias).strip().lower()] = name

        for web in self.webs_data:
            name = web.get("name", "").strip()
            if not name:
                continue
            alias_map[name.lower()] = name
            for alias in web.get("aliases", []):
                alias_map[str(alias).strip().lower()] = name

        return alias_map

    def _message(self, key, default_text):
        return self.tts_config.get("messages", {}).get(key, default_text)

    def _respond(self, status, message, commands=None, extra=None):
        result = {
            "status": status,
            "message": message,
            "is_complex": len(commands or []) > 1,
            "commands": commands or []
        }
        if extra:
            result.update(extra)
        return result

    def _generate_system_prompt(self):
        apps = [app.get("name", "") for app in self.apps_data if app.get("name")]
        webs = [web.get("name", "") for web in self.webs_data if web.get("name")]
        valid_targets = ", ".join(apps + webs)

        alias_guide = []
        for item in self.apps_data + self.webs_data:
            name = item.get("name", "")
            aliases = ", ".join(item.get("aliases", []))
            alias_guide.append(f'- {name}: {aliases if aliases else "별칭 없음"}')
        alias_text = "\n".join(alias_guide)

        return f"""
당신은 사용자의 명령을 JSON 명령 시퀀스로 변환하는 전문가입니다.
반드시 다른 설명 없이 JSON만 출력하세요.

[대상 목록]
{valid_targets}

[대상 별칭 참고]
{alias_text}

[액션 및 파라미터 규칙]
1. "open": 앱 실행 또는 사이트 열기
   - 사용자가 "새로", "또", "하나 더", "새로운" 이라는 표현을 쓰면 반드시 params에 {{ "is_new": true }}를 포함하세요.
2. "input": 텍스트 입력
   - params 형식: {{ "text": "내용" }}
   - 사용자가 입력하라고 한 문구를 절대 바꾸지 말고 그대로 넣으세요.
3. "close": 앱/탭/창 닫기
4. "maximize", "minimize", "restore": 창 제어
5. "web_search": 웹 검색
   - 형식: {{ "action": "web_search", "target": "사이트이름", "params": {{ "query": "검색어" }} }}

[중요 규칙]
1. target은 반드시 대상 목록 중 하나의 정식 이름으로 넣으세요.
2. 사용자가 별칭으로 말하면 반드시 정식 이름으로 변환하세요.
3. 앱/웹 대상이 불명확하면 target은 null로 두세요.
4. 입력 명령과 열기 명령이 함께 있으면 commands 배열에 순서대로 모두 넣으세요.
5. "~에서 ~ 검색해줘" 형태는 web_search를 우선 사용하세요.
6. 특정 검색 사이트가 없으면 target은 "google"로 하세요.

[응답 형식 예시]
입력: "메모장 새로 열어줘"
출력:
{{
  "commands": [
    {{ "action": "open", "target": "메모장", "params": {{ "is_new": true }} }}
  ]
}}

입력: "메모장 열고 안녕이라고 써줘"
출력:
{{
  "commands": [
    {{ "action": "open", "target": "메모장", "params": {{}} }},
    {{ "action": "input", "target": "메모장", "params": {{ "text": "안녕" }} }}
  ]
}}

입력: "유튜브에서 아이유 검색해줘"
출력:
{{
  "commands": [
    {{ "action": "web_search", "target": "유튜브", "params": {{ "query": "아이유" }} }}
  ]
}}
"""

    def _is_unclear_text(self, user_text):
        if not user_text:
            return True

        cleaned = re.sub(r"\s+", " ", user_text).strip()
        if len(cleaned) < 2:
            return True

        vague_patterns = [
            r"^어+$",
            r"^음+$",
            r"^아+$",
            r"^저기+$",
            r"^그거+$",
            r"^이거+$"
        ]
        return any(re.match(p, cleaned) for p in vague_patterns)

    def _is_unsafe_request(self, user_text):
        lowered = (user_text or "").lower()
        blocked_keywords = self.security_config.get("blocked_keywords", [])

        for keyword in blocked_keywords:
            if str(keyword).lower() in lowered:
                return True, keyword

        return False, None

    def _normalize_target(self, target, user_text=""):
        if target:
            normalized = self._alias_to_name.get(str(target).strip().lower())
            if normalized:
                return normalized

        lowered = (user_text or "").lower()
        for alias, name in self._alias_to_name.items():
            if alias in lowered:
                return name

        return None

    def analyze(self, user_text, history=None):
        # 1) STT 불명확 → 즉시 재질문
        if self._is_unclear_text(user_text):
            msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
            return self._respond("clarify", msg, commands=[])

        # 2) 위험 요청 1차 차단
        unsafe, matched_keyword = self._is_unsafe_request(user_text)
        if unsafe:
            self.logger.warning(f"Blocked by interpreter: {matched_keyword}")
            msg = self._message("deny_unsafe", "이 요청은 보안상 실행할 수 없어요.")
            return self._respond(
                "denied",
                msg,
                commands=[],
                extra={"blocked_keyword": matched_keyword}
            )

        system_prompt = self._generate_system_prompt()
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_text}
        ]

        try:
            response = ollama.chat(model=self.model_name, messages=messages)
            content = response["message"]["content"]

            json_match = re.search(r"\{.*\}", content, re.DOTALL)
            if not json_match:
                self.logger.warning("응답에서 JSON을 찾을 수 없습니다.")
                msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
                return self._respond("clarify", msg, commands=[])

            raw_data = json.loads(json_match.group(0))
            return self._build_commands(raw_data, user_text)

        except Exception as e:
            self.logger.error(f"Analysis Error: {e}")
            msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
            return self._respond("clarify", msg, commands=[])

    def _build_commands(self, raw_data, user_text=""):
        commands = raw_data.get("commands", [])

        if not isinstance(commands, list):
            msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
            return self._respond("clarify", msg, commands=[])

        normalized_commands = []

        for cmd in commands:
            action = cmd.get("action")
            target = self._normalize_target(cmd.get("target"), user_text)
            params = cmd.get("params", {})

            if params is None or not isinstance(params, dict):
                params = {}

            if not target:
                msg = self._message("need_target", "어떤 프로그램이나 웹을 제어할지 다시 말씀해 주세요.")
                return self._respond("clarify", msg, commands=[])

            normalized_commands.append({
                "intent": "system",
                "action": action,
                "target": target,
                "params": params
            })

        if not normalized_commands:
            msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
            return self._respond("clarify", msg, commands=[])

        return self._respond(
            "ok",
            "명령 해석을 완료했어요.",
            commands=normalized_commands
        )