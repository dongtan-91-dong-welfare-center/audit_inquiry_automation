# tests/core/test_ocr_engine.py

import os
import cv2

# conftest.py가 작동하므로, sys.path 설정 없이 바로 src 모듈 임포트 가능
from src.core.pdf_loader import PDFLoader
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor

def test_ocr_pipeline_integration():
    """
    [통합 테스트 파이프라인]
    PDFLoader -> Preprocessor -> OCRExtractor가 연계되었을 때
    실제 은행 조회서 이미지가 어떤 3차원 리스트(표 단위)로 도출되는지 확인합니다.
    """
    
    # 1. 테스트 이미지 경로 설정 (tests/data/input/ 기준)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    pdf_path = os.path.join(current_dir, "..", "data", "input", "bank_audit_letter-scan.pdf")
    
    print(f"\n▶ 1. PDF 파일 로딩 중: {os.path.basename(pdf_path)}")
    
    # PDFLoader 클래스를 불러와서 일괄적으로 돌리는 흐름 유지
    loader = PDFLoader(pdf_path)
    page_images = loader.convert_to_images()
    
    # pytest에서는 assert문을 활용해 에러를 검증합니다.
    assert page_images is not None and len(page_images) > 0, "❌ PDF에서 이미지를 불러오지 못했습니다. 경로를 확인해주세요."
    print(f"   - 로드 성공 (총 {len(page_images)} 페이지 변환 완료)")

    # 2. 전처리 (Preprocessor) 모듈 실행
    print("\n▶ 2. 전처리 파이프라인 통과 중 (전체 페이지 배열 처리 -> 표 탐지 -> 크롭)...")
    preprocessor = ImagePreprocessor()
    
    # 메인 파이프라인인 process_page 호출 (결과는 표 이미지들의 리스트)
    table_images = preprocessor.process_pages(page_images) 
    assert table_images, "❌ 전처리된 표 이미지가 없습니다 (표를 찾지 못함)."
    print(f"   - 전처리 완료! 총 {len(table_images)}개의 표 영역 이미지가 추출되었습니다.")

    # 3. OCR (OCRExtractor) 모듈 실행
    print("\n▶ 3. OCR 엔진 구동 및 표 데이터 일괄 추출 중...")
    extractor = OCRExtractor(psm=6)
    
    all_tables_data = extractor.extract_table_data(table_images)
    
    # 4. 결과 출력
    if not all_tables_data:
         print("   ❌ 추출된 데이터가 전혀 없습니다.")
    else:
        for table_idx, table_data in enumerate(all_tables_data):
            print(f"\n================== [ 표 {table_idx + 1} 결과 ] ==================")
            
            if not table_data:
                print("   해당 표에서 추출된 데이터가 없습니다.")
            else:
                for i, row in enumerate(table_data):
                    print(f"Row {i:02d} | 칸 수: {len(row)} | 데이터: {row}")
                    
    print("\n=======================================================================\n")
