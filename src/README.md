# 🚀 Pluiz (플루이즈)

**On-Device형 AI 지능형 음성 비서**
> 단순 명령 실행을 넘어, 사용자의 맥락을 이해하고 OS를 직접 제어하는 3단계 지능형 PC 제어 시스템입니다.

---

## 🛠 1. 기술 스택 및 환경 구성 (Tech Stack)

### 💻 사전 설치 필요 (System Requirements)
프로젝트 실행 전, 다음 프로그램들이 시스템에 반드시 설치되어 있어야 합니다.

* **[Ollama](https://ollama.com/)**: 로컬 LLM 구동 엔진
    * 설치 후 터미널에서 실행: `ollama pull llama3`
* **FFmpeg**: 음성 데이터 처리용 (STT 필수)
    * 설치 후 시스템 환경 변수(Path) 등록 확인 필수
* **NVIDIA CUDA Toolkit**: GPU 가속을 통한 빠른 응답 속도 확보
    * 본인의 그래픽카드 버전에 맞는 CUDA 설치 권장 (v11.8 권장)

### 🐍 파이썬 가상환경 세팅
```bash
# 1. 가상환경 생성 (Python 3.10 권장)
conda create -n pluiz python=3.10 -y
conda activate pluiz

# 2. PyTorch 설치 (GPU 가속용)
conda install pytorch torchvision torchaudio pytorch-cuda=11.8 -c pytorch -c nvidia -y

# 3. 라이브러리 일괄 설치
pip install -r requirements.txt
```

---

## ⚙️ 2. 환경 변수 설정 (Environment Variables)

보안 및 설정 관리를 위해 프로젝트 루트 폴더에 `.env` 파일을 생성하고 아래 내용을 입력해 주세요. (해당 파일은 `.gitignore`에 의해 GitHub에 업로드되지 않습니다.)

```env
# LLM 설정 (Ollama에서 다운로드한 모델명)
LLM_MODEL_NAME=llama3

# STT 설정 (tiny, base, small, medium, large-v3 중 선택)
STT_MODEL_SIZE=base
```

---

## 🌿 3. 협업 가이드 (Git Branch Strategy)

우리 프로젝트는 효율적인 관리를 위해 **5단계 브랜치 구조**를 사용합니다.

| 브랜치 이름 | 역할 | 권한 |
| :--- | :--- | :--- |
| `main` | **최종 성역**. 교수님 제출용 완성본 | 직접 수정 절대 금지 |
| `develop` | **공동 작업실**. 모든 기능이 합쳐지는 곳 | PR을 통해서만 업데이트 |
| `feature/이름` | **개인 작업실**. 각 팀원의 전용 공간 | 자유로운 작업 및 Push |

### 🔄 데일리 작업 루틴
1.  **내 브랜치에서 작업**: `git push origin feature/본인이름`
2.  **병합 요청**: GitHub 사이트에서 **Pull Request(PR)** 생성
    * `base: develop` ← `compare: feature/본인이름`
3.  **검토 후 승인**: 팀원 확인 후 `Merge`

> ⚠️ **주의사항**: `main` 브랜치에 직접 Push는 절대 금지입니다. 파일명을 `보고서_최종_1.docx`처럼 바꾸지 마세요. Git이 이력을 관리하므로 파일명은 고정합니다.

---

## 🏃 4. 실행 방법 (Usage)

실행 전 반드시 **Ollama 서비스가 구동 중인지 확인**하세요.

```bash
# 가상환경 활성화 확인
conda activate pluiz

# 메인 스크립트 실행
python main.py
```

---

## ❓ 예외 상황 해결 (Troubleshooting)

### 💥 충돌(Conflict)이 발생했어요!
누군가 먼저 `develop`을 업데이트했을 때 발생합니다.
1.  `git checkout develop` -> `git pull origin develop` (최신본 가져오기)
2.  `git checkout feature/내이름` -> `git merge develop` (내 브랜치에 합치기)
3.  에러 난 파일 수정 후 다시 `add`, `commit`, `push` 진행

### ⏪ 실수를 되돌리고 싶어요!
이미 Push한 내역을 삭제하거나 수정하고 싶을 때는 혼자 해결하려다 꼬일 수 있으니 **반드시 팀장에게 먼저 문의**하세요!

---

### 💡 추가 정보
* **STT**: `faster-whisper` 기반 실시간 음성 인식
* **Control**: `PyAutoGUI`, `pywinauto`를 통한 OS 제어
* **UI**: `PyQt6` 기반 인터페이스

---
