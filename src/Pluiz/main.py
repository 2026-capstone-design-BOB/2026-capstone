# main.py
import sys
import os
from core.controller import PluizController
from utils.logger import get_logger

def main():
    # 터미널 창 깨끗하게 정리 (Windows)
    os.system('cls' if os.name == 'nt' else 'clear')
    
    logger = get_logger("Main")
    print("=" * 50)
    print("       PLUIZ AI ASSISTANT - Development Mode")
    print("=" * 50)
    logger.info("시스템 초기화 중...")
    
    try:
        pluiz = PluizController()
        print("\n✨ Pluiz가 깨어났습니다!")
        print("📢 '메모장 열어줘' 같이 명령해 보세요.")
        print("🛑 종료하려면 Ctrl+C를 누르세요.\n")
        
        while True:
            print("\n[기다리는 중...] 👂 말씀하세요", end="\r")
            pluiz.process_voice_command()
            
    except KeyboardInterrupt:
        print("\n\n👋 Pluiz를 종료합니다. 수고하셨습니다 기획자님!")
        sys.exit(0)
    except Exception as e:
        logger.error(f"치명적 오류: {e}")
        print(f"\n❌ 에러 발생: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()