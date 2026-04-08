# 음성 인식 모듈
# core/stt.py
import io
import os
import torch
import speech_recognition as sr
from faster_whisper import WhisperModel
from utils.logger import get_logger
import config

# 중복 라이브러리 충돌 방지
os.environ["KMP_DUPLICATE_LIB_OK"] = "TRUE"

class STTEngine:
    def __init__(self):
        self.logger = get_logger("STTEngine")
        device = "cuda" if torch.cuda.is_available() else "cpu"
        self.logger.info(f"STT 엔진 초기화 시작 (Device: {device})")
        
        # 모델 로드
        self.model = WhisperModel(
            config.STT_MODEL_SIZE, 
            device=device, 
            # VRAM이 부족하다면 int8_float16으로 양자화하여 메모리 사용량을 절반으로 줄입니다.
            compute_type="int8_float16" if device == "cuda" else "int8"
        )
        self.recognizer = sr.Recognizer()
        self.microphone = sr.Microphone()

    def listen(self):
        with self.microphone as source:
            self.logger.info("청취 시작...")
            self.recognizer.adjust_for_ambient_noise(source, duration=1)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=10)
                return audio
            except sr.WaitTimeoutError:
                return None

    def transcribe(self, audio):
        if audio is None: return ""
        
        try:
            audio_data = io.BytesIO(audio.get_wav_data())
            segments, _ = self.model.transcribe(audio_data, language="ko")
            text = "".join([segment.text for segment in segments]).strip()
            self.logger.info(f"인식 결과: {text}")
            return text
        except Exception as e:
            self.logger.error(f"STT 변환 에러: {e}")
            return ""