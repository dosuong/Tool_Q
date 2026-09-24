"""Đăng nhập GV qua Supabase Auth thật (xem `online_exam/supabase_auth.py`) — không tự làm
đăng ký/băm mật khẩu cho GV nữa (Supabase lo phần đó, tài khoản do người vận hành tự thêm
trong Supabase Dashboard). `hash_password`/`verify_password` (bcrypt) ở đây vẫn giữ lại vì
được tái sử dụng cho tài khoản HS (xem `online_exam/student_auth.py`) — 2 nhu cầu khác nhau
dùng chung 2 hàm thuần, không liên quan gì tới cách GV đăng nhập.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from sqlalchemy import select

from online_exam import supabase_auth
from online_exam.db import get_session
from online_exam.db_models import Teacher, TeacherSession

SESSION_DAYS = 30


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def _get_or_create_teacher_profile(email: str, supabase_uid: str) -> int:
    """Just-in-time provisioning: tạo/tìm profile local ngay sau khi xác thực (Supabase hoặc
    dev-fallback) thành công — `teachers.id` (int) vẫn là khoá ngoại ổn định cho phần còn lại
    của app (classes/exams/namespace khung mẫu), không cần đổi gì ở những chỗ đó."""
    email = email.strip().lower()
    with get_session() as session:
        teacher = session.execute(select(Teacher).where(Teacher.email == email)).scalar_one_or_none()
        if teacher:
            if teacher.supabase_uid != supabase_uid:
                teacher.supabase_uid = supabase_uid
                session.commit()
            return teacher.id
        teacher = Teacher(email=email, supabase_uid=supabase_uid)
        session.add(teacher)
        session.commit()
        session.refresh(teacher)
        return teacher.id


def login_teacher(email: str, password: str):
    """Trả về (teacher_id, error_message) — teacher_id=None nếu thất bại.

    Nếu CHƯA cấu hình `st.secrets["supabase"]` (dev local, chưa có project Supabase thật): chỉ
    chấp nhận đúng tài khoản dev cố định. Nếu ĐÃ cấu hình: luôn gọi Supabase Auth thật, KHÔNG
    bao giờ rơi về tài khoản dev dù Supabase lỗi/timeout — đây là ranh giới bảo mật quan trọng
    nhất của module này, tuyệt đối không đổi thành try/except gộp 2 nhánh lại."""
    email = email.strip().lower()
    password = password or ""

    if supabase_auth.get_config() is None:
        if email == supabase_auth.DEV_FALLBACK_EMAIL and password == supabase_auth.DEV_FALLBACK_PASSWORD:
            teacher_id = _get_or_create_teacher_profile(email, supabase_auth.DEV_FALLBACK_UID)
            return teacher_id, None
        return None, "Email hoặc mật khẩu không đúng."

    uid, error = supabase_auth.login_with_password(email, password)
    if error:
        return None, error
    teacher_id = _get_or_create_teacher_profile(email, uid)
    return teacher_id, None


def _hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_remember_token(teacher_id: int) -> str:
    """Sinh 1 token ngẫu nhiên, lưu bản băm SHA-256 (không dùng bcrypt — token đã đủ entropy,
    không cần hash chậm chống brute-force như mật khẩu người dùng tự đặt)."""
    raw_token = secrets.token_urlsafe(32)
    with get_session() as session:
        session.add(TeacherSession(
            teacher_id=teacher_id,
            token_hash=_hash_token(raw_token),
            expires_at=_utcnow() + timedelta(days=SESSION_DAYS),
        ))
        session.commit()
    return raw_token


def verify_remember_token(raw_token: str):
    if not raw_token:
        return None
    token_hash = _hash_token(raw_token)
    with get_session() as session:
        now = _utcnow()
        sess = session.execute(
            select(TeacherSession).where(TeacherSession.token_hash == token_hash)
        ).scalar_one_or_none()
        if not sess:
            return None
        expires_at = sess.expires_at
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)
        if expires_at <= now:
            return None
        return sess.teacher_id


def revoke_remember_token(raw_token: str):
    if not raw_token:
        return
    token_hash = _hash_token(raw_token)
    with get_session() as session:
        sess = session.execute(
            select(TeacherSession).where(TeacherSession.token_hash == token_hash)
        ).scalar_one_or_none()
        if sess:
            session.delete(sess)
            session.commit()


def get_teacher(teacher_id: int) -> Teacher | None:
    with get_session() as session:
        return session.get(Teacher, teacher_id)
