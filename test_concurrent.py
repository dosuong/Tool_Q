import sys
import concurrent.futures
from datetime import datetime
from online_exam import service, auth, student_auth
from grader import runner
from online_exam.grading import grade_problem
import time

def run_concurrent_test():
    print("=== BẮT ĐẦU BỘ TEST TẢI & ĐỒNG THỜI (CONCURRENCY TEST) ===")
    
    # 1. Setup
    teacher_id = auth._get_or_create_teacher_profile("load_test@example.com", "uid_load")
    room = service.create_class(teacher_id, f"Lớp Load Test {datetime.now().strftime('%H%M%S')}")
    class_id = room.id
    print(f"[Setup] Đã tạo lớp: {room.name}")
    
    exam_meta = {
        "title": "Bài thi Concurrency",
        "description": "Test chịu tải nhiều học sinh",
        "allow_code_editor": True,
        "allow_file_upload": False,
        "duration_minutes": 10,
        "access_code": None,
        "final_score_policy": "best"
    }
    problems_draft = [{
        "id": None, "title": "Câu 1: X2", "description": "In ra a*2", "max_score": 10.0,
        "penalty_percent_per_submit": 0, "max_attempts": 3,
        "test_cases": [
            {"id": None, "input": "5", "expected_output": "10\n", "is_sample": True, "timeout": 5, "note": ""}
        ]
    }]
    
    exam_id = service.save_exam(teacher_id, class_id, exam_meta, problems_draft, None)
    service.set_exam_published(exam_id, teacher_id, True)
    exam_for_hs = service.get_exam_for_student(exam_id, class_id)
    problems_hs = service.load_exam_problems_for_student(exam_id)
    prob1 = problems_hs[0]
    print("[Setup] Đã tạo Bài kiểm tra giới hạn 3 lần nộp/câu.")

    # ---------------------------------------------------------
    # TEST 1: 1 HỌC SINH SPAM NÚT NỘP BÀI CÙNG LÚC (RACE CONDITION)
    # ---------------------------------------------------------
    print("\n--- TEST 1: RACE CONDITION (1 HS bấm nộp 10 lần cùng 1 mili-giây) ---")
    st_spam, _ = service.create_student(teacher_id, class_id, "HS Spam", "hs_spam")
    enroll_spam = service.create_enrollment(exam_id, st_spam.id)
    prog_spam = service.get_or_create_problem_progress(enroll_spam.id, prob1["id"])
    
    correct_code = "a = int(input())\nprint(a * 2)"
    res_correct = grade_problem(correct_code, prob1, prob1["test_cases"])
    
    def spam_submit(i):
        try:
            # Simulate slight network delay overlap
            sub = service.record_official_submission(prog_spam.id, prob1, exam_for_hs, enroll_spam, "editor", correct_code, None, res_correct)
            return f"Thành công (Điểm: {sub.final_score})"
        except Exception as e:
            return f"Bị chặn: {str(e)}"
            
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(spam_submit, i) for i in range(10)]
        results = [f.result() for f in futures]
    
    success_count = sum(1 for r in results if "Thành công" in r)
    blocked_count = sum(1 for r in results if "Bị chặn" in r)
    print(f"Kết quả Spam: {success_count} lần thành công, {blocked_count} lần bị chặn bảo mật.")
    assert success_count == 3, f"Lỗi bảo mật! Lẽ ra chỉ được thành công đúng 3 lần (max_attempts=3), nhưng lại thành công {success_count} lần."
    print("=> TEST 1 PASS: Cơ chế SELECT FOR UPDATE đã chặn đứng tấn công Race Condition xuất sắc!")

    # ---------------------------------------------------------
    # TEST 2: 20 HỌC SINH NỘP BÀI ĐỒNG THỜI (LOAD TEST)
    # ---------------------------------------------------------
    print("\n--- TEST 2: LOAD TEST (20 HS cùng nộp bài 1 lúc) ---")
    students = []
    for i in range(20):
        st, _ = service.create_student(teacher_id, class_id, f"HS {i}", f"hs_load_{i}")
        en = service.create_enrollment(exam_id, st.id)
        pr = service.get_or_create_problem_progress(en.id, prob1["id"])
        students.append((st, en, pr))
        
    print(f"Đã chuẩn bị xong {len(students)} học sinh. Bắt đầu bắn request đồng thời...")
    
    def hs_submit(student_data):
        st, en, pr = student_data
        try:
            sub = service.record_official_submission(pr.id, prob1, exam_for_hs, en, "editor", correct_code, None, res_correct)
            return True
        except Exception as e:
            print(f"Lỗi HS {st.full_name}: {e}")
            return False

    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(hs_submit, sd) for sd in students]
        success_list = [f.result() for f in futures]
        
    end_time = time.time()
    total_success = sum(success_list)
    print(f"Đã xử lý xong {total_success}/20 học sinh nộp bài trong {end_time - start_time:.2f} giây.")
    assert total_success == 20, "Có học sinh bị lỗi khi nộp bài đồng thời!"
    print("=> TEST 2 PASS: Database Connection Pool xử lý đa luồng hoàn hảo không bị nghẽn (Deadlock)!")

    # Cleanup
    service.delete_or_archive_class(class_id, teacher_id)
    print("\n=== HOÀN THÀNH CONCURRENCY TEST! HỆ THỐNG CỰC KỲ VỮNG CHẮC. ===")

if __name__ == '__main__':
    run_concurrent_test()
