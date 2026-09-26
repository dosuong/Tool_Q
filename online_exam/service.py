"""Nghiệp vụ: lớp học + bài kiểm tra online (nhiều câu). Mọi hàm nhận tường minh
`teacher_id` và tự lọc theo quyền sở hữu — không có hàm "lấy tất cả" thiếu điều
kiện lọc, để tránh lặp lại đúng loại bug đã từng gặp (nhiều GV thấy dữ liệu
của nhau) ở luồng cũ trước khi có tài khoản.
"""
import random
import string
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from online_exam import auth, student_auth
from online_exam.db import get_session
from online_exam.db_models import (
    ClassRoom, Enrollment, Exam, ExamProblem, ExamTestCase, ProblemProgress, Student, Submission,
    SubmissionResult,
)


class SubmissionBlocked(Exception):
    """Nộp câu bị từ chối ở phút chót (hết lượt/hết giờ ngay lúc ghi transaction) — bài đã
    CHẤM xong (tốn vài giây) nhưng KHÔNG được lưu. HS cần được báo rõ lý do, không phải lỗi
    hệ thống, để tránh hoang mang tưởng mất bài."""

_JOIN_CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits if c not in "0O1I")


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _generate_join_code(session, length: int = 6) -> str:
    for _ in range(50):
        code = "".join(random.choices(_JOIN_CODE_ALPHABET, k=length))
        exists_already = session.execute(
            select(ClassRoom.id).where(ClassRoom.join_code == code)
        ).scalar_one_or_none()
        if not exists_already:
            return code
    raise RuntimeError("Không sinh được mã lớp duy nhất — thử lại.")


# ---------------------------------------------------------------- Lớp học ---

def create_class(teacher_id: int, name: str) -> ClassRoom:
    with get_session() as session:
        join_code = _generate_join_code(session)
        room = ClassRoom(teacher_id=teacher_id, name=name.strip(), join_code=join_code)
        session.add(room)
        session.commit()
        session.refresh(room)
        return room


def list_classes(teacher_id: int, include_archived: bool = False) -> list[ClassRoom]:
    with get_session() as session:
        stmt = select(ClassRoom).where(ClassRoom.teacher_id == teacher_id)
        if not include_archived:
            stmt = stmt.where(ClassRoom.is_archived.is_(False))
        stmt = stmt.order_by(ClassRoom.created_at.desc())
        return list(session.execute(stmt).scalars().all())


def get_class(class_id: int, teacher_id: int) -> ClassRoom | None:
    with get_session() as session:
        return session.execute(
            select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id)
        ).scalar_one_or_none()


def get_class_by_id(class_id: int) -> ClassRoom | None:
    """Không lọc theo teacher_id — dùng cho luồng HS đã đăng nhập (đã biết đúng class_id qua
    tài khoản của mình, không cần xác thực lại quyền sở hữu GV)."""
    with get_session() as session:
        return session.get(ClassRoom, class_id)


