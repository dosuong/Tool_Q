# Các dạng đề Tool_Q hỗ trợ — ví dụ khung mẫu sẵn dùng

Mỗi mục dưới đây là 1 file JSON hoàn chỉnh — copy nguyên khối, vào tab **"Quản lý khung mẫu" → Nâng cao: xem/nạp JSON trực tiếp**, dán vào ô "Dán 1 JSON khung mẫu khác vào đây rồi bấm Nạp" → bấm **"Nạp JSON vào bảng test case"** → sửa lại tên/mô tả nếu muốn → bấm **Lưu khung mẫu**.

Xem giải thích từng trường trong [`HUONG_DAN_SU_DUNG.md`](HUONG_DAN_SU_DUNG.md).

## Mẫu trống (khung sườn)

```json
{
  "name": "",
  "description": "",
  "function_name": null,
  "structural_rules": {
    "required_constructs": [],
    "forbidden_constructs": [],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {"input": "", "expected_output": "", "timeout": 5, "note": ""}
  ]
}
```

---

## 1. Vòng lặp in dãy số (bắt buộc dùng `while`)

Chỉ chấp nhận chương trình hoàn chỉnh (`function_name: null`), có ràng buộc cấu trúc code.

```json
{
  "name": "In so 1 den 10 bang while",
  "description": "In ra cac so tu 1 den 10, moi so 1 dong, bat buoc dung vong lap while.",
  "function_name": null,
  "structural_rules": {
    "required_constructs": ["While"],
    "forbidden_constructs": ["For"],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {"input": "", "expected_output": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10", "timeout": 5, "note": "case duy nhat"}
  ]
}
```

## 2. Rẽ nhánh if/else (kiểm tra số nguyên tố)

Cho phép cả 2 kiểu nộp (chương trình hoặc hàm `la_so_nguyen_to(n)` trả về `true`/`false`).

```json
{
  "name": "Kiem tra so nguyen to",
  "description": "Nhap 1 so nguyen n, in ra 'N la so nguyen to' hoac 'N khong phai so nguyen to'.",
  "function_name": "la_so_nguyen_to",
  "structural_rules": {
    "required_constructs": [],
    "forbidden_constructs": [],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {"input": "7\n", "expected_output": "7 la so nguyen to", "call_args": [7], "expected_return": true, "timeout": 5, "note": "so nguyen to"},
    {"input": "8\n", "expected_output": "8 khong phai so nguyen to", "call_args": [8], "expected_return": false, "timeout": 5, "note": "hop so"},
    {"input": "1\n", "expected_output": "1 khong phai so nguyen to", "call_args": [1], "expected_return": false, "timeout": 5, "note": "truong hop dac biet: 1"},
    {"input": "2\n", "expected_output": "2 la so nguyen to", "call_args": [2], "expected_return": true, "timeout": 5, "note": "so nguyen to nho nhat"}
  ]
}
```

## 3. Hàm số học đơn giản (tính tổng hai số, cho cả 2 kiểu nộp)

```json
{
  "name": "Tinh tong hai so",
  "description": "Doc 2 so nguyen tu stdin (moi so 1 dong), in ra tong. Hoac viet ham giai(a, b) tra ve tong.",
  "function_name": "giai",
  "structural_rules": {
    "required_constructs": [],
    "forbidden_constructs": [],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {"input": "3\n5\n", "expected_output": "8", "call_args": [3, 5], "call_kwargs": {}, "expected_return": 8, "timeout": 5, "note": "hai so duong"},
    {"input": "-1\n1\n", "expected_output": "0", "call_args": [-1, 1], "call_kwargs": {}, "expected_return": 0, "timeout": 5, "note": "mot am mot duong"}
  ]
}
```

## 4. Xử lý chuỗi (đảo ngược chuỗi)

```json
{
  "name": "Dao nguoc chuoi",
  "description": "Nhap 1 chuoi, in ra chuoi da dao nguoc. Hoac viet ham dao_chuoi(s).",
  "function_name": "dao_chuoi",
  "structural_rules": {
    "required_constructs": [],
    "forbidden_constructs": [],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {"input": "hello\n", "expected_output": "olleh", "call_args": ["hello"], "expected_return": "olleh", "timeout": 5, "note": "chuoi tieng Anh"},
    {"input": "Python\n", "expected_output": "nohtyP", "call_args": ["Python"], "expected_return": "nohtyP", "timeout": 5, "note": "co chu hoa"}
  ]
}
```

