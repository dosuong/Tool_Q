# Hướng dẫn "Sinh đáp án tự động" — các dạng bài & cách nhập

Đây là tính năng dùng nhiều nhất khi tạo khung mẫu: upload 1 file lời giải mẫu đúng, gõ input/tham số mẫu, app tự chạy và điền đáp án — khỏi cần tự tính tay.

**Nguyên tắc chung cho cả 2 chế độ**: mỗi **khối** = 1 test case, các khối cách nhau bằng 1 dòng **chỉ chứa `---`**.

---

## A. Chế độ CHƯƠNG TRÌNH (đọc `input()`, tự `print()`)

Mỗi dòng trong 1 khối = đúng 1 lần chương trình gọi `input()`.

### A1. Không cần input (chương trình cố định)

Ví dụ: in các số 1 → 10 trên cùng 1 dòng.

```python
# solution.py
for i in range(1, 11):   # range(1, 11) mới đủ tới 10 — range(1, 10) chỉ ra tới 9!
    print(i, end=" ")
print()
```

Vì không có `input()` nào, ô "Danh sách input mẫu" **để trống** — app tự hiểu là 1 test case duy nhất với input rỗng. Đáp án sinh ra: `1 2 3 4 5 6 7 8 9 10 ` (có khoảng trắng cuối do `end=" "` — không sao, hệ thống tự bỏ qua khoảng trắng thừa cuối dòng khi so sánh).

### A2. Đọc 1 số duy nhất

```python
n = int(input())
print(n * 2)
```
Input mẫu:
```
5
---
10
```

### A3. Đọc nhiều số, mỗi số 1 dòng riêng

```python
a = int(input())
b = int(input())
print(a + b)
```
Input mẫu:
```
3
5
---
10
-2
```

### A4. Đọc 1 mảng trên 1 dòng (cách nhau bởi dấu cách) — dạng phổ biến nhất

```python
n = int(input())
arr = list(map(int, input().split()))
print(max(arr))
```
Input mẫu (mỗi khối 2 dòng: `n`, rồi cả mảng cách nhau dấu cách):
```
5
5 3 8 3 9
---
3
10 20 30
```

### A5. Đọc mảng + 1 tham số khác (vd tìm số lớn thứ k)

```python
n = int(input())
arr = list(map(int, input().split()))
k = int(input())
sorted_desc = sorted(arr, reverse=True)
print(sorted_desc[0])
print(sorted_desc[k - 1])
```
Input mẫu (mỗi khối 3 dòng: `n`, mảng, `k`):
```
5
5 3 8 3 9
2
---
3
10 20 30
1
```

### A6. Đọc chuỗi

```python
s = input()
print(s[::-1])
```
Input mẫu:
```
hello
---
Python
```

---

## B. Chế độ HÀM (gọi trực tiếp, không qua stdin)

**Quy tắc bắt buộc phải nhớ**: mỗi khối `call_args` là **1 mảng JSON chứa đúng số tham số của hàm, theo đúng thứ tự**. Nếu bản thân 1 tham số là mảng, phải **bọc thêm 1 lớp ngoặc** cho tham số đó.

### B1. Không tham số

```python
def loi_chao():
    return "Hello"
```
call_args mẫu:
```
[]
```

### B2. 1 tham số (số hoặc chuỗi)

```python
def binh_phuong(x):
    return x * x
```
call_args mẫu:
```
[5]
---
[-3]
```

### B3. 2 tham số đơn giản

```python
def giai(a, b):
    return a + b
```
call_args mẫu:
```
[3, 5]
---
[10, -2]
```

### B4. 1 tham số là MẢNG — nhớ bọc thêm ngoặc

```python
def tong_mang(arr):
    return sum(arr)
```
call_args mẫu:
```
[[1, 2, 3, 4, 5]]
---
[[10, 20, 30]]
```
Ngoặc **ngoài** = danh sách tham số (ở đây chỉ có 1 phần tử) — ngoặc **trong** = chính mảng `arr`.

### B5. Mảng + 1 tham số khác — đúng dạng bạn hỏi "số lớn nhất và số lớn thứ K"

```python
def giai(arr, k):
    sorted_desc = sorted(arr, reverse=True)
    return [sorted_desc[0], sorted_desc[k - 1]]
```
call_args mẫu (giống hệt ví dụ bạn viết `[[1, 2, 3, 4, 5], 3]` — đúng):
```
[[1, 2, 3, 4, 5], 3]
---
[[10, 20, 30], 1]
```
Ngoặc ngoài có **2 phần tử** (đúng 2 tham số của `giai`): phần tử 1 là mảng `arr` (có ngoặc riêng), phần tử 2 là số `k` (không cần bọc thêm vì vốn đã là giá trị đơn).

### B6. Hàm chỉ `print()`, không `return`

