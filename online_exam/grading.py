"""Cầu nối chấm 1 CÂU cho luồng thi online. KHÔNG viết lại logic chấm — gọi thẳng
grader.runner.grade_one (so khớp output/hàm) và grader.ast_checker.check_structure
(kiểm tra cấu trúc), y hệt cách online_exam/ui_create_exam.py đã làm cho khu "Chạy thử đề".

Dùng chung cho cả "Chạy thử" (chỉ truyền test case mẫu) và "Nộp câu này" (truyền toàn
bộ test case mẫu+ẩn) — nơi gọi (ui_student_exam.py) quyết định truyền tập test case nào,
hàm ở đây không tự phân biệt trial/official.
"""
import tempfile
from pathlib import Path

from grader.ast_checker import check_structure
from grader.models import TestCase
from grader.runner import grade_one

MAX_CODE_LENGTH = 100_000


def grade_problem(code_text: str, problem: dict, test_cases: list[dict]) -> dict:
    """Chấm `code_text` với `test_cases` (danh sách dict, mỗi cái có key 'id'/'is_sample'/...).

    Trả về:
        {
            "pass_ratio": float,        # 0.0 nếu vi phạm cấu trúc bắt buộc (xem bên dưới)
            "structure_ok": bool,
            "violations": [str, ...],
            "results": [
                {"test_case_id": int, "is_sample": bool, "passed": bool,
                 "actual_output": str, "error_message": str, "execution_time_ms": None},
                ...
            ],
        }
    """
    code_text = code_text[:MAX_CODE_LENGTH]

    structure_ok, violations = check_structure(
        code_text,
        problem.get("required_constructs") or [],
        problem.get("forbidden_constructs") or [],
        problem.get("forbidden_imports") or [],
        problem.get("forbidden_calls") or [],
    )
    function_name = problem.get("function_name") or None

    results = []
    with tempfile.TemporaryDirectory(prefix="oe_submit_") as tmp:
        code_path = Path(tmp) / "submission.py"
        code_path.write_text(code_text, encoding="utf-8")
        for i, tc_dict in enumerate(test_cases, start=1):
            tc = TestCase(
                input=tc_dict.get("input", ""),
                expected_output=tc_dict.get("expected_output", ""),
                timeout=tc_dict.get("timeout", 5.0),
                note=tc_dict.get("note", ""),
                ignore_trailing_whitespace=tc_dict.get("ignore_trailing_whitespace", True),
                call_args=tc_dict.get("call_args"),
                call_kwargs=tc_dict.get("call_kwargs"),
                expected_return=tc_dict.get("expected_return"),
            )
            r = grade_one(code_path, tc, i, "online", function_name)
            results.append({
                "test_case_id": tc_dict.get("id"),
                "is_sample": bool(tc_dict.get("is_sample")),
                "passed": bool(r.passed),
                "actual_output": r.actual_output,
                "error_message": r.error_message or r.short_message,
                "execution_time_ms": None,
            })

    total = len(results)
    passed_count = sum(1 for r in results if r["passed"])
    pass_ratio = (passed_count / total) if total else 0.0
    # check_structure() chỉ trả violations khi câu này CÓ cấu hình quy tắc (nếu không cấu
    # hình gì thì luôn ok=True) — nên zero điểm ở đây an toàn, không phạt oan câu không có quy tắc.
    if not structure_ok:
        pass_ratio = 0.0

    return {
        "pass_ratio": pass_ratio,
        "structure_ok": structure_ok,
        "violations": violations,
        "results": results,
    }
