# 공통 로깅 도구, 에러 발생 시 동일한 형식으로 에러 기록하기 위해 만든 파일, 개발용(배포x)
# utils/logger.py
import logging
import os
from datetime import datetime

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        # 로그 저장 폴더 생성
        log_path = "logs"
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        # 파일 핸들러 (날짜별 저장)
        file_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(os.path.join(log_path, file_name), encoding='utf-8')
        
        # 포맷 설정
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger