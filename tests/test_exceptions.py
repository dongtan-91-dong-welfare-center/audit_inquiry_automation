from src import exceptions


def test_exceptions_exist():
    assert hasattr(exceptions, 'PasswordProtectedError')
    assert hasattr(exceptions, 'FileCorruptedError')
    assert hasattr(exceptions, 'InvalidFilenameError')
    assert hasattr(exceptions, 'EmptyFileError')
    assert hasattr(exceptions, 'ExtractionError')


def test_exceptions_are_exceptions():
    assert issubclass(exceptions.PasswordProtectedError, Exception)
    assert issubclass(exceptions.FileCorruptedError, Exception)
    assert issubclass(exceptions.InvalidFilenameError, Exception)
    assert issubclass(exceptions.EmptyFileError, Exception)
    assert issubclass(exceptions.ExtractionError, Exception)
