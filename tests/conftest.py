# tests/conftest.py
"""
pytest가 실행될 때 자동으로 로드되는 설정 및 공유 리소스 파일
여러 테스트 파일(.py)에서 공통으로 사용할 데이터(Fixture)나 환경 설정을 한곳에서 관리하기 위해 사용
"""
import sys
import os

# 프로젝트 루트 디렉토리를 sys.path에 추가
# sys.path: 파이썬이 모듈이나 패키지를 찾을 때 훑어보는 경로 목록
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../')))

"""
os.path.dirname(__file__): 본 파일의 경로(프로젝트 루트/tests/conftest.py)
os.path.join(os.path.dirname(__file__), '../'): 프로젝트 루트의 상대 경로
os.path.abspath(os.path.join(os.path.dirname(__file__), '../')): 프로젝트 루트의 절대 경로
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../'))): 프로젝트 루트의 절대 경로를 파이썬 검색 경로의 0번인덱스(가장 우선 순위)로 추가
"""