```python
def in_loi_chao():
    print("Xin chao")
```
call_args mẫu:
```
[]
```
→ app tự điền `expected_output: "Xin chao"` (và `expected_return: null`).

---

## Bảng tra nhanh: bao nhiêu lớp ngoặc cho `call_args`?

| Hàm có... | Cách viết call_args |
|---|---|
| 0 tham số | `[]` |
| 1 số/chuỗi | `[5]` hoặc `["abc"]` |
| 2+ số/chuỗi | `[3, 5]` |
| 1 mảng | `[[1, 2, 3]]` |
| 1 mảng + tham số khác | `[[1, 2, 3], 5]` |
| 2 mảng | `[[1, 2], [3, 4]]` |

**Mẹo nhớ nhanh**: đếm dấu phẩy ở cấp ngoài cùng của `call_args` = đúng bằng số tham số hàm nhận. Nếu 1 "tham số" của bạn lại chứa dấu phẩy bên trong (vd 1 mảng nhiều phần tử), nó phải nằm gọn trong 1 cặp ngoặc riêng để không bị đếm nhầm thành nhiều tham số.

---

# PHỤ LỤC: Ngân hàng ví dụ theo chủ đề Tin học THPT

Toàn bộ đáp án dưới đây đã được **chạy kiểm chứng thực tế**, copy code + `call_args` là dùng được ngay (chế độ Hàm). Muốn dùng chế độ Chương trình, chỉ cần viết lại thành script đọc `input()`/`print()` tương ứng như phần A ở trên.

## I. Cấu trúc rẽ nhánh (if/else)

**Kiểm tra chẵn/lẻ**
```python
def kiem_tra_chan_le(n):
    return "Chan" if n % 2 == 0 else "Le"
```
call_args: `[4]` → `"Chan"` · `[7]` → `"Le"`

**Kiểm tra năm nhuận**
```python
def nam_nhuan(y):
    return (y % 4 == 0 and y % 100 != 0) or (y % 400 == 0)
```
call_args: `[2024]` → `true` · `[1900]` → `false` · `[2000]` → `true`

## II. Cấu trúc lặp (for/while) — số học cơ bản

**Tổng từ 1 đến n**
```python
def tong_1_n(n):
    s = 0
    for i in range(1, n + 1):
        s += i
    return s
```
call_args: `[10]` → `55`

**Đếm số lượng số nguyên tố trong đoạn [1, n]**
```python
def dem_nguyen_to(n):
    c = 0
    for i in range(2, n + 1):
        is_p = True
        for j in range(2, int(i ** 0.5) + 1):
            if i % j == 0:
                is_p = False
                break
        if is_p:
            c += 1
    return c
```
call_args: `[10]` → `4` (2, 3, 5, 7)

**Ước chung lớn nhất (UCLN) / Bội chung nhỏ nhất (BCNN) — thuật toán Euclid**
```python
def ucln(a, b):
    while b:
        a, b = b, a % b
    return a

def bcnn(a, b):
    return a * b // ucln(a, b)
```
call_args cho `ucln`: `[12, 18]` → `6` — call_args cho `bcnn`: `[4, 6]` → `12`
(2 hàm khác nhau → tạo 2 khung mẫu riêng, mỗi khung khai báo đúng 1 tên hàm.)

## III. Mảng / Danh sách (List)

**Tổng và trung bình cộng**
```python
def tong_tb(arr):
    return [sum(arr), sum(arr) / len(arr)]
```
call_args: `[[1, 2, 3, 4]]` → `[10, 2.5]`

**Đếm số dương / âm / bằng 0**
```python
def dem_dau(arr):
    duong = sum(1 for x in arr if x > 0)
    am = sum(1 for x in arr if x < 0)
    khong = len(arr) - duong - am
    return [duong, am, khong]
```
call_args: `[[-1, 2, -3, 0, 5]]` → `[2, 2, 1]`

**Tìm kiếm tuyến tính (trả vị trí, -1 nếu không có)**
```python
def tim_kiem(arr, x):
    return arr.index(x) if x in arr else -1
```
call_args: `[[3, 7, 1, 9], 7]` → `1` · `[[3, 7, 1, 9], 100]` → `-1`

**Đảo ngược mảng**
```python
def dao_mang(arr):
    return arr[::-1]
```
call_args: `[[1, 2, 3]]` → `[3, 2, 1]`

**Sắp xếp không dùng `sorted`/`.sort()`** — xem ví dụ đầy đủ (bubble sort) trong `CAC_DANG_DE_HO_TRO.md` mục 7, nhớ đặt `forbidden_calls: ["sorted", "sort"]`.

## IV. Xâu ký tự (String)

**Độ dài chuỗi**
```python
def do_dai(s):
    return len(s)
```
call_args: `["Xin chao"]` → `8`

