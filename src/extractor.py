"""
데이터 추출기(Extractor): PDF 문서 분석 및 데이터 추출 엔진

[모듈 개요]
PDF 파일 내부를 분석하여 우리가 원하는 '표(Table)' 데이터를 찾아내는 핵심 모듈입니다.
두 가지 전략을 상황에 따라 유연하게 사용합니다.

[핵심 전략: Hybrid Approach]
1. 1차 시도 (고속/정확): '텍스트형 PDF'인 경우
   - pdfplumber 라이브러리를 사용하여 텍스트 레이어를 직접 읽습니다.
   - 속도가 빠르고 정확도가 매우 높습니다.

2. 2차 시도 (저속/강력): '이미지형(스캔) PDF'인 경우
   - pdfplumber가 표를 찾지 못하면, 해당 페이지를 이미지로 변환합니다.
   - 컴퓨터 비전(OpenCV) 기술로 표의 테두리(Contour)나 격자(Grid)를 찾습니다.
   - OCR(광학 문자 인식)을 통해 이미지 속의 글자를 텍스트로 변환합니다.

[구현된 요구사항]
- Req-111 (다중 문서 유형 처리)
- Func-113 (스캔본 이미지 전처리)
"""

from typing import List, Optional
import re

# PDF 처리 라이브러리 (ADR-001)
import pdfplumber
# 수치 연산 및 이미지 처리를 위한 라이브러리
import numpy as np
import pandas as pd
from PIL import Image

# 우리가 만든 OCR 모듈 (글자 인식 담당)
from .ocr import image_to_text


def extract_tables_from_pdf(pdf_path: str) -> List[pd.DataFrame]:
    """
    하나의 PDF 파일 전체를 순회하며 모든 표를 추출합니다.

    Args:
        pdf_path (str): 처리할 PDF 파일의 경로

    Returns:
        List[pd.DataFrame]: 추출된 표들의 리스트 (각 표는 엑셀 시트 하나에 대응됩니다)
    """
    tables: List[pd.DataFrame] = []

    # PDF 파일을 엽니다.
    with pdfplumber.open(pdf_path) as pdf:
        # 각 페이지를 하나씩 넘기며 검사합니다.
        for page in pdf.pages:
            # [전략 1] pdfplumber 자체 기능으로 표 추출 시도
            raw_tables = page.extract_tables()

            if raw_tables:
                # 텍스트 레이어가 살아있는 PDF라면 여기서 표가 발견됩니다.
                for t in raw_tables:
                    df = pd.DataFrame(t)
                    df = _normalize_df(df) # 데이터 정제 (빈칸 처리 등)
                    tables.append(df)
            else:
                # [전략 2] 표를 못 찾았다면 '스캔본'일 확률이 높습니다.
                # 이미지 처리 방식으로 전환하여 표를 강제로 찾아냅니다.
                found = _tables_from_image_page(page)
                tables.extend(found)

    # Req-113: 다중 페이지에 걸친 동일한 구조의 표들을 병합하여 하나의 표로 반환
    return _merge_consecutive_tables(tables)


def _merge_consecutive_tables(tables: List[pd.DataFrame]) -> List[pd.DataFrame]:
    """
    연속된 표들의 컬럼(헤더)이 동일하면 하나로 병합합니다. (Func-121)

    - 순서대로 순회하며 현재 테이블의 컬럼명이 이전 테이블의 컬럼명과
      완전히 일치하면 pd.concat으로 병합하고 인덱스를 재설정합니다.
    - 그렇지 않다면 새로운 표로 취급합니다.
    """
    if not tables:
        return []

    merged: List[pd.DataFrame] = []
    prev = tables[0]
    for cur in tables[1:]:
        # 컬럼명이 완전히 동일한지 비교
        if list(cur.columns) == list(prev.columns):
            # 동일하면 병합
            prev = pd.concat([prev, cur], ignore_index=True)
        else:
            # 다르면 이전 테이블을 결과에 추가하고 현재를 다음 prev로 설정
            merged.append(prev.reset_index(drop=True))
            prev = cur

    # 마지막 누락된 테이블 추가
    merged.append(prev.reset_index(drop=True))
    return merged


