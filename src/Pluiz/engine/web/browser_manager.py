import os
from playwright.sync_api import sync_playwright
from utils.logger import get_logger

class BrowserManager:
    def __init__(self):
        self.logger = get_logger("BrowserManager")
        self.playwright = None
        self.browser = None
        self.context = None
        self.page = None

    def get_driver(self, headless=False, force_new=False):
        """
        브라우저 인스턴스를 반환합니다.
        :param force_new: '새로 열어줘' 등의 키워드가 있을 경우 True로 전달
        """
        
        # 1. '새로 열기' 요청이 들어왔을 경우 기존 것 정리
        if force_new and self.page:
            self.logger.info("🆕 사용자의 요청으로 새로운 브라우저 세션을 시작합니다.")
            self.quit()

        # 2. 기존 브라우저가 살아있는지 체크 (재사용 로직)
        if self.page:
            try:
                # 브라우저가 닫혔는지 확인하는 가장 가벼운 방법
                if not self.page.is_closed():
                    self.logger.info("♻️ 기존 브라우저 세션을 재사용합니다.")
                    return self.page
            except Exception:
                self.logger.info("🌐 기존 세션이 유효하지 않습니다. 다시 초기화합니다.")
                self.quit()

        # 3. 브라우저 새로 띄우기
        try:
            self.logger.info("🌐 Playwright 브라우저 엔진을 가동합니다...")
            if not self.playwright:
                self.playwright = sync_playwright().start()

            # 보안 정책에 훨씬 강한 방식
            self.browser = self.playwright.chromium.launch(
                headless=headless,
                slow_mo=500, #모든 동작 사이에 0.5초 여유
                args=["--window-size=1280,1024"]
            )
            
            # 독립된 컨텍스트(세션) 생성
            self.context = self.browser.new_context(
                viewport={'width': 1280, 'height': 1024}
            )
            
            self.page = self.context.new_page()
            self.logger.info("✅ 새 브라우저 창이 준비되었습니다.")
            return self.page

        except Exception as e:
            self.logger.error(f"❌ 브라우저 실행 실패: {e}")
            return None

    def quit(self):
        """리소스 완전히 해제"""
        try:
            if self.page: self.page.close()
            if self.context: self.context.close()
            if self.browser: self.browser.close()
            if self.playwright: self.playwright.stop()
        except:
            pass
        finally:
            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None