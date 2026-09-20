"""Chạy trong 1 subprocess riêng (cách ly khỏi tiến trình chính của app).

Import file học sinh như 1 module, gọi hàm theo tên quy ước với các
tham số cho trước. Bắt lại cả (a) giá trị hàm trả về và (b) toàn bộ
nội dung print() xảy ra TRONG LÚC gọi hàm, rồi in ra 1 dòng JSON duy
nhất kèm marker để phân biệt với các print() khác (nếu có) ở code
top-level của module, vốn chạy trước khi bắt đầu ghi lại stdout.
"""
import contextlib
import importlib.util
import io
import json
import sys

RESULT_MARKER = "###RESULT###"


def main():
    student_path, function_name, call_args_json, call_kwargs_json = sys.argv[1:5]

    spec = importlib.util.spec_from_file_location("student_module", student_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    if not hasattr(module, function_name):
        print(f"Không tìm thấy hàm '{function_name}' trong file nộp.", file=sys.stderr)
        sys.exit(1)

    func = getattr(module, function_name)
    args = json.loads(call_args_json)
    kwargs = json.loads(call_kwargs_json)

    captured = io.StringIO()
    with contextlib.redirect_stdout(captured):
        result = func(*args, **kwargs)

    payload = {"return": result, "stdout": captured.getvalue()}
    print(RESULT_MARKER + json.dumps(payload))


if __name__ == "__main__":
    main()
