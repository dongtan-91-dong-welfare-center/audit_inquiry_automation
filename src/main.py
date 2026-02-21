# src/main.py

import streamlit as st
# TODO: src.core 및 src.utils에서 필요한 모듈들 임포트

def render_ui():
    """
    [UI 담당자]
    Streamlit 화면을 구성하고 사용자 입력을 받습니다.
    """
    # TODO: 페이지 기본 설정 (st.set_page_config)
    # TODO: 타이틀 및 프로그램 설명 작성 (st.title, st.markdown)
    
    # TODO: 회사명 입력 텍스트 박스 구현 (st.text_input) - 엑셀 파일명으로 사용
    # TODO: PDF 파일 다중 업로더 구현 (st.file_uploader, accept_multiple_files=True)
    
    # TODO: '데이터 추출 및 엑셀 생성' 실행 버튼 구현 (st.button)
    pass

def process_workflow(company_name, uploaded_files):
    """
    [메인 워크플로우 담당자]
    업로드된 파일들을 5단계 핵심 파이프라인으로 통과시킵니다.
    """
    # TODO: 프로그레스 바(Progress bar) 초기화
    
    # all_extracted_data = []
    
    # TODO: 업로드된 각 PDF 파일에 대해 반복문 실행
        # 1. pdf_loader: PDF를 이미지 리스트로 변환
        # 2. preprocessor: 각 이미지를 OCR에 적합하게 전처리
        # 3. ocr_engine: 전처리된 이미지에서 표/텍스트 데이터 추출
        # 4. postprocessor (1차): 개별 파일 단위 데이터를 DataFrame으로 구조화
        # all_extracted_data.append(추출된 DataFrame)
        
    # TODO: 4. postprocessor (2차): all_extracted_data의 모든 DataFrame을 하나로 병합
    
    # TODO: 5. excel_builder: 병합된 최종 DataFrame을 '{company_name}.xlsx' 바이트 데이터로 변환
    
    # TODO: Streamlit 다운로드 버튼(st.download_button)을 통해 엑셀 파일 제공
    pass

if __name__ == "__main__":
    # TODO: render_ui() 호출 및 버튼 클릭 시 process_workflow() 실행 로직 연결
    pass