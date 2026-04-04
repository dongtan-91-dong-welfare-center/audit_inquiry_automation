from fastapi import FastAPI, UploadFile, File
import cv2
import numpy as np
import os
from paddleocr import PaddleOCR

# FastAPI 앱 초기화
app = FastAPI(title="Audit OCR Engine API")

# 병렬 연산 라이브러리 충돌 방지
os.environ['KMP_DUPLICATE_LIB_OK'] = 'True'
os.environ['PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK'] = 'True' # 모델 다운로드 체크 경고 제거

# 서버 가동 시 1회만 모델 가중치를 로드하여 메모리에 상주 (속도 최적화)
print("Initializing PaddleOCR Engine...")
# ir_optim은 2.7 버전 이상에서 지원하지 않으므로 제거
ocr_engine = PaddleOCR(use_angle_cls=True, lang='korean')

def group_into_rows(ocr_data: list) -> list:
    """기존 OCRExtractor._group_into_rows 로직 이관"""
    items = []
    for text_block in ocr_data:
        if not text_block or len(text_block) < 2: continue
        box, text_data = text_block[0], text_block[1]
        text = str(text_data[0]).strip()
        if not text: continue
            
        y_coords = [point[1] for point in box]
        x_coords = [point[0] for point in box]
        top = min(y_coords)
        height = max(y_coords) - top
        
        items.append({
            'text': text, 'top': top, 'height': height,
            'left': min(x_coords), 'center_y': top + (height / 2)
        })
        
    if not items: return []
    items.sort(key=lambda x: x['top'])
    
    row_clusters = []
    current_cluster = [items[0]]
    for item in items[1:]:
        avg_y = sum(i['center_y'] for i in current_cluster) / len(current_cluster)
        if abs(item['center_y'] - avg_y) < (item['height'] / 2 + 5):
            current_cluster.append(item)
        else:
            row_clusters.append(current_cluster)
            current_cluster = [item]
    if current_cluster: row_clusters.append(current_cluster)
    
    parsed_rows = []
    for cluster in row_clusters:
        cluster.sort(key=lambda x: x['left'])
        row_data = [x['text'] for x in cluster if x['text']]
        if row_data: parsed_rows.append(row_data)
        
    return parsed_rows

@app.post("/extract")
async def extract_text(file: UploadFile = File(...)):
    """
    메인 애플리케이션(preprocessor.py 결과물)으로부터 바이너리 이미지를 받아
    np.ndarray로 복원한 뒤 OCR을 수행하고 결과를 반환합니다.
    """
    # 1. HTTP 전송을 위해 직렬화된 Byte Array 읽기
    contents = await file.read()
    
    # 2. Byte 데이터를 다시 Numpy 배열로 디코딩 (전처리 파이프라인의 결과물과 동일한 상태로 복구)
    nparr = np.frombuffer(contents, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    # 3. OCR 엔진 구동
    result = ocr_engine.ocr(img)
    
    # 4. 결과 그룹화 및 JSON 반환
    if not result or not result[0]:
        return {"data": []}
        
    parsed_rows = group_into_rows(result[0])
    return {"data": parsed_rows}