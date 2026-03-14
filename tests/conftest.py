# tests/conftest.py
"""
pytest가 실행될 때 자동으로 로드되는 설정 및 공유 리소스 파일
여러 테스트 파일(.py)에서 공통으로 사용할 데이터(Fixture)나 환경 설정을 한곳에서 관리하기 위해 사용
"""
import sys
import numpy as np
import pytest
from pathlib import Path
from unittest.mock import MagicMock

# 프로젝트 루트 디렉토리를 sys.path에 추가
# sys.path: 파이썬이 모듈이나 패키지를 찾을 때 훑어보는 경로 목록
# sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))
# PROJECT_ROOT = Path(__file__).parent
# sys.path.insert(0, str(PROJECT_ROOT))
"""
os.path.dirname(__file__): 본 파일의 경로(프로젝트 루트/tests/conftest.py)
os.path.join(os.path.dirname(__file__), '../'): 프로젝트 루트의 상대 경로
os.path.abspath(os.path.join(os.path.dirname(__file__), '../')): 프로젝트 루트의 절대 경로
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))): 프로젝트 루트의 절대 경로를 파이썬 검색 경로의 0번인덱스(가장 우선 순위)로 추가
"""

# 이미지 생성 팩토리
# Preprocessor와 PdfLoader에서 규격화된 데이터를 사용하여 테스트하기 위함
@pytest.fixture
def mock_image_factory():
    """
    테스트용 가짜 이미지를 생성하는 팩토리입니다.
    usage: mock_image_factory(height=500, width=500, channels=3)
    """
    def _create_image(height=1000, width=1000, channels=3, color=255):
        if channels == 1:
            shape = (height, width)
        else:
            shape = (height, width, channels)
        return np.full(shape, color, dtype=np.uint8)
    return _create_image

# PDF 파일 객체 모킹
@pytest.fixture
def mock_pdf_file():
    """
    PDFLoader 입력으로 들어갈 파일 객체를 모킹합니다.
    """
    mock_file = MagicMock()
    mock_file.name = "(주)삼성전자_2_중소기업은행.pdf"
    mock_file.size = 1024 * 1024 # 1MB
    mock_file.read.return_value = b"%PDF-1.4 mock content"
    return mock_file

# 공통으로 사용할 실제 PDF 경로 Fixture
# pytest 명령어를 입력해 테스트를 시작할 때 딱 한 번 실행되어 생성되고, 모든 테스트 파일의 테스트 함수가 종료될 때까지 유지/공유하는 함수
@pytest.fixture(scope="session")
def scan_pdf_path():
    """
    테스트에 필요한 실제 스캔본 PDF 경로를 반환합니다.
    scope="session"으로 설정하여 전체 테스트 기간 중 딱 한 번만 경로를 확인합니다.
    """
    # 프로젝트 루트 기준 경로 설정
    project_root = Path(__file__).parent.parent
    path = project_root / "tests" / "data" / "input" / "(주)삼성전자_1_농협은행.pdf"

    if not path.exists():
        # 파일이 없을 경우 테스트를 skip하게 만듦
        pytest.skip(f"테스트용 파일이 존재하지 않습니다: {path}")

    return str(path)

# # Pytest 마커 정의 (커스텀 태그 등록)
# def pytest_configure(config):
#     """
#     커스텀 마커를 등록하여 'pytest -m integration' 처럼 실행할 수 있게 합니다.
#     """
#     config.addinivalue_line("markers", "integration: 실제 PDF 파일을 사용하는 무거운 통합 테스트")
#     config.addinivalue_line("markers", "unit: Mock을 사용하는 가벼운 단위 테스트")
