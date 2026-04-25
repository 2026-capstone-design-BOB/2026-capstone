# core/stt.py, core/interpreter.py 테스트용 임시 파일
# 실제 마이크 입력을 받아 LLM이 약속된 JSON 규격을 정확히 생성하는지 확인한다. (음성인식&Json파일 생성 가능, 실제 OS 제어는 안 됨, 한 번 실행이 정상이다)
# test_core.py
from core.stt import STTEngine
from core.interpreter import IntentInterpreter
from utils.logger import get_logger
import json

def run_core_test():
    logger = get_logger("CoreTest")
    logger.info("=== Core Layer 통합 테스트 시작 ===")

    # 1. 모듈 초기화
    try:
        stt = STTEngine()
        interpreter = IntentInterpreter()
        logger.info("모듈 초기화 성공")
    except Exception as e:
        logger.error(f"초기화 실패: {e}")
        return

    # 2. 음성 인식 단계
    print("\n[테스트] 아무 명령이나 말씀해 보세요... (예: 메모장 열어줘)")
    audio = stt.listen()
    user_text = stt.transcribe(audio)

    if not user_text:
        print("인식된 텍스트가 없습니다.")
        return

    print(f"인식 결과: {user_text}")

    # 3. 의도 분석 단계
    print("AI 분석 중...")
    result = interpreter.analyze(user_text)

    # 4. 규격 검증 (Interface Check)
    if result:
        print("\n=== 최종 분석 결과 (JSON) ===")
        print(json.dumps(result, indent=4, ensure_ascii=False))
        
        # 필수 필드 체크
        required_fields = ["intent", "action", "target", "params"]
        missing = [field for field in required_fields if field not in result]
        
        if not missing:
            print("\n✅ 규격 검증 통과: 모든 필수 필드가 포함되어 있습니다.")
        else:
            print(f"\n❌ 규격 검증 실패: 누락된 필드 -> {missing}")
    else:
        print("\n❌ 분석 실패: AI가 유효한 JSON을 반환하지 않았습니다.")

if __name__ == "__main__":
    run_core_test()