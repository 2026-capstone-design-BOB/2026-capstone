# 모든 컨트롤러(메모장, 카톡 등)의 부모가 될 추상 클래스
# engine/base.py
from abc import ABC, abstractmethod
from utils.logger import get_logger

class BaseController(ABC):
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
    def execute(self, action: str, target: str, params: dict = None):
        """
        모든 엔진은 이 메서드를 통해 명령을 실행해야 합니다.
        """
        pass