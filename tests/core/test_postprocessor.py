# tests/core/test_postprocessor.py

import os
import cv2
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor
from src.core.postprocessor import PostProcessor

def test_postprocessor_integration():
    """
    [후처리(PostProcessor) 전용 테스트]
    전처리 -> OCR 추출을 거친 날것(Raw)의 데이터를 PostProcessor에 통과시켜,
    오류가 수정된 깔끔한 최종 결과물이 나오는지 확인합니다.
    """
    # 1. 테스트 데이터 준비
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(current_dir, "..", "data", "input", "bank_audit_letter-0003.jpg")
    raw_image = cv2.imread(img_path)
    assert raw_image is not None

    # 2. 전처리 및 OCR 모듈 준비
    preprocessor = ImagePreprocessor()
    extractor = OCRExtractor(psm=6)
    processed_tables = preprocessor.process_page(raw_image)
    
    # 3. [테스트 핵심] 후처리 인스턴스 생성
    postprocessor = PostProcessor()
    
    print(f"\n▶ 데이터 후처리(정제) 결과 확인: {os.path.basename(img_path)}")
    
    for table_idx, table_img in enumerate(processed_tables):
        # 날것의 데이터 획득
        raw_rows = extractor.extract_table_data(table_img)
        
        # 정제 함수 적용
        cleaned_rows = postprocessor.process_data(raw_rows)
        
        # 후처리 결과 출력
        print(f"\n================== [ 표 {table_idx + 1} 정제 완료 데이터 (Cleaned) ] ==================")
        if not cleaned_rows:
            print("   추출/정제된 데이터가 없습니다.")
        else:
            for i, row in enumerate(cleaned_rows):
                print(f"Row {i:02d} | 칸 수: {len(row)} | 데이터: {row}")
                
    print("\n=======================================================================\n")