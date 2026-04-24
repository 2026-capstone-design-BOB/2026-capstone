import threading
import queue
import time
import os
from gtts import gTTS
import pygame
from utils.logger import get_logger

class Speaker:
    def __init__(self):
        self.logger = get_logger("Speaker")
        self.enabled = True
        self._queue = queue.Queue()
        self._stop_event = threading.Event()
        
        # 임시 음성 파일 경로 (현재 폴더에 생성)
        self.temp_file = "tts_output.mp3"
        
        # 1. pygame mixer 초기화
        try:
            pygame.mixer.init()
        except Exception as e:
            self.logger.error(f"Pygame mixer init error: {e}")

        self._worker = threading.Thread(target=self._tts_worker, daemon=True)
        self._worker.start()

    def _tts_worker(self):
        self.logger.info("gTTS + Pygame Worker thread started.")

        while not self._stop_event.is_set():
            try:
                # 큐에서 텍스트 가져오기
                try:
                    text = self._queue.get(timeout=0.5)
                except queue.Empty:
                    continue

                if text is None:
                    break

                clean_text = str(text).strip()
                if not clean_text:
                    continue

                self.logger.info(f"TTS speak start (gTTS): {clean_text}")

                # 2. Google TTS로 음성 파일 생성 (.mp3)
                tts = gTTS(text=clean_text, lang='ko')
                tts.save(self.temp_file)

                # 3. pygame으로 재생
                pygame.mixer.music.load(self.temp_file)
                pygame.mixer.music.play()

                # 4. 재생이 끝날 때까지 대기 (가장 중요: 여기서 씹히는 걸 방지함)
                while pygame.mixer.music.get_busy():
                    time.sleep(0.1)

                # 5. 다음 파일 덮어쓰기를 위해 unload
                pygame.mixer.music.unload()
                
                # 가끔 파일 삭제 권한 문제가 생길 수 있으니 try로 감쌈
                try:
                    if os.path.exists(self.temp_file):
                        os.remove(self.temp_file)
                except:
                    pass

                self.logger.info("TTS speak done.")

            except Exception as e:
                self.logger.error(f"TTS worker error: {e}")
                time.sleep(0.5)

        self.logger.info("TTS Worker thread finished.")

    def speak(self, text: str):
        if not self.enabled or not text:
            return
        
        # 큐에 텍스트 넣기
        self._queue.put(str(text).strip())
        self.logger.info(f"TTS queued: {text}")

    def stop(self):
        self._stop_event.set()
        self._queue.put(None)