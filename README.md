# 금융거래조회서 키인 자동화 시스템 (Audit Inquiry Automation)

이 프로젝트는 회계 감사 과정에서 수기로 진행되던 '금융거래조회서'의 데이터 입력 작업을 자동화하는 시스템입니다. 사용자가 PDF 형태의 스캔본 문서를 업로드하면, 시스템이 이미지 전처리와 광학 문자 인식(OCR)을 거쳐 표 데이터를 추출하고 지정된 엑셀 템플릿에 맞추어 변환해 줍니다. 

## 🤷‍♂️ 기술 스택
* **Language:** Python (3.9 ~ 3.11)
* **Frontend / UI:** Streamlit
* **PDF Processing:** pdfplumber
* **Computer Vision:** OpenCV (`cv2`)
* **OCR Engine:** PaddleOCR
* **Package Management:** Poetry
> **참고:** 각 기술 스택의 상세 도입 배경 및 프레임워크 비교 내용은 [`docs/architecture/adr_summary.md`](docs/architecture/adr_summary.md)를 확인해 주세요.

## 📂 폴더 구조
```text
audit_inquiry_automation/
├── src/                  # 핵심 비즈니스 로직
│   ├── core/             # 전처리, OCR 엔진, 엑셀 빌더 등 메인 컴포넌트
│   └── utils/            # 데이터 검증 및 포매터
├── docs/                 # 아키텍처, 기술 상세, 운영 및 설치 매뉴얼
├── tests/                # 단위, 통합, 정확도 테스트
│   └── data/             # 테스트용 PDF 입력값 및 템플릿
├── main.py               # Streamlit 앱 실행 엔트리포인트
└── pyproject.toml        # 의존성 및 패키지 관리
```

## 🔧 아키텍처
본 시스템은 다음과 같은 단방향 데이터 파이프라인 구조를 가집니다.
`PDF 파일 업로드` ➡️ `이미지 변환` ➡️ `이미지 전처리(최적화/크롭)` ➡️ `OCR 텍스트 추출` ➡️ `후처리(데이터 정제/병합)` ➡️ `엑셀 매핑 및 반환`

> **참고:** 전체 시스템 파이프라인과 각 컴포넌트의 상세 역할은 [`docs/architecture/system_overview.md`](docs/architecture/system_overview.md)를 참고하시기 바랍니다.

## 🚀 주요 기능
* **자동 파일명 파싱:** 업로드된 PDF 파일명에서 '감사대상회사', '조회처', '조회처 유형' 자동 추출.
* **OCR 최적화 이미지 전처리:** 노이즈 제거, 표 영역 자동 크롭, 오인식 방지를 위한 세로선 제거.
* **지능형 표 데이터 병합:** 여러 페이지에 걸쳐 분할된 표를 자동으로 인식하고 하나의 표로 병합.
* **유사 문자 자동 보정:** '0/O', '1/I' 등 문맥상 빈번하게 발생하는 OCR 오인식 자동 교정.
* **의도된 공란 보존:** 대출 잔액 없음 등 원본 문서의 의도된 빈칸을 논리적으로 유지.

## 📊 실행 흐름
1. Streamlit 웹 인터페이스 접속
2. 금융거래조회서 PDF 파일 업로드
3. OCR 처리를 수행할 마지막 페이지 범위 설정 (기본 시작: 3페이지)
4. '처리 시작' 버튼 클릭 (자동 파이프라인 가동)
5. '엑셀 다운로드' 버튼 클릭하여 결과물 확인

> **참고:** 상세한 화면 구성 및 각 단계별 사용 가이드는 [`docs/operation/user_manual.md`](docs/operation/user_manual.md)를 참고해 주세요. OCR 데이터 추출 로직의 상세 과정은 [`docs/technical/ocr_pipeline_details.md`](docs/technical/ocr_pipeline_details.md)에 기술되어 있습니다.

## ⚙️ 환경 설정
본 프로젝트는 **Poetry**를 기반으로 패키지 의존성을 관리합니다.
```bash
# 1. 의존성 설치
poetry install

# 2. 시스템 실행
poetry run streamlit run main.py
```
> **참고:** OS별 환경 설정(OpenCV, 그래픽 라이브러리 등) 및 상세 설치 가이드는 [`docs/operation/install_guide.md`](docs/operation/install_guide.md)를 확인해 주세요.

## 📊 테스트
시스템 안정성과 OCR 인식률을 보장하기 위해 `pytest`를 활용한 다각도 테스트가 구성되어 있습니다.
* `tests/unit/`: 모듈별 단위 기능 테스트 (전처리, 후처리, 유효성 검사 등)
* `tests/integration/`: 파이프라인 전체 흐름 테스트
* `tests/unit/test_accuracy.py`: 실제 OCR 엔진의 데이터 추출 정확도 검증

## 💡 프로젝트 관리
* **이슈 트래킹:** GitHub Issues 기능을 활용하며, 버그 리포트, 기능 추가, 요구사항 관리, 화면 보고 등 세분화된 템플릿(`.github/ISSUE_TEMPLATE/`)을 사용합니다.
* **요구사항 관리:** 초기 [기획 산출물](https://docs.google.com/spreadsheets/d/1qUclaf1vGhyrnFFPQoa0_MShbkzTYcgHezVEV9st0Xw/edit?gid=0#gid=0)을 기반으로 요구사항 수용 및 개발 상태를 추적합니다.

## 🔧 추후 개선 사항
현재 1차 개발이 완료되었으며, 향후 고도화 시 다음 항목들이 추가될 예정입니다.
* 파생상품계약, 보관 어음/수표 등 복잡한 계단식 구조 표에 대한 추출 로직 추가 적용.
* **(보류 항목)** 추출된 데이터 중 OCR 신뢰도가 낮은 항목에 대한 시각적 알림 제공 기능.
* **(보류 항목)** 시스템 내에서 원본 이미지와 추출 결과를 즉각적으로 대조하고 편집할 수 있는 '검증 인터페이스' 구축.

## 📌 주의사항
1. **입력 제약:**
   * PDF 포맷만 지원 (최대 300MB, 한 번에 최대 10개).
   * 암호가 설정된 문서는 처리가 불가하므로 반드시 암호 해제 후 업로드해야 합니다.
   * 조회서 규격상 최소 3페이지 이상의 문서만 정상 처리됩니다.
2. **최종 책임 (회계사 검토 의무):**
   * 본 시스템은 원본 문서에 기재된 내용을 '있는 그대로' 정확히 추출하는 것을 목표로 합니다. 원본의 합계가 맞지 않거나 필수 항목이 누락된 경우, 시스템은 임의로 계산을 교정하거나 내용을 창작하지 않습니다. 최종 데이터의 논리적 검증은 담당 회계사의 몫입니다. (상세 검증 규칙은 [`docs/technical/validation_rules.md`](docs/technical/validation_rules.md) 참고)