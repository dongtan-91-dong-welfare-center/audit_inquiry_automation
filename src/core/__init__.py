import os
import sys

# 현재 파일(src/core/__init__.py)의 경로를 기준으로 프로젝트 루트 디렉토리를 계산합니다.
# 1. os.path.abspath(__file__)        -> .../src/core/__init__.py
# 2. os.path.dirname(1번)             -> .../src/core
# 3. os.path.dirname(2번)             -> .../src
# 4. os.path.dirname(3번)             -> .../프로젝트 루트 디렉토리
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 프로젝트 루트가 시스템 경로(sys.path)에 없으면 추가하여 모듈 임포트가 가능하게 합니다.
if project_root not in sys.path:
    sys.path.append(project_root)