# engine/speaker.py
# 역할: 오직 텍스트를 음성으로 변환하는 기능만 수행.
# TTS 로직은 브라우저(Web)나 OS 제어와 마찬가지로 일종의 **'출력 엔진'**입니다. 따라서 engine 디렉토리에 위치시키는 것이 가장 구조적으로 옳습니다.
import pyttsx3
import threading

class Speaker:
    def __init__(self):
        # 이제 __init__에서 엔진을 미리 만들지 않습니다.
        pass

    def speak(self, text):
        if not text: return
        
        # 별도 스레드에서 돌리지 않고 직접 실행하되, 
        # 매번 init -> say -> runAndWait -> stop 순으로 확실히 닫아줍니다.
        try:
            print(f"🔊 [TTS 실행 중] {text}")
            engine = pyttsx3.init()
            
            # 속도 및 볼륨 설정
            engine.setProperty('rate', 185)
            engine.setProperty('volume', 1.0)
            
            # 한국어 설정 (필요 시)
            voices = engine.getProperty('voices')
            for voice in voices:
                if "Korean" in voice.name or "KO" in voice.id:
                    engine.setProperty('voice', voice.id)
                    break
            
            engine.say(text)
            engine.runAndWait()
            
            # 💡 핵심: 사용 후 엔진 리소스를 확실히 해제
            engine.stop()
            del engine 
            
        except Exception as e:
            print(f"❌ TTS 엔진 충돌: {e}")

    def stop(self):
        # 일회용 방식에서는 특별히 할 일이 없지만 인터페이스 유지를 위해 둠
        pass