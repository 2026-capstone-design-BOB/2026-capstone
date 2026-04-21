# ---------------------- 개발용, type + voice 둘 다 가능 모드 ----------------------

import sys
import os
from core.controller import PluizController
from utils.logger import get_logger

def main():
    # 터미널 창 깨끗하게 정리 (Windows)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    logger = get_logger("Main")
    print("=" * 50)
    print("       PLUIZ AI ASSISTANT - Test Mode")
    print("=" * 50)
    logger.info("시스템 초기화 중...")
    
    try:
        pluiz = PluizController()
        print("\n✨ Pluiz가 테스트 모드로 깨어났습니다!")
        print("💡 [방법 1] 직접 명령을 타이핑하세요 (예: 메모장 최대화)")
        print("💡 [방법 2] 아무 내용 없이 Enter를 치면 음성 인식을 시작합니다.")
        print("🛑 종료하려면 'exit' 입력 또는 Ctrl+C를 누르세요.\n")
        
        while True:
            # 사용자로부터 직접 입력 받기
            user_input = input("\n[명령 대기중] > ").strip()
            
            if user_input.lower() == 'exit':
                raise KeyboardInterrupt
            
            if not user_input:
                # 입력을 안 하고 Enter만 치면 기존 음성 인식 실행
                print("🎤 음성 인식 모드 실행 중...", end="\r")
                pluiz.process_voice_command()
            else:
                # 직접 입력한 텍스트로 로직 검증 (STT 생략)
                print(f"⌨️ 입력된 텍스트: {user_input}")
                intent_data = pluiz.interpreter.analyze(user_input)
                
                if not intent_data:
                    print("⚠️ 해석 실패: LLM 응답을 확인하세요.")
                    continue

                commands = intent_data.get("commands", [])
                for cmd in commands:
                    action = cmd.get("action")
                    target = cmd.get("target")
                    params = cmd.get("params", {})

                    if pluiz.web_handler.is_mine(target):
                        pluiz.logger.info(f"🌐 Web 위임: {target} ({action})")
                        result = pluiz.web_handler.execute(action, target, params)
                    else:
                        pluiz.logger.info(f"💻 OS 위임: {target} ({action})")
                        result = pluiz.os_handler.execute(action, target, params)

                    if result.get("status") == "success":
                        mode = f" [{result.get('mode')}]" if result.get('mode') else ""
                        print(f"🚀 실행 성공: {target} -> {action}{mode}")
                    else:
                        print(f"⚠️ 실행 실패: {target} (사유: {result.get('reason')})")
            
    except KeyboardInterrupt:
        print("\n\n👋 테스트를 종료합니다. 수고하셨습니다 기획자님!")
        sys.exit(0)
    except Exception as e:
        logger.error("치명적 오류 발생: %s", str(e))
        logger.exception("치명적 오류 발생")
        print(f"\n❌ 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

# ----------------------- 음성만 ----------------------
# # main.py
# import sys
# import os
# from core.controller import PluizController
# from utils.logger import get_logger

# def main():
#     # 터미널 창 깨끗하게 정리 (Windows)
#     os.system('cls' if os.name == 'nt' else 'clear')
    
#     logger = get_logger("Main")
#     print("=" * 50)
#     print("       PLUIZ AI ASSISTANT - Development Mode")
#     print("=" * 50)
#     logger.info("시스템 초기화 중...")
    
#     try:
#         pluiz = PluizController()
#         print("\n✨ Pluiz가 깨어났습니다!")
#         print("📢 '메모장 열어줘' 같이 명령해 보세요.")
#         print("🛑 종료하려면 Ctrl+C를 누르세요.\n")
        
#         while True:
#             print("\n[기다리는 중...] 👂 말씀하세요", end="\r")
#             pluiz.process_voice_command()
            
#     except KeyboardInterrupt:
#         print("\n\n👋 Pluiz를 종료합니다. 수고하셨습니다 기획자님!")
#         sys.exit(0)
#     except Exception as e:
#         logger.error(f"치명적 오류: {e}")
#         print(f"\n❌ 에러 발생: {e}")
#         sys.exit(1)

# if __name__ == "__main__":
#     main()