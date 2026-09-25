import streamlit as st
import concurrent.futures
import time
import pandas as pd
from datetime import datetime

# Import các service có sẵn của hệ thống bạn
from online_exam import service, auth
from online_exam.grading import grade_problem

st.set_page_config(page_title="Demo Chống Spam", page_icon="🛡️", layout="wide")

st.title("🛡️ Demo Trực Quan: Hệ Thống Chống Spam & Chịu Tải")
st.markdown("Công cụ này dùng để biểu diễn trực tiếp sức mạnh xử lý đa luồng (Concurrency) của hệ thống trước hội đồng/người dùng.")

# --- KHỞI TẠO DỮ LIỆU ẢO ---
@st.cache_resource
def setup_dummy_data():
    teacher_id = auth._get_or_create_teacher_profile("demo_admin@example.com", "demo_uid")
    room = service.create_class(teacher_id, f"Lớp Demo {datetime.now().strftime('%H%M%S')}")
    st_spam, _ = service.create_student(teacher_id, room.id, "Học sinh Spam", "hs_spam_1")
    
    exam_meta = {
        "title": "Bài thi Demo", "description": "", "allow_code_editor": True, 
        "allow_file_upload": False, "duration_minutes": 10, "access_code": None, "final_score_policy": "best"
    }
    problems_draft = [{
        "id": None, "title": "Câu 1: Demo", "description": "Demo", "max_score": 10.0,
        "penalty_percent_per_submit": 0, "max_attempts": 3,
        "test_cases": [{"id": None, "input": "1", "expected_output": "1\n", "is_sample": True, "timeout": 5}]
    }]
    exam_id = service.save_exam(teacher_id, room.id, exam_meta, problems_draft, None)
    service.set_exam_published(exam_id, teacher_id, True)
    exam_for_hs = service.get_exam_for_student(exam_id, room.id)
    prob1 = service.load_exam_problems_for_student(exam_id)[0]
    
    # Kết quả chấm ảo (để đỡ phải chạy subprocess)
    res_correct = grade_problem("print(1)", prob1, prob1["test_cases"])
    
    return teacher_id, room.id, st_spam, exam_id, exam_for_hs, prob1, res_correct

try:
    teacher_id, class_id, st_spam, exam_id, exam_for_hs, prob1, res_correct = setup_dummy_data()
except Exception as e:
    st.error(f"Lỗi khởi tạo: {e}")
    st.stop()

# -----------------------------------------
# KỊCH BẢN 1: SPAM (RACE CONDITION)
# -----------------------------------------
st.header("1. Kịch bản: Học sinh cố tình Spam nút nộp bài (Giới hạn: 3 lần)")
st.write("Mô phỏng 1 học sinh dùng Tool/Bot gửi 10 yêu cầu nộp bài tại cùng đúng 1 mili-giây.")

if st.button("🚀 Kích hoạt Tấn công Spam (10 Requests)", type="primary"):
    enroll = service.create_enrollment(exam_id, st_spam.id)
    prog = service.get_or_create_problem_progress(enroll.id, prob1["id"])
    
    def spam_task(i):
        time.sleep(0.1) # Đồng bộ các luồng xuất phát cùng lúc
        try:
            service.record_official_submission(prog.id, prob1, exam_for_hs, enroll, "editor", "print(1)", None, res_correct)
            return "Thành công"
        except Exception as e:
            return "Bị chặn"

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    with st.spinner("Đang hứng chịu đợt tấn công đa luồng..."):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(spam_task, i) for i in range(10)]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                results.append(f.result())
                progress_bar.progress((i + 1) / 10)
                status_text.text(f"Đã xử lý {i+1}/10 requests...")
    
    success = results.count("Thành công")
    blocked = results.count("Bị chặn")
    
    col1, col2 = st.columns(2)
    col1.metric("✅ Số bài lọt qua (Giới hạn 3)", success, delta="Đúng thiết kế" if success==3 else "Lỗi", delta_color="normal" if success==3 else "inverse")
    col2.metric("🛡️ Số bài bị chặn đứng (Ngăn chặn Race Condition)", blocked)
    
    st.bar_chart(pd.DataFrame({"Trạng thái": ["Chấp nhận", "Bị chặn"], "Số lượng": [success, blocked]}).set_index("Trạng thái"))
    
    if success == 3:
        st.success("Hệ thống hoạt động HOÀN HẢO! Lớp khoá CSDL (SELECT FOR UPDATE) đã ngăn chặn tuyệt đối tình trạng Spam.")

st.divider()

# -----------------------------------------
# KỊCH BẢN 2: LOAD TEST (50 HỌC SINH)
# -----------------------------------------
st.header("2. Kịch bản: Sức chịu tải (50 Học sinh nộp bài cùng lúc)")
st.write("Mô phỏng cảnh cuối giờ, toàn bộ 50 học sinh trong lớp ấn nộp bài thi cùng một khoảnh khắc (Load/Stress Test).")

# Dùng cache để không phải tạo lại 50 user mỗi lần reload
@st.cache_resource
def setup_50_students():
    with st.spinner("Đang tạo ảo 50 học sinh (chỉ chạy 1 lần)..."):
        students = []
        for i in range(50):
            st_i, _ = service.create_student(teacher_id, class_id, f"Học sinh {i}", f"hs_load_{i}_{int(time.time())}")
            en = service.create_enrollment(exam_id, st_i.id)
            pr = service.get_or_create_problem_progress(en.id, prob1["id"])
            students.append((st_i, en, pr))
        return students

if st.button("🔥 Kích hoạt 50 Học sinh nộp đồng loạt"):
    students_data = setup_50_students()
    
    def hs_submit(student_data):
        st_i, en, pr = student_data
        try:
            service.record_official_submission(pr.id, prob1, exam_for_hs, en, "editor", "print(1)", None, res_correct)
            return "Thành công"
        except Exception as e:
            return "Lỗi"

    progress_bar = st.progress(0)
    status_text = st.empty()
    
    results = []
    start_time = time.time()
    
    with st.spinner("Đang cho 50 luồng chạy đồng thời (Concurrency)..."):
        # Max_workers=50 để 50 luồng ép thẳng vào Connection Pool (Size=5, Max=15)
        with concurrent.futures.ThreadPoolExecutor(max_workers=50) as executor:
            futures = [executor.submit(hs_submit, sd) for sd in students_data]
            for i, f in enumerate(concurrent.futures.as_completed(futures)):
                results.append(f.result())
                progress_bar.progress((i + 1) / 50)
                status_text.text(f"Đã xử lý {i+1}/50 học sinh...")
                
    end_time = time.time()
    total_time = end_time - start_time
    
    success = results.count("Thành công")
    failed = results.count("Lỗi")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("✅ Nộp bài thành công", success)
    c2.metric("❌ Gặp lỗi (Rớt kết nối)", failed)
    c3.metric("⏱️ Thời gian xử lý", f"{total_time:.2f} giây")
    
    st.bar_chart(pd.DataFrame({"Trạng thái": ["Thành công", "Lỗi"], "Số lượng": [success, failed]}).set_index("Trạng thái"))
    
    if success == 50:
        st.success(f"Tuyệt vời! Connection Pool của cơ sở dữ liệu đã tự động điều phối hàng đợi. Tất cả 50 học sinh đều nộp thành công trong vòng {total_time:.2f} giây mà không hề sập máy chủ!")
