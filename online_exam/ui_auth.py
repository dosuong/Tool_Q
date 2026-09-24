"""Trang Đăng nhập GV (Supabase Auth thật — không còn tự đăng ký) + khôi phục phiên qua
cookie ("nhớ đăng nhập")."""
import streamlit as st
from streamlit_cookies_controller import CookieController

from online_exam import auth, ui_style

COOKIE_NAME = "pygrader_teacher_token"


def _cookie_controller() -> CookieController:
    if "_cookie_controller" not in st.session_state:
        st.session_state["_cookie_controller"] = CookieController()
    return st.session_state["_cookie_controller"]


def try_restore_session():
    """Gọi ở đầu app.py mỗi lượt chạy — nếu chưa có teacher_id trong session_state
    (vd sau khi mở tab mới/F5 mất session), thử khôi phục từ cookie hoặc URL."""
    if st.session_state.get("teacher_id"):
        return
    
    token = None
    # 1. Lấy từ URL (Chắc chắn 100% hoạt động trên Streamlit Cloud kể cả khi bị chặn Cookie)
    if "session" in st.query_params:
        token = st.query_params["session"]

    # 2. Lấy nhanh từ native Streamlit context
    if not token and hasattr(st, "context") and hasattr(st.context, "cookies"):
        token = st.context.cookies.get(COOKIE_NAME)
        
    # 3. Fallback lại bằng component
    if not token:
        token = _cookie_controller().get(COOKIE_NAME)
        
    if token:
        teacher_id = auth.verify_remember_token(token)
        if teacher_id:
            st.session_state["teacher_id"] = teacher_id
            # Lưu lại vào URL để F5 không bị mất
            st.query_params["session"] = token


def logout():
    token = _cookie_controller().get(COOKIE_NAME) or st.query_params.get("session")
    if token:
        auth.revoke_remember_token(token)
        _cookie_controller().remove(COOKIE_NAME)
    if "session" in st.query_params:
        del st.query_params["session"]
    st.session_state.pop("teacher_id", None)
    st.rerun()


def render_login_page():
    """Chỉ còn form Đăng nhập — tài khoản GV do người vận hành tự thêm trong Supabase
    Dashboard (Authentication > Users), không có tính năng tự đăng ký trong app nữa.
    Bố cục siết gọn để vừa 1 màn hình, không cần cuộn (xem thêm CSS ở ui_style.py)."""
    _, col_center, _ = st.columns([1, 1.2, 1])
    with col_center:
        with st.container(border=True, key="login_card"):
            st.markdown("## :material/fact_check: PyGrader")
            st.markdown("#### Đăng nhập dành cho Giáo viên")

            with st.form("login_form", border=False):
                email = st.text_input(ui_style.required_label("Email"), key="login_email")
                password = st.text_input(ui_style.required_label("Mật khẩu"), type="password", key="login_password")
                col_remember, col_submit = st.columns([1.3, 1])
                remember = col_remember.checkbox("Ghi nhớ đăng nhập", value=True)
                submitted = col_submit.form_submit_button(
                    "Đăng nhập", type="primary", icon=":material/login:", use_container_width=True,
                )
            if submitted:
                if not email or not password:
                    st.error("Nhập đủ email và mật khẩu.")
                else:
                    teacher_id, error = auth.login_teacher(email, password)
                    if error:
                        st.error(error, icon=":material/error:")
                    else:
                        st.session_state["teacher_id"] = teacher_id
                        if remember:
                            token = auth.create_remember_token(teacher_id)
                            _cookie_controller().set(COOKIE_NAME, token)
                            # Lưu vào URL để bypass lỗi iframe chặn cookie trên Streamlit Cloud
                            st.query_params["session"] = token
                            import time
                            time.sleep(0.5)  # Đợi cookie kịp ghi vào trình duyệt trước khi rerun
                        st.rerun()

            if st.button(
                "Tôi là học sinh — vào làm bài kiểm tra", icon=":material/school:",
                key="goto_student_mode_btn", use_container_width=True,
            ):
                st.query_params["mode"] = "student"
                st.rerun()
