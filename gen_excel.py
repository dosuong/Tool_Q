import pandas as pd
data = [
    {'Học sinh': 'Nguyễn Văn A', 'Tài khoản': '1a01012000', 'Bài': 'Câu 1: Tính tổng', 'Điểm': 10.0, 'Lượt nộp': 1, 'Trạng thái': 'Hoàn thành', 'Lỗi tại Test Case': '', 'Chi tiết lỗi': ''},
    {'Học sinh': 'Nguyễn Văn A', 'Tài khoản': '1a01012000', 'Bài': 'Câu 2: Số nguyên tố', 'Điểm': 0.0, 'Lượt nộp': 3, 'Trạng thái': 'Có lỗi', 'Lỗi tại Test Case': '2', 'Chi tiết lỗi': 'Lỗi: ValueError tại dòng 5\nTraceback (most recent call last):\n  File "solution.py", line 5, in <module>\n    int("a")'},
    {'Học sinh': 'Nguyễn Văn A', 'Tài khoản': '1a01012000', 'Bài': 'Câu 3: Đếm từ', 'Điểm': 0.0, 'Lượt nộp': 1, 'Trạng thái': 'Có lỗi', 'Lỗi tại Test Case': '1', 'Chi tiết lỗi': 'Sai kết quả đầu ra (không khớp mong đợi)'}
]
df = pd.DataFrame(data)
df.to_excel('mau_chi_tiet_loi.xlsx', index=False)
print('Done!')
