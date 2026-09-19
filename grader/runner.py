import difflib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional

from grader.models import GradeResult, TestCase

FRAME_RE = re.compile(r'File "(?P<file>.+?)", line (?P<line>\d+)(?:, in (?P<where>.+))?')
RESULT_MARKER = "###RESULT###"

_WRAPPER_PATH = Path(__file__).resolve().parent / "function_wrapper.py"


def _build_env():
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    env["PYTHONUTF8"] = "1"
    return env


def _run_subprocess(args, input_text, timeout):
    return subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=_build_env(),
    )


def run_capture_only(solution_file: Path, input_text: str, timeout: float = 5.0):
    """Chạy solution.py của GV, trả về (stdout, stderr, returncode) thô, không so sánh."""
    try:
        proc = _run_subprocess([sys.executable, str(solution_file)], input_text, timeout)
    except subprocess.TimeoutExpired:
        return "", "TIMEOUT: qua thoi gian cho phep", -1
    return proc.stdout, proc.stderr, proc.returncode


def run_function_capture_only(solution_file: Path, function_name: str, call_args, call_kwargs=None, timeout: float = 5.0):
    """Chạy solution.py ở chế độ hàm (dùng để sinh đáp án mẫu, không so sánh).

    Trả về (gia_tri_tra_ve, thong_bao_loi) — gia_tri_tra_ve là None nếu có lỗi.
    """
    call_kwargs = call_kwargs or {}
    try:
        proc = _run_subprocess(
            [
                sys.executable, str(_WRAPPER_PATH), str(solution_file), function_name,
                json.dumps(call_args), json.dumps(call_kwargs),
            ],
            None, timeout,
        )
    except subprocess.TimeoutExpired:
        return None, f"Quá thời gian cho phép ({timeout}s)."

    if proc.returncode != 0 or proc.stderr.strip():
        _, _, err_msg = _parse_traceback(proc.stderr)
        return None, err_msg or "Lỗi không rõ khi gọi hàm."

    result_line = ""
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(RESULT_MARKER):
            result_line = line[len(RESULT_MARKER):]
            break

    if not result_line:
        return None, "Không nhận được kết quả trả về từ hàm."

    try:
        return json.loads(result_line), None
    except json.JSONDecodeError:
        return None, "Kết quả trả về không phải JSON hợp lệ."


def _parse_traceback(stderr: str):
    stderr = stderr.strip()
    if not stderr:
        return None, None, ""
    lines = stderr.splitlines()
    last_line = lines[-1]
    error_type = last_line.split(":", 1)[0].strip()
    frames = list(FRAME_RE.finditer(stderr))
    error_line = int(frames[-1].group("line")) if frames else None
    return error_type, error_line, last_line


def _normalize(text: str, ignore_trailing_ws: bool) -> str:
    if not ignore_trailing_ws:
        return text
    lines = [ln.rstrip() for ln in text.replace("\r\n", "\n").split("\n")]
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def _first_diff(expected: str, actual: str) -> str:
    diff = list(difflib.unified_diff(
        expected.splitlines(), actual.splitlines(), "ky_vong", "thuc_te", lineterm=""
    ))
    return "\n".join(diff[:20]) if diff else ""


def _apply_crash(result: GradeResult, stderr: str, context: str = "Chương trình lỗi"):
    result.crashed = True
    err_type, err_line, err_msg = _parse_traceback(stderr)
    result.error_type = err_type or "UnknownError"
    result.error_line = err_line
    result.error_message = err_msg
    loc = f" (dòng {err_line})" if err_line else ""
    result.short_message = f"{context}: {result.error_type}{loc} — {err_msg}"


def _try_function_mode(student_file: Path, function_name: str, test_case: TestCase, result: GradeResult):
    result.mode_used = "function"
    call_args = test_case.call_args if test_case.call_args is not None else []
    call_kwargs = test_case.call_kwargs if test_case.call_kwargs is not None else {}

    try:
        proc = _run_subprocess(
            [
                sys.executable, str(_WRAPPER_PATH), str(student_file), function_name,
                json.dumps(call_args), json.dumps(call_kwargs),
            ],
            None, test_case.timeout,
        )
    except subprocess.TimeoutExpired:
        result.timed_out = True
        result.short_message = f"Quá thời gian cho phép ({test_case.timeout}s) khi gọi hàm — nghi ngờ vòng lặp vô hạn."
        return result

    result.returncode = proc.returncode
    result.raw_stderr = proc.stderr

    if proc.returncode != 0 or proc.stderr.strip():
        _apply_crash(result, proc.stderr, context=f"Lỗi khi gọi hàm '{function_name}'")
        return result

    result_line = ""
    for line in reversed(proc.stdout.splitlines()):
        if line.startswith(RESULT_MARKER):
            result_line = line[len(RESULT_MARKER):]
            break

    if not result_line:
        result.short_message = "Không nhận được kết quả trả về từ hàm."
        return result

    try:
        actual_return = json.loads(result_line)
    except json.JSONDecodeError:
        result.short_message = "Kết quả trả về không đọc được (không phải JSON hợp lệ)."
        return result

    result.actual_output = json.dumps(actual_return, ensure_ascii=False)
    result.expected_output = json.dumps(test_case.expected_return, ensure_ascii=False)

    if actual_return == test_case.expected_return:
        result.passed = True
        result.short_message = "OK"
    else:
        result.short_message = "Giá trị trả về không khớp với đáp án."
        result.diff_summary = f"Kỳ vọng: {result.expected_output}\nThực tế: {result.actual_output}"
    return result


def grade_one(
    student_file: Path,
    test_case: TestCase,
    case_index: int,
    bai_label: str = "",
    function_name: Optional[str] = None,
) -> GradeResult:
    result = GradeResult(
        student_name=student_file.stem,
        student_file=student_file.name,
        bai_label=bai_label,
        case_index=case_index,
        case_note=test_case.note,
        expected_output=test_case.expected_output,
        stdin_given=test_case.input,
    )

    try:
        proc = _run_subprocess([sys.executable, str(student_file)], test_case.input, test_case.timeout)
    except subprocess.TimeoutExpired:
        result.timed_out = True
        result.short_message = f"Quá thời gian cho phép ({test_case.timeout}s) — nghi ngờ vòng lặp vô hạn."
        return result

    result.returncode = proc.returncode
    result.actual_output = proc.stdout
    result.raw_stderr = proc.stderr

    if proc.returncode != 0 or proc.stderr.strip():
        _apply_crash(result, proc.stderr)
        return result

    act_norm = _normalize(proc.stdout, test_case.ignore_trailing_whitespace)

    can_try_function = (
        function_name
        and test_case.call_args is not None
        and test_case.expected_return is not None
    )

    if act_norm == "" and can_try_function:
        return _try_function_mode(student_file, function_name, test_case, result)

    if act_norm == "":
        result.short_message = "Chương trình không in ra kết quả nào (stdout rỗng)."
        result.diff_summary = result.short_message
        return result

    exp_norm = _normalize(test_case.expected_output, test_case.ignore_trailing_whitespace)
    if exp_norm == act_norm:
        result.passed = True
        result.short_message = "OK"
        return result

    result.diff_summary = _first_diff(exp_norm, act_norm)
    result.short_message = "Output không khớp với đáp án mẫu."
    return result
