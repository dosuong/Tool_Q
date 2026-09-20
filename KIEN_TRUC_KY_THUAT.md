# Tool_Q — Tài liệu kiến trúc & kỹ thuật

Tài liệu này giải thích **toàn bộ bên trong** của Tool_Q: cấu trúc thư mục, thư viện dùng,
luồng chạy, các thuật toán lõi, và những điểm kỹ thuật đáng chú ý. Dành cho việc bảo trì/mở
rộng sau này (kể cả khi người đọc không nhớ chi tiết đã cùng xây dựng lúc trước).

Các file hướng dẫn *sử dụng* (cho giáo viên) nằm ở nơi khác, không lặp lại ở đây:
- [`HUONG_DAN_SU_DUNG.md`](HUONG_DAN_SU_DUNG.md) — cách dùng app từng bước.
- [`CAC_DANG_DE_HO_TRO.md`](CAC_DANG_DE_HO_TRO.md) — các dạng đề bài + ví dụ nhập khung mẫu.
- [`HUONG_DAN_SINH_DAP_AN_TU_DONG.md`](HUONG_DAN_SINH_DAP_AN_TU_DONG.md) — cách dùng tính năng sinh đáp án tự động.

---

## 1. Tool_Q giải quyết bài toán gì

Giáo viên tin học ra đề lập trình Python cho học sinh, thu bài `.py` (qua Zalo/Classroom/email…),
rồi cần chấm hàng chục–hàng trăm file: chạy từng file, so kết quả in ra với đáp án, kiểm tra học
sinh có dùng đúng vòng lặp/cấu trúc yêu cầu không, và tổng hợp điểm. Làm tay việc này rất tốn thời
gian và dễ sai sót. Tool_Q tự động hoá toàn bộ quy trình đó thành 3 bước trên giao diện web:
tạo khung mẫu đề bài → upload bài học sinh → bấm chấm, ra bảng điểm + chi tiết lỗi từng em.

Mô hình triển khai: **không có tài khoản đăng nhập, không phân quyền học sinh** — giáo viên là
người dùng duy nhất tương tác với app, học sinh không bao giờ truy cập trực tiếp.

---

## 2. Cấu trúc thư mục

```
Tool_Q/
├── app.py                        # Toàn bộ giao diện Streamlit (entry point duy nhất)
├── requirements.txt               # streamlit, pytest, pandas, pytest-xdist
├── setup.bat / run.bat             # cài đặt 1 lần / chạy app bằng double-click (Windows)
├── .streamlit/config.toml           # cấu hình Streamlit (theme, server)
├── .devcontainer/devcontainer.json   # cấu hình môi trường dev container (nếu mở bằng Codespaces/devcontainer)
│
├── grader/                        # "bộ máy chấm bài" — tách hẳn khỏi UI, không phụ thuộc Streamlit
│   ├── models.py                    # 3 dataclass dữ liệu lõi: TestCase, GradeResult, StructureResult
│   ├── runner.py                     # chạy code học sinh cách ly, so khớp output, fallback sang chấm hàm
│   ├── function_wrapper.py            # script con để gọi 1 hàm cụ thể trong file học sinh, chạy trong subprocess riêng
│   ├── ast_checker.py                  # kiểm tra cấu trúc code tĩnh bằng module `ast` (không chạy code)
│   ├── exam_batch.py                    # parse quy ước tên file <hs>_bai<N>.py, gom nhóm theo bài khi chấm kỳ thi
│   ├── templates_store.py                # đọc/ghi khung mẫu dạng file JSON trong templates/
│   ├── pytest_plugin.py                   # GraderPlugin — gom kết quả structured từ pytest để hiển thị lên UI
│   ├── conftest.py                         # sinh test động (pytest_generate_tests) — bắt buộc là file thật (không phải plugin) để pytest-xdist worker nạp được
│   └── test_runner.py                      # 2 hàm test thực sự được pytest collect và chạy
│
├── templates/                      # mỗi khung mẫu (đề bài) = 1 file JSON, do GV tạo/sửa qua UI
│   └── *.json
│
└── sample_students/                 # file .py mẫu dùng để tự kiểm thử app (không phải phần của app)
```

