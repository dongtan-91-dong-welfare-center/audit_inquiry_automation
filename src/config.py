"""
설정(Configuration) 관리 모듈

[모듈 개요]
프로그램이 실행될 때 필요한 모든 '환경 설정값'을 한곳에서 관리하는 제어판입니다.
이 파일 덕분에 코드를 직접 수정하지 않고도, 외부 설정(환경 변수)만 바꿔서
프로그램의 동작 모드나 파일 저장 경로 등을 유연하게 변경할 수 있습니다.

[주요 역할]
1. 개발 환경(내 컴퓨터)과 운영 환경(실제 서버) 구분
2. 데이터 파일들이 저장될 경로 지정
3. 사용할 OCR 엔진이나 언어 설정 관리
4. 기획서(Configurations.csv)에 정의된 주요 제약 사항(용량 제한 등) 반영 준비
"""

import os


class Config:
    """
    프로그램 전체에서 공유되는 설정값들을 정의한 클래스입니다.
    `os.getenv('키', '기본값')` 패턴을 사용하여,
    외부에서 설정이 들어오면 그걸 쓰고, 없으면 기본값을 쓰도록 되어 있습니다.
    """

    # [환경 설정]
    # 현재 프로그램이 '개발 모드(development)'인지 '실제 배포 모드(production)'인지 결정합니다.
    # 배포 모드에서는 에러 메시지를 사용자에게 숨기는 등 보안 기능이 작동할 수 있습니다.
    ENV = os.getenv('ENV', 'development')

    # [경로 설정]
    # 프로그램이 사용할 데이터 폴더의 위치입니다.
    # 기획서 CONF-009(저장 경로) 등과 연결될 수 있는 기본 경로입니다.
    DATA_PATH = os.getenv('DATA_PATH', 'data/')

    # 테스트용 샘플 파일이나 고정된 데이터(Fixture)가 있는 위치를 지정합니다.
    # os.path.join을 사용하여 운영체제(Windows/Mac/Linux)에 상관없이 경로를 올바르게 합칩니다.
    SAMPLES_PATH = os.path.join(DATA_PATH, 'samples/')
    FIXTURES_PATH = os.path.join(DATA_PATH, 'fixtures/')

    # [OCR 엔진 설정]
    # 어떤 OCR 기술을 사용할지 결정합니다. (ADR-001 관련)
    # 기본값은 'tesseract'로 되어 있으나, 환경 변수를 통해 'paddleocr'로 변경할 수 있도록 유연성을 둡니다.
    OCR_ENGINE = os.getenv('OCR_ENGINE', 'tesseract')

    # OCR이 주로 읽어야 할 언어를 설정합니다. (기본값: 영어)
    # 한국어가 포함된 문서를 읽으려면 'eng+kor' 등으로 설정을 변경하면 됩니다.
    OCR_LANGUAGE = os.getenv('OCR_LANGUAGE', 'eng')

    # [내보내기 설정]
    # 결과물을 어떤 형식으로 저장할지 결정합니다. (Req-141: 원엑셀 생성)
    # 현재는 엑셀(xlsx)이 기본입니다.
    EXPORT_FORMAT = os.getenv('EXPORT_FORMAT', 'xlsx')

    # [로그 설정]
    # 프로그램 실행 기록(Log)을 얼마나 자세히 남길지 결정합니다.
    # INFO: 일반적인 진행 상황 기록 / DEBUG: 개발용 상세 기록 / ERROR: 에러만 기록
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')

    @staticmethod
    def init_app(app):
        """
        Flask나 기타 웹 프레임워크와 연결할 때 사용하는 초기화 함수입니다.
        현재 구조(Streamlit)에서는 직접적으로 사용되지 않을 수 있으나,
        확장성을 위해(2단계 Enterprise) 미리 자리를 잡아둔 것입니다.
        """
        pass