"""
Streamlit 기반의 금융거래조회서 자동화 프런트엔드 (MVP)

[프로그램 개요]
이 파일은 사용자가 웹 브라우저에서 직접 상호작용하는 '화면(UI)'을 담당합니다.
사용자가 PDF 파일을 업로드하면, 뒷단(Backend)에 있는 로직을 호출하여
표를 추출하고 결과를 엑셀로 내려받을 수 있게 해줍니다.

[주요 기능]
1. PDF 파일 업로드 (Drag & Drop)
2. OCR(광학 문자 인식) 언어 설정
3. 추출된 데이터의 미리보기 표시
4. 결과물 엑셀 다운로드
"""

import io
import tempfile
import zipfile
import concurrent.futures
from pathlib import Path
import csv
import re

# streamlit: 웹 화면을 쉽게 만들어주는 라이브러리
import streamlit as st
# pandas: 데이터(표)를 다루고 엑셀로 변환하는 데 사용하는 라이브러리
import pandas as pd

# 우리가 만든 핵심 로직(PDF에서 표 추출)을 가져옵니다.
from src.extractor import extract_tables_from_pdf
from src import processor
from src.config import Config


# 페이지의 제목과 레이아웃을 설정합니다. (브라우저 탭 이름 등)
st.set_page_config(page_title="Audit Inquiry Automation", layout="wide")


def _save_uploaded_file(uploaded) -> str:
    """
    사용자가 웹으로 업로드한 파일을 임시 저장소에 저장하는 함수입니다.

    [왜 필요한가요?]
    Streamlit으로 업로드된 파일은 처음에 컴퓨터의 메모리(RAM)에만 존재합니다.
    하지만 PDF 처리 라이브러리들은 실제 파일 경로(디스크에 있는 파일)를 필요로 하는 경우가 많습니다.
    따라서 메모리에 있는 내용을 잠시 '임시 파일'로 만들어서 저장해두는 과정입니다.

    Args:
        uploaded: Streamlit 업로더가 반환한 파일 객체

    Returns:
        str: 저장된 임시 파일의 경로 (예: /tmp/tmp1234.pdf)
    """
    # delete=False: 파일을 닫아도 삭제되지 않게 설정 (나중에 읽어야 하므로)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")

    # 사용자가 올린 파일의 내용을 씁니다.
    tmp.write(uploaded.getbuffer())

    # 데이터가 확실히 기록되도록 강제 저장(flush)하고 파일을 닫습니다.
    tmp.flush()
    tmp.close()

    return tmp.name


def _create_excel_bytes(tables: list[pd.DataFrame]) -> bytes:
    """
    추출된 표 데이터(DataFrame 리스트)를 엑셀 파일 형식의 데이터(bytes)로 변환합니다.

    [왜 필요한가요?]
    서버에 엑셀 파일을 실제로 생성해서 저장했다가 다시 읽는 것은 비효율적입니다.
    대신 메모리 상에서 가상의 엑셀 파일을 만들고, 그 자체를 '다운로드' 할 수 있게 해줍니다.

    Args:
        tables: 추출된 표 데이터들이 담긴 리스트

    Returns:
        bytes: 엑셀 파일의 바이너리 데이터 (다운로드 가능한 형태)
    """
    # 메모리 내에 가상의 파일을 생성합니다 (BytesIO)
    buf = io.BytesIO()

    # 엑셀 작성 도구(ExcelWriter)를 엽니다. 엔진은 openpyxl을 사용합니다.
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        # 리스트에 있는 표를 하나씩 꺼내서, 각각 다른 시트(Sheet)에 저장합니다.
        for idx, df in enumerate(tables, start=1):
            df.to_excel(writer, sheet_name=f"table_{idx}", index=False)

    # 파일 포인터를 맨 앞으로 돌립니다. (처음부터 읽어서 다운로드해주기 위함)
    buf.seek(0)
    return buf.read()