**Nguyên tắc tách lớp quan trọng nhất:** thư mục `grader/` là một thư viện chấm bài thuần Python,
không `import streamlit` ở đâu cả. `app.py` chỉ gọi vào các hàm của `grader/` rồi vẽ kết quả lên
UI. Nhờ vậy toàn bộ logic chấm bài (`runner.py`, `ast_checker.py`, …) có thể test độc lập bằng
`pytest` bình thường, không cần dựng Streamlit lên mới test được.

---

## 3. Thư viện sử dụng

| Thư viện | Vai trò trong dự án |
|---|---|
| **streamlit** | Toàn bộ giao diện web (UI), điều hướng sidebar (`st.navigation`/`st.Page`), dialog xác nhận xoá (`st.dialog`), bảng nhập liệu (`st.data_editor`), tải file (`st.file_uploader`), CSS tuỳ biến (`st.html`). |
| **pytest** | Engine chấm bài hàng loạt. Mỗi cặp (file học sinh × test case) hoặc (file học sinh × luật cấu trúc) trở thành 1 "test" pytest, chạy qua `pytest.main()` được gọi ngay từ trong `app.py`. |
| **pytest-xdist** | Plugin cho pytest, cho phép chạy các test song song trên nhiều tiến trình con (`-n <số luồng>`) — dùng khi GV bật "Chạy song song" để chấm nhanh hơn với khối lượng bài lớn. |
| **pandas** | Gom kết quả chấm (list[dict]) thành `DataFrame` để tính tổng hợp (bao nhiêu học sinh đạt, %), hiển thị bảng, và xuất CSV. |
| `ast` (chuẩn) | Phân tích cú pháp code học sinh thành cây cú pháp trừu tượng, dùng để kiểm tra cấu trúc (for/while/list-comp/đệ quy, import cấm, gọi hàm cấm) mà **không cần chạy code**. |
| `subprocess` (chuẩn) | Chạy code học sinh (và file lời giải mẫu) trong 1 tiến trình con riêng biệt — cách ly khỏi tiến trình chính của app, có timeout để chặn vòng lặp vô hạn. |
| `difflib` (chuẩn) | So khớp output kỳ vọng vs thực tế, sinh đoạn diff ngắn để GV nhìn nhanh chỗ sai. |
| `tempfile` (chuẩn) | Tạo thư mục tạm để ghi file học sinh vừa upload xuống đĩa (pytest cần file thật để chạy `subprocess`), tự dọn dẹp sau khi chấm xong. |
| `json` (chuẩn) | Định dạng lưu khung mẫu (`templates/*.json`), và định dạng trung gian để truyền dữ liệu test case sang các tiến trình worker của pytest-xdist. |
| `re` (chuẩn) | Regex parse traceback Python (lấy đúng dòng lỗi/loại lỗi) và parse quy ước tên file `<học_sinh>_bai<N>.py`. |
| `contextlib`, `io` (chuẩn) | `redirect_stdout` bắt lại nội dung `print()` xảy ra bên trong lúc gọi hàm học sinh (chế độ chấm hàm). |
| `importlib.util` (chuẩn) | Nạp file `.py` của học sinh như 1 module Python (không phải `import` tên cố định) để lấy ra đúng hàm cần gọi, trong `function_wrapper.py`. |

Không có framework backend riêng (Flask/FastAPI/DB) — toàn bộ trạng thái phiên làm việc nằm trong
`st.session_state` của Streamlit, dữ liệu bền vững duy nhất là các file JSON trong `templates/`.

---

## 4. Luồng hoạt động end-to-end

### 4.1. Tạo/sửa khung mẫu (trang "Quản lý khung mẫu")

1. GV chọn 1 đề có sẵn (nạp từ `templates/<tên>.json` qua `templates_store.load_template`) hoặc để
   trống để tạo đề mới.
