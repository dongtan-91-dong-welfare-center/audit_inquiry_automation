import pytest

from src import processor
from src.exceptions import PasswordProtectedError, ExtractionError


def test_process_raises_password_error(monkeypatch, tmp_path):
    # mock extract_tables_from_pdf to raise an encrypted-like error
    def _raise_encrypted(path):
        raise Exception('file is password protected')

    monkeypatch.setattr(processor, 'extract_tables_from_pdf', _raise_encrypted)

    pdf = tmp_path / 'a.pdf'
    pdf.write_text('dummy')
    out = tmp_path / 'a.xlsx'

    with pytest.raises(PasswordProtectedError):
        processor.process_pdf_to_excel(str(pdf), str(out))


def test_process_raises_extraction_error(monkeypatch, tmp_path):
    def _raise_other(path):
        raise RuntimeError('unknown failure')

    monkeypatch.setattr(processor, 'extract_tables_from_pdf', _raise_other)

    pdf = tmp_path / 'b.pdf'
    pdf.write_text('dummy')
    out = tmp_path / 'b.xlsx'

    with pytest.raises(ExtractionError):
        processor.process_pdf_to_excel(str(pdf), str(out))
