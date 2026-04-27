# test_security.py
from core.security import SecurityManager

def test_security():
    sm = SecurityManager()
    
    print(f"현재 로드된 키워드 목록: {sm.blocked_keywords[:5]}...") # 리스트 확인용

    # 테스트 케이스
    tests = [
        "네이버 지도 열어줘",      # 정상
        "시스템32 삭제해",         # 위험 (system32)
        "C 드라이브 포맷해",       # 위험 (포맷)
        "regedit 실행해"           # 위험 (regedit)
    ]

    for t in tests:
        safe, kw = sm.is_safe(t)
        result = "✅ 통과" if safe else f"❌ 차단(키워드: {kw})"
        print(f"입력: '{t}' -> 결과: {result}")

if __name__ == "__main__":
    test_security()