2. Khai báo: mô tả, yêu cầu cấu trúc code (bắt buộc/cấm dùng for/while/list-comp/đệ quy, cấm
   import gì, cấm gọi hàm/phương thức gì), và **tên hàm** nếu muốn chấp nhận bài nộp dạng hàm.
3. Có thể **sinh đáp án tự động**: upload 1 file lời giải mẫu, nhập input mẫu (chế độ chương
   trình) hoặc bộ tham số gọi hàm (chế độ hàm) → app tự chạy lời giải mẫu để điền
   `expected_output`/`expected_return`, rồi **tự lưu luôn** khung mẫu (không cần bấm Lưu lần 2).
4. Bảng test case (`st.data_editor`) cho sửa tay từng dòng: `input`, `expected_output`,
   `call_args`, `expected_return`, `timeout`, `note`.
5. Bấm "Lưu khung mẫu" → `templates_store.save_template()` ghi file JSON xuống
   `templates/<tên_đã_chuẩn_hoá>.json`.

### 4.2. Chấm bài (trang "Chấm 1 đề" hoặc "Chấm cả kỳ thi")

```
Upload file .py
      │
      ▼
Ghi xuống thư mục tạm (tempfile.TemporaryDirectory)
      │
      ▼
Ghép mỗi file với test case của đúng khung mẫu
  → danh sách "output_cases" (file × test case) + "structure_cases" (file × luật cấu trúc)
      │
      ▼
_serialize_cases(): chuyển Path/dataclass → dict JSON-hoá được
      │
      ▼
Ghi ra 1 file JSON tạm, đường dẫn đặt vào biến môi trường TOOLQ_CASES_FILE
      │
      ▼
pytest.main(["-q", ..., "grader/test_runner.py", ("-n", workers nếu song song)],
            plugins=[GraderPlugin(...)])
      │
      ├─ grader/conftest.py: pytest_generate_tests() đọc lại TOOLQ_CASES_FILE,
      │  parametrize test_runner.py theo đúng số case → mỗi case = 1 "test"
      │
      ├─ grader/test_runner.py chạy từng test:
      │     - test_student_stdout   → gọi grader.runner.grade_one(...)
      │     - test_student_structure → gọi grader.ast_checker.check_structure(...)
      │  mỗi test gắn kết quả structured vào request.node.user_properties
      │
      └─ GraderPlugin.pytest_runtest_logreport() gom các user_properties đó lại
         thành 2 list: output_results, structure_results
      │
      ▼
app.py nhận lại 2 list này, dùng pandas tổng hợp theo học sinh, vẽ bảng + chi tiết + CSV
```

### 4.3. Bên trong `grade_one()` (1 file học sinh × 1 test case)

```
subprocess.run([python, student_file.py], input=test_case.input, timeout=...)
      │
      ├─ Timeout             → GradeResult.timed_out = True
      ├─ Lỗi (returncode≠0 / có stderr) → parse traceback → error_type/error_line/error_message
      ├─ Chạy OK, stdout RỖNG + có khai báo function_name + test case có call_args
      │        → FALLBACK: thử "chế độ hàm" (xem 4.4)
      ├─ Chạy OK, stdout rỗng, KHÔNG fallback được → báo "không in ra gì"
      └─ Chạy OK, có stdout → so khớp (rstrip từng dòng, bỏ dòng trắng cuối) với expected_output
                → khớp: passed=True | khác: sinh diff ngắn bằng difflib
```

### 4.4. Chế độ chấm hàm (`_try_function_mode`)

Khi chương trình học sinh chạy xong mà không in ra gì (nghĩa là học sinh có thể chỉ viết `def`,
không gọi/không print), hệ thống **tự động** thử gọi thẳng hàm đó trong 1 subprocess riêng khác
(`function_wrapper.py`), thay vì báo sai ngay:

- `function_wrapper.py` được gọi như `python function_wrapper.py <file_học_sinh> <tên_hàm>
  <call_args JSON> <call_kwargs JSON>`.
- Nó `importlib.util.spec_from_file_location(...)` nạp file học sinh như 1 module, tìm đúng hàm
  theo tên, gọi hàm với tham số, đồng thời `contextlib.redirect_stdout` để bắt luôn mọi `print()`
  xảy ra *bên trong* lúc gọi hàm.
