import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from utils.logger import get_logger

class BrowserManager:
    def __init__(self):
        self.logger = get_logger("BrowserManager")
        self.driver = None

    def get_driver(self, headless=False):
        """브라우저 인스턴스를 반환하거나 새로 생성합니다."""
        if self.driver:
            try:
                # 브라우저가 아직 살아있는지 체크
                _ = self.driver.current_url
                return self.driver
            except Exception:
                self.logger.info("기존 브라우저가 닫혀있습니다. 새 세션을 시작합니다.")
                self.driver = None

        try:
            options = webdriver.ChromeOptions()
            if headless:
                options.add_argument("--headless")
            
            # OSHandler 제어와 겹치지 않도록 표준 해상도 설정
            options.add_argument("--window-size=1280,1024")
            options.add_experimental_option("detach", True)  # 스크립트 종료 후에도 브라우저 유지

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            return self.driver
        except Exception as e:
            self.logger.error(f"브라우저 실행 실패: {e}")
            return None

    def quit(self):
        if self.driver:
            self.driver.quit()
            self.driver = None