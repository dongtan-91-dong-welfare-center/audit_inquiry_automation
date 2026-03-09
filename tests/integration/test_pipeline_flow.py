# tests/integration/test_pipeline_flow.py

import os
import pytest
from src.core.pdf_loader import PDFLoader
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor
from src.core.postprocessor import PostProcessor

@pytest.mark.integration
def test_pipeline_integration():
    """
    [파이프라인 연계 테스트]
    PDFLoader -> Preprocessor -> OCRExtractor -> PostProcessor가 연계되었을 때
    실제 은행 조회서 이미지가 최종적으로 어떻게 정제된 딕셔너리로 도출되는지 눈으로 확인합니다.
    """
    # 1. 테스트 데이터 준비
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "..", "data", "input", "(주)삼성전자_1_농협은행.pdf")
    
    print(f"\n▶ 1. PDF 파일 로딩 중: {os.path.basename(pdf_path)}")
    loader = PDFLoader(pdf_path)
    bank_name = loader.metadata["bank_name"]
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
    final_result = postprocessor.process_data(all_tables_data, bank_name=bank_name)

    print(f"\n▶ 데이터 후처리(정제) 결과 확인: {os.path.basename(pdf_path)}")
    financial_table = final_result.get("financial_table", [])
    loan_table = final_result.get("loan_table", [])

    print(f"\n[ 🏦 금융상품(예·적금) 테이블 - 총 {len(financial_table)}건 추출 ]")
    if not financial_table:
        print("   데이터가 없습니다.")
    else:
        for i, row in enumerate(financial_table):
            print(f"   Row {i:02d} | 칸 수: {len(row)} | 데이터: {row}")

    print(f"\n[ 💰 대출거래 테이블 - 총 {len(loan_table)}건 추출 ]")
    if not loan_table:
        print("   데이터가 없습니다.")
    else:
        for i, row in enumerate(loan_table):
            print(f"   Row {i:02d} | 칸 수: {len(row)} | 데이터: {row}")

    print("\n=================================================================\n")
