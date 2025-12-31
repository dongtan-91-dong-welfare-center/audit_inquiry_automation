# 금융거래조회서 자동화 (Audit Inquiry Automation)

본 프로젝트는 금융거래조회서(PDF) 내의 표(Table)를 자동으로 탐지하고, OCR(광학 문자 인식)을 통해 데이터를 추출하여 **단일 엑셀 파일(One-Excel)**로 변환해주는 자동화 프로그램입니다.

## 🌟 주요 기능

- **하이브리드 데이터 추출 (Hybrid Extraction):**
  - **텍스트형 PDF:** `pdfplumber`를 사용하여 텍스트 레이어를 빠르고 정확하게 추출합니다.
  - **이미지형(스캔) PDF:** `OpenCV`로 표 격자를 탐지하고 `PaddleOCR`을 통해 텍스트를 복원합니다.
- **지능형 표 병합:** 페이지를 넘어가는 긴 표의 헤더 구조를 분석하여 자동으로 하나의 시트로 병합합니다.
- **원클릭 엑셀 생성:** 추출된 모든 표를 하나의 엑셀 파일 내 개별 시트로 정리하여 제공합니다.
- **사용자 편의성:** Streamlit 기반의 웹 UI와 대량 처리를 위한 CLI 환경을 모두 지원합니다.

## 📂 프로젝트 구조

```text
audit-inquiry-automation
├── src/
│   ├── __init__.py        # 패키지 초기화
│   ├── cli.py             # CLI 실행 진입점 (대량 처리용)
│   ├── processor.py       # 전체 처리 흐름(추출->변환)을 제어하는 지휘관 모듈
│   ├── extractor.py       # PDF 표 추출 및 OCR 핵심 엔진 (Hybrid 방식)
│   ├── excel_writer.py    # 데이터프레임 -> 엑셀 변환 및 저장 로직
│   ├── detection.py       # (Wrapper) 표 탐지 인터페이스
│   ├── ocr.py             # (Wrapper) OCR 엔진 인터페이스
│   ├── config.py          # 환경 설정 및 상수 관리
│   └── utils.py           # 로깅, 파일명 파싱, 정규식 등 유틸리티
├── tests/                 # 단위 테스트 폴더
├── assets/                # 템플릿 및 매핑 파일
├── app.py                 # Streamlit 웹 애플리케이션 진입점
├── pyproject.toml         # Poetry 의존성 및 빌드 설정
├── poetry.lock            # 의존성 잠금 파일
└── README.md              # 프로젝트 설명서
```

🚀 설치 방법 (Installation)
이 프로젝트는 Poetry를 사용하여 의존성을 관리합니다.

``` Bash
poetry install
```

참고: PaddleOCR 및 OpenCV 관련 라이브러리가 포함되어 있어 설치에 시간이 소요될 수 있습니다.

💻 사용 방법 (Usage)
1. 웹 UI 실행 (Streamlit)
가장 간편한 방법으로, 브라우저에서 파일을 업로드하고 결과를 확인할 수 있습니다.

``` Bash
poetry run streamlit run main.py
```

2. CLI 실행 (Terminal)
대량의 파일을 처리하거나 서버 환경에서 실행할 때 사용합니다.

``` Bash
poetry run python -m src.cli --input data/sample.pdf --output result.xlsx
```

3. 테스트 실행
작성된 단위 테스트를 수행하여 시스템 무결성을 확인합니다.

``` Bash
poetry run pytest -q
```

🛠 기술 스택 및 알고리즘
- Framework: Streamlit (UI), Click (CLI)

- PDF Processing: pdfplumber (Primary), PaddleOCR + OpenCV (Fallback)

- Data Handling: Pandas, OpenPyXL

- Table Detection Algorithm:

    1. 1차 시도: pdfplumber로 텍스트 기반 표 추출 시도.

    2. 2차 시도 (Fallback): 추출 실패 시 이미지 모드로 전환.

    3. 이미지 처리: OpenCV로 수평/수직선을 검출하여 교차점(Intersection) 기반으로 셀(Cell) 인식.

    4. OCR: 각 셀 영역에 대해 PaddleOCR을 수행하여 텍스트 복원.

    5. 구조 분석: 연속된 페이지의 헤더를 비교하여 동일 구조일 경우 자동 병합.

🤝 기여 (Contributing)
버그 제보나 기능 개선 요청은 Issue를 등록해 주세요. Pull Request 또한 언제나 환영합니다.

📄 라이선스 (License)
본 프로젝트는 MIT License를 따릅니다. 자세한 내용은 LICENSE 파일을 참고하세요.
