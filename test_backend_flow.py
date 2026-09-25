import sys
from datetime import datetime, timezone
from online_exam import service, auth, student_auth
from grader import runner

def run_test():
    print("=== BẮT ĐẦU CHẠY BỘ TEST TỰ ĐỘNG KHÉP KÍN ===")
    
    # 1. Giả lập Giáo viên
    teacher_email = "test_e2e_teacher@example.com"
    teacher_id = auth._get_or_create_teacher_profile(teacher_email, "dummy_uid_123")
    print(f"[1] Đã tạo/lấy tài khoản Giáo viên (ID: {teacher_id})")
    
    # 2. Tạo Lớp
    class_name = f"Lớp TEST Tự Động {datetime.now().strftime('%H%M%S')}"
    room = service.create_class(teacher_id, class_name)
    class_id = room.id
    print(f"[2] Đã tạo lớp mới: {room.name} (ID: {class_id})")
    
    # 3. Thêm Học sinh
    student, raw_pw = service.create_student(teacher_id, class_id, "Nguyễn Văn Test E2E", "test_hs_123")
    print(f"[3] Đã thêm học sinh: {student.full_name} - Tải khoản: {student.username} - Pass: {raw_pw}")
    
    # 4. Tạo Bài kiểm tra
    exam_meta = {
        "title": "Bài thi Test E2E",
        "description": "Dùng để kiểm thử tự động",
        "allow_code_editor": True,
        "allow_file_upload": False,
        "duration_minutes": 10,
        "access_code": None,
        "final_score_policy": "best"
    }
    problems_draft = [{
        "id": None,
        "title": "Câu 1: Cộng 2 số",
        "description": "Nhập a và b trên 2 dòng, in ra a+b.",
        "max_score": 10.0,
        "penalty_percent_per_submit": 0,
        "max_attempts": 3,
        "function_name": None,
        "required_constructs": [],
        "forbidden_constructs": [],
        "forbidden_imports": [],
        "forbidden_calls": [],
        "test_cases": [
            {"id": None, "input": "3\n5", "expected_output": "8\n", "is_sample": True, "timeout": 5, "note": "Test mẫu"},
            {"id": None, "input": "10\n-2", "expected_output": "8\n", "is_sample": False, "timeout": 5, "note": "Test ẩn"}
        ]
    }]
    
    exam_id = service.save_exam(teacher_id, class_id, exam_meta, problems_draft, None)
    service.set_exam_published(exam_id, teacher_id, True)
    exam_obj = service.get_exam(exam_id, teacher_id)
    print(f"[4] Đã tạo và công bố bài kiểm tra: {exam_obj.title} (ID: {exam_id})")
    
    # 5. Học sinh đăng nhập và làm bài
    student_logged = student_auth.authenticate_student(student.username, raw_pw)
    assert student_logged is not None
    
    exam_for_hs = service.get_exam_for_student(exam_id, class_id)
    assert exam_for_hs is not None
    
    enrollment = service.create_enrollment(exam_id, student.id)
    print(f"[5] Học sinh {student.full_name} đã vào làm bài (Enrollment ID: {enrollment.id})")
    
    problems_hs = service.load_exam_problems_for_student(exam_id)
    prob1 = problems_hs[0]
    
    progress = service.get_or_create_problem_progress(enrollment.id, prob1["id"])
    
    # 6. Học sinh nộp code SAI
    wrong_code = "a = int(input())\nb = int(input())\nprint(a - b)"
    from online_exam.grading import grade_problem
    res_wrong = grade_problem(wrong_code, prob1, prob1["test_cases"])
    sub_wrong = service.record_official_submission(progress.id, prob1, exam_for_hs, enrollment, "editor", wrong_code, None, res_wrong)
    print(f"[6] Học sinh nộp code SAI (a-b). Điểm đạt được: {sub_wrong.final_score}/{prob1['max_score']}")
    assert sub_wrong.final_score == 0
    
    # 7. Học sinh nộp code ĐÚNG
    correct_code = "a = int(input())\nb = int(input())\nprint(a + b)"
    res_correct = grade_problem(correct_code, prob1, prob1["test_cases"])
    sub_correct = service.record_official_submission(progress.id, prob1, exam_for_hs, enrollment, "editor", correct_code, None, res_correct)
    print(f"[7] Học sinh nộp code ĐÚNG (a+b). Điểm đạt được: {sub_correct.final_score}/{prob1['max_score']}")
    assert sub_correct.final_score == 10.0
    
    # 8. Xem kết quả (Giáo viên)
    results = service.get_exam_results_table(exam_id, teacher_id)
    print(f"[8] Lấy bảng điểm Giáo viên. Số học sinh đã làm: {len(results['rows'])}")
    hs_row = results['rows'][0]
    print(f"   => Điểm tổng của HS: {hs_row['total_score']}")
    assert hs_row['total_score'] == 10.0
    
    # 9. Dọn dẹp
    service.delete_or_archive_class(class_id, teacher_id)
    print("[9] Đã dọn dẹp xoá/lưu trữ lớp test thành công.")
    
    print("=== TẤT CẢ CÁC BƯỚC TEST ĐỀU HOÀN THÀNH XUẤT SẮC! ===")

if __name__ == '__main__':
    run_test()
