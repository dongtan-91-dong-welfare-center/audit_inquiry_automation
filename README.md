# PaddleOCR Document Pipeline

PP-StructureV3 + PP-OCRv5 기반 문서 → Markdown/JSON 변환 파이프라인.  
PDF 및 이미지에서 레이아웃을 유지한 구조화 데이터를 추출하여 RAG 시스템에 제공합니다.

## 아키텍처

```
                     ┌─────────────────────────────────────────────────┐
                     │              FastAPI (app.py)                    │
                     │   POST /parse    POST /parse/batch   GET /health│
                     └────────────┬────────────────────────────────────┘
                                  │
                     ┌────────────▼────────────────────────────────────┐
                     │          DocumentPipeline (pipeline.py)          │
                     │                                                  │
                     │  ┌─ mode=structure ──────────────────────────┐  │
                     │  │         PP-StructureV3 Pipeline            │  │
                     │  │                                            │  │
                     │  │  Preprocessing                             │  │
                     │  │    ├─ Doc Orientation Classify (optional)  │  │
                     │  │    └─ Doc Unwarping (optional)             │  │
                     │  │                                            │  │
                     │  │  PP-OCRv5 (내장)                           │  │
                     │  │    ├─ PP-OCRv5_server_det (텍스트 검출)    │  │
                     │  │    └─ PP-OCRv5_server_rec (텍스트 인식)    │  │
                     │  │                                            │  │
                     │  │  Layout Analysis                           │  │
                     │  │    ├─ PP-DocLayout-plus (레이아웃 검출)    │  │
                     │  │    └─ Region Detection                     │  │
                     │  │                                            │  │
                     │  │  Document Items Recognition                │  │
                     │  │    ├─ Table Recognition (SLANeXt)          │  │
                     │  │    ├─ Formula Recognition (UniMERNet)      │  │
                     │  │    ├─ Seal Recognition                     │  │
                     │  │    └─ Chart Parsing                        │  │
                     │  │                                            │  │
                     │  │  Postprocessing → Markdown / JSON          │  │
                     │  └────────────────────────────────────────────┘  │
                     │                                                  │
                     │  ┌─ mode=ocr_only ───────────────────────────┐  │
                     │  │         PP-OCRv5 Pipeline                  │  │
                     │  │    ├─ Text Detection                       │  │
                     │  │    ├─ Text Recognition                     │  │
                     │  │    └─ → Plain text output                  │  │
                     │  └────────────────────────────────────────────┘  │
                     └─────────────────────────────────────────────────┘
                                  │
                     ┌────────────▼────────────────────────────────────┐
                     │  DocumentResult (schemas.py)                     │
                     │    ├─ full_markdown   → RAG 벡터 DB에 저장       │
                     │    ├─ pages[].elements → 레이아웃 메타데이터     │
                     │    └─ raw_json        → 상세 구조 데이터         │
                     └─────────────────────────────────────────────────┘
```

## 두 모드 비교

| 항목 | `structure` (PP-StructureV3) | `ocr_only` (PP-OCRv5) |
|------|------------------------------|------------------------|
| 레이아웃 분석 | ✅ 18종 문서 요소 | ❌ |
| 테이블 인식 | ✅ HTML/Markdown 변환 | ❌ |
| 수식 인식 | ✅ LaTeX 변환 | ❌ |
| 차트 파싱 | ✅ 데이터 추출 | ❌ |
| 출력 포맷 | Markdown + JSON | Plain text |
| 속도 | ~3-5초/페이지 (A100) | ~0.5-1초/페이지 |
| 용도 | 복잡한 문서, 보고서, 논문 | 단순 스캔, 텍스트 위주 |

## 설치 & 실행

### 로컬 실행

```bash
# 1. PaddlePaddle GPU 설치 (CUDA 12.x)
pip install paddlepaddle-gpu==3.1.0

# 2. 의존성 설치
pip install paddleocr>=3.1.0 fastapi uvicorn[standard] \
    python-multipart pydantic pydantic-settings aiofiles PyMuPDF

# 3. 환경변수 설정
cp .env.example .env  # 필요에 따라 수정

# 4. 서버 실행
python app.py
```

## API 사용법

### 단일 파일 파싱

```bash
# PP-StructureV3 모드 (레이아웃 + 테이블 + 수식)
curl -X POST http://localhost:8090/parse \
  -F "file=@report.pdf" \
  -F "mode=structure"

# PP-OCRv5 모드 (텍스트만 빠르게)
curl -X POST http://localhost:8090/parse \
  -F "file=@scan.png" \
  -F "mode=ocr_only"

# 특정 페이지만 처리
curl -X POST http://localhost:8090/parse \
  -F "file=@document.pdf" \
  -F "mode=structure" \
  -F "pages=0,1,2"
```

### Python 클라이언트

```python
import httpx

async with httpx.AsyncClient(timeout=300) as client:
    with open("report.pdf", "rb") as f:
        resp = await client.post(
            "http://localhost:8090/parse",
            files={"file": ("report.pdf", f)},
            data={"mode": "structure"},
        )
    result = resp.json()
    print(result["full_markdown"])
```



## 환경변수

| 변수 | 기본값 | 설명 |
|------|--------|------|
| `PADDLE_DEVICE` | `gpu:0` | 사용할 디바이스 |
| `PADDLE_PORT` | `8090` | 서버 포트 |
| `PADDLE_TEXT_DET_MODEL` | `PP-OCRv5_server_det` | 텍스트 검출 모델 |
| `PADDLE_TEXT_REC_MODEL` | `PP-OCRv5_server_rec` | 텍스트 인식 모델 |
| `PADDLE_USE_TABLE_RECOGNITION` | `true` | 테이블 인식 on/off |
| `PADDLE_USE_FORMULA_RECOGNITION` | `true` | 수식 인식 on/off |
| `PADDLE_MAX_FILE_SIZE_MB` | `100` | 업로드 파일 크기 제한 |

## 모델 선택 가이드

- **server 모델** (`PP-OCRv5_server_det/rec`): 정확도 우선. VRAM ~4GB. 문서 분석, 보고서 처리용.
- **mobile 모델** (`PP-OCRv5_mobile_det/rec`): 속도 우선. VRAM ~1GB. 대량 처리, CPU 환경용.

## 프로젝트 구조

```
paddle-doc-pipeline/
├── app.py              # FastAPI 서버 (엔드포인트 정의)
├── pipeline.py         # 핵심 파이프라인 (PP-StructureV3 + PP-OCRv5)
├── schemas.py          # Pydantic 요청/응답 모델
├── config.py           # 설정 (환경변수 기반)
├── client_example.py   # 클라이언트 & aidoc_workflow 연동 예시
├── pyproject.toml      # 의존성 정의
├── Dockerfile          # GPU Docker 이미지
├── docker-compose.yml  # 컨테이너 오케스트레이션
└── .env.example        # 환경변수 템플릿
```
