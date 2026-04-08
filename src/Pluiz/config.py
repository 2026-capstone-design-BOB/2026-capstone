# 모든 설정 값을 관리, 나중에 경로 바뀌어도 이 파일만 고치면 되도록
# config.py
import os

# AI 모델 설정
STT_MODEL_SIZE = "base"  # tiny, base, small, medium, large
LLM_MODEL_NAME = "llama3.1"

# 경로 설정
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_DIR = os.path.join(BASE_DIR, "logs")

# 음성 인식 설정
INPUT_DEVICE_INDEX = None  # 기본 마이크 사용
ENERGY_THRESHOLD = 1000    # 마이크 감도 (환경에 따라 조절)