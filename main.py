# main.py

import streamlit as st
import os

from src.core.pdf_loader import PDFLoader, DEFAULT_START_PAGE
from src.core.preprocessor import ImagePreprocessor
from src.core.ocr_engine import OCRExtractor
from src.core.native_extractor import NativeExtractor
from src.core.postprocessor import PostProcessor
from src.core.excel_builder import ExcelBuilder

def render_ui():
    """
    Streamlit 화면을 구성하고 사용자 입력을 받습니다.
    """
    st.set_page_config(page_title="감사조회서 자동화 시스템", layout="wide")
    st.title("📄 감사조회서 데이터 추출 및 엑셀 자동화")
    st.markdown("업로드된 금융거래조회서(PDF)를 분석하여 엑셀 파일로 변환합니다.")

    # 설정 영역
    # 가장 기본적인 조회서 양식을 가정하고 입력하지 않으면 4페이지까지 OCR 처리하도록 기본값을 설정
    # TODO: 실제 업무에서는 송장이 PDF 맨 앞 페이지에 포함되어 있으므로 기본값을 5페이지로 변경
    with st.expander("⚙️ 처리 설정", expanded=True):
        end_page = st.number_input("종료 페이지 (선택)", min_value=DEFAULT_START_PAGE, value=4, step=1, help=f"OCR을 수행할 마지막 페이지 번호(최소 {DEFAULT_START_PAGE}페이지 이상)")
        use_gpu = st.checkbox("GPU 가속 사용", value=False, help="PaddleOCR의 GPU 연산을 활성화합니다. (paddlepaddle-gpu 설치 필요)")

    # 파일 업로드 영역
    uploaded_files = st.file_uploader(
        "PDF 파일들을 업로드하세요",
        type=["pdf"],
        accept_multiple_files=True
    )

    # 실행 버튼
    if st.button("🚀 데이터 추출 및 엑셀 생성", type="primary"):
        if not uploaded_files:
            st.warning("먼저 PDF 파일을 하나 이상 업로드해주세요.")
        else:
            process_workflow(uploaded_files, DEFAULT_START_PAGE, end_page, use_gpu)

def process_workflow(uploaded_files, start_page, end_page, use_gpu):
    """
    업로드된 파일들을 핵심 파이프라인으로 통과시키고 최종 엑셀 파일을 생성합니다.
    """
    total_files = len(uploaded_files)
    progress_bar = st.progress(0, text="초기화 중...")

    target_company_name = ""
    output_path = ""

    st.info("AI 모델 및 파이프라인 엔진을 초기화 중입니다. 잠시만 기다려주세요...")
    preprocessor = ImagePreprocessor()
    ocr = OCRExtractor(use_gpu=use_gpu)
    postprocessor = PostProcessor()
    builder = ExcelBuilder()

    # Native PDF 처리를 위한 인스턴스 생성
    native_extractor = NativeExtractor()

    # 업로드된 PDF 파일들을 순차적으로 처리
    for idx, file in enumerate(uploaded_files):
        status_text = f"[{idx+1}/{total_files}] '{file.name}' 처리 중..."
        progress_bar.progress(idx / total_files, text=status_text)

        try:
            # 1. PDF Loader 초기화 및 메타데이터(파일명 정보) 파싱
            loader = PDFLoader(file)

            # 회사명을 추출하여 대표 이름으로 설정
            # 조회처명을 추출하여
            target_company_name = loader.metadata.get("company_name")
            bank_name = loader.metadata.get("bank_name")
            if idx == 0:
                st.info(f"파싱된 감사대상회사: **{target_company_name}**")

            # Native PDF인지 스캔 이미지인지 판별
            is_native = loader.is_native_pdf()

            if is_native:
                st.info(f"[{file.name}] 디지털 생성(Native) PDF를 감지했습니다. 고속 추출 모드로 전환합니다.")
                # 전처리, OCR 과정을 생략하고 바로 데이터 추출
                extracted_tables = native_extractor.extract_table_data(file, start_page, end_page)
            else:
                # 기존 방식 (이미지 변환 -> 전처리 -> OCR 추출)
                # 페이지 이미지 추출
                images = loader.convert_to_images(start_page=start_page, end_page=end_page)
                # 2. Preprocessor
                table_images = preprocessor.process_pages(images)
                # 3. OCR_Engine
                extracted_tables = ocr.extract_table_data(table_images)

            # 4. Postprocessor
            processed_tables = postprocessor.process_data(extracted_tables, bank_name)
            # 5. Excel_Builder
            output_path = builder.export_to_excel(
                company_name=target_company_name,
                bank_name=bank_name,
                processed_tables=processed_tables
            )
        except Exception as e:
            error_name = type(e).__name__
            st.error(f"파일 '{file.name}' 건너뜀 [{error_name}]: {e}")
            continue

    progress_bar.progress(1.0, text="데이터 추출 및 엑셀 저장 완료!")
    st.success("🎉 모든 파일의 처리가 완료되었습니다!")

    # ExcelBuilder가 정상적으로 구동되어 output_path(str)가 반환되었는지 확인 & 파일이 실제로 존재하는지 검증
    if output_path and os.path.exists(output_path):
        # 파일이 저장된 절대 경로를 화면에 표시
        absolute_path = os.path.abspath(output_path)
        st.info(f"📂 엑셀 파일이 다음 경로에 안전하게 저장되었습니다:\n\n`{absolute_path}`")
        # excel_builder.py에서 ws.append()를 사용하고 있어서 행 자체를 삭제하지 않고 delete로 삭제하면 데이터가 남아있는 것으로 간주됩니다.
        st.markdown(
            "### :red[🚨 주의사항 : 불가피하게 동일한 PDF를 다시 돌려야 하는 경우,]"
        )
        st.markdown(
            "#### :red[엑셀에서 내용만 지우지 말고 처음 입력되었던 **'행 자체를 우클릭하여 삭제'**한 후 다시 구동해 주세요!]"
        )
    else:
        st.error("엑셀 파일 생성에 실패했거나 경로를 찾을 수 없습니다.")

    # TODO: 웹으로 서비스를 제공하게 되는 경우에 다운로드 버튼을 제공할 예정입니다.

if __name__ == "__main__":
    # 프로그램 실행 시 메인 UI 렌더링 함수 호출
    render_ui()
