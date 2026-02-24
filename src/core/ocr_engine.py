#src/core/ocr_engine.py
import re
import cv2
import pytesseract
from pytesseract import Output
import numpy as np
import pandas as pd
from typing import List

class OCRExtractor:
    """
    [AI/OCR 담당자]
    전처리된 이미지(Numpy ndarray)를 입력받아 Tesseract OCR을 구동하고,
    인식된 텍스트들을 위치(좌표) 기반으로 묶어 2차원 리스트로 반환합니다.
    """
    
    def __init__(self, psm: int = 6, lang: str = 'kor+eng'):
        """
        OCR 엔진 초기화 및 환경 설정.
        - psm 6: 단일 균일 텍스트 블록 가정 (표 형태에 적합)
        - lang: 한국어 및 영어 동시 인식
        """
        self.config = f'--oem 3 --psm {psm} -l {lang}'
        # pytesseract는 로컬에 설치된 'Tesseract' 실행파일을 호출하는 래퍼입니다.
        # 따라서 Tesseract에 전달되는 옵션은 명령줄에 붙는 '옵션 문자열' 형태로 전달되어야 합니다.
        # 예: 터미널에서 `tesseract 이미지.jpg 결과물 --oem 3 --psm 6 -l kor+eng` 처럼 동작합니다.
        # 여기서 `self.config`는 위의 명령어 뒤에 붙을 옵션 텍스트를 미리 구성한 값입니다.
        # - oem 3: LSTM 기반 OCR 엔진 사용(기본값)
        # - psm 6: 단일 균일 텍스트 블록 가정 (표 인식에 적합)
        # - lang: 인식할 언어 (예: 'kor+eng')
    def extract_table_data(self, processed_image: np.ndarray) -> List[List[str]]:
        """
        OpenCV로 전처리된 이미지 배열을 받아 텍스트를 추출하고,
        표 형태의 2차원 리스트(List of Lists)로 변환하여 반환합니다.
        
        Args:
            processed_image (np.ndarray): 전처리 파이프라인에서 넘어온 이미지 배열
            
        Returns:
            List[List[str]]: 행(Row) 단위로 텍스트가 묶인 2차원 리스트 
                             예: [['예금종류', '계좌번호'], ['보통예금', '111-222']]
        """
        try:
            # 1. OCR 구동: 글자와 상세 좌표(Bounding Box) 데이터를 DataFrame으로 추출
            data = pytesseract.image_to_data(
                processed_image, 
                config=self.config, 
                output_type=Output.DATAFRAME
            )
        except pytesseract.TesseractNotFoundError:
            raise EnvironmentError("Tesseract가 설치되어 있지 않거나 PATH에 없습니다.")

        # 2. 추출된 데이터를 바탕으로 행(Row) 단위 그룹화 실행
        parsed_rows = self._group_into_rows(data)
        
        return parsed_rows

    def _group_into_rows(self, df: pd.DataFrame) -> List[List[str]]:
        """
        (내부 헬퍼 메서드) 단어들의 Y축 중심좌표를 계산하여 
        동일한 수평선상에 있는 단어들을 같은 행(Row)으로 묶어줍니다.
        """
        # # 빈 텍스트(노이즈) 필터링
        # df = df[df.text.str.strip() != '']
        # 빈칸 제거를 시키고 작업할지는 추후 테스트하면서 결정
        
        # 1. NaN(결측치) 데이터 제거: Tesseract가 만든 텍스트 없는 껍데기 영역(블록, 줄 등) 날리기
        df = df.dropna(subset=['text']).copy()
        
        # 2. 모든 텍스트를 문자열로 확실히 변환 후 앞뒤 공백(스페이스, 엔터 등) 제거
        df['text'] = df['text'].astype(str).str.strip()
        
        # 3. 공백을 다듬었더니 아무것도 안 남은 텅 빈 문자열('') 쓰레기 데이터 날리기
        df = df[df['text'] != '']
        
        # 상단(top) 좌표 기준으로 1차 정렬
        df = df.sort_values(by='top')
        
        if df.empty:
            return []
            
        row_clusters = []
        # to_dict() 메서도는 기본적으로 열 단위로 묶음 생성
        # DataFrame을 딕셔너리 리스트로 변환하여 순회하면서 행(Row) 단위로 묶음 생성
        items = df.to_dict('records')
        current_cluster = [items[0]]
        
        for item in items[1:]:
            # 현재 묶음(행)의 평균 Y 중심점 계산
            cluster_ys = [(i['top'] + i['height']/2) for i in current_cluster]
            avg_y = sum(cluster_ys) / len(cluster_ys)
            
            # 새로 판별할 단어의 Y 중심점 계산
            item_y = item['top'] + item['height']/2
            
            # 허용 오차(글자 높이의 절반 + 5px) 이내면 같은 행으로 편입
            # 스캔 과정에서 테이블이 약간 기울어질 수 있기 때문에 사용하는 조건
            # '금융상품의' , '종류(1)'와 같이 글자 사이가 떨어져 있는 것을 하나의 행으로 인식하고자 하는 코드가 아님.
            # 위와 같은 결과값 조정은 postprocessing 단계에서 별도로 처리할 예정입니다.
            if abs(item_y - avg_y) < (item['height'] / 2 + 5):
                current_cluster.append(item)
            else:
                # 오차를 벗어나면 다음 행으로 넘김
                row_clusters.append(current_cluster)
                current_cluster = [item]
                
        if current_cluster:
            row_clusters.append(current_cluster)
            
        # 각 행 내부에서 X축(left) 좌표 기준으로 왼쪽부터 오른쪽으로 정렬 후 텍스트만 추출
        parsed_rows = []
        for cluster in row_clusters:
            cluster.sort(key=lambda x: x['left'])
            
            row_data = []
            for x in cluster:
                # 정규표현식으로 표 테두리 노이즈(|, 한글 ㅣ, 대괄호 등) 싹 지우기
                cleaned_text = re.sub(r'[|ㅣ\[\]_]', '', x['text']).strip()
                
                # 노이즈를 지우고 나서도 글자가 남아있을 때만 리스트에 추가
                if cleaned_text: 
                    row_data.append(cleaned_text)
            
            # 텅 빈 줄이 아니면 최종 결과에 추가
            if row_data:
                parsed_rows.append(row_data)
                
        return parsed_rows