- In ra đúng 1 dòng cuối cùng dạng `###RESULT###{"return": ..., "stdout": ...}` — marker
  `###RESULT###` giúp tách kết quả thật khỏi các `print()` khác có thể xảy ra ở code top-level của
  file học sinh (chạy trong lúc `exec_module`).
- `runner.py` so khớp **độc lập** cả `return` (nếu khung mẫu có khai `expected_return`) lẫn
  `stdout` (nếu có khai `expected_output`) — học sinh có thể sai 1 trong 2 mà vẫn được báo rõ lỗi
  nào, không gộp chung mập mờ.
- Nếu hàm học sinh tự raise exception khi gọi (vd chia cho 0), traceback tự nhiên trỏ đúng vào
  dòng lỗi bên trong hàm — dùng lại nguyên cơ chế parse traceback của chế độ chương trình, không
  cần code riêng.

### 4.5. Kiểm tra cấu trúc code (`ast_checker.check_structure`)

Chạy hoàn toàn tĩnh, không thực thi code:
1. `ast.parse(source_code)` → cây cú pháp. Lỗi cú pháp ở bước này được báo luôn là 1 vi phạm cấu
   trúc (kèm số dòng), không crash chương trình chấm.
2. Duyệt cây (`ast.walk`) để xác định có mặt: `for`, `while`, list comprehension, và **đệ quy**
   (dò trong từng `FunctionDef`, xem thân hàm có gọi lại chính tên hàm đó không).
3. Gom tập `import`/`from ... import` ở mức module gốc (`a.name.split(".")[0]` để chuẩn hoá
   `numpy.random` → `numpy`).
4. Gom tập tên hàm/phương thức được **gọi trực tiếp** (`ast.Call`) — phân biệt gọi kiểu
   `sorted(x)` (lấy `func.id`) và gọi kiểu `x.sort()` (lấy `func.attr`), để hỗ trợ cấm cả hàm dựng
   sẵn lẫn phương thức của list.
5. So các tập trên với `required_constructs`/`forbidden_constructs`/`forbidden_imports`/
   `forbidden_calls` khai báo trong khung mẫu → sinh danh sách vi phạm dạng câu tiếng Việt dễ đọc.

### 4.6. Chấm cả kỳ thi (`exam_batch.group_by_bai`)

Khi upload hàng trăm file 1 lượt, mỗi file được đối chiếu với regex
`^(?P<student>.+)_bai(?P<bai_num>\d+)\.py$` để tách "học sinh nào" + "bài số mấy". File khớp được
gom theo `bai_num`; file không khớp quy ước tên được liệt kê riêng trong `unmatched` để GV thấy
ngay và tự xử lý — **không bao giờ âm thầm bỏ qua**. Sau khi map "bai{N}" → đúng khung mẫu (GV tự
gán qua UI, không lệ thuộc cứng vào tên file JSON), toàn bộ case của tất cả các bài được **gộp
chung thành 1 lần gọi `pytest.main()`** — không lặp lại việc khởi động pytest cho từng đề.

---

## 5. Điểm kỹ thuật đáng chú ý (điểm sáng)

### 5.1. Dùng pytest làm engine chấm bài thay vì tự viết vòng lặp

Thay vì `for file in files: for case in cases: cham(file, case)`, mỗi cặp (file × case) được biến
thành 1 "test" pytest thật sự qua `pytest_generate_tests` (parametrize động). Lợi ích: có sẵn
report/summary chuẩn, và **có sẵn khả năng chạy song song bằng pytest-xdist** chỉ bằng cách thêm
`-n <n>` — không phải tự viết cơ chế multiprocessing.

### 5.2. Vượt qua giới hạn của pytest-xdist với dữ liệu động (`conftest.py` + file JSON tạm)

