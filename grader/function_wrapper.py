"""Chạy trong 1 subprocess riêng (cách ly khỏi tiến trình chính của app).

Import file học sinh như 1 module, gọi hàm theo tên quy ước với các
tham số cho trước, rồi in giá trị trả về ra stdout kèm marker để phân
biệt với các print() thừa khác có thể có trong module.
"""
import importlib.util
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
    result = func(*args, **kwargs)
    print(RESULT_MARKER + json.dumps(result))


if __name__ == "__main__":
    main()
