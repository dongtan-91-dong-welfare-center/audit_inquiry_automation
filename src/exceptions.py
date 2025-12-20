"""
커스텀 예외 정의 모듈

정의된 예외들:
- PasswordProtectedError: 암호로 보호된 파일
- FileCorruptedError: 파일 손상 또는 파싱 오류
- InvalidFilenameError: 파일명 파싱 실패 (Func-111)
- EmptyFileError: 파일 내용이 비어있음
- ExtractionError: 표 추출 실패
"""


class PasswordProtectedError(Exception):
    """암호로 보호된 PDF 등을 나타내는 예외"""


class FileCorruptedError(Exception):
    """PDF 문법 오류 등 파일이 손상되었을 때 발생"""


class InvalidFilenameError(Exception):
    """파일명 파싱 실패 (Func-111)"""


class EmptyFileError(Exception):
    """파일 내용이 비어있을 때 발생"""


class ExtractionError(Exception):
    """표 추출 로직 전반의 실패를 나타내는 일반 예외"""