**Kiểm tra chuỗi đối xứng (palindrome)**
```python
def la_doi_xung(s):
    t = s.lower()
    return t == t[::-1]
```
call_args: `["madam"]` → `true` · `["hello"]` → `false`

**Đếm số từ**
```python
def dem_tu(s):
    return len(s.split())
```
call_args: `["Hello the world"]` → `3`

**Đếm số lần xuất hiện 1 ký tự**
```python
def dem_ky_tu(s, c):
    return s.count(c)
```
call_args: `["banana", "a"]` → `3`

**Viết hoa chữ cái đầu mỗi từ**
```python
def viet_hoa(s):
    return s.title()
```
call_args: `["chao ban"]` → `"Chao Ban"`

## V. Số học / Lý thuyết số

**Số hoàn hảo** (tổng ước số, trừ chính nó, bằng chính nó)
```python
def la_so_hoan_hao(n):
    return sum(i for i in range(1, n) if n % i == 0) == n
```
call_args: `[6]` → `true` · `[28]` → `true` · `[10]` → `false`

**Số chính phương**
```python
def la_chinh_phuong(n):
    r = int(n ** 0.5)
    return r * r == n
```
call_args: `[16]` → `true` · `[17]` → `false`

**Phân tích ra thừa số nguyên tố**
```python
def phan_tich(n):
    factors = []
    d = 2
    while d * d <= n:
        while n % d == 0:
            factors.append(d)
            n //= d
        d += 1
    if n > 1:
        factors.append(n)
    return factors
```
call_args: `[12]` → `[2, 2, 3]` · `[17]` → `[17]`

**Số đối xứng (số Palindrome, khác với chuỗi ở mục IV)**
```python
def la_so_doi_xung(n):
    s = str(n)
    return s == s[::-1]
```
call_args: `[121]` → `true` · `[123]` → `false`

## VI. Đệ quy

**Dãy Fibonacci đệ quy** — nhớ đặt `required_constructs: ["Recursion"]`
```python
def fib(n):
    return n if n < 2 else fib(n - 1) + fib(n - 2)
```
call_args: `[0]` → `0` · `[1]` → `1` · `[10]` → `55`

**Tổng 1..n bằng đệ quy**
```python
def tong_de_quy(n):
    return 0 if n == 0 else n + tong_de_quy(n - 1)
```
call_args: `[5]` → `15`

## VII. Ma trận (danh sách 2 chiều)

Lưu ý: ma trận là 1 tham số nhưng bản thân nó đã là "mảng của mảng" — `call_args` cần **3 lớp ngoặc**: ngoặc ngoài (danh sách tham số) + ngoặc của ma trận + ngoặc của từng dòng.

**Tổng toàn bộ phần tử**
```python
def tong_ma_tran(m):
    return sum(sum(row) for row in m)
```
call_args: `[[[1, 2], [3, 4]]]` → `10`

**Tổng đường chéo chính** (ma trận vuông)
```python
def duong_cheo(m):
    return sum(m[i][i] for i in range(len(m)))
```
call_args: `[[[1, 2, 3], [4, 5, 6], [7, 8, 9]]]` → `15`

**Ma trận chuyển vị**
```python
def chuyen_vi(m):
    return [list(row) for row in zip(*m)]
```
call_args: `[[[1, 2], [3, 4], [5, 6]]]` → `[[1, 3, 5], [2, 4, 6]]`

## VIII. Từ điển / đếm tần suất (nâng cao)

`expected_return` cũng chấp nhận kiểu **object JSON** (tương ứng `dict` trong Python) — so sánh không phân biệt thứ tự khoá.

```python
def dem_tan_suat(s):
    d = {}
    for c in s:
        d[c] = d.get(c, 0) + 1
    return d
```
call_args: `["aab"]` → `{"a": 2, "b": 1}`

## IX. Dạng bài KHÔNG phù hợp với PyGrader (giới hạn hiện tại)

- **Đọc/ghi file** (`open("input.txt")`...): công cụ chỉ cấp dữ liệu qua `input()`/tham số hàm, không tự tạo sẵn file mẫu trên đĩa cho chương trình đọc — cần đổi đề sang đọc từ `input()` để chấm được.
- **Có yếu tố ngẫu nhiên** (`random` không `seed` cố định): output không lặp lại giống nhau mỗi lần chạy nên không so khớp được.
- **Vẽ hình/đồ hoạ** (turtle, matplotlib...): ngoài phạm vi so khớp văn bản của công cụ.
- **Số thực có sai số làm tròn dài** (vd chia không hết): nên làm tròn kết quả trong code (`round(x, 2)`) trước khi `return`/`print` để đáp án mẫu ổn định, tránh lệch ở chữ số thập phân cuối.