def _normalize_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    추출된 표 데이터(DataFrame)를 깔끔하게 정리합니다.
    - None이나 NaN 같은 결측치를 빈 문자열("")로 바꿉니다.
    - 앞뒤 공백을 제거합니다. (예: " 100 " -> "100")
    """
    return df.fillna("").map(lambda x: str(x).strip())


def _tables_from_image_page(page) -> List[pd.DataFrame]:
    """
    [이미지 처리 방식 1: 윤곽선(Contour) 기반]
    페이지 전체를 이미지로 변환한 뒤, '네모난 상자(표 영역)'를 찾아서 내용을 읽습니다.

    [동작 원리]
    1. 페이지를 그림(Image)으로 변환
    2. 그림을 흑백으로 바꾸고, 선을 뚜렷하게 만듦 (전처리)
    3. 가로선과 세로선이 교차하는 '격자 무늬'를 찾음
    4. 격자 무늬들의 외곽선(Contour)을 따서 표라고 추정되는 영역을 잘라냄
    5. 잘라낸 영역을 OCR(글자 인식)에게 보내 텍스트로 변환
    """
    try:
        # 해상도 300dpi로 이미지를 뜹니다. (해상도가 높아야 글자가 잘 보임)
        pil_img: Image.Image = page.to_image(resolution=300).original
    except Exception:
        return []

    # OpenCV(컴퓨터 비전 라이브러리)를 사용하여 이미지 분석 시작
    try:
        import cv2

        # 1. 이미지 색상 변환 (RGB -> BGR -> Grayscale)
        # 컴퓨터가 선을 찾기 쉽도록 흑백으로 만듭니다.
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        # 2. 이진화 (Thresholding)
        # 배경은 검은색, 글자와 선은 흰색으로 만듭니다.
        th = cv2.adaptiveThreshold(~gray, 255, cv2.ADAPTIVE_THRESH_MEAN_C, cv2.THRESH_BINARY, 15, -2)

        # 3. 수평선과 수직선 분리 검출
        # 가로로 긴 막대 필터와 세로로 긴 막대 필터를 사용하여 선만 남깁니다.
        horizontal = th.copy()
        vertical = th.copy()

        cols = horizontal.shape[1]
        horizontal_size = max(1, cols // 30)
        # 가로선 검출 필터
        horiz_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (horizontal_size, 1))
        horizontal = cv2.erode(horizontal, horiz_structure)
        horizontal = cv2.dilate(horizontal, horiz_structure)

        rows = vertical.shape[0]
        vertical_size = max(1, rows // 30)
        # 세로선 검출 필터
        vert_structure = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vertical_size))
        vertical = cv2.erode(vertical, vert_structure)
        vertical = cv2.dilate(vertical, vert_structure)

        # 4. 표 격자 생성
        # 가로선과 세로선을 합치면 표 모양의 격자가 나옵니다.
        mask = cv2.add(horizontal, vertical)

        # 5. 윤곽선(Contours) 찾기
        # 격자 모양의 테두리를 찾습니다.
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        candidates = []
        for cnt in contours:
            x, y, w, h = cv2.boundingRect(cnt)
            # 너무 작은 영역(노이즈)은 표가 아니라고 판단하고 무시합니다.
            if w < 50 or h < 30:
                continue
            candidates.append((x, y, w, h))

        # 6. 표 순서 정렬 (좌상단 -> 우하단 순서)
        # 문서 흐름대로 표를 읽기 위함입니다.
        candidates = sorted(candidates, key=lambda b: (b[1], b[0]))

        dfs: List[pd.DataFrame] = []
        for (x, y, w, h) in candidates:
            # 원본 이미지에서 표 영역만 잘라냅니다(Crop).
            crop = img[y : y + h, x : x + w]
            pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))

            # 잘라낸 이미지를 OCR에 넣어 글자를 읽습니다.
            text = image_to_text(pil_crop)

            # 읽은 글자를 행/열 구조의 데이터(DataFrame)로 변환합니다.
            df = _parse_ocr_text_to_df(text)
            if df is not None:
                dfs.append(df)

        return dfs

    except Exception:
        # [Fallback] OpenCV 처리에 실패하거나 설치되어 있지 않은 경우
        # 정교한 표 추출을 포기하고, 페이지 전체를 통째로 OCR 돌려서 텍스트를 읽습니다.
        text = image_to_text(pil_img)
        df = _parse_ocr_text_to_df(text)
        return [df] if df is not None else []


def extract_tables_from_image(pil_img: Image.Image) -> List[pd.DataFrame]:
    """
    [이미지 처리 방식 2: 격자(Grid) 교차점 기반]
    이미지에서 표를 감지하고, '셀(Cell)' 단위로 쪼개서 인식합니다.

    *참고: 이 함수는 _tables_from_image_page보다 더 정밀하게(셀 단위로) 표를 뜯어내고 싶을 때 사용됩니다.
    (현재 코드 흐름상 _tables_from_image_page 내에서 호출되지는 않지만, 독립적으로 사용 가능한 강력한 기능입니다.)

    [동작 원리]
    1. 가로선/세로선을 찾습니다. (위와 동일)
    2. 선들이 만나는 '교차점'을 찾습니다.
    3. 교차점 좌표를 기준으로 엑셀 칸처럼 영역을 나눕니다.
    4. 각 칸(Cell)마다 이미지를 잘라서 OCR을 수행합니다. -> 인식률 대폭 향상
    """
    try:
        import cv2

        # ... (전처리 과정은 위와 유사하므로 생략) ...
        img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        _, bw = cv2.threshold(~gray, 128, 255, cv2.THRESH_BINARY | cv2.THRESH_OTSU)

        # 구조 요소 사이즈 설정
        cols = bw.shape[1]
        rows = bw.shape[0]
        horiz_size = max(1, cols // 30)
        vert_size = max(1, rows // 30)

        horiz_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (horiz_size, 1))
        vert_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (1, vert_size))

        # 가로선/세로선 추출
        horizontal = cv2.erode(bw, horiz_kernel)
        horizontal = cv2.dilate(horizontal, horiz_kernel)

        vertical = cv2.erode(bw, vert_kernel)
        vertical = cv2.dilate(vertical, vert_kernel)

        # [핵심] 교차점(Intersections) 찾기
        # 가로선과 세로선이 겹치는 부분(AND 연산)이 바로 셀의 모서리입니다.
        intersections = cv2.bitwise_and(horizontal, vertical)

        # 교차점들의 좌표를 통해 표의 행(Row)과 열(Col) 라인 위치를 파악합니다.
        def _line_positions(binary, axis=0):
            # 픽셀 합계를 통해 선이 있는 위치를 찾습니다.
            s = binary.sum(axis=axis)
            pts = []
            in_run = False
            start = 0
            for i, val in enumerate(s):
                if val > 0 and not in_run:
                    in_run = True
                    start = i
                elif val == 0 and in_run:
                    in_run = False
                    pts.append((start + i - 1) // 2) # 선의 두께를 고려해 중심점 계산
            if in_run:
                pts.append((start + len(s) - 1) // 2)
            return pts

        xs = _line_positions(intersections, axis=0) # 세로선 위치들 (x좌표)
        ys = _line_positions(intersections, axis=1) # 가로선 위치들 (y좌표)

        # 격자가 제대로 형성되지 않았다면(선이 2개 미만) 표가 아닙니다.
        if len(xs) < 2 or len(ys) < 2:
            return []

        # [셀 단위 순회]
        # 찾은 좌표를 바탕으로 루프를 돌며 각 셀을 하나씩 잘라냅니다.
        tables: List[pd.DataFrame] = []
        nrows = len(ys) - 1
        ncols = len(xs) - 1
        cells = [["" for _ in range(ncols)] for _ in range(nrows)]

        for r in range(nrows):
            for c in range(ncols):
                # 현재 셀의 좌표 계산
                x1 = xs[c]
                x2 = xs[c + 1]
                y1 = ys[r]
                y2 = ys[r + 1]

                # 경계선(테두리)을 포함하면 OCR 오인식이 생길 수 있으므로,
                # 안쪽으로 살짝(pad=2px) 좁혀서 자릅니다.
                pad = 2
                x1s = max(0, x1 + pad)
                x2s = min(img.shape[1], x2 - pad)
                y1s = max(0, y1 + pad)
                y2s = min(img.shape[0], y2 - pad)

                if x2s <= x1s or y2s <= y1s:
                    text = ""
                else:
                    # 셀 이미지 Crop -> OCR 수행
                    crop = img[y1s:y2s, x1s:x2s]
                    pil_crop = Image.fromarray(cv2.cvtColor(crop, cv2.COLOR_BGR2RGB))
                    text = image_to_text(pil_crop) # 여기서 '이 셀의 값'이 나옵니다.

                cells[r][c] = text.strip()

        # 2차원 리스트(cells)를 DataFrame으로 변환
        df = pd.DataFrame(cells)
        return [df]

    except Exception:
        return []


def _parse_ocr_text_to_df(text: str) -> Optional[pd.DataFrame]:
    """
    [텍스트 파싱]
    OCR이 통째로 읽어온 텍스트 덩어리를 분석하여 표 구조로 만듭니다.

    규칙:
    1. 줄바꿈(\n)은 새로운 '행(Row)'으로 봅니다.
    2. 연속된 공백(2칸 이상)이나 탭(\t)은 '열(Column)' 구분자로 봅니다.
    3. 열이 2개 이상이어야 표로 인정합니다.
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    if not lines:
        return None

    # 정규식: 공백 2개 이상(\s{2,}) 또는 탭(\t)을 기준으로 쪼갭니다.
    rows = [re.split(r'\s{2,}|\t', ln) for ln in lines]

    max_cols = max(len(r) for r in rows)
    if max_cols < 2:
        return None # 열이 하나뿐이면 표가 아니라고 판단

    # 모든 행의 길이를 맞춥니다 (빈칸 채우기)
    norm_rows = [r + [''] * (max_cols - len(r)) for r in rows]

    df = pd.DataFrame(norm_rows).map(lambda x: str(x).strip())
    return df