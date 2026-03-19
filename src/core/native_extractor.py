import pdfplumber
from typing import List

class NativeExtractor:
    """
    [Native PDF 담당자]
    디지털 방식으로 생성된(Native) PDF의 경우, 무거운 전처리와 OCR 과정을 거치지 않고
    pdfplumber를 이용하여 텍스트와 표 데이터를 직접 파싱하는 우회(Bypass) 추출기입니다.
    """

    def extract_table_data(self, pdf_stream, start_page: int, end_page: int) -> List[List[List[str]]]:
        """
        pdfplumber를 사용하여 디지털 PDF에서 직접 표를 추출하고,
        OCRExtractor와 동일한 3차원 리스트 형태(List[List[List[str]]])로 병합하여 반환합니다.

        Args:
            pdf_stream: Streamlit에서 업로드된 파일 스트림 또는 파일 경로
            start_page: 추출을 시작할 페이지 번호 (1부터 시작)
            end_page: 추출을 종료할 페이지 번호

        Returns:
            List[List[List[str]]]: 여러 표의 데이터가 담긴 3차원 리스트
        """
        all_tables = []

        # 파일 포인터를 처음으로 되돌려 안전하게 다시 읽을 수 있도록 합니다.
        if hasattr(pdf_stream, 'seek'):
            pdf_stream.seek(0)

        with pdfplumber.open(pdf_stream) as pdf:
            total_pages = len(pdf.pages)
            if end_page is None:
                end_page = total_pages

            # 슬라이싱 인덱스는 0부터 시작하므로 start_page-1
            target_pages = pdf.pages[start_page - 1:end_page]

            for page in target_pages:
                # 테이블 추출 (결과: List[List[List[str]]])
                # page.extract_tables()는 해당 페이지 내의 모든 표를 찾아 반환합니다.
                tables = page.extract_tables()

                if tables:
                    # 표 내부의 빈 셀(None)을 빈 문자열('')로 치환하고, 좌우 공백을 제거하여 정제합니다.
                    cleaned_tables = []
                    for table in tables:
                        cleaned_table = []
                        for row in table:
                            # row가 유효한 리스트인지 확인
                            if not row:
                                continue

                            cleaned_row = []
                            for cell in row:
                                # 셀에 값이 없으면 빈 문자열, 있으면 앞뒤 공백 제거
                                cleaned_cell = str(cell).strip() if cell is not None else ""
                                cleaned_row.append(cleaned_cell)

                            # 정제된 행이 내용이 있는지 확인 (모두 빈칸인 행은 제외)
                            if any(cell_content != "" for cell_content in cleaned_row):
                                cleaned_table.append(cleaned_row)

                        if cleaned_table:
                            cleaned_tables.append(cleaned_table)

                    # 페이지별로 추출된 표들을 하나의 큰 리스트에 병합
                    all_tables.extend(cleaned_tables)

        return all_tables
