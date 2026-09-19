# Hướng dẫn sử dụng Tool_Q

Công cụ chấm bài lập trình Python tự động cho giáo viên — so khớp output, chấm được cả bài nộp dạng hàm, kiểm tra cấu trúc code, và chấm hàng loạt bằng pytest.

**Mô hình sử dụng**: giáo viên tự thu bài học sinh (qua Zalo, Google Classroom, email...) rồi tự upload vào công cụ. Học sinh không cần truy cập công cụ này.

---

## 1. Cài đặt & chạy

| Việc cần làm | Thao tác |
|---|---|
| Lần đầu tiên (chỉ 1 lần) | Double-click `setup.bat` — tự tạo môi trường ảo Python và cài `streamlit`, `pytest`, `pandas`, `pytest-xdist`. |
| Mỗi lần muốn dùng | Double-click `run.bat` — tự mở trình duyệt tới `http://localhost:8501`. Đóng cửa sổ terminal đen sẽ tắt app. |
| Nhiều giáo viên cùng dùng | Xem mục [7. Triển khai](#7-triển-khai-cho-nhiều-giáo-viên) bên dưới. |

Nếu gặp lỗi **Permission denied** khi chạy `run.bat`: đóng hết cửa sổ terminal cũ, đợi vài giây rồi mở lại — thường chỉ là xung đột tạm thời (có tiến trình khác đang giữ file).

---

## 2. Quy trình tổng quát

1. **Tạo khung mẫu** (tab "Quản lý khung mẫu"): đặt tên đề, khai báo input/đáp án mẫu cho từng test case.
2. **Upload bài học sinh** (tab "Chấm 1 đề" hoặc "Chấm cả kỳ thi"): chọn đúng khung mẫu, upload file `.py`.
3. **Xem kết quả**: bấm Chấm bài — hệ thống chạy pytest ngầm, trả về bảng điểm, chi tiết lỗi từng dòng, và file CSV tải về.

---

## 3. Tab "Quản lý khung mẫu"

### 3.1. Chọn / tạo đề bài

| Ô | Chức năng |
|---|---|
| **Chọn đề có sẵn để sửa** | Để trống = đang tạo đề mới. Chọn 1 đề = nạp toàn bộ dữ liệu đề đó vào các ô bên dưới. |
| **Tên đề bài** | Tên dùng làm tên file lưu (vd `Bai_1` → `templates/Bai_1.json`). Ký tự đặc biệt bị loại, dấu cách đổi thành `_`. |
| **Mô tả ngắn** | Hiển thị cho GV khi chọn đề ở tab Chấm bài — không ảnh hưởng logic chấm. |
| **Xoá khung mẫu này** (chỉ hiện khi đã chọn đề có sẵn) | Tick xác nhận rồi mới bấm được nút xoá — tránh xoá nhầm. Xoá vĩnh viễn, không hoàn tác. |

### 3.2. Khung "Yêu cầu cấu trúc code" (tuỳ chọn)

| Ô | Chức năng |
|---|---|
| **Bắt buộc dùng** | Chọn trong `For / While / ListComp / Recursion`. Bài nộp thiếu cấu trúc này bị đánh dấu vi phạm dù output đúng. |
| **Cấm dùng** | Cùng danh sách trên — bài nộp có dùng cấu trúc này bị đánh dấu vi phạm. |
| **Cấm import các thư viện** | Tên thư viện cách nhau dấu phẩy, vd `math, itertools`. Bắt qua câu lệnh `import`. |
| **Cấm gọi hàm/phương thức có sẵn** | Vd `sorted, sort, min, max`. `sorted` chặn `sorted(x)`, `sort` chặn `x.sort()` — cần điền cả hai nếu muốn chặn trọn vẹn. |
| **Tên hàm cho phép nộp dạng hàm** | Để trống = chỉ nhận chương trình hoàn chỉnh. Điền tên (vd `giai`) = học sinh có thể chỉ viết 1 hàm, hệ thống tự phát hiện và gọi hàm đó. |

### 3.3. Hộp "Sinh đáp án tự động từ file lời giải mẫu" (tuỳ chọn)

| Ô | Chức năng |
|---|---|
| **Upload solution.py** | File lời giải đúng của GV — phải là **chương trình hoàn chỉnh** (đọc `input()`, tự `print()`). Không dùng được cho chế độ hàm. |
| **Danh sách input mẫu** | Mỗi bộ input cho 1 test case, các bộ cách nhau bởi 1 dòng chỉ chứa `---`. Mỗi dòng trong 1 bộ = 1 lần gọi `input()`. |
| **Sinh đáp án từ lời giải mẫu** | Chạy `solution.py` với từng bộ input, lấy output làm `expected_output`, tự điền vào bảng Test case. |

### 3.4. Bảng Test case

Sửa trực tiếp như Excel — bấm dấu `+` ở cuối bảng để thêm dòng, chọn dòng rồi xoá để bớt.

| Cột | Dùng khi nào |
|---|---|
| `input (stdin)` | Chế độ **chương trình**. Giả lập bàn phím, mỗi lần `input()` đọc 1 dòng. |
| `expected_output` | Chế độ **chương trình**. Output đúng mong đợi. |
| `call_args (JSON)` | Chế độ **hàm**. Danh sách tham số gọi hàm, cú pháp JSON — vd `[3, 5]`. |
| `expected_return (JSON)` | Chế độ **hàm**. Giá trị hàm phải trả về, cú pháp JSON — vd `8` hoặc `[9, 8]`. |
| `timeout (s)` | Số giây tối đa cho phép chạy — bài lặp vô hạn bị dừng và tính là trượt. |
| `ghi chú` | Chỉ để GV dễ nhớ. |

> Một test case có thể điền **cả 2 cặp cột** cùng lúc — hệ thống tự chọn đúng cặp theo cách học sinh nộp bài (xem mục 6.1).

### 3.5. Nâng cao & Lưu

| Ô / nút | Chức năng |
|---|---|
| **Nâng cao: xem/nạp JSON trực tiếp** | Xem trước JSON sẽ lưu; có thể dán 1 JSON khác vào ô rồi bấm "Nạp JSON vào bảng test case" để điền nhanh. |
| **Lưu khung mẫu** | Ghi file JSON. Cảnh báo trước nếu có dòng bỏ trống `expected_output` (và không có `expected_return`). |

---

## 4. Tab "Chấm 1 đề"

Dùng khi chấm lẻ tẻ 1 bài tập cho 1 đề duy nhất.

| Ô / nút | Chức năng |
|---|---|
| Chọn đề bài | Chọn khung mẫu đã tạo ở Tab 1. |
| Chạy song song (pytest-xdist) | Bật để chấm nhiều file cùng lúc — nhanh hơn khi nhiều bài nộp/nhiều bài bị timeout. |
| Số luồng song song | Chỉ hiện khi bật chạy song song, mặc định 4, giới hạn theo số nhân CPU máy. |
| Upload bài làm học sinh (.py) | Chọn nhiều file `.py` cùng lúc. |
| Chấm bài | Chạy pytest ngầm cho toàn bộ file × toàn bộ test case của đề. |

---

## 5. Tab "Chấm cả kỳ thi"

Dùng khi có nhiều đề cùng lúc (vd 1 kỳ thi 5 bài) — upload toàn bộ bài của cả lớp trong 1 lần.

| Ô / nút | Chức năng |
|---|---|
| Chọn các đề tham gia kỳ thi | Chọn toàn bộ khung mẫu thuộc kỳ thi. |
| `'<tên đề>' = bai` | 1 ô cho mỗi đề đã chọn — gán đề đó ứng với số mấy trong tên file học sinh nộp. |
| Chạy song song / Số luồng | Giống Tab "Chấm 1 đề" — nên bật khi số file lớn. |
| Upload toàn bộ bài làm học sinh | Chọn tất cả file `.py` của mọi học sinh, mọi bài, 1 lần. |
| Chấm toàn bộ | Tự phân loại file theo tên, ghép đúng đề, chấm hết trong 1 lượt. |

> **Quy ước đặt tên file bắt buộc**: `<ten_hoc_sinh>_bai<N>.py` — ví dụ `NguyenVanA_bai1.py`, `NguyenVanA_bai2.py`. File sai quy ước bị liệt kê riêng trong cảnh báo và **không được chấm**.

---

## 6. Khái niệm quan trọng

### 6.1. Program mode vs Function mode — tự động phát hiện

Nếu đề có khai báo **Tên hàm cho phép nộp dạng hàm**, hệ thống thử theo thứ tự:

1. Chạy file như 1 chương trình độc lập, truyền `input` vào stdin. Có in ra gì đó → so với `expected_output`. **Xong.**
2. Nếu chạy xong không lỗi nhưng **không in gì** (stdout rỗng) → chuyển bước 3.
3. Import file như 1 module, gọi hàm theo tên đã khai báo với `call_args` → so giá trị trả về với `expected_return`.

Nhờ vậy học sinh viết chương trình hoàn chỉnh *hoặc* chỉ viết hàm đều được chấm đúng.

### 6.2. Kiểm tra cấu trúc code (AST)

Đây là kiểm tra **tĩnh** — chỉ đọc mã nguồn thành cây cú pháp, không chạy chương trình — nên phát hiện được cả những thứ không thể biết qua output (có dùng `for` không, có gọi `sorted()` không...). Ngược lại, không đánh giá được thuật toán tối ưu hay không — chỉ đúng/sai theo đúng luật đã khai báo.

### 6.3. Timeout & an toàn khi chạy code học sinh

Mỗi bài nộp chạy trong 1 tiến trình con riêng biệt (subprocess) kèm giới hạn thời gian (`timeout`, mặc định 5 giây) — đủ chặn vòng lặp vô hạn mà không cần Docker/sandbox phức tạp.

### 6.4. Chạy song song (pytest-xdist)

Mặc định chấm tuần tự. Với lớp đông hoặc nhiều đề cùng lúc, bật "Chạy song song" để chấm đồng thời nhiều file — giảm thời gian chờ, kết quả giống hệt dù bật hay tắt.

---

## 7. Triển khai cho nhiều giáo viên

Mặc định Tool_Q chạy riêng trên máy 1 người. Muốn các GV khác trong trường cùng dùng qua 1 link:

1. Đẩy toàn bộ thư mục dự án lên 1 GitHub repository (nên để **riêng tư** vì chứa đề thi).
2. Vào `share.streamlit.io` → đăng nhập bằng GitHub → chọn repo, chọn file `app.py` → Deploy.
3. Nhận 1 link cố định dạng `https://ten-app.streamlit.app`, gửi cho các GV khác.

> Lưu ý: mọi người dùng chung 1 link sẽ thấy chung danh sách khung mẫu — công cụ hiện chưa phân vùng riêng theo từng giáo viên.

---

## 8. Xử lý sự cố thường gặp

| Hiện tượng | Nguyên nhân | Cách xử lý |
|---|---|---|
| Bài đúng vẫn báo "Output không khớp", ô Kỳ vọng trống trơn | `expected_output` của test case đó chưa được điền | Vào Tab 1, điền đáp án đúng vào bảng Test case, Lưu lại |
| Lưu khung mẫu báo lỗi JSON không hợp lệ | `call_args`/`expected_return` gõ sai cú pháp JSON | Dùng đúng cú pháp: mảng `[3, 5]`, chuỗi có ngoặc kép `"chuoi"`, không dấu phẩy dư ở cuối |
| Nộp dạng hàm luôn báo "Không tìm thấy hàm" | Tên hàm học sinh đặt khác tên đã khai báo | Nhắc học sinh đặt đúng tên hàm quy ước, hoặc sửa lại tên hàm trong khung mẫu |
| Chạy `run.bat` báo Permission denied | Tiến trình khác đang giữ file / phần mềm diệt virus quét tạm thời | Đóng hết cửa sổ terminal cũ, thử lại sau vài giây |
| Chấm cả kỳ thi: một số file "biến mất" | Tên file không đúng quy ước `<hoc_sinh>_bai<N>.py` | Xem cảnh báo phía trên bảng kết quả, đổi tên đúng chuẩn rồi upload lại |
| Cấm `sorted` nhưng học sinh dùng `.sort()` vẫn lọt | `sorted` và `sort` là 2 tên gọi khác nhau | Điền cả hai: `sorted, sort` |

---

Xem thêm file [`CAC_DANG_DE_HO_TRO.md`](CAC_DANG_DE_HO_TRO.md) để có sẵn ví dụ JSON khung mẫu cho từng dạng bài — copy vào ô "Nâng cao: xem/nạp JSON trực tiếp" rồi bấm "Nạp JSON vào bảng test case".
