"""Sinh test động (pytest_generate_tests) cho grader/test_runner.py.

Đặt ở đây (thay vì trong 1 plugin truyền qua `pytest.main(plugins=[...])`) vì khi
bật chạy song song (pytest-xdist), các worker process được spawn riêng biệt và
KHÔNG nhận được plugin instance truyền qua tham số `plugins=` của tiến trình
chính — chúng chỉ tự nạp file conftest.py thật sự nằm trên đĩa. Dữ liệu test case
được ghi ra 1 file JSON tạm, đường dẫn truyền qua biến môi trường
TOOLQ_CASES_FILE — đọc lại ngay bên trong hàm (không cache ở cấp module) để luôn
lấy đúng dữ liệu mới nhất mỗi lần gọi `pytest.main()`, kể cả khi app chạy nhiều
lượt chấm liên tiếp trong cùng 1 tiến trình Streamlit.
"""
import dataclasses
import json
import os
from pathlib import Path

from grader.models import TestCase

_TESTCASE_FIELDS = {f.name for f in dataclasses.fields(TestCase)}


def _load_cases():
    path = os.environ.get("TOOLQ_CASES_FILE")
    if not path or not Path(path).exists():
        return [], []
    data = json.loads(Path(path).read_text(encoding="utf-8"))

    output_cases = []
    for c in data.get("output_cases", []):
        tc_kwargs = {k: v for k, v in c["test_case"].items() if k in _TESTCASE_FIELDS}
        output_cases.append({
            "student_file": Path(c["student_file"]),
            "test_case": TestCase(**tc_kwargs),
            "case_index": c["case_index"],
            "bai_label": c["bai_label"],
            "function_name": c["function_name"],
            "case_id": c["case_id"],
        })

    structure_cases = []
    for c in data.get("structure_cases", []):
        structure_cases.append({
            "student_file": Path(c["student_file"]),
            "structural_rules": c["structural_rules"],
            "bai_label": c["bai_label"],
            "case_id": c["case_id"],
        })
    return output_cases, structure_cases


def pytest_generate_tests(metafunc):
    names = set(metafunc.fixturenames)
    if {"student_file", "test_case", "case_index", "bai_label", "function_name"} <= names:
        output_cases, _ = _load_cases()
        metafunc.parametrize(
            "student_file,test_case,case_index,bai_label,function_name",
            [
                (c["student_file"], c["test_case"], c["case_index"], c["bai_label"], c["function_name"])
                for c in output_cases
            ],
            ids=[c["case_id"] for c in output_cases],
        )
    elif {"student_file", "structural_rules", "bai_label"} <= names:
        _, structure_cases = _load_cases()
        metafunc.parametrize(
            "student_file,structural_rules,bai_label",
            [(c["student_file"], c["structural_rules"], c["bai_label"]) for c in structure_cases],
            ids=[c["case_id"] for c in structure_cases],
        )