Đây là bug đã gặp và sửa: ban đầu `pytest_generate_tests` nằm trong `GraderPlugin`, truyền qua
`pytest.main(plugins=[plugin])`. Khi bật song song, pytest-xdist tách ra các **tiến trình worker
độc lập** (gw0, gw1, …) để tự thu thập (collect) test — các worker này **không hề nhận được**
plugin instance truyền qua tham số `plugins=` của tiến trình chính, nên báo lỗi
`fixture 'student_file' not found`.

Cách sửa: chuyển `pytest_generate_tests` sang một **file `conftest.py` thật sự nằm trên đĩa**
(`grader/conftest.py`) — cơ chế nạp `conftest.py` của pytest áp dụng cho mọi tiến trình, kể cả
worker. Vì dữ liệu test case (chứa `Path`, `dataclass`) không thể truyền thẳng qua biến môi
trường, nó được serialize ra JSON (`_serialize_cases` trong `app.py`), ghi vào 1 file tạm, và
`conftest.py` đọc lại đường dẫn file đó qua biến môi trường `TOOLQ_CASES_FILE` — đọc **mỗi lần
`pytest_generate_tests` được gọi**, không cache ở cấp module, để tránh dữ liệu cũ bị dùng lại giữa
các lượt chấm liên tiếp trong cùng 1 tiến trình Streamlit dài hạn.

### 5.3. Tự động phát hiện kiểu bài nộp (chương trình vs hàm)

GV không cần biết trước học sinh sẽ nộp kiểu nào. Hệ thống thử "chương trình hoàn chỉnh" trước
(khớp với thói quen phổ biến nhất); chỉ khi output rỗng và khung mẫu có đủ thông tin cho chế độ
hàm thì mới fallback — không tốn thêm 1 lượt subprocess nếu chương trình đã in ra gì đó.

### 5.4. Marker `###RESULT###` để tách kết quả thật khỏi print() thừa

Vì `function_wrapper.py` phải `exec_module()` toàn bộ file học sinh (bao gồm mọi code ở top-level,
có thể có `print()` không liên quan), nó không thể chỉ đọc dòng cuối cùng của stdout một cách ngây
thơ nếu không có marker riêng biệt khó trùng lặp ngẫu nhiên.

### 5.5. Cách ly an toàn bằng subprocess kép

Không bao giờ `import` trực tiếp code học sinh vào tiến trình chính của Streamlit (tránh code lỗi/
độc hại làm crash cả app). Có 2 lớp subprocess độc lập dùng chung `_run_subprocess()`:
chạy thẳng file (`grade_one`) và chạy qua `function_wrapper.py` (`_call_function_wrapper`) — cả
hai đều có timeout và ép `PYTHONIOENCODING=utf-8`/`PYTHONUTF8=1` để tránh lỗi tiếng Việt trên
Windows.

### 5.6. Streamlit session-state: tránh 2 bug kinh điển

- **Không one-shot pop dữ liệu editor**: bảng test case dùng key bền `tc_data_{tên_đề}` (khởi tạo
  đúng 1 lần, không `.pop()` sau khi đọc), tránh mất dữ liệu khi có rerender xen giữa.
- **Không set giá trị widget sau khi nó đã render trong cùng 1 lượt chạy script**: đổi lựa chọn
  `selectbox` (`template_choice`) sau khi lưu/xoá phải đi qua 1 key trung gian
  `pending_template_choice`, được áp dụng ở **đầu hàm trang** (trước khi `st.selectbox` render) ở
  lượt chạy kế tiếp — Streamlit cấm sửa trực tiếp session_state của 1 widget đã render.

### 5.7. Tách UI khỏi logic chấm bài hoàn toàn

`grader/` không phụ thuộc Streamlit, nên có thể viết unit test cho `runner.py`/`ast_checker.py`
bằng pytest thông thường mà không cần giả lập UI — hữu ích nếu sau này muốn thêm giao diện khác
(CLI, API) dùng chung engine chấm.

---

## 6. Cấu trúc dữ liệu JSON của 1 khung mẫu

