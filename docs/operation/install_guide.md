# 설치 및 환경 설정 가이드

## 1. 개요
본 문서는 '금융거래조회서 키인 자동화 시스템'을 로컬 환경 또는 운영 서버에 구축하기 위한 설치 및 설정 방법을 안내합니다. 본 프로젝트는 의존성 관리를 위해 **uv**를 사용하며, 웹 UI 구성을 위해 **Streamlit**을, 광학 문자 인식을 위해 **PaddleOCR**을 핵심 엔진으로 사용합니다.

## 2. 시스템 요구사항
시스템을 실행하기 위해 사전에 아래의 환경이 준비되어야 합니다.
* **OS:** Windows 10 이상, macOS (Apple Silicon 포함), 또는 Linux (Ubuntu 20.04+ 권장)
* **Python:** 3.9 이상 3.11 이하 (의존성 패키지 호환성 권장)
* **Package Manager:** uv
* **Container Runtime (macOS 한정):** Docker Desktop 또는 **OrbStack**(강력 권장)

## 3. 설치 프로세스

### 3.1. 저장소 클론 및 패키지 설치
프로젝트 소스 코드를 로컬 환경으로 가져온 후, `pyproject.toml`과 `uv.lock`을 기반으로 의존성 패키지를 설치합니다.

```bash
# 1. 프로젝트 저장소 클론 (경로는 실제 환경에 맞게 수정)
git clone https://github.com/dongtan-91-dong-welfare-center/audit_inquiry_automation.git
cd audit_inquiry_automation

# 2. uv를 통한 가상환경 생성 및 의존성 패키지 설치
uv sync
```
*※ `uv sync` 실행 시 `pdfplumber`, `opencv-python`, `paddleocr`, `streamlit` 등의 핵심 라이브러리가 자동으로 설치됩니다.*

### 3.2. 시스템 의존성 라이브러리 설치 (OS별)
본 프로젝트는 운영체제에 따른 라이브러리 충돌(OpenMP)을 방지하기 위해 OS별 맞춤형 OCR 실행 구조를 가집니다. 본인의 개발 환경에 맞는 설정을 진행해 주세요.

* **Windows/Linux 환경:** 
  Windows 및 일반 Linux 환경에서는 별도의 설정 없이 로컬 엔진이 정상 작동합니다.
  (참고) Linux 환경에서 이미지 처리에러 발생 시 아래 시스템 라이브러리 설치 필요:

  `sudo apt-get update && sudo apt-get install libgl1 libglib2.0-0`

* **macOS (Apple Silicon) 환경:**
  Apple M칩 환경에서는 패키지 충돌 방지를 위해 OCR 엔진을 별도의 가벼운 Docker 컨테이너로 띄워 통신합니다.
  1) OCR API 서버 빌드 및 실행
  프로젝트 루트 디렉토리에서 아래 명령어를 실행하여 서버를 백그라운드에 띄웁니다. (OrbStack 또는 Docker Desktop 실행 필수)

  ``` bash
  docker build -t ocr-engine-api .
  docker run -d -p 8000:8000 --name ocr-server ocr-engine-api
  ```
  
  2) 환경 변수 설정 (.env)
  프로젝트 루트에 .env 파일을 생성하고 아래 값을 입력합니다. 이 설정이 켜져 있어야 메인 애플리케이션이 Docker 서버로 OCR을 요청합니다.

  ``` plaintext
  USE_REMOTE_OCR=True
  ```

### 3.3. Tesseract 엔진 설치
현재 시스템의 메인 OCR 엔진은 `PaddleOCR` (ADR-006)이지만, 테스트 환경이나 과거 버전(ADR-005)의 호환성을 위해 `Tesseract`를 사용해야 하는 경우, 시스템 환경변수에 엔진을 등록해야 합니다.
* 상세 설치 방법은 프로젝트 내의 `docs/achieve/tesseract_install_guide.md` 문서를 참조하시기 바랍니다.

## 4. 시스템 실행 방법

모든 설치가 완료되면, Streamlit 프레임워크를 통해 메인 파이프라인(`main.py`)을 실행합니다.

```bash
# 가상환경 내에서 Streamlit 앱 실행
uv run streamlit run main.py
```

* 실행 후 터미널에 출력되는 `Local URL` (일반적으로 `http://localhost:8501`)을 브라우저에 입력하여 메인 페이지(SCR-01)에 접속합니다.

## 5. 구동 전 확인 사항 및 제약 조건 (System Constraints)
원활한 시스템 운영을 위해 `Functions.csv (FUNC-001)`에 정의된 입력 제약 사항을 사전에 확인하시기 바랍니다.

* **최대 파일 용량:** 개별 PDF 파일의 크기는 **최대 300MB**를 초과할 수 없습니다.
* **동시 처리 제한:** 한 번에 업로드하여 처리할 수 있는 파일은 **최대 10개**로 제한됩니다.
* **보안 문서:** 암호가 설정되어 보호된 PDF 파일은 시스템에서 전처리 및 OCR 작업이 불가능하므로, 사전에 암호를 해제한 후 업로드해야 합니다.
* **최소 페이지 수:** 금융거래조회서의 기본 규격 특성상, 페이지 수가 3장 미만인 PDF는 시스템 오류 방지를 위해 입력이 제한됩니다.