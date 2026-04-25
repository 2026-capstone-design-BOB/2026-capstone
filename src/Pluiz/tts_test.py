# test_tts.py
from engine.speaker import Speaker

def test():
    print("TTS 테스트를 시작합니다...")
    s = Speaker()
    s.speak("안녕하세요. 소리가 들린다면 정상입니다.")
    print("테스트 종료.")

if __name__ == "__main__":
    test()