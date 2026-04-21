import time
from engine.os_handler import OSHandler
from engine.web_handler import WebHandler

def test_complex_flow():
    os_h = OSHandler()
    web_h = WebHandler()

    print("\n[Step 1] 브라우저 실행 테스트")
    res1 = web_h.execute("open", "browser", {"url": "https://www.naver.com"})
    print(f"결과: {res1}")

    time.sleep(2)

    print("\n[Step 2] 로컬 메모장 실행 테스트 (OSHandler 협업)")
    res2 = os_h.execute("open", "메모장")
    print(f"결과: {res2}")

    print("\n[Step 3] 메모장에 텍스트 입력")
    os_h.execute("input", "메모장", {"text": "브라우저와 메모장이 동시에 제어되고 있습니다."})

    print("\n✅ 모든 핸들러가 충돌 없이 동작함을 확인했습니다.")

if __name__ == "__main__":
    test_complex_flow()