# # 공통 로깅 도구, 에러 발생 시 동일한 형식으로 에러 기록하기 위해 만든 파일, 개발용(배포x)
import logging
import os
import sys
import functools # 추가
from datetime import datetime

def get_logger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    if not logger.handlers:
        log_path = "logs"
        if not os.path.exists(log_path):
            os.makedirs(log_path)

        # 포맷 설정 (기존과 동일)
        detailed_format = logging.Formatter(
            '%(asctime)s | [%(levelname)s] | %(name)s | %(filename)s:%(lineno)d\n > %(message)s \n'
        )

        file_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.FileHandler(os.path.join(log_path, file_name), encoding='utf-8')
        file_handler.setFormatter(detailed_format)
        logger.addHandler(file_handler)

        stream_handler = logging.StreamHandler(sys.stdout)
        stream_handler.setFormatter(detailed_format)
        logger.addHandler(stream_handler)

    return logger

# --- 추가된 추적 데코레이터 ---
def trace_action(logger):
    """함수의 입력값과 결과값을 자동으로 로깅합니다."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # args[0]은 self(OSHandler), args[1]은 action, args[2]는 target, args[3]은 params
            action = args[1] if len(args) > 1 else None
            target = args[2] if len(args) > 2 else None
            params = args[3] if len(args) > 3 else kwargs.get('params', {})

            logger.info(f"🚀 [EXECUTE] Action: {action} | Target: {target}")
            if params:
                logger.debug(f"📦 [PARAMS] 상세 데이터: {params}")

            try:
                result = func(*args, **kwargs)
                logger.info(f"✅ [RESULT] 실행 성공: {result}")
                return result
            except Exception as e:
                logger.error(f"❌ [ERROR] 실행 중 오류 발생: {str(e)}", exc_info=True)
                return {"status": "error", "reason": str(e)}
        return wrapper
    return decorator
# # utils/logger.py
# import logging
# import os
# import sys
# from datetime import datetime

# def get_logger(name):
#     logger = logging.getLogger(name)
#     logger.setLevel(logging.DEBUG)

#     if not logger.handlers:
#         # 1. 로그 폴더 생성
#         log_path = "logs"
#         if not os.path.exists(log_path):
#             os.makedirs(log_path)

#         # ---------------------------------------------------------
#         # [설정] 로그 출력 포맷 (여기서 정보량을 조절합니다)
#         # %(asctime)s: 시간 / %(name)s: 로거이름 / %(levelname)s: 등급
#         # %(filename)s: 파일명 / %(lineno)d: 라인번호 / %(funcName)s: 함수명
#         # ---------------------------------------------------------
#         detailed_format = logging.Formatter(
#             '%(asctime)s | [%(levelname)s] | %(name)s | %(filename)s:%(lineno)d (%(funcName)s) \n > %(message)s \n'
#         )

#         # --- 기능 1: 파일 저장 (날짜별) ---
#         file_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
#         file_handler = logging.FileHandler(os.path.join(log_path, file_name), encoding='utf-8')
#         file_handler.setFormatter(detailed_format)
#         logger.addHandler(file_handler) # [끄고 싶으면 이 줄을 주석처리]

#         # --- 기능 2: 콘솔(터미널) 즉시 출력 ---
#         stream_handler = logging.StreamHandler(sys.stdout)
#         stream_handler.setFormatter(detailed_format)
#         logger.addHandler(stream_handler) # [끄고 싶으면 이 줄을 주석처리]

#     return logger

# --- [팁] 에러 발생 시 전체 경로(Traceback)를 찍는 법 ---
# 로직 코드(WebHandler 등)에서 에러를 잡을 때 아래처럼 쓰세요:
# try:
#     ...로직...
# except Exception:
#     logger.exception("상세 에러 발생!") 
#     # .error 대신 .exception을 쓰면 어디서 터졌는지 Traceback을 다 찍어줍니다.


# import logging
# import os
# from datetime import datetime

# def get_logger(name):
#     logger = logging.getLogger(name)
#     logger.setLevel(logging.DEBUG)

#     if not logger.handlers:
#         # 로그 저장 폴더 생성
#         log_path = "logs"
#         if not os.path.exists(log_path):
#             os.makedirs(log_path)

#         # 파일 핸들러 (날짜별 저장)
#         file_name = f"{datetime.now().strftime('%Y-%m-%d')}.log"
#         file_handler = logging.FileHandler(os.path.join(log_path, file_name), encoding='utf-8')
        
#         # 포맷 설정
#         formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
#         file_handler.setFormatter(formatter)
#         logger.addHandler(file_handler)

#     return logger