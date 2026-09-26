"""SQLAlchemy ORM models cho toàn bộ module thi trực tuyến.

Dùng model khai báo (declarative) + Base.metadata.create_all() thay vì file
schema.sql/Alembic riêng — đơn giản hơn đáng kể cho quy mô dự án này (vài GV
nội bộ), và Postgres/SQLite đều hiểu được các kiểu dữ liệu dùng ở đây. Nếu
sau này schema cần thay đổi thường xuyên hơn, có thể chuyển sang Alembic mà
không phải viết lại các bảng.
"""
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, Numeric, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Teacher(Base):
    """Hồ sơ GV cục bộ (profile mirror) — KHÔNG còn lưu mật khẩu. Việc xác thực nay uỷ quyền
    hoàn toàn cho Supabase Auth (hoặc tài khoản dev-fallback cố định khi chưa cấu hình Supabase,
    xem online_exam/supabase_auth.py); row này chỉ tự tạo (just-in-time) sau lần đăng nhập thành
    công đầu tiên, dùng `id` (int) làm khoá ngoại ổn định cho classes/exams/namespace khung mẫu."""
    __tablename__ = "teachers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    supabase_uid: Mapped[str | None] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class TeacherSession(Base):
    """"Nhớ đăng nhập" qua cookie — token_hash là SHA-256 của token ngẫu nhiên (không dùng bcrypt vì
    token đã có entropy cao sẵn, không cần hash chậm chống brute-force như mật khẩu)."""
    __tablename__ = "teacher_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class ClassRoom(Base):
    __tablename__ = "classes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    join_code: Mapped[str] = mapped_column(String(20), unique=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Student(Base):
    """Tài khoản HS do GV cấp (username/password tự sinh) — thay cho việc HS tự gõ tên/MSHS
    không kiểm chứng ở thiết kế trước đó. Mỗi tài khoản gắn cố định 1 lớp; mật khẩu chỉ lưu
    bcrypt hash, GV không xem lại được sau khi tạo (chỉ "Reset mật khẩu" để sinh mật khẩu mới)."""
    __tablename__ = "students"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    class_id: Mapped[int] = mapped_column(ForeignKey("classes.id", ondelete="CASCADE"), nullable=False)
    teacher_id: Mapped[int] = mapped_column(ForeignKey("teachers.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    allow_code_editor: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    allow_file_upload: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    opens_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closes_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    duration_minutes: Mapped[int | None] = mapped_column(Integer, nullable=True)
    access_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    final_score_policy: Mapped[str] = mapped_column(String(10), default="best", nullable=False)
    allow_ai_assistant: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_archived: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    force_unlocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow, nullable=False)


class ExamProblem(Base):
    __tablename__ = "exam_problems"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    max_score: Mapped[float] = mapped_column(Numeric, nullable=False)
    penalty_percent_per_submit: Mapped[float] = mapped_column(Numeric, default=0, nullable=False)
    max_attempts: Mapped[int | None] = mapped_column(Integer, nullable=True)
    function_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    required_constructs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    forbidden_constructs: Mapped[list | None] = mapped_column(JSON, nullable=True)
    forbidden_imports: Mapped[list | None] = mapped_column(JSON, nullable=True)
    forbidden_calls: Mapped[list | None] = mapped_column(JSON, nullable=True)


class ExamTestCase(Base):
    __tablename__ = "test_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_id: Mapped[int] = mapped_column(ForeignKey("exam_problems.id", ondelete="CASCADE"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    is_sample: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    input: Mapped[str] = mapped_column(Text, default="")
    expected_output: Mapped[str] = mapped_column(Text, default="")
    call_args: Mapped[list | None] = mapped_column(JSON, nullable=True)
    call_kwargs: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    expected_return: Mapped[object | None] = mapped_column(JSON, nullable=True)
    timeout: Mapped[float] = mapped_column(Numeric, default=5, nullable=False)
    note: Mapped[str] = mapped_column(String(255), default="")
    ignore_trailing_whitespace: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Enrollment(Base):
    """1 HS 'vào' 1 bài kiểm tra. Định danh HS lấy từ `student_id` (tài khoản thật, đã đăng
    nhập) — KHÔNG lưu tên/mã riêng ở đây nữa để tránh dữ liệu trùng lặp có thể lệch với
    `Student.full_name` nếu GV sửa tên sau này; mọi nơi cần hiển thị tên/username thì JOIN
    sang bảng `students`."""
    __tablename__ = "enrollments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    exam_id: Mapped[int] = mapped_column(ForeignKey("exams.id", ondelete="CASCADE"), nullable=False)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)

    __table_args__ = (UniqueConstraint("exam_id", "student_id", name="uq_enrollment_exam_student"),)


class ProblemProgress(Base):
    __tablename__ = "problem_progress"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    enrollment_id: Mapped[int] = mapped_column(ForeignKey("enrollments.id", ondelete="CASCADE"), nullable=False)
    problem_id: Mapped[int] = mapped_column(ForeignKey("exam_problems.id", ondelete="CASCADE"), nullable=False)
    attempts_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    best_submission_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    draft_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    draft_saved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (UniqueConstraint("enrollment_id", "problem_id", name="uq_progress_enrollment_problem"),)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem_progress_id: Mapped[int] = mapped_column(ForeignKey("problem_progress.id", ondelete="CASCADE"), nullable=False)
    attempt_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_trial: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    submission_mode: Mapped[str] = mapped_column(String(10), nullable=False)
    code_text: Mapped[str] = mapped_column(Text, nullable=False)
    original_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, nullable=False)
    passed_ratio: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    raw_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    penalty_applied: Mapped[float | None] = mapped_column(Numeric, nullable=True)
    final_score: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    __table_args__ = (UniqueConstraint("problem_progress_id", "attempt_number", name="uq_submission_attempt"),)


class SubmissionResult(Base):
    __tablename__ = "submission_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    submission_id: Mapped[int] = mapped_column(ForeignKey("submissions.id", ondelete="CASCADE"), nullable=False)
    # ondelete="CASCADE": nếu 1 test case bị xoá (chỉ có thể xảy ra khi GV "Mở khoá khẩn cấp" và xoá hẳn
    # 1 test case cũ — xem online_exam/service.py), chi tiết đúng/sai theo test đó mất theo, nhưng điểm
    # tổng đã chấm trong `submissions.final_score` KHÔNG bị đụng tới (không tự động chấm lại).
    test_case_id: Mapped[int] = mapped_column(ForeignKey("test_cases.id", ondelete="CASCADE"), nullable=False)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actual_output: Mapped[str] = mapped_column(Text, default="")
    error_message: Mapped[str] = mapped_column(Text, default="")
    execution_time_ms: Mapped[float | None] = mapped_column(Numeric, nullable=True)

    __table_args__ = (UniqueConstraint("submission_id", "test_case_id", name="uq_result_submission_testcase"),)
