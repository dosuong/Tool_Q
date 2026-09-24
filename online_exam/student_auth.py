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

import hmac
import hashlib
import base64

def generate_student_token(student: Student) -> str:
    """Sinh token phiên làm việc stateless dựa trên ID và password_hash của học sinh."""
    payload = str(student.id).encode("utf-8")
    key = student.password_hash.encode("utf-8")
    sig = hmac.new(key, payload, hashlib.sha256).digest()
    sig_b64 = base64.urlsafe_b64encode(sig).decode("utf-8").rstrip("=")
    return f"{student.id}.{sig_b64}"

def verify_student_token(token: str) -> Student | None:
    """Xác thực token và trả về object Student, nếu mật khẩu bị đổi thì token cũ tự vô hiệu."""
    if not token or "." not in token:
        return None
    try:
        student_id_str, sig_b64 = token.split(".", 1)
        student_id = int(student_id_str)
    except Exception:
        return None
        
    with get_session() as session:
        student = session.get(Student, student_id)
        if not student or student.is_archived:
            return None
        payload = str(student.id).encode("utf-8")
        key = student.password_hash.encode("utf-8")
        expected_sig = hmac.new(key, payload, hashlib.sha256).digest()
        expected_b64 = base64.urlsafe_b64encode(expected_sig).decode("utf-8").rstrip("=")
        if hmac.compare_digest(sig_b64, expected_b64):
            return student
    return None
