import json
import os
import urllib.parse
from fuzzywuzzy import process
from engine.base import BaseController
from engine.web.browser_manager import BrowserManager
from utils.logger import get_logger

class WebHandler(BaseController):
    def __init__(self):
        super().__init__()
        self.logger = get_logger("WebHandler")
        self.browser_mgr = BrowserManager()
        self.config_path = os.path.join("assets", "webs_config.json")
        self.webs_data = self._load_config()
        self.search_targets = self._prepare_search_targets()

    def _load_config(self):
        try:
            if os.path.exists(self.config_path):
                with open(self.config_path, "r", encoding="utf-8") as f:
                    # JSON 구조 내 "apps" 리스트 추출
                    return json.load(f).get("apps", [])
            return []
        except Exception as e:
            self.logger.error(f"Web Config 로드 실패: {e}")
            return []

    def _prepare_search_targets(self):
        targets = {}
        for web in self.webs_data:
            targets[web["name"]] = web
            for alias in web.get("aliases", []):
                targets[alias] = web
        return targets

    def _get_best_match(self, target):
        choices = list(self.search_targets.keys())
        if not choices: return None, 0
        best_match, score = process.extractOne(target, choices)
        return (self.search_targets[best_match], score) if score >= 60 else (None, score)

    def is_mine(self, target: str):
        _, score = self._get_best_match(target)
        return score >= 60

    def execute(self, action: str, target: str, params: dict = None):
        params = params or {}
        web_info, _ = self._get_best_match(target)
        
        # 기본 URL 설정 (open/close 로직용)
        url = web_info["path"] if web_info else params.get("url")

        # --- [1. 스마트 브라우저/탭 종료 액션] ---
        if action in ["close", "web_close"]:
            driver = self.browser_mgr.get_driver()
            if not driver: 
                return {"status": "fail", "reason": "no_active_driver"}

            handles = driver.window_handles
            
            if len(handles) <= 1:
                self.browser_mgr.quit()
                return {"status": "success", "mode": "all_quit"}

            target_found = False
            for handle in handles:
                driver.switch_to.window(handle)
                if url and url.rstrip('/') in driver.current_url.rstrip('/'):
                    driver.close()
                    target_found = True
                    break
            
            if not target_found:
                driver.close()

            remaining_handles = driver.window_handles
            if remaining_handles:
                driver.switch_to.window(remaining_handles[-1])
                return {"status": "success", "mode": "tab_closed"}
            else:
                self.browser_mgr.quit()
                return {"status": "success", "mode": "last_tab_quit"}

        # --- [2. 공통 드라이버 확보] ---
        driver = self.browser_mgr.get_driver(headless=params.get("headless", False))
        if not driver: return {"status": "fail", "reason": "driver_init_failed"}

        try:
            # --- [3. 웹 페이지 열기] ---
            if action in ["open", "navigate"]:
                if not url: return {"status": "fail", "reason": "no_url"}
                
                target_handle = None
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    if url.rstrip('/') in driver.current_url.rstrip('/'):
                        target_handle = handle
                        break
                
                if target_handle and not params.get("is_new"):
                    self.logger.info(f"🌐 이미 {target} 페이지가 열려 있어 해당 탭으로 전환합니다.")
                    driver.switch_to.window(target_handle)
                else:
                    self.logger.info("🌐 %s 페이지를 새 탭으로 엽니다: %s", target, url)
                    driver.execute_script(f"window.open('{url}', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])
                
                return {"status": "success", "url": driver.current_url}
            
            # --- [4. 웹 검색 (JSON 설정 기반)] ---
            elif action == "web_search":
                # LLM이 분석한 query 또는 일반 input에서 들어온 text 모두 허용
                query = params.get("query") or params.get("text", "")
                if not query: return {"status": "fail", "reason": "no_query"}

                # 1단계: JSON에 정의된 search_url이 있는지 확인
                # 2단계: 없으면 구글을 기본 검색 엔진으로 사용 (Fallback)
                search_pattern = None
                if web_info and "search_url" in web_info:
                    search_pattern = web_info["search_url"]
                else:
                    # 기본 매칭이 안되거나 search_url이 없는 경우 구글 패턴 사용
                    search_pattern = "https://www.google.com/search?q={query}"

                # {query} 치환 및 URL 인코딩
                encoded_query = urllib.parse.quote(query)
                full_url = search_pattern.replace("{query}", encoded_query)
                self.logger.info("🌐 검색 실행 URL: %s", full_url)
                driver.execute_script(f"window.open('{full_url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])
                
                return {"status": "success", "search_url": full_url}

            # --- [5. 기타 제어 (창 크기, 스크롤)] ---
            elif action in ["maximize", "restore"]:
                driver.maximize_window()
                return {"status": "success", "mode": "maximize"}
            
            elif action == "minimize":
                driver.minimize_window()
                return {"status": "success", "mode": "minimize"}

            elif action == "web_scroll":
                direction = params.get("direction", "down")
                px = 500 if direction == "down" else -500
                driver.execute_script(f"window.scrollBy(0, {px});")
                return {"status": "success", "mode": "scroll"}
            
            return {"status": "fail", "reason": f"unknown_web_action: {action}"}
            
        except Exception as e:
            self.logger.error(f"Web Action 실행 중 오류: {e}")
            return {"status": "fail", "reason": str(e)}