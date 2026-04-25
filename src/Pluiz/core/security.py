# core/security.py
import json
import os

class SecurityManager:
    def __init__(self, config_path="assets/tts_security_config.json"):
        self.blocked_keywords = []
        self.blocked_apps = []
        
        if os.path.exists(config_path):
            with open(config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                # 이제 파일 전체가 보안 설정이므로 바로 가져옵니다.
                self.blocked_keywords = data.get("blocked_keywords", [])
                self.blocked_apps = data.get("blocked_apps", [])
            print(f"DEBUG: 보안 키워드 {len(self.blocked_keywords)}개 로드 완료.")
        else:
            print(f"ERROR: 보안 설정을 찾을 수 없습니다: {os.path.abspath(config_path)}")

    def is_safe(self, user_text):
        if not user_text:
            return True, ""
        
        # 공백 제거 없이 소문자로만 비교 (키워드 매칭 확률 높임)
        lowered_text = user_text.lower()
        
        for keyword in self.blocked_keywords:
            if keyword and keyword.lower() in lowered_text:
                return False, keyword
                
        return True, ""