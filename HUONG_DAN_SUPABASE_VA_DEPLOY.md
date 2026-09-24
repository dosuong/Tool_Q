# Hướng dẫn: Tạo Supabase, kết nối & Deploy PyGrader (module thi online)

Hướng dẫn này dành riêng cho phần **thi/làm bài trực tuyến** (`online_exam/`) — phần cần một
cơ sở dữ liệu Postgres thật để lưu tài khoản GV, lớp, bài kiểm tra, bài nộp của học sinh
**vĩnh viễn** (không mất khi deploy lại). 3 trang chấm bài cũ (Quản lý khung mẫu/Chấm 1 đề/Chấm
cả kỳ thi) không cần Supabase, chỉ khung mẫu JSON như trước.

**Quan trọng cần biết trước:** app **KHÔNG cần** bạn tự chạy file SQL nào để tạo bảng. Ngay khi
app kết nối được tới Postgres lần đầu, `online_exam/db.py` tự động gọi
`Base.metadata.create_all()` (SQLAlchemy) để tạo đủ 11 bảng (`teachers`, `classes`, `students`,
`exams`, `exam_problems`, `test_cases`, `enrollments`, `problem_progress`, `submissions`,
`submission_results`, `teacher_sessions`) — bạn chỉ cần cung cấp đúng **connection string**.

**Có 2 phần cấu hình Supabase riêng biệt cần làm** (dễ nhầm là 1):
1. **Postgres Database** (Phần 1-2 dưới đây) — nơi lưu dữ liệu (lớp, bài kiểm tra, điểm...).
2. **Supabase Auth** (Phần 1B) — nơi xác thực đăng nhập GV thật (tài khoản do bạn tự thêm, không ai tự đăng ký được). Tài khoản HS (username/password do GV cấp trong app) **không** liên quan tới Supabase Auth — chỉ lưu trong chính Postgres ở mục 1.

---

## Phần 1 — Tạo project Supabase

### Bước 1.1 — Đăng ký & tạo project