def main():
    """
    메인 실행 함수입니다.
    화면의 전체적인 흐름(UI Flow)을 정의합니다.
    """

    # 1. 화면 제목 표시
    st.title("금융거래조회서 표 추출 및 엑셀 변환")

    # 2. 파일 업로드 위젯 표시
    # 사용자가 파일을 올리기 전까지 uploaded 변수는 None입니다.
    # 다중 파일 업로드 허용
    uploaded = st.file_uploader("PDF 파일 업로드", type=["pdf"], accept_multiple_files=True)

    # 3. 추가 옵션 입력 (OCR 언어 설정)
    # lang = st.text_input("OCR 언어 (예: eng+kor)", value="eng+kor")

    # 4. 파일이 업로드되었을 때만 아래 로직을 실행합니다.
    if uploaded is not None:
        # 여러 파일을 업로드했을 경우 리스트로 전달됩니다.
        files = uploaded if isinstance(uploaded, (list, tuple)) else [uploaded]

        st.info(f"업로드 완료: {', '.join([f.name for f in files])}")

        # 실행 버튼
        if st.button("표 탐지 및 OCR 실행 (다중 파일)"):
            # 비동기 동시성 값 로드 (Configurations.csv의 CONF-005 참고)
            def _get_concurrency():
                default = 2  # CONF-005 값(ASYNC_TASK_CONCURRENCY)
                try:
                    # design/Configurations.csv에서 CONF-005를 찾아보되,
                    # 실패하면 기본값을 사용합니다.
                    with open("design/Configurations.csv", encoding="utf-8") as f:
                        for line in f:
                            if "CONF-005" in line:
                                m = re.search(r"(\d+)", line)
                                if m:
                                    return int(m.group(1))
                except Exception:
                    pass
                return default

            concurrency = _get_concurrency()

            # 임시 디렉터리를 만들어 각 파일의 엑셀을 저장합니다.
            with tempfile.TemporaryDirectory() as tmpdir:
                total = len(files)
                st.info(f"총 {total}개 파일을 처리합니다. (동시 작업자: {concurrency})")
                progress_bar = st.progress(0)
                status_text = st.empty()

                results = []  # 생성된 출력 파일 경로 목록

                def _process_one(uploaded_file):
                    # 업로드 파일을 디스크에 저장
                    pdf_path = _save_uploaded_file(uploaded_file)
                    out_path = str(Path(tmpdir) / (Path(uploaded_file.name).stem + ".xlsx"))
                    try:
                        processed = processor.process_pdf_to_excel(pdf_path, out_path)
                        # 처리 결과가 0이면 표를 못 찾은 것이므로 플레이스홀더 엑셀 생성
                        if not Path(out_path).exists():
                            # 빈 엑셀 생성 (결과 없음 표시)
                            import pandas as pd

                            pd.DataFrame({"info": ["No tables found"]}).to_excel(out_path, index=False)
                        return (uploaded_file.name, out_path, None)
                    except Exception as e:
                        # 에러가 발생하면 텍스트 파일로 에러 메시지를 저장
                        err_path = str(Path(tmpdir) / (Path(uploaded_file.name).stem + "_error.txt"))
                        with open(err_path, "w", encoding="utf-8") as ef:
                            ef.write(str(e))
                        return (uploaded_file.name, err_path, str(e))

                # 스레드 풀을 사용해 병렬 처리
                with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
                    futures = [ex.submit(_process_one, f) for f in files]
                    completed = 0
                    for fut in concurrent.futures.as_completed(futures):
                        name, path, error = fut.result()
                        results.append((name, path, error))
                        completed += 1
                        progress_bar.progress(int(completed / total * 100))
                        status_text.text(f"완료: {completed}/{total} - {name} {'(에러)' if error else '(성공)'}")

                # ZIP으로 묶기
                zip_buf = io.BytesIO()
                with zipfile.ZipFile(zip_buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                    for name, path, error in results:
                        arcname = Path(name).stem + Path(path).suffix
                        zf.write(path, arcname=arcname)

                zip_buf.seek(0)

                st.success(f"처리 완료: {total}개 파일 중 {len(results)}개 결과 생성")
                st.download_button(
                    label="모든 결과 ZIP 다운로드",
                    data=zip_buf.getvalue(),
                    file_name="extracted_results.zip",
                    mime="application/zip",
                )


# 이 파일이 직접 실행될 때만 main() 함수를 호출합니다.
if __name__ == "__main__":
    main()