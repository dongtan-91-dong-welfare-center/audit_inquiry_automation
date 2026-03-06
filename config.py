"""Configuration for PaddleOCR Document Pipeline."""

from __future__ import annotations

import os
import sys
from enum import Enum
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings

# ── Colab / 권한 문제 사전 처리 ──────────────────────────
# paddlex가 import되기 전에 환경변수를 설정해야 함

# 모델 소스 체크 비활성화
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")

# Colab 환경 감지
IS_COLAB = "google.colab" in sys.modules or os.path.exists("/content")

# 모델 캐시 디렉토리: 쓰기 권한이 있는 곳으로 설정
_default_model_dir = "/content/paddle_models" if IS_COLAB else str(Path.home() / ".paddlex" / "official_models")

# paddlex 내부에서 사용하는 모델 디렉토리 환경변수
# paddlex는 PADDLE_PDX_MODEL_DIR 또는 내부 기본값 사용
_model_dir = os.environ.get("PADDLE_PDX_MODEL_DIR", _default_model_dir)
os.environ["PADDLE_PDX_MODEL_DIR"] = _model_dir
Path(_model_dir).mkdir(parents=True, exist_ok=True)


class ParseMode(str, Enum):
    """문서 파싱 모드."""

    STRUCTURE = "structure"  # PP-StructureV3: 레이아웃 + 테이블 + 수식 → Markdown/JSON
    OCR_ONLY = "ocr_only"  # PP-OCRv5 only: 텍스트만 빠르게 추출


class Settings(BaseSettings):
    """Application settings – 환경변수 또는 .env 파일로 오버라이드 가능."""

    model_config = {"env_prefix": "PADDLE_", "env_file": ".env"}

    # ── 서버 ──────────────────────────────────────────────
    host: str = "0.0.0.0"
    port: int = 8090
    workers: int = 1  # GPU 모델이므로 보통 1 worker

    # ── GPU ───────────────────────────────────────────────
    device: str = Field(default="gpu:0", description="gpu:0, gpu:1, cpu 등")

    # ── PP-StructureV3 설정 ──────────────────────────────
    use_doc_orientation_classify: bool = False
    use_doc_unwarping: bool = False
    use_textline_orientation: bool = False

    # 모델 선택 (server 버전이 정확도 높음, mobile은 가벼움)
    text_det_model: str = "PP-OCRv5_server_det"
    text_rec_model: str = "PP-OCRv5_server_rec"

    # StructureV3 세부 on/off
    use_seal_recognition: bool = True
    use_table_recognition: bool = True
    use_formula_recognition: bool = True
    use_chart_recognition: bool = True

    # ── 파일 경로 ────────────────────────────────────────
    upload_dir: Path = Path("/tmp/paddle-uploads")
    output_dir: Path = Path("/tmp/paddle-outputs")
    max_file_size_mb: int = 100

    # ── RAG 후처리 ───────────────────────────────────────
    chunk_by_page: bool = True  # 페이지별 Markdown 분리 여부
    include_layout_info: bool = True  # JSON에 레이아웃 bbox 포함


settings = Settings()
settings.upload_dir.mkdir(parents=True, exist_ok=True)
settings.output_dir.mkdir(parents=True, exist_ok=True)