```json
{
  "name": "Bai 1 - In so 1 den 10 bang while",
  "description": "In ra các số từ 1 đến 10, mỗi số 1 dòng, dùng vòng lặp while.",
  "function_name": null,
  "structural_rules": {
    "required_constructs": ["While"],
    "forbidden_constructs": ["For"],
    "forbidden_imports": [],
    "forbidden_calls": []
  },
  "test_cases": [
    {
      "input": "",
      "expected_output": "1\n2\n3\n4\n5\n6\n7\n8\n9\n10",
      "call_args": null,
      "call_kwargs": null,
      "expected_return": null,
      "timeout": 5,
      "note": "case duy nhất"
    }
  ]
}
```

`function_name: null` = chỉ chấp nhận bài nộp dạng chương trình hoàn chỉnh. Khi có `function_name`,
mỗi test case có thể khai thêm `call_args`/`call_kwargs`/`expected_return` để hỗ trợ song song cả
2 kiểu chấm (xem mục 4.4).

---

## 7. Các module trong `grader/` — tham chiếu nhanh

| File | Hàm/lớp chính | Việc gì |
|---|---|---|
| `models.py` | `TestCase`, `GradeResult`, `StructureResult` | Toàn bộ dữ liệu lõi đều là `@dataclass`, có `.to_dict()` để chuyển sang dict cho pandas/JSON. |
| `runner.py` | `grade_one`, `run_capture_only`, `run_function_capture_only`, `_try_function_mode`, `_parse_traceback` | Chạy code cách ly, so khớp, chấm hàm, parse lỗi. |
| `function_wrapper.py` | `main()` | Script độc lập (không import bởi Python khác, chỉ chạy như subprocess) gọi 1 hàm học sinh + bắt stdout. |
| `ast_checker.py` | `check_structure`, `_detect_recursion`, `_imported_modules`, `_called_names` | Phân tích tĩnh cấu trúc code. |
| `exam_batch.py` | `parse_filename`, `group_by_bai` | Quy ước tên file khi chấm hàng loạt nhiều đề. |
| `templates_store.py` | `list_templates`, `load_template`, `save_template`, `delete_template` | I/O đọc/ghi `templates/*.json`. |
| `pytest_plugin.py` | `GraderPlugin` | Gom `pytest_runtest_logreport` thành 2 list kết quả + báo tiến độ (`set_progress_callback`) cho thanh progress trên UI. |
| `conftest.py` | `pytest_generate_tests`, `_load_cases` | Sinh test động — bắt buộc là file thật để pytest-xdist worker tự nạp được (xem mục 5.2). |
| `test_runner.py` | `test_student_stdout`, `test_student_structure` | 2 hàm test pytest thực sự chạy, gắn kết quả vào `user_properties` để plugin đọc lại. |

---

## 8. Hạn chế đã biết

- **Không phân quyền/đăng nhập**: nếu deploy public (Streamlit Community Cloud) cho nhiều GV cùng
  dùng chung 1 link, mọi người thấy chung 1 danh sách khung mẫu (không có khái niệm "khung mẫu của
  riêng tôi"). Phù hợp với mô hình 1 GV/1 máy, hoặc 1 tổ bộ môn tin tưởng lẫn nhau.
  - **Streamlit Community Cloud dùng filesystem tạm thời**: `templates/*.json` lưu qua UI có thể
    mất khi container bị khởi động lại — nên định kỳ tải khung mẫu về/commit vào git nếu deploy
    theo hướng này.
- **An toàn subprocess ở mức timeout, chưa phải sandbox đầy đủ** (không giới hạn RAM/CPU/network,
  không chặn học sinh đọc/ghi file hệ thống) — chấp nhận được với môi trường lớp học tin cậy, không
  phù hợp nếu chạy code từ nguồn không tin cậy hoàn toàn.
- **`ast_checker` chỉ phát hiện cấu trúc ở cấp cú pháp**, không hiểu ngữ nghĩa (vd học sinh dùng
  `while True` giả làm `for` vẫn bị tính là "có While" dù ý đồ khác).
- **Chế độ hàm so sánh `return` bằng `==` sau `json.loads`/`json.dumps`** — không phân biệt được
  kiểu dữ liệu mà JSON không phân biệt (vd `tuple` vs `list`, `int` vs `float` nguyên).
