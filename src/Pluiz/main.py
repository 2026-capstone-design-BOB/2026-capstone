# main.py
import sys
import os
from core.controller import PluizController
from utils.logger import get_logger

def main():
    # 터미널 창 깨끗하게 정리
    os.system('cls' if os.name == 'nt' else 'clear')
    
    logger = get_logger("Main")
    print("=" * 50)
    print("       PLUIZ AI ASSISTANT - Demo Mode")
    print("=" * 50)
    logger.info("시스템 초기화 중...")
    
    try:
        # 컨트롤러 초기화
        pluiz = PluizController()
        print("\n✨ Pluiz가 데모 모드로 깨어났습니다!")
        print("📢 별도의 입력 없이 바로 음성으로 명령하세요.")
        print("🛑 종료하려면 Ctrl+C를 누르거나 '종료해줘'라고 말씀하세요.\n")
        
        while True:
            # 텍스트 입력 대기(input) 없이 바로 음성 인식 루프 진입
            print("\n[기다리는 중...] 👂 말씀하세요", end="\r")
            
            # 음성 인식 -> 분석 -> 실행 -> TTS 피드백까지 한 번에 처리
            pluiz.process_voice_command()

    except KeyboardInterrupt:
        # Ctrl+C 종료 시 인사
        if 'pluiz' in locals():
            pluiz.speaker.speak("데모를 종료합니다. 수고하셨습니다.")
        print("\n\n👋 Pluiz를 종료합니다. 수고하셨습니다!")
        sys.exit(0)
        
    except Exception as e:
        # 에러 발생 시 로그 기록 및 종료
        logger.error(f"치명적 오류 발생: {e}")
        print(f"\n❌ 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# # ---------------------- 개발용, type + voice 둘 다 가능 모드 ----------------------

# import sys
# import os
# from core.controller import PluizController
# from utils.logger import get_logger

# def main():
#     # 터미널 창 깨끗하게 정리
#     os.system('cls' if os.name == 'nt' else 'clear')
    
#     logger = get_logger("Main")
#     print("=" * 50)
#     print("       PLUIZ AI ASSISTANT - Test Mode")
#     print("=" * 50)
#     logger.info("시스템 초기화 중...")
    
#     try:
#         pluiz = PluizController()
#         print("\n✨ Pluiz가 테스트 모드로 깨어났습니다!")
#         print("💡 [방법 1] 직접 명령을 타이핑하세요 (예: 메모장 최대화)")
#         print("💡 [방법 2] 아무 내용 없이 Enter를 치면 음성 인식을 시작합니다.")
#         print("🛑 종료하려면 'exit' 입력 또는 Ctrl+C를 누르세요.\n")
        

#         while True:
#             user_input = input("\n[명령 대기중] > ").strip()
            
#             if user_input.lower() == 'exit':
#                 raise KeyboardInterrupt
            
#             if not user_input:
#                 # 1. 음성 인식 모드 (이미 내부에서 TTS/보안 처리됨)
#                 print("🎤 음성 인식 모드 실행 중...", end="\r")
#                 pluiz.process_voice_command()
#             else:
#                 # 2. 텍스트 입력 모드
#                 print(f"⌨️ 입력된 텍스트: {user_input}")
                
#                 # [수정 핵심] 일일이 루프 돌리지 말고, Controller의 통합 함수 하나만 호출!
#                 # 이 함수 안에서 보안 검사 -> 분석 -> 실행 -> TTS가 순차적으로 일어납니다.
#                 pluiz.process_text_command(user_input)

#     except KeyboardInterrupt:
#         # 종료 시 인사 멘트 추가하면 기분 좋겠죠?
#         if 'pluiz' in locals():
#             pluiz.speaker.speak("테스트를 종료합니다. 수고하셨습니다.")
#         print("\n\n👋 테스트를 종료합니다. 수고하셨습니다 기획자님!")
#         sys.exit(0)
#     except Exception as e:
#         logger.error("치명적 오류 발생: %s", str(e))
#         logger.exception("치명적 오류 상세 정보")
#         print(f"\n❌ 에러 발생: {e}")
#         sys.exit(1)

# if __name__ == "__main__":
#     main()