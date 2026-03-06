"""
FastAPI Application – PaddleOCR Document Parsing Service

엔드포인트:
  POST /parse         ← 파일 업로드 → Markdown + JSON 반환
  POST /parse/batch   ← 다중 파일 일괄 처리
  GET  /health        ← 헬스체크
"""

from __future__ import annotations

import logging
import shutil
import tempfile
import uuid
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, HTMLResponse

from config import settings
from pipeline import get_pipeline
from schemas import DocumentResult, HealthResponse, ParseMode, ParseRequest

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)

# ── App ──────────────────────────────────────────────────

app = FastAPI(
    title="PaddleOCR Document Pipeline",
    description="PP-StructureV3 + PP-OCRv5 기반 문서 → Markdown/JSON 변환 API",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

ALLOWED_EXTENSIONS = {".pdf", ".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}


# ── Lifecycle ────────────────────────────────────────────


@app.on_event("startup")
async def startup() -> None:
    """서버 시작 시 파이프라인 모델 pre-load (선택적)."""
    logger.info("Initializing pipeline (device=%s)...", settings.device)
    # 첫 요청에 lazy-load 되지만, 원하면 여기서 미리 로드 가능:
    # pipe = get_pipeline()
    # pipe._get_structure_pipeline()
    logger.info("Pipeline ready.")


# ── Endpoints ────────────────────────────────────────────


@app.get("/", response_class=HTMLResponse)
async def serve_ui() -> HTMLResponse:
    index_path = Path(__file__).parent / "index.html"
    if index_path.exists():
        return HTMLResponse(content=index_path.read_text(encoding="utf-8"))
    return HTMLResponse(content="<h1>UI Not Found</h1>", status_code=404)


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    pipe = get_pipeline()
    return HealthResponse(
        status="ok",
        models_loaded=pipe.is_loaded,
        device=settings.device,
    )


@app.post("/parse", response_model=DocumentResult)
async def parse_document(
    file: UploadFile = File(..., description="PDF 또는 이미지 파일"),
    mode: Annotated[str, Form()] = "structure",
    pages: Annotated[str | None, Form()] = None,
    use_table: Annotated[bool, Form()] = True,
    use_formula: Annotated[bool, Form()] = True,
    use_chart: Annotated[bool, Form()] = True,
) -> DocumentResult:
    """단일 파일 파싱.

    Args:
        file: 업로드 파일 (PDF, PNG, JPG, ...)
        mode: "structure" (PP-StructureV3) 또는 "ocr_only" (PP-OCRv5)
        pages: 처리할 페이지 (예: "0,1,2" 또는 null=전체) – PDF만 해당
        use_table: 테이블 인식 활성화
        use_formula: 수식 인식 활성화
        use_chart: 차트 인식 활성화
    """
    # 확장자 검증
    suffix = Path(file.filename or "unknown").suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"지원하지 않는 파일 형식: {suffix}. 지원: {ALLOWED_EXTENSIONS}",
        )

    # 파일 크기 검증
    content = await file.read()
    size_mb = len(content) / (1024 * 1024)
    if size_mb > settings.max_file_size_mb:
        raise HTTPException(
            status_code=413,
            detail=f"파일 크기 {size_mb:.1f}MB > 최대 {settings.max_file_size_mb}MB",
        )

    # 임시 파일 저장
    request_id = uuid.uuid4().hex[:12]
    tmp_dir = Path(tempfile.mkdtemp(prefix=f"paddle_{request_id}_"))
    file_path = tmp_dir / f"input{suffix}"
    file_path.write_bytes(content)

    # 페이지 파싱
    page_list: list[int] | None = None
    if pages:
        try:
            page_list = [int(p.strip()) for p in pages.split(",")]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"잘못된 pages 형식: {pages}")

    # 파싱 모드
    try:
        parse_mode = ParseMode(mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"잘못된 mode: {mode}. 'structure' 또는 'ocr_only' 사용",
        )

    # 출력 디렉토리
    save_dir = settings.output_dir / request_id

    try:
        pipe = get_pipeline()
        result = pipe.parse_document(
            file_path=file_path,
            mode=parse_mode,
            pages=page_list,
            save_dir=save_dir,
        )
        return result
    except Exception as e:
        logger.exception("Parse failed for %s", file.filename)
        raise HTTPException(status_code=500, detail=f"파싱 실패: {e}")
    finally:
        # 임시 업로드 파일 정리 (output은 유지)
        shutil.rmtree(tmp_dir, ignore_errors=True)


@app.post("/parse/batch")
async def parse_batch(
    files: list[UploadFile] = File(..., description="다중 파일 업로드"),
    mode: Annotated[str, Form()] = "structure",
) -> list[DocumentResult]:
    """다중 파일 일괄 파싱."""
    if len(files) > 20:
        raise HTTPException(status_code=400, detail="한 번에 최대 20개 파일")

    results: list[DocumentResult] = []
    for f in files:
        # 개별 파싱 재사용
        suffix = Path(f.filename or "unknown").suffix.lower()
        if suffix not in ALLOWED_EXTENSIONS:
            continue

        content = await f.read()
        request_id = uuid.uuid4().hex[:12]
        tmp_dir = Path(tempfile.mkdtemp(prefix=f"paddle_{request_id}_"))
        file_path = tmp_dir / f"input{suffix}"
        file_path.write_bytes(content)

        try:
            parse_mode = ParseMode(mode)
        except ValueError:
            parse_mode = ParseMode.STRUCTURE

        save_dir = settings.output_dir / request_id

        try:
            pipe = get_pipeline()
            result = pipe.parse_document(
                file_path=file_path,
                mode=parse_mode,
                save_dir=save_dir,
            )
            results.append(result)
        except Exception as e:
            logger.exception("Batch parse failed for %s", f.filename)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    return results


# ── 직접 실행 ────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app:app",
        host=settings.host,
        port=settings.port,
        workers=settings.workers,
        reload=False,
    )
