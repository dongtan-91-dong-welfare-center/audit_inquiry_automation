# 설치 및 환경 설정 가이드

## 1. 개요
본 문서는 '금융거래조회서 키인 자동화 시스템'을 로컬 환경 또는 운영 서버에 구축하기 위한 설치 및 설정 방법을 안내합니다. 본 프로젝트는 의존성 관리를 위해 **Poetry**를 사용하며, 웹 UI 구성을 위해 **Streamlit**을, 광학 문자 인식을 위해 **PaddleOCR**을 핵심 엔진으로 사용합니다.

## 2. 시스템 요구사항
시스템을 실행하기 위해 사전에 아래의 환경이 준비되어야 합니다.
* **OS:** Windows 10 이상, macOS, 또는 Linux (Ubuntu 20.04+ 권장)
* **Python:** 3.9 이상 3.11 이하 (의존성 패키지 호환성 권장)
* **Package Manager:** Poetry (버전 1.4 이상)

## 3. 설치 프로세스

### 3.1. 저장소 클론 및 패키지 설치
프로젝트 소스 코드를 로컬 환경으로 가져온 후, `pyproject.toml`과 `poetry.lock`을 기반으로 의존성 패키지를 설치합니다.

```bash
# 1. 프로젝트 저장소 클론 (경로는 실제 환경에 맞게 수정)
git clone https://github.com/dongtan-91-dong-welfare-center/audit_inquiry_automation.git
cd audit_inquiry_automation

# 2. Poetry를 통한 가상환경 생성 및 의존성 패키지 설치
poetry install
```
*※ `poetry install` 실행 시 `pdfplumber`, `opencv-python`, `paddleocr`, `streamlit` 등의 핵심 라이브러리가 자동으로 설치됩니다.*

### 3.2. 시스템 의존성 라이브러리 설치 (OS별)
**OpenCV** 및 **PaddleOCR**이 정상적으로 이미지를 처리하기 위해 OS 레벨의 그래픽 라이브러리가 필요할 수 있습니다.

* **Linux (Ubuntu) 환경:**
  ```bash
  sudo apt-get update
  sudo apt-get install libgl1-mesa-glx libglib2.0-0
  ```
* **Windows/macOS 환경:** 별도의 추가 설치 없이 동작하는 경우가 일반적이나, 에러 발생 시 MSVC(Windows) 또는 Xcode Command Line Tools(macOS) 설치가 필요할 수 있습니다.

### 3.3. Tesseract 엔진 설치
현재 시스템의 메인 OCR 엔진은 `PaddleOCR` (ADR-006)이지만, 테스트 환경이나 과거 버전(ADR-005)의 호환성을 위해 `Tesseract`를 사용해야 하는 경우, 시스템 환경변수에 엔진을 등록해야 합니다.
* 상세 설치 방법은 프로젝트 내의 `docs/achieve/tesseract_install_guide.md` 문서를 참조하시기 바랍니다.

## 4. 시스템 실행 방법

모든 설치가 완료되면, Streamlit 프레임워크를 통해 메인 파이프라인(`main.py`)을 실행합니다.

```bash
# 가상환경 내에서 Streamlit 앱 실행
poetry run streamlit run main.py
```

* 실행 후 터미널에 출력되는 `Local URL` (일반적으로 `http://localhost:8501`)을 브라우저에 입력하여 메인 페이지(SCR-01)에 접속합니다.

## 5. 구동 전 확인 사항 및 제약 조건 (System Constraints)
원활한 시스템 운영을 위해 `Functions.csv (FUNC-001)`에 정의된 입력 제약 사항을 사전에 확인하시기 바랍니다.

* **최대 파일 용량:** 개별 PDF 파일의 크기는 **최대 300MB**를 초과할 수 없습니다.
* **동시 처리 제한:** 한 번에 업로드하여 처리할 수 있는 파일은 **최대 10개**로 제한됩니다.
* **보안 문서:** 암호가 설정되어 보호된 PDF 파일은 시스템에서 전처리 및 OCR 작업이 불가능하므로, 사전에 암호를 해제한 후 업로드해야 합니다.
* **최소 페이지 수:** 금융거래조회서의 기본 규격 특성상, 페이지 수가 3장 미만인 PDF는 시스템 오류 방지를 위해 입력이 제한됩니다.