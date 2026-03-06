"""Pydantic schemas for API request/response."""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


# ── Request ──────────────────────────────────────────────


class ParseMode(str, Enum):
    STRUCTURE = "structure"
    OCR_ONLY = "ocr_only"


class ParseRequest(BaseModel):
    """파싱 요청 옵션 (multipart form의 JSON 파트)."""

    mode: ParseMode = ParseMode.STRUCTURE
    pages: list[int] | None = Field(
        default=None,
        description="처리할 페이지 번호 (0-indexed). None이면 전체.",
    )
    use_table_recognition: bool = True
    use_formula_recognition: bool = True
    use_chart_recognition: bool = True
    return_markdown: bool = True
    return_json: bool = True


# ── Response ─────────────────────────────────────────────


class BBox(BaseModel):
    """Bounding box (x1, y1, x2, y2)."""

    x1: float
    y1: float
    x2: float
    y2: float


class TextBlock(BaseModel):
    """OCR only 모드에서 반환되는 텍스트 블록."""

    text: str
    confidence: float
    bbox: BBox | None = None


class LayoutElement(BaseModel):
    """PP-StructureV3가 파싱한 레이아웃 요소."""

    element_type: str = Field(description="text, table, figure, formula, title, etc.")
    content: str = ""
    bbox: BBox | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class PageResult(BaseModel):
    """단일 페이지 파싱 결과."""

    page_index: int
    width: int | None = None
    height: int | None = None
    markdown: str = ""
    elements: list[LayoutElement] = Field(default_factory=list)
    ocr_blocks: list[TextBlock] = Field(default_factory=list)


class DocumentResult(BaseModel):
    """전체 문서 파싱 결과."""

    filename: str
    total_pages: int
    mode: ParseMode
    pages: list[PageResult]
    full_markdown: str = Field(default="", description="전체 페이지 Markdown 합본")
    raw_json: dict[str, Any] | None = Field(
        default=None, description="PP-StructureV3 원본 JSON"
    )


class HealthResponse(BaseModel):
    status: str = "ok"
    models_loaded: bool = False
    device: str = ""
