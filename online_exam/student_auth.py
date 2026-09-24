"""Xác thực tài khoản HS (username/password do GV cấp) — bcrypt tự làm, tái dùng
`auth.hash_password`/`auth.verify_password`. Tách riêng khỏi `auth.py` (vốn giờ chỉ lo đăng
nhập GV qua Supabase) vì đây là 1 nhu cầu khác hẳn: nhiều tài khoản HS, GV tự tạo/reset mật
khẩu ngay trong app, không qua Supabase.
"""
import random
import secrets
import string

from sqlalchemy import select

from online_exam import auth
from online_exam.db import get_session
from online_exam.db_models import Student

_SAFE_ALPHABET = "".join(c for c in string.ascii_lowercase + string.digits if c not in "0ol1i")


def generate_username(session) -> str:
    for _ in range(50):
        candidate = "hs" + "".join(random.choices(_SAFE_ALPHABET, k=6))
        exists_already = session.execute(
            select(Student.id).where(Student.username == candidate)
        ).scalar_one_or_none()
        if not exists_already:
            return candidate
    raise RuntimeError("Không sinh được username duy nhất — thử lại.")


def generate_password(length: int = 8) -> str:
    return "".join(secrets.choice(_SAFE_ALPHABET) for _ in range(length))


def authenticate_student(username: str, password: str) -> Student | None:
    username = (username or "").strip().lower()
    with get_session() as session:
        student = session.execute(
            select(Student).where(Student.username == username, Student.is_archived.is_(False))
        ).scalar_one_or_none()
        if student and auth.verify_password(password or "", student.password_hash):
            return student
        return None
