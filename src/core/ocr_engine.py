#src/core/ocr_engine.py
import cv2
import numpy as np
from typing import List
from paddleocr import PaddleOCR


class OCRExtractor:
    """
    [AI/OCR 담당자]
    전처리된 이미지(Numpy ndarray)를 입력받아 PaddleOCR을 구동하고,
    인식된 텍스트들을 위치(좌표) 기반으로 묶어 3차원 리스트로 반환합니다.
    """
    
    def __init__(self, lang: str = 'korean'):
        """
        PaddleOCR 엔진 초기화 및 환경 설정.
        - lang: 'korean' (한국어 및 영어 동시 인식 지원)
        - use_angle_cls: 텍스트 방향 자동 보정 활성화 (기울어진 글자 교정)
        """
        # 처음 실행 시 모델 가중치를 다운로드하므로 약간의 시간이 소요될 수 있습니다.
        # show_log=False 파라미터는 버전 호환성 문제로 제외하여 기본값으로 실행합니다.
        self.ocr = PaddleOCR(use_angle_cls=True, lang=lang)

    def extract_table_data(self, table_images: List[np.ndarray]) -> List[List[List[str]]]:
        """
        OpenCV로 전처리된 여러 개의 표 이미지 배열(리스트)을 받아 각각 텍스트를 추출하고,
        표 형태의 3차원 리스트(List of List of Lists)로 변환하여 반환합니다.
        
        [아키텍처 설계 근거: List[List[List[str]]] 변환 이유]
        Tesseract(DataFrame 반환), PaddleOCR(튜플/리스트 반환), Google Vision API(JSON 반환) 등 
        사용하는 OCR 프레임워크나 라이브러리에 따라 도출되는 결과값의 데이터 형태가 모두 다릅니다.
        따라서 본 엔진의 최종 출력을 가장 범용적인 '3차원 문자열 리스트'로 표준화하여 반환함으로써, 
        추후 다른 OCR 엔진으로 교체하더라도 뒷단의 후처리 담당(postprocessor.py) 로직을 
        수정할 필요가 없도록 유지보수성과 확장성을 확보하였습니다.
        
        Args:
            table_images (List[np.ndarray]): 전처리 파이프라인에서 넘어온 표 이미지 배열들의 리스트
            
        Returns:
            List[List[List[str]]]: 여러 표의 데이터가 담긴 3차원 리스트 
                             예: [ [['표1-예금종류', '계좌번호'], ['보통예금', '111-222']], [['표2-대출', '금액']] ]
        """
        all_tables_data = []
        
        for table_image in table_images:
            # 1. OCR 구동: 글자와 상세 좌표(Bounding Box) 데이터를 리스트 형태로 추출
            # 결과물 형태: [  [  [  [x1,y1],[x2,y2],[x3,y3],[x4,y4]  ], ('텍스트', 신뢰도)  ], ...]
            result = self.ocr.ocr(table_image)

            # 빈 껍데기 표([None])거나 인식된 데이터([[]])가 아예 없으면 패스
            # result[0]은 1번 표 이미지에서 인식된 텍스트와 좌표 데이터의 리스트입니다.
            if not result or not result[0]:
                continue
                
            # 2. 추출된 데이터를 바탕으로 행(Row) 단위 그룹화 실행
            # OCR 결과물에서 좌표, 신뢰도 등의 데이터는 제거한 채 텍스트만 추출하여 2차원 리스트로 묶어주는 헬퍼 메서드
            parsed_rows = self._group_into_rows(result[0])
            
            # 3. 유효한 행 데이터가 추출된 경우에만 최종 결과에 추가
            if parsed_rows:
                all_tables_data.append(parsed_rows)
                
        return all_tables_data

    def _group_into_rows(self, ocr_data: list) -> List[List[str]]:
        """
        (내부 헬퍼 메서드) 단어들의 Y축 중심좌표를 계산하여 
        동일한 수평선상에 있는 단어들을 같은 행(Row)으로 묶어줍니다.
        ocr_data는 한 개의 표 이미지에서 추출된 텍스트와 좌표 데이터의 리스트입니다.
        """
        items = []
        
        # 1. 전처리 및 정제: PaddleOCR 결과물에서 안전하게 좌표와 텍스트 추출
        for text_block in ocr_data:
            # text_block 형식이 유효한지 안전하게 검사 (방어적 프로그래밍)
            """
            text_block은 [  [x1,y1],[x2,y2],[x3,y3],[x4,y4]  ], ('텍스트', 신뢰도)  ] 형태의 한 개 단어 블록입니다.
            isinstance(객체,(list,tuple))는 객체가 리스트나 튜플인지 확인하는 파이썬 내장 함수로 여기서 (타입1, 타입2)는 OR 조건입니다.
            현재의 paddleocr은 list 형태로 결과물을 반환하지만, 혹시 모를 버전 업이나 다른 OCR 엔진으로 교체 시 튜플 형태로 반환될 가능성도 대비하여 유연하게 검사합니다.
            len(text_block) < 2 조건은 text_block이 최소한 좌표와 텍스트 데이터를 모두 포함하는지 확인하는 안전장치입니다.
            """
            if not text_block or not isinstance(text_block, (list, tuple)) or len(text_block) < 2:
                continue
            
            box = text_block[0]
            text_data = text_block[1]
            
            # 텍스트 데이터가 비어있어 발생하는 IndexError 엣지 케이스 완벽 차단
            if not text_data or not isinstance(text_data, (list, tuple)) or len(text_data) == 0:
                continue
                
            # 앞뒤 공백(스페이스, 엔터 등) 제거 후 텅 빈 문자열은 버림
            # text_data는 ('텍스트', 신뢰도) 형태이므로 text_data[0]이 실제 텍스트입니다.
            text = str(text_data[0]).strip()
            if not text:
                continue
                
            # Bounding Box 좌표값이 올바른 형태인지 확인
            if not isinstance(box, (list, tuple)) or len(box) == 0:
                continue
                
            try:
                # 4개의 꼭짓점 좌표에서 Y축, X축 리스트 분리
                y_coords = [point[1] for point in box]
                x_coords = [point[0] for point in box]
                
                # 영역의 최상단(top), 높이(height), 좌측(left) 계산
                """
                컴퓨터 비전에서는 일반적으로 좌표계의 원점(0,0)이 이미지의 왼쪽 상단에 위치하기 때문에,
                Y축은 아래로 갈수록 증가하고 X축은 오른쪽으로 갈수록 증가합니다. 따라서 top은 Y좌표 중 가장 작은 값이 됩니다.
                """
                top = min(y_coords)
                height = max(y_coords) - top
                left = min(x_coords)
                
                items.append({
                    'text': text,
                    'top': top,
                    'height': height,
                    'left': left,
                    'center_y': top + (height / 2) # Y축 중심점 계산
                })
            except (IndexError, TypeError):
                # 좌표 데이터 구조가 이상하게 반환된 특수 케이스 무시
                continue
                
        if not items:
            return []
            
        # 2. 상단(top) 좌표 기준으로 전체 단어 1차 세로 정렬
        items.sort(key=lambda x: x['top'])
        
        row_clusters = []
        current_cluster = [items[0]]
        
        # 3. Y축 중심점(center_y)을 기준으로 행(Row) 묶기
        for item in items[1:]:
            # 현재 묶음(행)의 평균 Y 중심점 계산
            cluster_ys = [i['center_y'] for i in current_cluster]
            avg_y = sum(cluster_ys) / len(cluster_ys)
            
            # 허용 오차(글자 높이의 절반 + 5px) 이내면 같은 행으로 편입
            # 스캔 과정에서 테이블이 약간 기울어질 수 있기 때문에 사용하는 조건
            # '금융상품의' , '종류(1)'와 같이 글자 사이가 떨어져 있는 것을 하나의 행으로 인식하고자 하는 코드가 아님.
            # 위와 같은 결과값 조정은 postprocessing 단계에서 별도로 처리할 예정입니다.
            if abs(item['center_y'] - avg_y) < (item['height'] / 2 + 5):
                current_cluster.append(item)
            else:
                # 오차를 벗어나면 다음 줄(행)으로 넘김
                row_clusters.append(current_cluster)
                current_cluster = [item]
                
        # 마지막 남은 묶음 털어내기
        if current_cluster:
            row_clusters.append(current_cluster)
            
        # 4. 각 행 내부에서 X축(left) 좌표 기준으로 왼쪽부터 오른쪽으로 정렬 후 텍스트만 추출
        parsed_rows = []
        for cluster in row_clusters:
            cluster.sort(key=lambda x: x['left'])
            
            # 구조화가 끝났으므로 딕셔너리에서 순수 텍스트(알맹이)만 리스트로 묶음
            row_data = [x['text'] for x in cluster if x['text']]
            
            if row_data:
                parsed_rows.append(row_data)
                
        return parsed_rows