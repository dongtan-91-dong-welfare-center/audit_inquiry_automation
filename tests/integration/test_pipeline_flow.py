# tests/integration/test_pipeline_flow.py

import os
import pytest
import openpyxl

from src.core.pdf_loader import PDFLoader
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor
from src.core.postprocessor import PostProcessor
from src.core.excel_builder import ExcelBuilder

@pytest.mark.integration
def test_full_pipeline_integration():
    """
    [전체 파이프라인 통합 테스트]
    PDFLoader -> Preprocessor -> OCRExtractor -> PostProcessor -> ExcelBuilder
    실제 은행 조회서 PDF가 최종적으로 어떻게 엑셀 파일로 도출되는지 엔드투엔드로 검증합니다.
    """
    # 1. 테스트 데이터 준비
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "..", "data", "input", "(주)삼성전자_1_농협은행.pdf")

    print(f"\n▶ 1. PDF 파일 로딩 중: {os.path.basename(pdf_path)}")
    loader = PDFLoader(pdf_path)
    bank_name = loader.metadata["bank_name"]
    company_name = loader.metadata["company_name"]
    print(f"   - 🏦 인식된 회사명: {company_name} / 은행명: {bank_name}")

    page_images = loader.convert_to_images()
    assert page_images is not None and len(page_images) > 0, "❌ PDF 로드 실패"
    print(f"   - 로드 성공 (총 {len(page_images)} 페이지)")

    # 2. 전처리 (Preprocessor) 모듈 실행
    print("\n▶ 2. 전처리 파이프라인 통과 중 (표 탐지 및 크롭)...")
    preprocessor = ImagePreprocessor()
    table_images = preprocessor.process_pages(page_images)
    assert table_images, "❌ 표를 찾지 못했습니다."
    print(f"   - 전처리 완료! 총 {len(table_images)}개의 표 영역 추출")

    # 3. OCR (OCRExtractor) 모듈 실행
    print("\n▶ 3. OCR 엔진 구동 및 표 데이터 추출 중...")
    extractor = OCRExtractor()
    all_tables_data = extractor.extract_table_data(table_images)
    assert all_tables_data, "❌ OCR 추출 데이터가 없습니다."

    # 4. 후처리 (PostProcessor) 모듈 실행
    print("\n▶ 4. PostProcessor 데이터 정제 및 분할 중...")
    postprocessor = PostProcessor()
    processed_tables = postprocessor.process_data(all_tables_data, bank_name=bank_name)

    # 5. 엑셀 생성 (ExcelBuilder) 모듈 실행
    print("▶ 5. 정제된 데이터를 엑셀 템플릿에 쓰는 중...")
    builder = ExcelBuilder()

    output_path = builder.export_to_excel(
        company_name=company_name,
        bank_name=bank_name,
        processed_tables=processed_tables,
        category="은행"
    )

    # 6. 엑셀 파일이 실제로 생성되었는지 최종 검증
    assert os.path.exists(output_path), f"❌ 엑셀 파일이 생성되지 않았습니다: {output_path}"

    print("\n====================== [ 파이프라인 완료 ] ======================")
    print(f"✅ 최종 엑셀 파일이 성공적으로 저장되었습니다.")
    print(f"📂 파일 위치: {os.path.abspath(output_path)}")
    print("=================================================================\n")