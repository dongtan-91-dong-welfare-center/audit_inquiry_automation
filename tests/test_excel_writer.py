import pandas as pd

from audit_inquiry_automation.excel_writer import write_tables_to_excel


def test_write_tables_to_excel(tmp_path):
    df1 = pd.DataFrame([{"a": 1, "b": 2}])
    out = tmp_path / "out.xlsx"
    write_tables_to_excel([df1], str(out))
    read = pd.read_excel(str(out), sheet_name="table_1")
    assert read.iloc[0]["a"] == 1
