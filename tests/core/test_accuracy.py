# src/core/achieve/test_accuracy.py

import os
import cv2
import pytest

from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor
from src.core.postprocessor import PostProcessor

# ==============================================================================
# 1. 정답 레이블 (Ground Truth) 데이터 정의
# ==============================================================================
GROUND_TRUTH = [
    ['예금', '352-1244-7439-83', '350,000', 'KRW', '3.6%', '24.12.31', '26.01.03'],
    ['예금', '416-1241-7568-93', '602,418,268', 'KRW', '2.5%', '24.10.21', '26.10.31', '비고'],
    ['적금', '786-7653-2796-14', '213,269', 'KRW', '2.4%', '25.12.31', '26.12.31'],
    ['적금', '127-4372-8697-58', '52,038', 'KRW', '2.5%', '24.12.31', '26.12.31'],
    ['적금', '579-6792-9206-94', '204,502', 'KRW', '2.5%', '25.10.30', '27.01.31'],
    ['적금', '401-1239-1382-69', '12,309', 'USD', '2.5%', '25.03.31', '26.12.31', '비고'],
    ['적금', '260-4373-4269-92', '1,294', 'USD', '2.5%', '25.03.14', '27.05.31', '비고'],
    ['적금', '972-3259-0179-35', '610,102,380', 'KRW', '2.5%', '25.07.19', '28.12.31'],
    ['적금', '296-9276-4926-84', '102,245', 'JPY', '9.3%', '25.04.04', '26.12.31'],
    ['적금', '279-1092-3068-27', '208,852', 'USD', '14.3%', '24.12.31', '26.10.31'],
    ['예·적금', '018-1239-8510-93', '93,209,201', 'KRW', '1.7%', '25.06.30', '27.01.31', '비고'],
    ['예·적금', '170-4683-5204-41', '290,038,294', 'KRW', '1.4%', '25.07.31', '27.12.31'],
    ['예·적금', '276-2670-4393-59', '1,234', 'USD', '2.1%', '25.10.14', '26.05.31'],
    ['예·적금', '119-3259-0832-25', '21,602', 'JPY', '1.9%', '24.12.31', '26.06.30'],
    ['예·적금', '209-3945-2035-83', '19,306', 'JPY', '0.7%', '25.07.30', '26.03.31', '비고'],
    ['예·적금', '346-7832-1294-63', '6,248', 'USD', '2.1%', '25.04.19', '27.01.31'],
    ['예금', '623-3522-7273-26', '20,192', 'KRW', '2.4%', '25.06.30', '27.12.31', '비고'],
    ['적금', '715-2368-0843-29', '902,582', 'KRW', '3.2%', '24.10.29', '28.12.31'],
]

def calculate_field_accuracy(cleaned_row, ground_truth_row):
    """
    한 행의 필드별 일치 여부를 계산합니다. (PostProcessor를 거쳤으므로 추가 필터링 최소화)
    """
    correct_count = 0
    # 정답 필드 수만큼만 비교
    for i in range(min(len(cleaned_row), len(ground_truth_row))):
        if cleaned_row[i] == ground_truth_row[i]:
            correct_count += 1
            
    return correct_count, len(ground_truth_row)

def test_postprocessor_accuracy_comparison():
    """
    [후처리 정확도 검증 테스트]
    PostProcessor를 통과한 최종 데이터와 Ground Truth를 비교하여 정확도를 산출합니다.
    """
    # 1. 이미지 로딩
    current_dir = os.path.dirname(os.path.abspath(__file__))
    img_path = os.path.join(current_dir, "..", "data", "input", "bank_audit_letter-0003.jpg")
    raw_image = cv2.imread(img_path)
    assert raw_image is not None
    
    # 2. 파이프라인(담당자) 초기화 및 실행
    preprocessor = ImagePreprocessor()
    extractor = OCRExtractor(psm=6)
    postprocessor = PostProcessor()
    
    processed_tables = preprocessor.process_page(raw_image)
    
    print("\n📊 [후처리(PostProcessor) 최종 정확도 리포트]")
    print("-" * 50)
    
    # 첫 번째 표만 분석
    raw_rows = extractor.extract_table_data(processed_tables[0])
    
    # [핵심] OCR 원본 데이터를 후처리기로 정제!
    cleaned_rows = postprocessor.process_data(raw_rows)
    
    total_fields = 0
    total_correct = 0
    
    # [개선] 헤더를 건너뛰고 실제 데이터가 시작되는 인덱스를 동적으로 탐색
    start_offset = 0
    for idx, row in enumerate(cleaned_rows):
        # 줄의 첫 번째 칸이 상품명(예금, 적금, 예·적금)으로 시작하면 데이터의 시작점으로 간주
        if row and row[0] in ['예금', '적금', '예·적금']:
            start_offset = idx
            break
    
    for i, gt_row in enumerate(GROUND_TRUTH):
        current_row_idx = i + start_offset
        if current_row_idx >= len(cleaned_rows):
            break
            
        cleaned_row = cleaned_rows[current_row_idx]
        correct, total = calculate_field_accuracy(cleaned_row, gt_row)
        
        total_correct += correct
        total_fields += total
        
        acc = (correct / total) * 100
        print(f"Row {current_row_idx:02d} | 정확도: {acc:6.1f}% | Correct: {correct}/{total}")
        
        # 100%가 아닐 경우에만 오답 노트 출력
        if acc < 100:
            print(f"   ㄴ [정답]: {gt_row}")
            print(f"   ㄴ [추출]: {cleaned_row}")

    final_accuracy = (total_correct / total_fields) * 100 if total_fields > 0 else 0
    print("-" * 50)
    print(f"✅ 최종 필드 정확도: {final_accuracy:.2f}%")
    
    # 목표 정확도 검증 (예: 95% 이상 기대)
    assert final_accuracy > 95, f"❌ 최종 정확도가 목표치에 미달합니다: {final_accuracy:.2f}%"

if __name__ == "__main__":
    test_postprocessor_accuracy_comparison()