import pytest
import os
from pathlib import Path

@pytest.fixture(scope="session")
def project_root():
    """프로젝트 루트 디렉토리를 반환합니다."""
    # tests/ 폴더의 상위 폴더를 루트로 가정
    return Path(__file__).parent.parent

@pytest.fixture(scope="session")
def sample_pdf_path(project_root):
    """테스트용 샘플 PDF 파일의 절대 경로를 반환합니다."""
    path = project_root / "data" / "samples" / "sample_file.pdf"
    if not path.exists():
        pytest.skip(f"테스트용 샘플 파일이 없습니다: {path}")
    return str(path)

@pytest.fixture(scope="session")
def output_dir(project_root):
    """테스트 결과물을 저장할 디렉토리를 반환하고, 없으면 생성합니다."""
    path = project_root / "data" / "test_output"
    os.makedirs(path, exist_ok=True)
    return str(path)
