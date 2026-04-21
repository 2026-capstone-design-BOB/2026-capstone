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

    try:
        stt = STTEngine()
        interpreter = IntentInterpreter()
        logger.info("모듈 초기화 성공")
    except Exception as e:
        logger.error(f"초기화 실패: {e}")
        return

    print("\n[테스트] 아무 명령이나 말씀해 보세요... (예: 메모장 열어줘)")
    audio = stt.listen()
    user_text = stt.transcribe(audio)

    if not user_text:
        print("인식된 텍스트가 없습니다.")
        return

    print(f"인식 결과: {user_text}")
    print("AI 분석 중...")

    result = interpreter.analyze(user_text)

    if result:
        print("\n=== 최종 분석 결과 (JSON) ===")
        print(json.dumps(result, indent=4, ensure_ascii=False))

        required_top_fields = ["status", "message", "is_complex", "commands"]
        missing_top = [field for field in required_top_fields if field not in result]

        if missing_top:
            print(f"\n❌ 상위 규격 검증 실패: 누락된 필드 -> {missing_top}")
            return

        if result["status"] == "ok":
            commands = result.get("commands", [])
            if not isinstance(commands, list) or len(commands) == 0:
                print("\n❌ 명령 검증 실패: commands가 비어 있습니다.")
                return

            command_required_fields = ["intent", "action", "target", "params"]
            invalid_commands = []

            for i, cmd in enumerate(commands):
                missing_cmd = [field for field in command_required_fields if field not in cmd]
                if missing_cmd:
                    invalid_commands.append((i, missing_cmd))

            if not invalid_commands:
                print("\n✅ 규격 검증 통과: 상위 구조 및 commands 필드가 정상입니다.")
            else:
                print("\n❌ 명령 검증 실패:")
                for idx, missing in invalid_commands:
                    print(f" - commands[{idx}] 누락 필드: {missing}")

        elif result["status"] in ["clarify", "denied"]:
            print(f"\n✅ 비실행 응답 처리 정상: status = {result['status']}")
        else:
            print(f"\n⚠ 알 수 없는 status 값: {result['status']}")
    else:
        print("\n❌ 분석 실패: AI가 유효한 JSON을 반환하지 않았습니다.")

if __name__ == "__main__":
    run_core_test()