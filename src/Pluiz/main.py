# main.py

import sys
import os
import time  # 👈 안내 음성이 나올 시간을 벌어주기 위해 추가
from core.controller import PluizController
from utils.logger import get_logger


def main():
    os.system('cls' if os.name == 'nt' else 'clear')

    logger = get_logger("Main")
    print("=" * 50)
    print("        PLUIZ AI ASSISTANT - Test Mode")
    print("=" * 50)
    logger.info("시스템 초기화 중...")

    pluiz = None

    try:
        pluiz = PluizController()
        
        # --- [추가] 시작 안내 음성 ---
        # 시스템이 켜지자마자 사용자에게 인사를 건넵니다.
        start_message = "반가워요! 플루이즈 시스템이 가동되었습니다. 무엇을 도와드릴까요?"
        pluiz.speaker.speak(start_message)
        # ---------------------------

        print("\n✨ Pluiz가 테스트 모드로 깨어났습니다!")
        print("💡 [방법 1] 직접 명령을 타이핑하세요 (예: 메모장 최대화)")
        print("💡 [방법 2] 아무 내용 없이 Enter를 치면 음성 인식을 시작합니다.")
        print("🛑 종료하려면 'exit' 입력 또는 Ctrl+C를 누르세요.\n")

        while True:
            user_input = input("\n[명령 대기중] > ").strip()

            if user_input.lower() == "exit":
                # 종료할 때도 인사를 하면 좋겠죠?
                pluiz.speaker.speak("시스템을 종료합니다. 수고하셨습니다.")
                time.sleep(1.5) # 인사가 끝날 시간을 잠깐 줍니다.
                raise KeyboardInterrupt

            if not user_input:
                print("🎤 음성 인식 모드 실행 중...", end="\r")
                pluiz.process_voice_command()
            else:
                print(f"⌨️ 입력된 텍스트: {user_input}")
                pluiz.process_text_command(user_input, speak_response=True)

    except KeyboardInterrupt:
        print("\n\n👋 테스트를 종료합니다. 수고하셨습니다 기획자님!")
        if pluiz:
            try:
                pluiz.shutdown()
            except Exception:
                pass
        sys.exit(0)

    except Exception as e:
        logger.error("치명적 오류 발생: %s", str(e))
        logger.exception("치명적 오류 발생")
        print(f"\n❌ 에러 발생: {e}")
        if pluiz:
            try:
                pluiz.shutdown()
            except Exception:
                pass
        sys.exit(1)


if __name__ == "__main__":
    main()