def class_has_any_submission(class_id: int) -> bool:
    with get_session() as session:
        stmt = (
            select(Submission.id)
            .join(ProblemProgress, Submission.problem_progress_id == ProblemProgress.id)
            .join(Enrollment, ProblemProgress.enrollment_id == Enrollment.id)
            .join(Exam, Enrollment.exam_id == Exam.id)
            .where(Exam.class_id == class_id, Submission.is_trial.is_(False))
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none() is not None


def set_class_active(class_id: int, teacher_id: int, is_active: bool):
    with get_session() as session:
        room = session.execute(
            select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if room:
            room.is_active = is_active
            session.commit()


def delete_or_archive_class(class_id: int, teacher_id: int) -> str:
    """Trả về 'deleted' hoặc 'archived' tuỳ đã có bài nộp hay chưa."""
    if class_has_any_submission(class_id):
        with get_session() as session:
            room = session.execute(
                select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id)
            ).scalar_one_or_none()
            if room:
                room.is_archived = True
                session.commit()
        return "archived"
    with get_session() as session:
        room = session.execute(
            select(ClassRoom).where(ClassRoom.id == class_id, ClassRoom.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if room:
            session.delete(room)
            session.commit()
    return "deleted"


# ------------------------------------------------------------ Bài kiểm tra ---

def list_exams(teacher_id: int, class_id: int | None = None, include_archived: bool = True) -> list[Exam]:
    """Mặc định BAO GỒM bài đã lưu trữ — dùng cho trang Kết quả (cần tra cứu lại).
    Trang Tạo/sửa bài kiểm tra phải tự truyền include_archived=False để loại bỏ."""
    with get_session() as session:
        stmt = select(Exam).where(Exam.teacher_id == teacher_id)
        if class_id is not None:
            stmt = stmt.where(Exam.class_id == class_id)
        if not include_archived:
            stmt = stmt.where(Exam.is_archived.is_(False))
        stmt = stmt.order_by(Exam.created_at.desc())
        return list(session.execute(stmt).scalars().all())


def get_exam(exam_id: int, teacher_id: int) -> Exam | None:
    with get_session() as session:
        return session.execute(
            select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
        ).scalar_one_or_none()


def exam_has_any_official_submission(exam_id: int) -> bool:
    with get_session() as session:
        stmt = (
            select(Submission.id)
            .join(ProblemProgress, Submission.problem_progress_id == ProblemProgress.id)
            .join(ExamProblem, ProblemProgress.problem_id == ExamProblem.id)
            .where(ExamProblem.exam_id == exam_id, Submission.is_trial.is_(False))
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none() is not None


def is_exam_locked_for_editing(exam_id: int) -> bool:
    """Khoá sửa câu/test case khi đã có >=1 lần nộp CHÍNH THỨC, TRỪ KHI GV đã bấm
    'Mở khoá khẩn cấp' (force_unlocked=True) — xem force_unlock_exam_editing()."""
    with get_session() as session:
        exam = session.get(Exam, exam_id)
        if exam is None or exam.force_unlocked:
            return False
    return exam_has_any_official_submission(exam_id)


def force_unlock_exam_editing(exam_id: int, teacher_id: int):
    """Escape hatch khi GV phát hiện đề sai sau khi đã có người nộp. KHÔNG re-chấm
    ngầm các bài đã nộp trước đó. Khi đã force-unlock, UI (ui_create_exam.py) chỉ
    cho SỬA tại chỗ các câu/test case đã có (không cho thêm/xoá) để tránh phá vỡ
    liên kết dữ liệu điểm đã ghi nhận của học sinh."""
    with get_session() as session:
        exam = session.execute(
            select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if exam:
            exam.force_unlocked = True
            session.commit()


def set_exam_published(exam_id: int, teacher_id: int, is_published: bool):
    with get_session() as session:
        exam = session.execute(
            select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if exam:
            exam.is_published = is_published
            session.commit()


def delete_or_archive_exam(exam_id: int, teacher_id: int) -> str:
    if exam_has_any_official_submission(exam_id):
        with get_session() as session:
            exam = session.execute(
                select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
            ).scalar_one_or_none()
            if exam:
                exam.is_archived = True
                session.commit()
        return "archived"
    with get_session() as session:
        exam = session.execute(
            select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if exam:
            session.delete(exam)
            session.commit()
    return "deleted"


def verify_exam_access(exam_id: int, access_code_input: str) -> bool:
    with get_session() as session:
        exam = session.get(Exam, exam_id)
        if exam is None:
            return False
        if not exam.access_code:
            return True
        return (access_code_input or "").strip() == exam.access_code


def _problem_to_dict(problem: ExamProblem, test_cases: list[ExamTestCase]) -> dict:
    return {
        "id": problem.id,
        "title": problem.title,
        "description": problem.description or "",
        "max_score": float(problem.max_score),
        "penalty_percent_per_submit": float(problem.penalty_percent_per_submit or 0),
        "max_attempts": problem.max_attempts,
        "function_name": problem.function_name,
        "required_constructs": problem.required_constructs or [],
        "forbidden_constructs": problem.forbidden_constructs or [],
        "forbidden_imports": problem.forbidden_imports or [],
        "forbidden_calls": problem.forbidden_calls or [],
        "test_cases": [
            {
                "id": tc.id,
                "input": tc.input,
                "expected_output": tc.expected_output,
                "call_args": tc.call_args,
                "call_kwargs": tc.call_kwargs,
                "expected_return": tc.expected_return,
                "timeout": float(tc.timeout),
                "note": tc.note,
                "is_sample": tc.is_sample,
            }
            for tc in test_cases
        ],
    }


def load_exam_full(exam_id: int, teacher_id: int) -> dict | None:
    """Nạp toàn bộ bài kiểm tra + các câu + test case thành 1 dict lồng nhau, tiện cho UI."""
    with get_session() as session:
        exam = session.execute(
            select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if exam is None:
            return None
        problems = session.execute(
            select(ExamProblem).where(ExamProblem.exam_id == exam_id).order_by(ExamProblem.order_index)
        ).scalars().all()
        problem_dicts = []
        for p in problems:
            tcs = session.execute(
                select(ExamTestCase).where(ExamTestCase.problem_id == p.id).order_by(ExamTestCase.order_index)
            ).scalars().all()
            problem_dicts.append(_problem_to_dict(p, tcs))
        return {
            "id": exam.id,
            "class_id": exam.class_id,
            "title": exam.title,
            "description": exam.description,
            "allow_code_editor": exam.allow_code_editor,
            "allow_file_upload": exam.allow_file_upload,
            "opens_at": exam.opens_at,
            "closes_at": exam.closes_at,
            "duration_minutes": exam.duration_minutes,
            "access_code": exam.access_code,
            "final_score_policy": exam.final_score_policy,
            "is_published": exam.is_published,
            "is_archived": exam.is_archived,
            "force_unlocked": exam.force_unlocked,
            "problems": problem_dicts,
        }


def save_exam(teacher_id: int, class_id: int, exam_meta: dict, problems: list[dict], exam_id: int | None = None) -> int:
    """Lưu 1 bài kiểm tra (tạo mới nếu exam_id=None, ngược lại sửa bài đã có).

    - Nếu bài CHƯA khoá (`is_exam_locked_for_editing`=False): xoá sạch và ghi lại toàn bộ
      câu/test case từ `problems` — an toàn vì chưa có gì tham chiếu tới các row cũ.
    - Nếu bài ĐÃ khoá nhưng GV đã "Mở khoá khẩn cấp" (force_unlocked=True): chỉ UPDATE
      tại chỗ các câu/test case đã có id trùng khớp (không xoá/không thêm mới) để không
      làm mất liên kết dữ liệu điểm học sinh đã ghi nhận trước đó.
    - Nếu bài ĐÃ khoá và CHƯA mở khoá khẩn cấp: bỏ qua hoàn toàn tham số `problems`,
      chỉ cập nhật các trường cấp bài kiểm tra (exam_meta).

    Trả về exam_id.
    """
    with get_session() as session:
        if exam_id is None:
            exam = Exam(teacher_id=teacher_id, class_id=class_id, **exam_meta)
            session.add(exam)
            session.flush()
        else:
            exam = session.execute(
                select(Exam).where(Exam.id == exam_id, Exam.teacher_id == teacher_id)
            ).scalar_one_or_none()
            if exam is None:
                raise ValueError("Không tìm thấy bài kiểm tra hoặc không có quyền sửa.")
            for key, value in exam_meta.items():
                setattr(exam, key, value)

        locked = False
        if exam_id is not None:
            has_submission = session.execute(
                select(Submission.id)
                .join(ProblemProgress, Submission.problem_progress_id == ProblemProgress.id)
                .join(ExamProblem, ProblemProgress.problem_id == ExamProblem.id)
                .where(ExamProblem.exam_id == exam_id, Submission.is_trial.is_(False))
                .limit(1)
            ).scalar_one_or_none() is not None
            locked = has_submission and not exam.force_unlocked

        if not locked:
            if exam_id is not None:
                existing_problems = session.execute(
                    select(ExamProblem).where(ExamProblem.exam_id == exam.id)
                ).scalars().all()
                is_unlocked_edit = any(
                    session.execute(
                        select(Submission.id)
                        .join(ProblemProgress, Submission.problem_progress_id == ProblemProgress.id)
                        .where(ProblemProgress.problem_id == p.id, Submission.is_trial.is_(False))
                        .limit(1)
                    ).scalar_one_or_none()
                    for p in existing_problems
                )
                if is_unlocked_edit and exam.force_unlocked:
                    _update_problems_in_place(session, exam.id, existing_problems, problems)
                else:
                    for p in existing_problems:
                        session.delete(p)
                    session.flush()
                    _insert_problems(session, exam.id, problems)
            else:
                _insert_problems(session, exam.id, problems)

        session.commit()
        return exam.id


def _insert_problems(session, exam_id: int, problems: list[dict]):
    for order_index, p in enumerate(problems, start=1):
        problem = ExamProblem(
            exam_id=exam_id, order_index=order_index, title=p["title"], description=p.get("description", ""),
            max_score=p["max_score"], penalty_percent_per_submit=p.get("penalty_percent_per_submit", 0),
            max_attempts=p.get("max_attempts"), function_name=p.get("function_name") or None,
            required_constructs=p.get("required_constructs") or [],
            forbidden_constructs=p.get("forbidden_constructs") or [],
            forbidden_imports=p.get("forbidden_imports") or [],
            forbidden_calls=p.get("forbidden_calls") or [],
        )
        session.add(problem)
        session.flush()
        for tc_order, tc in enumerate(p.get("test_cases", []), start=1):
            session.add(ExamTestCase(
                problem_id=problem.id, order_index=tc_order, is_sample=bool(tc.get("is_sample")),
                input=tc.get("input", ""), expected_output=tc.get("expected_output", ""),
                call_args=tc.get("call_args"), call_kwargs=tc.get("call_kwargs"),
                expected_return=tc.get("expected_return"), timeout=tc.get("timeout", 5),
                note=tc.get("note", ""), ignore_trailing_whitespace=tc.get("ignore_trailing_whitespace", True),
            ))


def _update_problems_in_place(session, exam_id: int, existing_problems: list[ExamProblem], problems: list[dict]):
    """Chỉ dùng khi đã force-unlock 1 bài có bài nộp — sửa tại chỗ theo id đã có, KHÔNG
    thêm/xoá câu hay test case (an toàn với dữ liệu điểm HS đã ghi nhận)."""
    existing_by_id = {p.id: p for p in existing_problems}
    for p_data in problems:
        p_id = p_data.get("id")
        problem = existing_by_id.get(p_id)
        if problem is None:
            continue  # bỏ qua câu mới thêm — không hỗ trợ thêm câu khi đã khoá
        problem.title = p_data["title"]
        problem.description = p_data.get("description", "")
        problem.max_score = p_data["max_score"]
        problem.penalty_percent_per_submit = p_data.get("penalty_percent_per_submit", 0)
        problem.max_attempts = p_data.get("max_attempts")
        problem.function_name = p_data.get("function_name") or None
        problem.required_constructs = p_data.get("required_constructs") or []
        problem.forbidden_constructs = p_data.get("forbidden_constructs") or []
        problem.forbidden_imports = p_data.get("forbidden_imports") or []
        problem.forbidden_calls = p_data.get("forbidden_calls") or []

        existing_tcs = {tc.id: tc for tc in session.execute(
            select(ExamTestCase).where(ExamTestCase.problem_id == problem.id)
        ).scalars().all()}
        for tc_data in p_data.get("test_cases", []):
            tc = existing_tcs.get(tc_data.get("id"))
            if tc is None:
                continue  # bỏ qua test case mới thêm — không hỗ trợ thêm khi đã khoá
            tc.input = tc_data.get("input", "")
            tc.expected_output = tc_data.get("expected_output", "")
            tc.call_args = tc_data.get("call_args")
            tc.call_kwargs = tc_data.get("call_kwargs")
            tc.expected_return = tc_data.get("expected_return")
            tc.timeout = tc_data.get("timeout", 5)
            tc.note = tc_data.get("note", "")
            tc.is_sample = bool(tc_data.get("is_sample"))


# --------------------------------------------------------- Tài khoản HS (GV quản lý) ---
# GV tự tạo/reset tài khoản cho từng HS trong lớp (username/password sinh ngẫu nhiên) —
# thay cho việc HS tự gõ tên/MSHS không kiểm chứng ở thiết kế trước đó.

def create_student(teacher_id: int, class_id: int, full_name: str, custom_username: str | None = None) -> tuple[Student, str]:
    """Trả về (student, raw_password) — raw_password chỉ có ở lần tạo này, GV phải copy/in
    ra ngay vì sau đó chỉ còn lưu bcrypt hash, không xem lại được."""
    room = get_class(class_id, teacher_id)
    if room is None:
        raise ValueError("Không tìm thấy lớp hoặc không có quyền.")
    raw_password = student_auth.generate_password()
    with get_session() as session:
        if custom_username:
            # Kiểm tra trùng lặp nếu dùng username tuỳ chỉnh
            exists = session.execute(select(Student.id).where(Student.username == custom_username)).scalar_one_or_none()
            if exists:
                # Nếu trùng, thêm vài ký tự ngẫu nhiên vào đuôi
                import random
                import string
                suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
                username = f"{custom_username}{suffix}"
            else:
                username = custom_username
        else:
            username = student_auth.generate_username(session)
            
        student = Student(
            class_id=class_id, username=username,
            password_hash=auth.hash_password(raw_password), full_name=full_name.strip(),
        )
        session.add(student)
        session.commit()
        session.refresh(student)
        return student, raw_password


def list_students(class_id: int, teacher_id: int, include_archived: bool = False) -> list[Student]:
    room = get_class(class_id, teacher_id)
    if room is None:
        return []
    with get_session() as session:
        stmt = select(Student).where(Student.class_id == class_id)
        if not include_archived:
            stmt = stmt.where(Student.is_archived.is_(False))
        stmt = stmt.order_by(Student.full_name)
        return list(session.execute(stmt).scalars().all())


def student_has_any_submission(student_id: int) -> bool:
    with get_session() as session:
        stmt = (
            select(Submission.id)
            .join(ProblemProgress, Submission.problem_progress_id == ProblemProgress.id)
            .join(Enrollment, ProblemProgress.enrollment_id == Enrollment.id)
            .where(Enrollment.student_id == student_id, Submission.is_trial.is_(False))
            .limit(1)
        )
        return session.execute(stmt).scalar_one_or_none() is not None


def delete_or_archive_student(student_id: int, teacher_id: int) -> str:
    """Trả về 'deleted' hoặc 'archived' — cùng quy tắc archive-nếu-đã-có-bài-nộp như lớp/bài
    kiểm tra, để không mất lịch sử điểm nếu HS đó đã nộp bài."""
    with get_session() as session:
        student = session.execute(
            select(Student).join(ClassRoom, Student.class_id == ClassRoom.id)
            .where(Student.id == student_id, ClassRoom.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if student is None:
            raise ValueError("Không tìm thấy học sinh hoặc không có quyền.")
        if student_has_any_submission(student_id):
            student.is_archived = True
            session.commit()
            return "archived"
        session.delete(student)
        session.commit()
        return "deleted"


def reset_student_password(student_id: int, teacher_id: int) -> str:
    """Sinh mật khẩu mới, trả về plaintext để GV hiển thị 1 lần — chỉ lưu bcrypt hash."""
    raw_password = student_auth.generate_password()
    with get_session() as session:
        student = session.execute(
            select(Student).join(ClassRoom, Student.class_id == ClassRoom.id)
            .where(Student.id == student_id, ClassRoom.teacher_id == teacher_id)
        ).scalar_one_or_none()
        if student is None:
            raise ValueError("Không tìm thấy học sinh hoặc không có quyền.")
        student.password_hash = auth.hash_password(raw_password)
        session.commit()
    return raw_password


def get_student(student_id: int) -> Student | None:
    with get_session() as session:
        return session.get(Student, student_id)


# --------------------------------------------------------- Học sinh vào lớp/thi ---
# Các hàm dưới đây nhận `student_id` đã xác thực qua student_auth.authenticate_student()
# (không nhận teacher_id vì HS không có tài khoản GV) — quyền truy cập đảm bảo bằng cách
# mọi truy vấn đều đi qua đúng exam_id/enrollment_id/student_id đã xác thực, không có hàm
# "lấy tất cả" thiếu điều kiện lọc.

def get_exam_for_student(exam_id: int, class_id: int) -> Exam | None:
    with get_session() as session:
        return session.execute(
            select(Exam).where(Exam.id == exam_id, Exam.class_id == class_id)
        ).scalar_one_or_none()


def list_exams_for_student(student_id: int) -> list[Exam]:
    """Bài đang hoạt động (công bố + chưa lưu trữ) HOẶC học sinh đã có enrollment từ trước —
    đảm bảo HS không bao giờ mất quyền xem lại điểm của chính mình dù GV có ẩn/lưu trữ bài
    sau đó (quy tắc đã chốt ở trang 'Bảng điểm của tôi')."""
    with get_session() as session:
        student = session.get(Student, student_id)
        if student is None:
            return []
        exams = list(session.execute(
            select(Exam).where(Exam.class_id == student.class_id).order_by(Exam.created_at.desc())
        ).scalars().all())
        if not exams:
            return []
        enrolled_ids = set(session.execute(
            select(Enrollment.exam_id).where(
                Enrollment.exam_id.in_([e.id for e in exams]), Enrollment.student_id == student_id,
            )
        ).scalars().all())
    return [e for e in exams if (e.is_published and not e.is_archived) or e.id in enrolled_ids]


def get_enrollment(exam_id: int, student_id: int) -> Enrollment | None:
    with get_session() as session:
        return session.execute(
            select(Enrollment).where(Enrollment.exam_id == exam_id, Enrollment.student_id == student_id)
        ).scalar_one_or_none()


def create_enrollment(exam_id: int, student_id: int) -> Enrollment:
    """Tạo enrollment lần đầu HS vào 1 bài kiểm tra (hoặc trả về bản đã có nếu HS quay lại) —
    tên/hiển thị luôn lấy từ `Student.full_name`, không còn lưu trùng lặp ở đây."""
    with get_session() as session:
        existing = session.execute(
            select(Enrollment).where(Enrollment.exam_id == exam_id, Enrollment.student_id == student_id)
        ).scalar_one_or_none()
        if existing:
            return existing
        enrollment = Enrollment(exam_id=exam_id, student_id=student_id)
        session.add(enrollment)
        session.commit()
        session.refresh(enrollment)
        return enrollment


def load_exam_problems_for_student(exam_id: int) -> list[dict]:
    """Giống load_exam_full() nhưng KHÔNG lọc theo teacher_id — chỉ gọi được sau khi exam_id
    đã được xác thực qua get_exam_for_student()/enrollment. Lưu ý: dict trả về CÓ chứa
    expected_output/expected_return của cả test ẩn (cần để chấm bài chính thức) — đây là dữ
    liệu ở phía SERVER (session_state), nơi gọi (ui_student_exam.py) chịu trách nhiệm KHÔNG
    render các trường này ra màn hình cho câu có is_sample=False."""
    with get_session() as session:
        problems = session.execute(
            select(ExamProblem).where(ExamProblem.exam_id == exam_id).order_by(ExamProblem.order_index)
        ).scalars().all()
        result = []
        for p in problems:
            tcs = session.execute(
                select(ExamTestCase).where(ExamTestCase.problem_id == p.id).order_by(ExamTestCase.order_index)
            ).scalars().all()
            result.append(_problem_to_dict(p, tcs))
        return result


def get_or_create_problem_progress(enrollment_id: int, problem_id: int) -> ProblemProgress:
    with get_session() as session:
        existing = session.execute(
            select(ProblemProgress).where(
                ProblemProgress.enrollment_id == enrollment_id, ProblemProgress.problem_id == problem_id,
            )
        ).scalar_one_or_none()
        if existing:
            return existing
        progress = ProblemProgress(enrollment_id=enrollment_id, problem_id=problem_id)
        session.add(progress)
        session.commit()
        session.refresh(progress)
        return progress


def get_or_create_problem_progress_bulk(enrollment_id: int, problem_ids: list[int]) -> dict[int, ProblemProgress]:
    """Nạp/tạo tiến độ cho NHIỀU câu trong tối đa 2 lượt round-trip DB (1 SELECT + 1 INSERT nếu
    thiếu), thay vì N lượt riêng lẻ (N = số câu). Quan trọng vì `st.tabs()` của Streamlit chạy
    lại code của TẤT CẢ các tab ở MỌI lần rerun (không chỉ tab đang xem) — nếu mỗi tab tự gọi
    get_or_create_problem_progress() riêng, số round-trip DB nhân theo số câu mỗi lần HS bấm
    bất kỳ nút nào, kể cả ở tab khác. Đây là nguyên nhân chính gây ra độ trễ 1-3s mỗi thao tác
    khi deploy thật (Streamlit Cloud + Supabase qua mạng, không phải SQLite cục bộ)."""
    if not problem_ids:
        return {}
    with get_session() as session:
        existing = session.execute(
            select(ProblemProgress).where(
                ProblemProgress.enrollment_id == enrollment_id,
                ProblemProgress.problem_id.in_(problem_ids),
            )
        ).scalars().all()
        progress_map = {p.problem_id: p for p in existing}
        missing_ids = [pid for pid in problem_ids if pid not in progress_map]
        if missing_ids:
            new_rows = [ProblemProgress(enrollment_id=enrollment_id, problem_id=pid) for pid in missing_ids]
            session.add_all(new_rows)
            session.commit()  # PK tự tăng đã có sẵn trên object ngay sau INSERT, không cần refresh()
            for row in new_rows:
                progress_map[row.problem_id] = row
        return progress_map


def save_draft(problem_progress_id: int, code_text: str):
    with get_session() as session:
        progress = session.get(ProblemProgress, problem_progress_id)
        if progress:
            progress.draft_code = code_text
            progress.draft_saved_at = _utcnow()
            session.commit()


def compute_deadline(exam: Exam, enrollment: Enrollment) -> datetime | None:
    """Hạn nộp có thẩm quyền = MIN(enrollment.started_at + exam.duration_minutes, exam.closes_at),
    bỏ qua vế nào không được cấu hình. None = không giới hạn thời gian."""
    deadlines = []
    if exam.duration_minutes:
        started = enrollment.started_at
        if started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        deadlines.append(started + timedelta(minutes=exam.duration_minutes))
    if exam.closes_at:
        closes_at = exam.closes_at
        if closes_at.tzinfo is None:
            closes_at = closes_at.replace(tzinfo=timezone.utc)
        deadlines.append(closes_at)
    return min(deadlines) if deadlines else None


def record_trial_submission(problem_progress_id: int, submission_mode: str, code_text: str,
                             original_filename: str | None, grading_result: dict) -> Submission:
    """'Chạy thử' — không tốn lượt, không đụng attempts_used/best_score, không cần transaction
    khoá row vì không giới hạn số lần chạy thử."""
    with get_session() as session:
        submission = Submission(
            problem_progress_id=problem_progress_id, attempt_number=None, is_trial=True,
            submission_mode=submission_mode, code_text=code_text, original_filename=original_filename,
            passed_ratio=grading_result["pass_ratio"], raw_score=None, penalty_applied=None, final_score=None,
        )
        session.add(submission)
        session.flush()
        for r in grading_result["results"]:
            if r["test_case_id"] is None:
                continue
            session.add(SubmissionResult(
                submission_id=submission.id, test_case_id=r["test_case_id"], passed=r["passed"],
                actual_output=r["actual_output"] or "", error_message=r["error_message"] or "",
                execution_time_ms=r.get("execution_time_ms"),
            ))
        session.commit()
        session.refresh(submission)
        return submission


def record_official_submission(problem_progress_id: int, problem: dict, exam: Exam, enrollment: Enrollment,
                                submission_mode: str, code_text: str, original_filename: str | None,
                                grading_result: dict) -> Submission:
    """Transaction chống race condition: khoá row problem_progress (SELECT ... FOR UPDATE — có
    hiệu lực thật trên Postgres, tự chặn transaction thứ 2 đợi tới khi transaction thứ nhất
    commit; SQLite bỏ qua mệnh đề này (không hỗ trợ khoá theo row), nên ở SQLite dev 2 giao dịch
    đồng thời có thể cùng đọc `attempts_used` cũ — lớp phòng vệ thứ 2 độc lập là
    UNIQUE(problem_progress_id, attempt_number) ở tầng DB, bắt bằng try/except bên dưới), kiểm
    tra lại lượt/giờ NGAY TRƯỚC KHI ghi (không tin kết quả kiểm tra sơ bộ ở UI, vì chấm bài chạy
    TRƯỚC transaction này và có thể mất vài giây — 1 tab/lần bấm khác có thể đã nộp xen vào giữa
    lúc đó).

    Raise SubmissionBlocked nếu tại đúng thời điểm ghi đã hết lượt/hết giờ, HOẶC nếu bị đụng độ
    ghi đồng thời (UNIQUE constraint) — bài vừa chấm không được lưu, HS cần được báo rõ lý do
    thay vì thấy lỗi hệ thống khó hiểu."""
    max_attempts = problem.get("max_attempts")
    max_score = problem["max_score"]
    penalty_percent = problem.get("penalty_percent_per_submit", 0) or 0
    deadline = compute_deadline(exam, enrollment)

    with get_session() as session:
        progress = session.execute(
            select(ProblemProgress).where(ProblemProgress.id == problem_progress_id).with_for_update()
        ).scalar_one_or_none()
        if progress is None:
            raise SubmissionBlocked("Không tìm thấy tiến độ làm bài.")

        now = _utcnow()
        if deadline is not None and now > deadline:
            raise SubmissionBlocked("Đã hết thời gian làm bài.")
        if max_attempts is not None and progress.attempts_used >= max_attempts:
            raise SubmissionBlocked("Đã dùng hết số lần nộp cho phép của câu này.")

        prior_wrong = session.execute(
            select(func.count(Submission.id)).where(
                Submission.problem_progress_id == problem_progress_id,
                Submission.is_trial.is_(False),
                Submission.passed_ratio < 1.0,
            )
        ).scalar_one()

        pass_ratio = grading_result["pass_ratio"]
        raw_score = pass_ratio * max_score
        penalty = min(penalty_percent / 100 * prior_wrong, 1.0) * max_score
        final_score = max(raw_score - penalty, 0.0)
        next_attempt_number = progress.attempts_used + 1

        submission = Submission(
            problem_progress_id=problem_progress_id, attempt_number=next_attempt_number, is_trial=False,
            submission_mode=submission_mode, code_text=code_text, original_filename=original_filename,
            passed_ratio=pass_ratio, raw_score=raw_score, penalty_applied=penalty, final_score=final_score,
        )
        try:
            session.add(submission)
            session.flush()  # cần submission.id trước khi có thể gán best_submission_id — có thể
            # raise IntegrityError ngay ở đây (UNIQUE problem_progress_id+attempt_number) nếu 2
            # giao dịch đồng thời cùng đọc attempts_used cũ trước khi cái nào commit (chỉ có thể
            # xảy ra khi FOR UPDATE không có hiệu lực thật, vd SQLite dev — xem docstring ở trên).

            for r in grading_result["results"]:
                if r["test_case_id"] is None:
                    continue
                session.add(SubmissionResult(
                    submission_id=submission.id, test_case_id=r["test_case_id"], passed=r["passed"],
                    actual_output=r["actual_output"] or "", error_message=r["error_message"] or "",
                    execution_time_ms=r.get("execution_time_ms"),
                ))

            progress.attempts_used = next_attempt_number

            # best_submission_id LUÔN là lần nộp có final_score cao nhất (dùng làm bài tham
            # khảo khi xem lại) — tính bằng truy vấn trực tiếp, không suy ra từ best_score vì
            # dưới policy "average" best_score không còn là điểm của 1 lần nộp cụ thể nào.
            # QUAN TRỌNG: sắp theo attempt_number DESC làm tiêu chí phụ để phá tie — nếu không,
            # 2 lần nộp CÙNG điểm (vd nộp lần 1 sai, nộp lại lần 2 vẫn sai giống hệt, cả 2 đều
            # 0 điểm) có thể khiến DB trả về lần nộp CŨ HƠN, khiến trang Kết quả/HS xem lại cứ
            # hiện mãi code của lần nộp đầu tiên dù đã nộp lại — đây là bug thật đã gặp.
            best_id, best_individual_score = session.execute(
                select(Submission.id, Submission.final_score)
                .where(Submission.problem_progress_id == problem_progress_id, Submission.is_trial.is_(False))
                .order_by(Submission.final_score.desc(), Submission.attempt_number.desc())
                .limit(1)
            ).one()
            progress.best_submission_id = best_id

            if exam.final_score_policy == "average":
                # Tính lại từ đầu (không luỹ kế) — quy mô vài chục lần nộp/câu nên query lại
                # rẻ và tránh sai số cộng dồn.
                avg_score = session.execute(
                    select(func.avg(Submission.final_score)).where(
                        Submission.problem_progress_id == problem_progress_id, Submission.is_trial.is_(False),
                    )
                ).scalar_one()
                progress.best_score = float(avg_score)
            else:
                progress.best_score = float(best_individual_score)

            session.commit()
        except IntegrityError:
            session.rollback()
            raise SubmissionBlocked(
                "Có một yêu cầu nộp khác cho câu này vừa xử lý cùng lúc — vui lòng thử lại."
            )
        session.refresh(submission)
        return submission


def get_student_exam_summary(exam_id: int, enrollment_id: int) -> dict:
    """Điểm từng câu (best_score hiện tại theo policy của bài) + tổng, cho 1 HS đã có
    enrollment ở 1 bài kiểm tra — dùng cho trang 'Bảng điểm của tôi'."""
    with get_session() as session:
        problems = session.execute(
            select(ExamProblem).where(ExamProblem.exam_id == exam_id).order_by(ExamProblem.order_index)
        ).scalars().all()
        progress_map = {}
        if problems:
            progress_map = {
                pp.problem_id: pp for pp in session.execute(
                    select(ProblemProgress).where(
                        ProblemProgress.enrollment_id == enrollment_id,
                        ProblemProgress.problem_id.in_([p.id for p in problems]),
                    )
                ).scalars().all()
            }
        rows = []
        total = 0.0
        for p in problems:
            pp = progress_map.get(p.id)
            score = float(pp.best_score) if pp and pp.best_score is not None else None
            total += score or 0.0
            rows.append({
                "problem_id": p.id, "title": p.title, "max_score": float(p.max_score),
                "score": score, "attempts_used": pp.attempts_used if pp else 0,
                "max_attempts": p.max_attempts,
            })
        return {
            "problems": rows, "total_score": total,
            "max_total": sum(float(p.max_score) for p in problems),
        }


def get_submission_with_results(submission_id: int) -> tuple[Submission | None, list[SubmissionResult]]:
    with get_session() as session:
        submission = session.get(Submission, submission_id)
        if submission is None:
            return None, []
        results = list(session.execute(
            select(SubmissionResult).where(SubmissionResult.submission_id == submission_id)
        ).scalars().all())
        return submission, results


# --------------------------------------------------------------------- Kết quả (GV) ---

def get_exam_results_table(exam_id: int, teacher_id: int) -> dict | None:
    """Bảng HS x điểm từng câu + tổng cho 1 bài, chỉ trả dữ liệu nếu đúng GV sở hữu bài đó
    (get_exam() đã lọc theo teacher_id) — None nếu không có quyền."""
    exam = get_exam(exam_id, teacher_id)
    if exam is None:
        return None
    with get_session() as session:
        problems = session.execute(
            select(ExamProblem).where(ExamProblem.exam_id == exam_id).order_by(ExamProblem.order_index)
        ).scalars().all()
        enrollments = session.execute(
            select(Enrollment, Student)
            .join(Student, Enrollment.student_id == Student.id)
            .where(Enrollment.exam_id == exam_id)
            .order_by(Student.full_name)
        ).all()
        progress_map = {}
        if enrollments:
            progresses = session.execute(
                select(ProblemProgress).where(
                    ProblemProgress.enrollment_id.in_([e.id for e, _ in enrollments]),
                )
            ).scalars().all()
            progress_map = {(pp.enrollment_id, pp.problem_id): pp for pp in progresses}

        rows = []
        for e, student in enrollments:
            per_problem = []
            total = 0.0
            for p in problems:
                pp = progress_map.get((e.id, p.id))
                score = float(pp.best_score) if pp and pp.best_score is not None else None
                total += score or 0.0
                per_problem.append({
                    "problem_id": p.id, "title": p.title, "max_score": float(p.max_score),
                    "score": score, "best_submission_id": pp.best_submission_id if pp else None,
                    "attempts_used": pp.attempts_used if pp else 0,
                })
            rows.append({
                # Giữ nguyên tên field student_name/student_code (student_code = username) để
                # ui_results.py không cần sửa gì — chỉ đổi nguồn dữ liệu bên trong.
                "enrollment_id": e.id, "student_name": student.full_name, "student_code": student.username,
                "per_problem": per_problem, "total_score": total,
            })
    return {
        "exam": exam,
        "problems": [{"id": p.id, "title": p.title, "max_score": float(p.max_score)} for p in problems],
        "rows": rows,
    }


def list_official_submissions(enrollment_id: int, problem_id: int) -> list[Submission]:
    """Chỉ trả các lần NỘP CHÍNH THỨC (is_trial=False) — theo quyết định đã chốt, GV KHÔNG
    xem được nháp/chạy thử real-time của HS, chỉ xem các lần đã bấm 'Nộp câu này'."""
    with get_session() as session:
        progress = session.execute(
            select(ProblemProgress).where(
                ProblemProgress.enrollment_id == enrollment_id, ProblemProgress.problem_id == problem_id,
            )
        ).scalar_one_or_none()
        if progress is None:
            return []
        return list(session.execute(
            select(Submission).where(
                Submission.problem_progress_id == progress.id, Submission.is_trial.is_(False),
            ).order_by(Submission.attempt_number)
        ).scalars().all())
