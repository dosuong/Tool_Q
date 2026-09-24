"""Xác thực GV qua Supabase Auth (GoTrue) bằng REST API thuần — KHÔNG dùng SDK `supabase-py`
(kéo theo gotrue/postgrest/realtime/storage3, quá nặng chỉ để cần mỗi "xác thực email/password").
Tài khoản GV do người vận hành tự thêm trong Supabase Dashboard (Authentication > Users) —
app này không có tính năng tự đăng ký.

Khi CHƯA cấu hình `st.secrets["supabase"]` (vd đang code/test ở máy local, chưa có project
Supabase thật), rơi về 1 tài khoản dev cố định để vẫn đăng nhập được — cùng tinh thần fallback
SQLite của `online_exam/db.py`. Fallback này CHỈ được gọi khi `get_config()` trả về None; không
tự kích hoạt trong bất kỳ nhánh lỗi/timeout nào khi ĐÃ có cấu hình Supabase thật (xem auth.py).
"""
import requests
import streamlit as st

DEV_FALLBACK_EMAIL = "dosuong16203@gmail.com"
DEV_FALLBACK_PASSWORD = "123456"
DEV_FALLBACK_UID = "dev-local"

_TOKEN_ENDPOINT = "{url}/auth/v1/token?grant_type=password"


def get_config() -> tuple[str, str] | None:
    try:
        cfg = st.secrets["supabase"]
        url, anon_key = cfg["url"], cfg["anon_key"]
        if not url or not anon_key:
            return None
        return url.rstrip("/"), anon_key
    except Exception:
        return None


def login_with_password(email: str, password: str) -> tuple[str | None, str | None]:
    """Trả về (supabase_uid, error). supabase_uid=None nếu thất bại."""
    config = get_config()
    if config is None:
        return None, "Chưa cấu hình Supabase Auth."
    url, anon_key = config

    try:
        resp = requests.post(
            _TOKEN_ENDPOINT.format(url=url),
            headers={"apikey": anon_key, "Content-Type": "application/json"},
            json={"email": email, "password": password},
            timeout=10,
        )
    except requests.RequestException:
        return None, "Không kết nối được máy chủ xác thực, thử lại."

    if resp.status_code != 200:
        return None, "Email hoặc mật khẩu không đúng."

    try:
        user_id = resp.json()["user"]["id"]
    except (ValueError, KeyError):
        return None, "Phản hồi không hợp lệ từ máy chủ xác thực."
    return user_id, None
