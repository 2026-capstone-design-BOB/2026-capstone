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
        url = web_info["path"] if web_info else params.get("url")
        
        # [핵심] 컨트롤러에서 넘어온 '새 창 의도' 확인
        force_new = params.get("force_new", False)

        # 1. 브라우저/페이지 확보 (Playwright 방식)
        page = self.browser_mgr.get_driver(
            headless=params.get("headless", False),
            force_new=force_new
        )
        if not page: return {"status": "fail", "reason": "driver_init_failed"}

        try:
            # --- [2. 종료 액션] ---
            if action in ["close", "web_close"]:
                self.browser_mgr.quit()
                return {"status": "success", "mode": "all_quit"}

            # --- [3. 웹 페이지 열기/이동] ---
            elif action in ["open", "navigate"]:
                if not url: return {"status": "fail", "reason": "no_url"}
                
                # 이미 해당 URL이 열려있는지 확인 (단, force_new가 아닐 때만)
                if not force_new and url.rstrip('/') in page.url.rstrip('/'):
                    self.logger.info(f"🌐 이미 {target} 페이지가 열려 있어 재사용합니다.")
                else:
                    self.logger.info(f"🌐 {target} 이동: {url}")
                    page.goto(url)
                return {"status": "success", "url": page.url}

            # --- [4. 웹 검색] ---
            elif action == "web_search":
                query = params.get("query") or params.get("text", "")
                if not query: return {"status": "fail", "reason": "no_query"}

                search_pattern = web_info["search_url"] if web_info and "search_url" in web_info \
                                 else "https://www.google.com/search?q={query}"
                
                full_url = search_pattern.replace("{query}", urllib.parse.quote(query))
                self.logger.info(f"🌐 검색 실행: {full_url}")
                page.goto(full_url)
                return {"status": "success", "search_url": full_url}

            # --- [5. 스마트 지도 검색 (매크로 강화 버전)] ---
            elif action == "map_search":
                departure = params.get("departure") 
                destination = params.get("destination")
                
                # 목적지가 없으면 즉시 실패 처리 (하드코딩 방지)
                if not destination: 
                    self.logger.error("❌ 목적지 데이터가 누락되었습니다.")
                    return {"status": "fail", "reason": "destination_missing"}

                # 출발지가 없으면 보통 '내 위치'를 의미하므로 '현재 위치'라고 명시
                if not departure:
                    departure = "현재 위치"

                self.logger.info(f"📍 지도 검색 실행: {departure} -> {destination}")
                
                # 1. wait_until을 "domcontentloaded"로 바꿉니다. (HTML 뼈대만 나오면 바로 실행)
                # 2. 혹시 모르니 timeout을 0(무제한)으로 주거나 넉넉히 줍니다.
                page.goto("https://map.naver.com/p/directions/", wait_until="domcontentloaded", timeout=60000)
                page.wait_for_timeout(2000) # 인터페이스 안정화 대기

                try:
                    # 2. 출발지 입력 창 찾기 및 클릭
                    # 신형 지도는 input_search 클래스를 공통으로 씁니다. nth(0)이 출발지입니다.
                    origin_input = page.locator(".input_search").nth(0)
                    origin_input.click()
                    page.wait_for_timeout(500)
                    
                    # 3. 기존 내용 지우고 한글자씩 입력 (네이버 필터링 우회)
                    page.keyboard.press("Control+A")
                    page.keyboard.press("Backspace")
                    page.keyboard.type(departure, delay=100) # 사람처럼 0.1초 간격 타이핑
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000)

                    # 4. 도착지 입력 창 찾기 및 클릭 (nth(1)이 도착지)
                    dest_input = page.locator(".input_search").nth(1)
                    dest_input.click()
                    page.wait_for_timeout(500)
                    
                    page.keyboard.type(destination, delay=100)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000)

                    # 5. 마지막 확인 사살 (엔터 한 번 더)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(1000) # 버튼 활성화 대기 시간 추가

                    # --- [수정된 클릭 로직] ---
                    # 클래스명이 중복되므로, '길찾기'라는 텍스트를 가진 버튼을 정확히 타겟팅합니다.
                    # .filter(has_text="길찾기")를 붙여서 '다시입력' 버튼과 차별화합니다.
                    search_btn = page.locator("button.btn_direction").filter(has_text="길찾기")
                    
                    if search_btn.count() > 0: # 버튼이 존재하는지 확인
                        self.logger.info("🖱️ '길찾기' 버튼을 정확히 찾아 클릭합니다.")
                        search_btn.first.click(force=True)
                    else:
                        # 최후의 보루: 텍스트로 찾기
                        self.logger.info("💻 텍스트 기반 버튼 클릭 시도")
                        page.get_by_role("button", name="길찾기").click(force=True)
                    # -------------------------

                    self.logger.info("✅ 사람처럼 입력 및 버튼 클릭 완료")
                except Exception as e:
                    self.logger.error(f"⚠️ 매크로 실행 중 오류: {e}")
                    return {"status": "fail", "reason": str(e)}

                return {"status": "success", "mode": "human_mimic_navigation"}

            # --- [6. 기타 제어] ---
            elif action == "web_scroll":
                direction = params.get("direction", "down")
                px = 500 if direction == "down" else -500
                page.evaluate(f"window.scrollBy(0, {px});")
                return {"status": "success", "mode": "scroll"}

            return {"status": "fail", "reason": f"unknown_web_action: {action}"}

        except Exception as e:
            self.logger.error(f"Web Action 실행 오류: {e}")
            return {"status": "fail", "reason": str(e)}