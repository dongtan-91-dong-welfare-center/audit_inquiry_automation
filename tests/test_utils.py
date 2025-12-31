import pytest

from src.utils import parse_filename


def test_parse_filename_basic_ascii():
    res = parse_filename('ABC123DEF')
    assert res == {'audited_company': 'ABC', 'inquired_company': 'DEF'}


def test_parse_filename_with_extension():
    res = parse_filename('회사A123조회처B.pdf')
    assert res == {'audited_company': '회사A', 'inquired_company': '조회처B'}


def test_parse_filename_invalid():
    # No digits => should fail to match per CONF-006
    assert parse_filename('InvalidFilename') is None


def test_parse_filename_complex():
    # multiple digits inside; audited_company should match up to first digit sequence
    res = parse_filename('CoX9PartnerY')
    assert res == {'audited_company': 'CoX', 'inquired_company': 'PartnerY'}


def test_setup_logger_creates_logger():
    from src.utils import setup_logger
    logger = setup_logger('test_logger')
    assert logger is not None
    # logger should have at least two handlers (stream + file)
    assert len(logger.handlers) >= 2