## 5. Danh sách/mảng (số lớn nhất và số lớn thứ k)

Hàm trả về **list** `[so_lon_nhat, so_lon_thu_k]` — xem lưu ý về tuple vs list trong `HUONG_DAN_SU_DUNG.md`.

```json
{
  "name": "So lon nhat va so lon thu k",
  "description": "Nhap n, day n so, va k. In so lon nhat va so lon thu k (theo thu hang, cho phep trung).",
  "function_name": "giai",
  "structural_rules": {
    "required_constructs": [],
    "forbidden_constructs": [],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {
      "input": "5\n5 3 8 3 9\n2\n",
      "expected_output": "9\n8",
      "call_args": [[5, 3, 8, 3, 9], 2],
      "expected_return": [9, 8],
      "timeout": 5,
      "note": "co so trung, k=2"
    },
    {
      "input": "3\n10 20 30\n1\n",
      "expected_output": "30\n30",
      "call_args": [[10, 20, 30], 1],
      "expected_return": [30, 30],
      "timeout": 5,
      "note": "k=1: lon nhat = lon thu 1"
    }
  ]
}
```

## 6. Đệ quy (giai thừa, bắt buộc dùng đệ quy)

```json
{
  "name": "Giai thua bang de quy",
  "description": "Nhap n, in ra n! (giai thua), bat buoc dung de quy (khong duoc dung vong lap).",
  "function_name": "giai_thua",
  "structural_rules": {
    "required_constructs": ["Recursion"],
    "forbidden_constructs": ["For", "While"],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {"input": "5\n", "expected_output": "120", "call_args": [5], "expected_return": 120, "timeout": 5, "note": "5! = 120"},
    {"input": "0\n", "expected_output": "1", "call_args": [0], "expected_return": 1, "timeout": 5, "note": "0! = 1"}
  ]
}
```

## 7. Cấm dùng hàm có sẵn (tự cài đặt sắp xếp, không được dùng `sorted`/`.sort()`)

```json
{
  "name": "Sap xep tang dan khong dung sorted",
  "description": "Nhap day so, in ra day da sap xep tang dan. Khong duoc dung ham sorted() hoac .sort() co san.",
  "function_name": "sap_xep",
  "structural_rules": {
    "required_constructs": [],
    "forbidden_constructs": [],
    "forbidden_imports": [],
    "forbidden_calls": ["sorted", "sort"]
  },
  "test_cases": [
    {
      "input": "4\n5 2 9 1\n",
      "expected_output": "1 2 5 9",
      "call_args": [[5, 2, 9, 1]],
      "expected_return": [1, 2, 5, 9],
      "timeout": 5,
      "note": "sap xep tang dan thu cong"
    }
  ]
}
```

---

## Lưu ý chung khi soạn đề

- **Nhiều test case cho 1 đề**: thêm nhiều dòng trong mảng `test_cases` — điểm sẽ hiện dạng `x/N` (số case đạt / tổng số case).
- **Bài thuật toán yêu cầu N lớn** (10^5 – 10^6 phần tử) để kiểm tra độ phức tạp thuật toán: Tool_Q hiện **chưa hỗ trợ tự sinh test cỡ lớn** — cần tự chuẩn bị input/expected_output cỡ lớn và dán tay vào JSON (có thể cồng kềnh).
- **Chỉ muốn nhận hàm, không nhận chương trình**: vẫn phải điền `input`/`expected_output` cho đủ trường bắt buộc, nhưng có thể để trống `input` — hệ thống sẽ tự fallback sang gọi hàm khi thấy stdout rỗng (xem mục 6.1 trong `HUONG_DAN_SU_DUNG.md`).
- **Kiểm tra cấu trúc mà không quan tâm output** (hiếm gặp): vẫn cần ít nhất 1 `test_cases` hợp lệ vì đây là trường bắt buộc của khung mẫu.
