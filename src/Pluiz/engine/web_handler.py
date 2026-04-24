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
        if not choices or not target:
            return None, 0
        best_match, score = process.extractOne(target, choices)
        return (self.search_targets[best_match], score) if score >= 60 else (None, score)

    def _respond(self, status, reason=None, message=None, **kwargs):
        result = {"status": status}
        if reason:
            result["reason"] = reason
        if message:
            result["message"] = message
        result.update(kwargs)
        return result

    def is_mine(self, target: str):
        _, score = self._get_best_match(target)
        return score >= 60

    def execute(self, action: str, target: str, params: dict = None):
        params = params or {}
        self.logger.info(f"🌐 [WEB_START] 액션: {action} | 타겟: {target} | 데이터: {params}")

        web_info, score = self._get_best_match(target)

        # 기본 URL 설정
        url = web_info["path"] if web_info else params.get("url")

        # --- [1. 웹 닫기] ---
        if action in ["close", "web_close"]:
            driver = self.browser_mgr.get_driver()
            if not driver:
                return self._respond(
                    "fail",
                    reason="no_active_driver",
                    message="현재 열려 있는 브라우저가 없어요."
                )

            handles = driver.window_handles

            if len(handles) <= 1:
                self.browser_mgr.quit()
                return self._respond(
                    "success",
                    mode="all_quit",
                    message="브라우저를 종료했어요."
                )

            target_found = False
            for handle in handles:
                driver.switch_to.window(handle)
                current_url = driver.current_url.rstrip("/")

                if url and url.rstrip("/") in current_url:
                    driver.close()
                    target_found = True
                    break

            if not target_found:
                driver.close()

            remaining_handles = driver.window_handles
            if remaining_handles:
                driver.switch_to.window(remaining_handles[-1])
                return self._respond(
                    "success",
                    mode="tab_closed",
                    message=f"{target} 탭을 닫았어요." if target else "현재 탭을 닫았어요."
                )
            else:
                self.browser_mgr.quit()
                return self._respond(
                    "success",
                    mode="last_tab_quit",
                    message="마지막 브라우저 탭을 닫았어요."
                )

        # --- [2. 공통 드라이버 확보] ---
        driver = self.browser_mgr.get_driver(headless=params.get("headless", False))
        if not driver:
            return self._respond(
                "fail",
                reason="driver_init_failed",
                message="브라우저를 시작하지 못했어요."
            )

        try:
            # --- [3. 웹 페이지 열기] ---
            if action in ["open", "navigate"]:
                if not url:
                    return self._respond(
                        "fail",
                        reason="no_url",
                        message="열 웹 주소를 찾지 못했어요."
                    )

                target_handle = None
                for handle in driver.window_handles:
                    driver.switch_to.window(handle)
                    current_url = driver.current_url.rstrip("/")
                    if url.rstrip("/") in current_url:
                        target_handle = handle
                        break

                if target_handle and not params.get("is_new"):
                    self.logger.info(f"🌐 이미 {target} 페이지가 열려 있어 해당 탭으로 전환합니다.")
                    driver.switch_to.window(target_handle)
                    return self._respond(
                        "success",
                        url=driver.current_url,
                        mode="focus",
                        message=f"이미 열려 있는 {target} 탭으로 이동했어요."
                    )
                else:
                    self.logger.info("🌐 %s 페이지를 새 탭으로 엽니다: %s", target, url)
                    driver.execute_script(f"window.open('{url}', '_blank');")
                    driver.switch_to.window(driver.window_handles[-1])

                    return self._respond(
                        "success",
                        url=driver.current_url,
                        mode="open",
                        message=f"{target} 페이지를 열었어요." if target else "웹페이지를 열었어요."
                    )

            # --- [4. 웹 검색] ---
            elif action == "web_search":
                query = params.get("query") or params.get("text", "")
                if not query:
                    return self._respond(
                        "fail",
                        reason="no_query",
                        message="검색어를 다시 말씀해주세요."
                    )

                if web_info and "search_url" in web_info:
                    search_pattern = web_info["search_url"]
                else:
                    search_pattern = "https://www.google.com/search?q={query}"

                encoded_query = urllib.parse.quote(query)
                full_url = search_pattern.replace("{query}", encoded_query)

                self.logger.info("🌐 검색 실행 URL: %s", full_url)
                driver.execute_script(f"window.open('{full_url}', '_blank');")
                driver.switch_to.window(driver.window_handles[-1])

                return self._respond(
                    "success",
                    search_url=full_url,
                    mode="search",
                    message=f"{query} 검색 결과를 열었어요."
                )

            # --- [5. 창 제어] ---
            elif action in ["maximize", "restore"]:
                driver.maximize_window()
                return self._respond(
                    "success",
                    mode="maximize",
                    message="브라우저 창을 최대화했어요."
                )

            elif action == "minimize":
                driver.minimize_window()
                return self._respond(
                    "success",
                    mode="minimize",
                    message="브라우저 창을 최소화했어요."
                )

            # --- [6. 스크롤] ---
            elif action == "web_scroll":
                direction = params.get("direction", "down")
                px = 500 if direction == "down" else -500
                driver.execute_script(f"window.scrollBy(0, {px});")

                if direction == "down":
                    msg = "페이지를 아래로 스크롤했어요."
                else:
                    msg = "페이지를 위로 스크롤했어요."

                return self._respond(
                    "success",
                    mode="scroll",
                    direction=direction,
                    message=msg
                )

            return self._respond(
                "fail",
                reason=f"unknown_web_action:{action}",
                message="지원하지 않는 웹 명령이에요."
            )

        except Exception as e:
            self.logger.error(f"Web Action 실행 중 오류: {e}")
            return self._respond(
                "fail",
                reason=str(e),
                message="웹 작업을 수행하지 못했어요."
            )