1. Vào [supabase.com](https://supabase.com) → **Start your project** → đăng nhập bằng GitHub (khuyên dùng, tiện cho bước deploy sau).
2. Bấm **New project**:
   - **Name**: đặt tuỳ ý, vd `pygrader-thi-online`.
   - **Database Password**: đặt 1 mật khẩu **mạnh và LƯU LẠI ngay** (dán vào ghi chú tạm) — đây là mật khẩu của chính database, không phải mật khẩu đăng nhập Supabase. Sẽ cần dán vào connection string ở Bước 1.2. Tránh ký tự `@ : / ? #` trong mật khẩu vì dễ gây lỗi khi ghép vào URL (nếu bắt buộc phải dùng, xem mục Xử lý sự cố bên dưới).
   - **Region**: chọn khu vực gần nơi HS/GV dùng nhất (vd `Southeast Asia (Singapore)`) để độ trễ thấp.
   - **Pricing Plan**: **Free** — đủ dùng cho quy mô vài lớp học.
3. Bấm **Create new project**, đợi khoảng 1-2 phút để Supabase khởi tạo hạ tầng.

### Bước 1.2 — Lấy connection string (bắt buộc dùng đúng loại pooler cổng 6543)

1. Trong project vừa tạo, vào **Project Settings** (icon bánh răng ở góc dưới trái) → **Database**.
2. Kéo xuống mục **Connection string** → chọn tab **URI**.
3. Ở phần **Connection pooling**, chọn:
   - **Mode**: `Transaction`
   - Kiểm tra port hiển thị là **`6543`** (không phải `5432`) — đây là pooler tương thích với môi trường serverless/nhiều kết nối ngắn hạn như Streamlit, tránh lỗi "too many connections" khi nhiều HS cùng vào.
4. Copy chuỗi dạng:
   ```
   postgresql://postgres.xxxxxxxxxxxx:[YOUR-PASSWORD]@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres
   ```
5. Thay `[YOUR-PASSWORD]` bằng đúng mật khẩu database đã đặt ở Bước 1.1 (Supabase không tự điền sẵn mật khẩu vào ô này).

Giữ nguyên chuỗi này — sẽ dùng lại y hệt ở cả Phần 2 (chạy local) lẫn Phần 3 (deploy).

---

## Phần 1B — Bật Supabase Auth cho GV (bắt buộc để đăng nhập thật)

App dùng thẳng Supabase Auth để xác thực GV — **không** có tính năng tự đăng ký trong app,
bạn tự thêm từng tài khoản GV trong Supabase Dashboard.

### Bước 1B.1 — Lấy `anon_key`

1. Vào **Project Settings** → **API**.
2. Copy **Project URL** (dạng `https://xxxxxxxxxxxx.supabase.co`) và **anon public key** (chuỗi dài bắt đầu `eyJ...`) — **không** dùng `service_role key` (khoá đó có toàn quyền, không được đưa vào app).

### Bước 1B.2 — Thêm tài khoản GV

1. Vào **Authentication** → **Users** → **Add user** → **Create new user**.
2. Nhập email + mật khẩu cho từng GV cần cấp quyền → bấm **Create user**.
3. Lặp lại cho mỗi GV — đây là cách duy nhất để có tài khoản GV mới (không có form đăng ký trong app).
4. Muốn đổi mật khẩu 1 GV: vào đúng dòng user đó → **...** → **Send password recovery** (gửi email đổi mật khẩu) hoặc **Reset password** (đặt trực tiếp).

### Bước 1B.3 — Điền vào `secrets.toml`

Thêm mục `[supabase]` (khác `[database]` ở Phần 2 — 2 mục riêng biệt, không gộp):

```toml
[supabase]
url = "https://xxxxxxxxxxxx.supabase.co"
anon_key = "eyJ..."
```

**Nếu bỏ trống/chưa cấu hình mục này** (vd mới tải code về, chưa kịp tạo Supabase): app tự
cho phép đăng nhập bằng 1 tài khoản test cố định **CHỈ DÙNG ĐỂ CHẠY THỬ LOCAL**:
- Email: `dosuong16203@gmail.com`
- Mật khẩu: `123456`

Tài khoản test này **tự động ngừng hoạt động** ngay khi bạn điền đúng mục `[supabase]` ở trên —
không phải lo bị lộ khi deploy thật, miễn là bạn nhớ điền secrets trước khi đưa link cho người khác dùng.

---

## Phần 2 — Kết nối & chạy thử ở máy local (trước khi deploy)

### Bước 2.1 — Điền vào `secrets.toml`

Trong thư mục dự án (`E:\a_Personal_Project\PyGrader`), mở/tạo file `.streamlit/secrets.toml`
(file này đã có sẵn trong `.gitignore` — **không** commit lên GitHub) với nội dung (gộp cả 2
mục `[database]` và `[supabase]` vào cùng 1 file):

```toml
[database]
url = "postgresql://postgres.xxxxxxxxxxxx:MatKhauThat@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

[supabase]
url = "https://xxxxxxxxxxxx.supabase.co"
anon_key = "eyJ..."
```

Dán đúng chuỗi đã lấy ở Bước 1.2 (đã thay mật khẩu thật vào).

### Bước 2.2 — Chạy app, kiểm tra bảng được tạo tự động

1. Double-click `run.bat` (hoặc `streamlit run app.py` trong terminal đã activate `.venv`).
2. Vào `http://localhost:8501` → thấy trang **Đăng nhập giáo viên** hiện lên bình thường (không báo lỗi kết nối) — nghĩa là app đã kết nối được Supabase và tự tạo xong bảng.
3. Đăng nhập bằng đúng 1 tài khoản GV đã tạo ở Bước 1B.2 để xác nhận Supabase Auth hoạt động và ghi được dữ liệu thật.
4. Quay lại Supabase Dashboard → **Table Editor** (icon bảng ở sidebar trái) → sẽ thấy đủ các bảng `teachers`, `classes`, `students`, `exams`... và bảng `teachers` đã có đúng 1 dòng tự tạo (JIT-provisioning) ứng với tài khoản Auth vừa đăng nhập.

Nếu bước này lỗi, xem mục **Xử lý sự cố thường gặp** ở cuối file trước khi sang Phần 3.

### Bước 2.3 — (Tuỳ chọn) Xoá dữ liệu Supabase test để bắt đầu sạch trước khi giao cho GV thật dùng

Nếu bạn vừa test tạo vài tài khoản/lớp giả ở Bước 2.2 và muốn xoá sạch trước khi dùng thật:
vào **Table Editor**, chọn từng bảng, xoá hết dòng (thứ tự không quan trọng vì các bảng đều
có `ON DELETE CASCADE` — xoá `teachers` sẽ tự xoá theo `classes`/`exams`/... liên quan), hoặc
đơn giản nhất là **Project Settings → General → Restart project** không xoá dữ liệu, mà phải
xoá tay từng bảng như trên (Supabase free tier không có nút "reset schema" 1 cú bấm).

---

## Phần 3 — Deploy lên Streamlit Community Cloud

### Bước 3.1 — Đẩy code lên GitHub

1. Nếu repo chưa có trên GitHub: tạo 1 repo mới (private hoặc public đều được), rồi:
   ```bash
   git remote add origin https://github.com/<ten-ban>/<ten-repo>.git
   git push -u origin master
   ```
2. **Kiểm tra lại** `.gitignore` đã chặn `.streamlit/secrets.toml` và `online_exam_dev.db` — tuyệt đối không để lộ mật khẩu database lên GitHub công khai. Chạy `git status` trước khi push để chắc chắn 2 file này không nằm trong danh sách "Changes to be committed".

### Bước 3.2 — Tạo app trên Streamlit Community Cloud

1. Vào [share.streamlit.io](https://share.streamlit.io) → đăng nhập bằng GitHub.
2. Bấm **Create app** → **Deploy a public app from GitHub** (hoặc private nếu repo private, cần cấp quyền truy cập).
3. Điền:
   - **Repository**: chọn đúng repo PyGrader.
   - **Branch**: `master` (hoặc `main` tuỳ tên nhánh chính của bạn).
   - **Main file path**: `app.py`.
   - **App URL**: đặt tên tuỳ ý, vd `pygrader-yourschool` → sẽ ra link `https://pygrader-yourschool.streamlit.app`.

### Bước 3.3 — Khai báo Secrets (bắt buộc, thay cho file `secrets.toml`)

1. Trước khi bấm Deploy (hoặc sau đó vào **App settings → Secrets**), dán đúng **toàn bộ** nội dung `secrets.toml` ở Bước 2.1 (cả 2 mục `[database]` và `[supabase]`, thiếu mục nào cũng gây lỗi):
   ```toml
   [database]
   url = "postgresql://postgres.xxxxxxxxxxxx:MatKhauThat@aws-0-ap-southeast-1.pooler.supabase.com:6543/postgres"

   [supabase]
   url = "https://xxxxxxxxxxxx.supabase.co"
   anon_key = "eyJ..."
   ```
   (y hệt nội dung file `.streamlit/secrets.toml` ở Bước 2.1 — Streamlit Cloud dùng ô Secrets thay cho file, vì file đã bị `.gitignore` chặn không đẩy lên GitHub). **Thiếu mục `[supabase]`**: app vẫn chạy nhưng tự rơi về tài khoản test cố định — bất kỳ ai biết được `dosuong16203@gmail.com`/`123456` (đã in trong file hướng dẫn này) đều đăng nhập được, nên **bắt buộc** phải điền `[supabase]` trước khi đưa link cho người khác dùng.
2. Bấm **Save**.

### Bước 3.4 — Deploy & kiểm tra

1. Bấm **Deploy** — đợi vài phút để Streamlit Cloud cài `requirements.txt` và khởi động app. Theo dõi log ở góc dưới phải nếu muốn xem tiến trình / bắt lỗi cài đặt gói.
2. App live → mở link (`https://<ten-app>.streamlit.app`) → kiểm tra:
   - Trang đăng nhập GV hiện đúng, đăng nhập lại được tài khoản đã tạo ở Bước 2.2 (chứng tỏ Cloud đang trỏ đúng vào Supabase, không phải SQLite local).
   - Mở thêm 1 tab ẩn danh, dán `https://<ten-app>.streamlit.app/?exam=<mã_lớp_thật>` → luồng học sinh hiện đúng, không cần đăng nhập.
3. Từ giờ, **mỗi lần bạn `git push` code mới lên nhánh đã deploy, Streamlit Cloud tự động build & deploy lại** — không cần thao tác thủ công gì thêm.

---

## Phần 4 — Vận hành thật: những điều cần nhớ

1. **"Đánh thức" app trước giờ thi**: cả Supabase free tier và Streamlit Community Cloud free tier đều tự tạm ngưng (sleep/pause) sau một thời gian không có ai truy cập — lần truy cập đầu tiên sau khi ngủ sẽ chậm vài giây tới vài chục giây (cold start). **Mở thử link app khoảng 5-10 phút trước giờ thi** để "đánh thức" trước, tránh HS tưởng app bị treo ngay phút đầu giờ thi.
2. **Theo dõi log khi có sự cố**: vào trang quản lý app trên share.streamlit.io → xem **Manage app → Logs** để biết lỗi thật (vd hết bộ nhớ, lỗi kết nối DB) thay vì đoán mò.
3. **Cập nhật code**: sửa code ở máy local → test kỹ bằng `run.bat` → `git push` → Streamlit Cloud tự deploy lại (thường mất 1-3 phút). Tránh sửa trực tiếp trên GitHub web rồi quên kéo về máy, dễ bị lệch code.
4. **Sao lưu dữ liệu định kỳ**: Supabase free tier không có backup point-in-time dài hạn. Sau mỗi đợt kiểm tra quan trọng, nên vào trang **Kết quả bài kiểm tra online** trong app, tải CSV bảng điểm + ZIP bài làm về lưu riêng — đừng chỉ tin tưởng hoàn toàn vào 1 bản duy nhất trên Supabase.
5. **Giới hạn quy mô free tier**: phù hợp khoảng 1 lớp 30-45 HS nộp bài cùng lúc trên 1 app. Nếu tổ chức nhiều lớp thi trùng giờ trên cùng 1 app, cân nhắc nâng gói Streamlit Cloud/Supabase hoặc tách lịch thi lệch giờ.

---

## Xử lý sự cố thường gặp

| Triệu chứng | Nguyên nhân thường gặp | Cách xử lý |
|---|---|---|
| App báo lỗi kết nối DB ngay khi mở (local hoặc Cloud) | Sai connection string, hoặc chưa thay `[YOUR-PASSWORD]` bằng mật khẩu thật | Kiểm tra lại từng ký tự trong `secrets.toml`/ô Secrets, đảm bảo copy đúng từ Supabase, không thừa/thiếu dấu ngoặc kép |
| Lỗi `password authentication failed` | Gõ sai/nhớ nhầm mật khẩu database lúc tạo project | Vào **Project Settings → Database → Reset database password**, đặt mật khẩu mới, cập nhật lại connection string ở cả `secrets.toml` local lẫn Secrets trên Cloud |
| Mật khẩu database có ký tự đặc biệt (`@`, `:`, `/`, `#`, ...) gây lỗi parse URL | Các ký tự này có ý nghĩa riêng trong cú pháp URL | Đặt lại mật khẩu chỉ gồm chữ + số (an toàn nhất), hoặc URL-encode ký tự đặc biệt (vd `@` → `%40`) nếu bắt buộc giữ |
| `too many connections` khi nhiều HS cùng vào | Đang dùng nhầm cổng `5432` (kết nối trực tiếp, giới hạn số kết nối thấp) thay vì pooler `6543` | Quay lại Bước 1.2, đảm bảo connection string đúng cổng `6543` và đúng chế độ `Transaction` |
| App local chạy được (SQLite) nhưng không thấy bảng nào trong Supabase | Chưa điền `secrets.toml`, app đang tự rơi về SQLite cục bộ (`online_exam_dev.db`) theo đúng thiết kế fallback | Kiểm tra file `.streamlit/secrets.toml` có tồn tại và đúng định dạng `[database]\nurl = "..."` |
| Deploy trên Cloud báo lỗi cài `psycopg2-binary` | Rất hiếm, thường do version Python trên Cloud không khớp | Vào **App settings → Advanced settings** kiểm tra Python version, hoặc thử pin lại version cụ thể trong `requirements.txt` |
| Sau khi deploy, sửa code push lên nhưng app không đổi | Cloud cache build cũ, hoặc push nhầm nhánh không phải nhánh đã deploy | Vào **Manage app → Reboot app**, kiểm tra đúng branch đã cấu hình ở Bước 3.2 |
| GV đăng nhập báo "Email hoặc mật khẩu không đúng" dù chắc chắn đúng | Chưa thêm tài khoản đó trong Supabase Authentication > Users (Bước 1B.2), hoặc gõ sai `anon_key`/`url` ở mục `[supabase]` | Vào **Authentication → Users** kiểm tra đúng email đã tồn tại; kiểm tra lại `anon_key` copy đúng từ **Project Settings → API** (không phải `service_role key`) |
| Tài khoản test `dosuong16203@gmail.com` vẫn đăng nhập được sau khi đã deploy thật | Quên điền mục `[supabase]` trong Secrets trên Streamlit Cloud (Bước 3.3) | Bổ sung ngay mục `[supabase]` vào Secrets rồi **Reboot app** — tài khoản test tự động ngừng hoạt động ngay khi mục này có mặt |
