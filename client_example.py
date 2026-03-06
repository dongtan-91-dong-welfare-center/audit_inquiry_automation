"""
클라이언트 예제 – paddle-doc-pipeline 서비스 호출.

기존 aidoc_workflow 등에서 HTTP로 호출하는 패턴.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import httpx

PIPELINE_URL = "http://localhost:8090"


# ── 1. 단일 파일 파싱 (Structure 모드) ──────────────────


async def parse_single_file(
    file_path: str | Path,
    mode: str = "structure",
    pages: str | None = None,
) -> dict:
    """단일 파일을 PP-StructureV3로 파싱하여 Markdown/JSON 반환."""
    file_path = Path(file_path)
    async with httpx.AsyncClient(timeout=300.0) as client:
        with open(file_path, "rb") as f:
            data = {"mode": mode}
            if pages:
                data["pages"] = pages

            resp = await client.post(
                f"{PIPELINE_URL}/parse",
                files={"file": (file_path.name, f, "application/octet-stream")},
                data=data,
            )
            resp.raise_for_status()
            return resp.json()


# ── 2. RAG용 Markdown 청크 추출 ─────────────────────────


def extract_rag_chunks(result: dict, chunk_size: int = 1000) -> list[dict]:
    """파싱 결과에서 RAG용 텍스트 청크를 생성.

    PP-StructureV3의 페이지별 Markdown을 기반으로
    적절한 크기의 청크로 분할합니다.
    """
    chunks: list[dict] = []
    filename = result["filename"]

    for page in result["pages"]:
        page_idx = page["page_index"]
        markdown = page.get("markdown", "")
        if not markdown.strip():
            continue

        # 간단한 단락 기반 청킹
        paragraphs = markdown.split("\n\n")
        current_chunk = ""

        for para in paragraphs:
            if len(current_chunk) + len(para) > chunk_size and current_chunk:
                chunks.append({
                    "text": current_chunk.strip(),
                    "metadata": {
                        "source": filename,
                        "page": page_idx,
                        "chunk_index": len(chunks),
                    },
                })
                current_chunk = para
            else:
                current_chunk += "\n\n" + para if current_chunk else para

        if current_chunk.strip():
            chunks.append({
                "text": current_chunk.strip(),
                "metadata": {
                    "source": filename,
                    "page": page_idx,
                    "chunk_index": len(chunks),
                },
            })

    return chunks


# ── 3. 기존 aidoc_workflow 연동 예시 ────────────────────


async def aidoc_paddle_integration(file_path: str) -> dict:
    """기존 aidoc_workflow LangGraph 파이프라인에서
    PaddleOCR 파싱 결과를 주입하는 패턴.

    사용법:
        # LangGraph state에서:
        parsed = await aidoc_paddle_integration("report.pdf")
        state["parsed_markdown"] = parsed["full_markdown"]
        state["parsed_chunks"] = parsed["chunks"]
    """
    # 1) PaddleOCR 서비스 호출
    result = await parse_single_file(file_path, mode="structure")

    # 2) RAG 청크 생성
    chunks = extract_rag_chunks(result)

    # 3) 통합 결과 반환
    return {
        "full_markdown": result.get("full_markdown", ""),
        "total_pages": result.get("total_pages", 0),
        "chunks": chunks,
        "elements_by_page": {
            p["page_index"]: p.get("elements", []) for p in result["pages"]
        },
    }


# ── 4. OCR-only 모드 (빠른 텍스트 추출) ────────────────


async def quick_ocr(file_path: str) -> str:
    """PP-OCRv5만 사용하여 텍스트를 빠르게 추출.
    레이아웃 분석이 필요 없는 간단한 문서에 적합.
    """
    result = await parse_single_file(file_path, mode="ocr_only")
    return result.get("full_markdown", "")


# ── 실행 예시 ────────────────────────────────────────────

if __name__ == "__main__":

    async def main():
        # 예시 1: Structure 모드 (전체 파싱)
        result = await parse_single_file("sample.pdf", mode="structure")
        print(f"=== {result['filename']} ===")
        print(f"총 {result['total_pages']}페이지, 모드: {result['mode']}")
        print(f"Markdown 길이: {len(result.get('full_markdown', ''))} chars")

        # RAG 청크 생성
        chunks = extract_rag_chunks(result)
        print(f"RAG 청크 수: {len(chunks)}")
        for i, chunk in enumerate(chunks[:3]):
            print(f"\n--- Chunk {i} (page {chunk['metadata']['page']}) ---")
            print(chunk["text"][:200] + "...")

        # 예시 2: OCR-only 모드 (빠른 텍스트)
        text = await quick_ocr("scan.png")
        print(f"\nOCR 결과: {text[:300]}...")

    asyncio.run(main())
