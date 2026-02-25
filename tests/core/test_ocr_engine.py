# tests/core/test_ocr_engine.py

import os
import cv2

# conftest.py가 작동하므로, sys.path 설정 없이 바로 src 모듈 임포트 가능
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor

def test_ocr_pipeline_integration():
    """
    [통합 테스트 파이프라인]
    preprocessor.py와 ocr_engine.py가 연계되었을 때
    실제 은행 조회서 이미지가 어떤 2차원 리스트로 도출되는지 확인합니다.
    """
    
    # 1. 테스트 이미지 경로 설정 (tests/data/input/ 기준)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(current_dir, "..", "data", "input", "bank_audit_letter-0003.jpg")
    
    print(f"\n▶ 1. 이미지 로딩 중: {os.path.basename(img_path)}")
    raw_image = cv2.imread(img_path)
    
    # pytest에서는 assert문을 활용해 에러를 검증합니다.
    assert raw_image is not None, "❌ 이미지를 불러오지 못했습니다. 경로를 확인해주세요."
    print(f"   - 로드 성공 (원본 크기: {raw_image.shape})")

    # 2. 전처리 (Preprocessor) 모듈 실행
    print("\n▶ 2. 전처리 파이프라인 통과 중 (기울기 보정 -> 표 탐지 -> 크롭)...")
    preprocessor = ImagePreprocessor()
    
    # 메인 파이프라인인 process_page 호출 (결과는 표 이미지들의 리스트)
    processed_tables = preprocessor.process_page(raw_image) 
    assert processed_tables, "❌ 전처리된 표 이미지가 없습니다 (표를 찾지 못함)."
    print(f"   - 전처리 완료! 총 {len(processed_tables)}개의 표 영역이 추출되었습니다.")

    # 3. OCR (OCRExtractor) 모듈 실행
    print("\n▶ 3. OCR 엔진 구동 및 표 추출 중...")
    extractor = OCRExtractor(psm=6)
    
    # 추출된 여러 개의 표 이미지에 대해 각각 OCR 실행
    for table_idx, processed_table in enumerate(processed_tables):
        print(f"\n================== [ 표 {table_idx + 1} 결과 ] ==================")
        
        extracted_rows = extractor.extract_table_data(processed_table)
        
        if not extracted_rows:
            print("   추출된 데이터가 없습니다.")
        else:
            for i, row in enumerate(extracted_rows):
                print(f"Row {i:02d} | 칸 수: {len(row)} | 데이터: {row}")
                
    print("\n=======================================================================\n")
