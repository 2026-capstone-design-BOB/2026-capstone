import ollama
import json
import os
import re
import config
from utils.logger import get_logger

try:
    import pyttsx3
except ImportError:
    pyttsx3 = None


class IntentInterpreter:
    def __init__(self):
        self.logger = get_logger("IntentInterpreter")
        self.model_name = config.LLM_MODEL_NAME
        self.config_path = os.path.join("assets", "apps_config.json")

        self.raw_config = self._load_raw_config()
        self.apps_data = self.raw_config.get("apps", [])
        self.tts_config = self.raw_config.get("tts", {})
        self.security_config = self.raw_config.get("security", {})

        self._alias_to_name = self._build_alias_map()

    def _load_raw_config(self):
        try:
            if not os.path.exists(self.config_path):
                return {}
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            self.logger.error(f"Config Load Error: {e}")
            return {}

    def _build_alias_map(self):
        alias_map = {}
        for app in self.apps_data:
            name = app.get("name", "").strip()
            if not name:
                continue
            alias_map[name.lower()] = name
            for alias in app.get("aliases", []):
                alias_map[str(alias).lower()] = name
        return alias_map

    def _init_tts(self):
        if not self.tts_config.get("enabled", False):
            return None
        if pyttsx3 is None:
            self.logger.warning("pyttsx3 is not installed. TTS disabled.")
            return None

        if self._tts_engine is None:
            try:
                self._tts_engine = pyttsx3.init()
                self._tts_engine.setProperty("rate", self.tts_config.get("rate", 185))
                self._tts_engine.setProperty("volume", self.tts_config.get("volume", 1.0))
            except Exception as e:
                self.logger.error(f"TTS Init Error: {e}")
                self._tts_engine = None
        return self._tts_engine

    def _speak(self, text):
        if not text or not self.tts_config.get("enabled", False):
            return

        if pyttsx3 is None:
            self.logger.warning("pyttsx3 is not installed. TTS disabled.")
            return

        try:
            engine = pyttsx3.init()
            engine.setProperty("rate", self.tts_config.get("rate", 185))
            engine.setProperty("volume", self.tts_config.get("volume", 1.0))
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as e:
            self.logger.error(f"TTS Speak Error: {e}")

    def _message(self, key, default_text):
        return self.tts_config.get("messages", {}).get(key, default_text)

    def _respond(self, status, message, commands=None, speak=False, extra=None):
        if speak:
            self._speak(message)

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
        valid_apps = ", ".join([app["name"] for app in self.apps_data])

        alias_guide = []
        for app in self.apps_data:
            aliases = ", ".join(app.get("aliases", []))
            alias_guide.append(f'- {app["name"]}: {aliases if aliases else "별칭 없음"}')
        alias_text = "\n".join(alias_guide)

        return f"""
당신은 사용자의 명령에서 핵심 키워드만 추출하는 도구입니다.
반드시 JSON 형식으로만 답변하세요.

[지원 앱 목록]
{valid_apps}

[앱 별칭 참고]
{alias_text}

[추출 규칙]
1. target: 반드시 위 목록에 있는 앱 이름 중 하나를 고르세요.
2. 사용자가 별칭(예: 크롬, 내모장, 계산)을 말하면 반드시 정식 앱 이름으로 변환하세요.
3. 앱이 전혀 명시되지 않았고 문맥상 추정이 어렵다면 target은 null 로 두세요.
4. is_new: 사용자가 "새로", "하나 더", "또" 라는 표현을 썼다면 true, 아니면 false.
5. text: 입력하라는 내용이 있다면 그 내용만 추출하세요. 없으면 null.
6. action:
   - 앱을 열거나 포커스하는 거라면 "open"
   - 내용을 쓰는 거라면 "input"
   - 닫는 거라면 "close"

[JSON 구조]
{{
  "target": "앱이름 또는 null",
  "action": "open" | "input" | "close",
  "is_new": boolean,
  "text": "내용 또는 null"
}}
"""

    def _is_unclear_text(self, user_text):
        if not user_text:
            return True

        cleaned = re.sub(r"\s+", " ", user_text).strip()
        if len(cleaned) < 2:
            return True

        vague_patterns = [
            r"^어+$", r"^음+$", r"^아+$", r"^저기+$", r"^그거+$", r"^이거+$"
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
            return self._respond("clarify", msg, commands=[], speak=True)

        # 2) 위험 요청 1차 차단
        unsafe, matched_keyword = self._is_unsafe_request(user_text)
        if unsafe:
            self.logger.warning(f"Blocked by interpreter: {matched_keyword}")
            msg = self._message("deny_unsafe", "이 요청은 보안상 실행할 수 없어요.")
            return self._respond(
                "denied",
                msg,
                commands=[],
                speak=True,
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
                msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
                return self._respond("clarify", msg, commands=[], speak=True)

            raw_data = json.loads(json_match.group(0))

            normalized_target = self._normalize_target(raw_data.get("target"), user_text)
            raw_data["target"] = normalized_target

            if not raw_data.get("target"):
                msg = self._message("need_target", "어떤 프로그램을 제어할지 다시 말씀해 주세요.")
                return self._respond("clarify", msg, commands=[], speak=True)

            return self._build_commands(raw_data)

        except Exception as e:
            self.logger.error(f"Analysis Error: {e}")
            msg = self._message("stt_unclear", "죄송해요. 잘 못 들었어요. 다시 말씀해 주세요.")
            return self._respond("clarify", msg, commands=[], speak=True)

    def _build_commands(self, raw_data):
        commands = []
        target = raw_data.get("target")
        action = raw_data.get("action", "open")
        is_new = raw_data.get("is_new", False)
        text = raw_data.get("text")

        # close 는 open 없이 바로 닫기
        if action == "close":
            commands.append({
                "intent": "system",
                "action": "close",
                "target": target,
                "params": {}
            })
            return {
                "status": "ok",
                "message": "닫기 명령을 준비했어요.",
                "is_complex": False,
                "commands": commands
            }

        # open / input 계열은 우선 창 확보
        commands.append({
            "intent": "system",
            "action": "open",
            "target": target,
            "params": {"force_new": is_new}
        })

        if action == "input" and text:
            commands.append({
                "intent": "system",
                "action": "input",
                "target": target,
                "params": {"text": text}
            })

        return {
            "status": "ok",
            "message": "명령 해석을 완료했어요.",
            "is_complex": len(commands) > 1,
            "commands": commands
        }