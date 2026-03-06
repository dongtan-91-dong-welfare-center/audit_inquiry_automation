"""
Core Document Parsing Pipeline
PP-StructureV3 (레이아웃 + 테이블 + 수식 → Markdown/JSON)
PP-OCRv5       (텍스트만 빠르게 추출)

PP-StructureV3 내부에 PP-OCRv5가 이미 포함되어 있으므로,
StructureV3 파이프라인 하나로 두 모드를 모두 커버합니다.
"""

from __future__ import annotations

import json
import logging
import tempfile
import time
from pathlib import Path
from typing import Any

import fitz  # PyMuPDF

from config import Settings, settings
from schemas import (
    BBox,
    DocumentResult,
    LayoutElement,
    PageResult,
    ParseMode,
    TextBlock,
)

logger = logging.getLogger(__name__)


class DocumentPipeline:
    """PP-StructureV3 + PP-OCRv5 기반 문서 파싱 파이프라인.

    Singleton 패턴으로 모델을 한 번만 로드합니다.
    """

    _instance: DocumentPipeline | None = None
    _initialized: bool = False

    def __new__(cls, *args: Any, **kwargs: Any) -> DocumentPipeline:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, cfg: Settings | None = None) -> None:
        if self._initialized:
            return
        self._cfg = cfg or settings
        self._structure_pipeline = None
        self._ocr_pipeline = None
        self._initialized = True

    # ── 모델 로드 (lazy) ────────────────────────────────

    def _get_structure_pipeline(self):
        """PP-StructureV3 파이프라인 (lazy init)."""
        if self._structure_pipeline is None:
            from paddleocr import PPStructureV3

            logger.info("Loading PP-StructureV3 pipeline (device=%s)...", self._cfg.device)
            t0 = time.time()
            self._structure_pipeline = PPStructureV3(
                text_detection_model_name=self._cfg.text_det_model,
                text_recognition_model_name=self._cfg.text_rec_model,
                use_doc_orientation_classify=self._cfg.use_doc_orientation_classify,
                use_doc_unwarping=self._cfg.use_doc_unwarping,
                use_textline_orientation=self._cfg.use_textline_orientation,
                use_seal_recognition=self._cfg.use_seal_recognition,
                use_table_recognition=self._cfg.use_table_recognition,
                use_formula_recognition=self._cfg.use_formula_recognition,
                use_chart_recognition=self._cfg.use_chart_recognition,
                device=self._cfg.device,
            )
            logger.info("PP-StructureV3 loaded in %.1fs", time.time() - t0)
        return self._structure_pipeline

    def _get_ocr_pipeline(self):
        """PP-OCRv5 파이프라인 (lazy init)."""
        if self._ocr_pipeline is None:
            from paddleocr import PaddleOCR

            logger.info("Loading PP-OCRv5 pipeline (device=%s)...", self._cfg.device)
            t0 = time.time()
            self._ocr_pipeline = PaddleOCR(
                text_detection_model_name=self._cfg.text_det_model,
                text_recognition_model_name=self._cfg.text_rec_model,
                use_doc_orientation_classify=self._cfg.use_doc_orientation_classify,
                use_doc_unwarping=self._cfg.use_doc_unwarping,
                use_textline_orientation=self._cfg.use_textline_orientation,
                device=self._cfg.device,
            )
            logger.info("PP-OCRv5 loaded in %.1fs", time.time() - t0)
        return self._ocr_pipeline

    @property
    def is_loaded(self) -> bool:
        return self._structure_pipeline is not None or self._ocr_pipeline is not None

    # ── PDF → 이미지 변환 ───────────────────────────────

    @staticmethod
    def pdf_to_images(
        pdf_path: Path,
        pages: list[int] | None = None,
        dpi: int = 200,
    ) -> list[tuple[int, Path]]:
        """PDF 페이지를 개별 이미지로 변환 (PyMuPDF).

        Returns:
            list of (page_index, image_path)
        """
        doc = fitz.open(str(pdf_path))
        total = doc.page_count
        target_pages = pages if pages else list(range(total))
        results: list[tuple[int, Path]] = []

        tmp_dir = Path(tempfile.mkdtemp(prefix="paddle_pdf_"))
        zoom = dpi / 72.0
        matrix = fitz.Matrix(zoom, zoom)

        for page_idx in target_pages:
            if page_idx >= total:
                logger.warning("Page %d out of range (total=%d), skipping", page_idx, total)
                continue
            page = doc[page_idx]
            pix = page.get_pixmap(matrix=matrix)
            img_path = tmp_dir / f"page_{page_idx:04d}.png"
            pix.save(str(img_path))
            results.append((page_idx, img_path))

        doc.close()
        return results

    # ── 핵심 파싱 메서드 ────────────────────────────────

    def parse_structure(
        self,
        image_path: str | Path,
        page_index: int = 0,
        save_dir: Path | None = None,
        **predict_kwargs: Any,
    ) -> PageResult:
        """PP-StructureV3로 단일 이미지 파싱 → Markdown + 레이아웃 JSON."""
        pipeline = self._get_structure_pipeline()
        image_path = str(image_path)
        t0 = time.time()

        outputs = pipeline.predict(input=image_path, **predict_kwargs)

        page_elements: list[LayoutElement] = []
        markdown_parts: list[str] = []
        raw_json_data: dict[str, Any] = {}

        for res in outputs:
            # save_to_markdown / save_to_json 으로 파일 저장
            if save_dir:
                save_dir.mkdir(parents=True, exist_ok=True)
                res.save_to_json(save_path=str(save_dir))
                res.save_to_markdown(save_path=str(save_dir))

            # 결과 파싱 – res 객체의 dict 표현에서 추출
            res_dict = self._extract_result_dict(res)
            raw_json_data = res_dict

            # Markdown 파일이 생성되었으면 읽기
            if save_dir:
                md_files = sorted(save_dir.glob("*.md"))
                for mf in md_files:
                    markdown_parts.append(mf.read_text(encoding="utf-8"))

            # 레이아웃 요소 추출
            page_elements = self._extract_layout_elements(res_dict)

        elapsed = time.time() - t0
        logger.info(
            "StructureV3 parsed page %d in %.2fs (%d elements)",
            page_index,
            elapsed,
            len(page_elements),
        )

        return PageResult(
            page_index=page_index,
            markdown="\n\n".join(markdown_parts),
            elements=page_elements,
        )

    def parse_ocr_only(
        self,
        image_path: str | Path,
        page_index: int = 0,
    ) -> PageResult:
        """PP-OCRv5로 텍스트만 빠르게 추출."""
        ocr = self._get_ocr_pipeline()
        image_path = str(image_path)
        t0 = time.time()

        results = ocr.predict(input=image_path)

        blocks: list[TextBlock] = []
        text_lines: list[str] = []

        for res in results:
            res_dict = self._extract_result_dict(res)
            dt_polys = res_dict.get("dt_polys", [])
            rec_texts = res_dict.get("rec_texts", [])
            rec_scores = res_dict.get("rec_scores", [])

            for i, text in enumerate(rec_texts):
                score = rec_scores[i] if i < len(rec_scores) else 0.0
                bbox = None
                if i < len(dt_polys):
                    poly = dt_polys[i]
                    if hasattr(poly, "tolist"):
                        poly = poly.tolist()
                    if len(poly) >= 2:
                        xs = [p[0] for p in poly]
                        ys = [p[1] for p in poly]
                        bbox = BBox(
                            x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys)
                        )
                blocks.append(TextBlock(text=text, confidence=score, bbox=bbox))
                text_lines.append(text)

        elapsed = time.time() - t0
        logger.info(
            "OCRv5 parsed page %d in %.2fs (%d blocks)",
            page_index,
            elapsed,
            len(blocks),
        )

        return PageResult(
            page_index=page_index,
            markdown="\n".join(text_lines),
            ocr_blocks=blocks,
        )

    # ── 문서 단위 파싱 (PDF / 이미지) ───────────────────

    def parse_document(
        self,
        file_path: Path,
        mode: ParseMode = ParseMode.STRUCTURE,
        pages: list[int] | None = None,
        save_dir: Path | None = None,
    ) -> DocumentResult:
        """PDF 또는 이미지 파일을 파싱.

        - PDF: 페이지별로 이미지 변환 후 처리
        - 이미지: 단일 페이지로 처리
        """
        suffix = file_path.suffix.lower()
        is_pdf = suffix == ".pdf"

        if is_pdf:
            page_images = self.pdf_to_images(file_path, pages=pages)
            total_pages = fitz.open(str(file_path)).page_count
        else:
            page_images = [(0, file_path)]
            total_pages = 1

        page_results: list[PageResult] = []

        for page_idx, img_path in page_images:
            page_save_dir = None
            if save_dir:
                page_save_dir = save_dir / f"page_{page_idx:04d}"

            if mode == ParseMode.STRUCTURE:
                result = self.parse_structure(
                    img_path, page_index=page_idx, save_dir=page_save_dir
                )
            else:
                result = self.parse_ocr_only(img_path, page_index=page_idx)

            page_results.append(result)

        # 전체 Markdown 합본 (페이지 구분자 포함)
        full_md_parts: list[str] = []
        for pr in page_results:
            if pr.markdown.strip():
                full_md_parts.append(
                    f"<!-- Page {pr.page_index + 1} -->\n{pr.markdown}"
                )

        return DocumentResult(
            filename=file_path.name,
            total_pages=total_pages,
            mode=mode,
            pages=page_results,
            full_markdown="\n\n---\n\n".join(full_md_parts),
        )

    # ── 유틸리티 ────────────────────────────────────────

    @staticmethod
    def _extract_result_dict(res: Any) -> dict[str, Any]:
        """PaddleOCR result 객체에서 dict를 추출.

        paddleocr 3.x의 결과 객체는 다양한 형태를 가질 수 있으므로
        여러 방법을 시도합니다.
        """
        # 방법 1: res['res'] (가장 일반적)
        if hasattr(res, "__getitem__"):
            try:
                inner = res["res"]
                if isinstance(inner, dict):
                    return inner
            except (KeyError, TypeError):
                pass

        # 방법 2: res.res (attribute)
        if hasattr(res, "res"):
            inner = res.res
            if isinstance(inner, dict):
                return inner

        # 방법 3: dict(res)
        try:
            return dict(res)
        except (TypeError, ValueError):
            pass

        # 방법 4: str 파싱 fallback
        logger.warning("Could not extract dict from result: %s", type(res))
        return {}

    @staticmethod
    def _extract_layout_elements(res_dict: dict[str, Any]) -> list[LayoutElement]:
        """PP-StructureV3 JSON 결과에서 LayoutElement 리스트 추출."""
        elements: list[LayoutElement] = []

        # parsing_result 키가 있는 경우 (StructureV3 표준)
        parsing_results = res_dict.get("parsing_result", [])
        if not parsing_results:
            # layout_parsing_result 등 대체 키 시도
            parsing_results = res_dict.get("layout_parsing_result", [])

        for item in parsing_results:
            if not isinstance(item, dict):
                continue
            element_type = item.get("type", item.get("label", "unknown"))
            content = item.get("content", item.get("text", ""))
            bbox = None
            bbox_raw = item.get("bbox", item.get("coordinate", None))
            if bbox_raw and len(bbox_raw) >= 4:
                if isinstance(bbox_raw[0], (list, tuple)):
                    # polygon → 바운딩박스
                    xs = [p[0] for p in bbox_raw]
                    ys = [p[1] for p in bbox_raw]
                    bbox = BBox(x1=min(xs), y1=min(ys), x2=max(xs), y2=max(ys))
                else:
                    bbox = BBox(
                        x1=bbox_raw[0], y1=bbox_raw[1],
                        x2=bbox_raw[2], y2=bbox_raw[3],
                    )

            elements.append(
                LayoutElement(
                    element_type=str(element_type),
                    content=str(content),
                    bbox=bbox,
                    metadata={
                        k: v
                        for k, v in item.items()
                        if k not in ("type", "label", "content", "text", "bbox", "coordinate")
                    },
                )
            )

        return elements


# ── 모듈 레벨 싱글턴 접근 ───────────────────────────────

_pipeline: DocumentPipeline | None = None


def get_pipeline() -> DocumentPipeline:
    """싱글턴 파이프라인 인스턴스 반환."""
    global _pipeline
    if _pipeline is None:
        _pipeline = DocumentPipeline()
    return _pipeline
