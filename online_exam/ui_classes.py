"""Trang GV: Quản lý lớp — tạo lớp, khoá/mở, xoá/lưu trữ, quản lý tài khoản học sinh."""
import streamlit as st

from online_exam import service, ui_style
from online_exam.ui_students import render_student_management


@st.dialog("Xoá lớp")
def _confirm_delete_class(class_id: int, teacher_id: int, name: str):
    st.write(f"Xoá lớp **'{name}'**? Nếu lớp đã có học sinh nộp bài, hệ thống sẽ **lưu trữ/ẩn** thay vì xoá hẳn để không mất dữ liệu điểm.")
    col1, col2 = st.columns(2)
    if col1.button("Huỷ", use_container_width=True, key="cancel_delete_class"):
        st.rerun()
    if col2.button("Xác nhận", icon=":material/delete:", use_container_width=True, key="confirm_delete_class"):
        result = service.delete_or_archive_class(class_id, teacher_id)
        st.session_state["_class_action_msg"] = (
            f"Đã xoá lớp '{name}'." if result == "deleted" else f"Lớp '{name}' đã có bài nộp — đã lưu trữ/ẩn thay vì xoá."
        )
        st.rerun()


def page_manage_classes(teacher_id: int):
    st.subheader("Quản lý lớp", icon=":material/groups:", divider="gray")

    if "_class_action_msg" in st.session_state:
        st.toast(st.session_state.pop("_class_action_msg"), icon=":material/check_circle:")

    with st.form("create_class_form", border=True):
        st.markdown("**:material/add_circle: Tạo lớp mới**")
        name = st.text_input(ui_style.required_label("Tên lớp (vd: 10A1 - Tin học)"))
        submitted = st.form_submit_button("Tạo lớp", type="primary", icon=":material/add:")
    if submitted:
        if not name.strip():
            st.error("Nhập tên lớp.")
        else:
            room = service.create_class(teacher_id, name)
            st.success(f"Đã tạo lớp '{room.name}'.", icon=":material/check_circle:")
            st.rerun()

    st.subheader("Danh sách lớp", icon=":material/list:", divider="gray")
    classes = service.list_classes(teacher_id)
    if not classes:
        st.info("Chưa có lớp nào — tạo lớp mới ở trên.", icon=":material/info:")
        return

    for room in classes:
        with st.container(border=True):
            col_info, col_actions = st.columns([3, 1])
            with col_info:
                status = "🟢 Đang mở" if room.is_active else "🔴 Đã khoá"
                st.markdown(f"**{room.name}** — {status}")
                st.caption("Học sinh vào bằng tài khoản (username/password) đã cấp ở mục 'Quản lý học sinh' bên dưới.")
            with col_actions:
                new_active = st.toggle("Mở lớp", value=room.is_active, key=f"toggle_active_{room.id}")
                if new_active != room.is_active:
                    service.set_class_active(room.id, teacher_id, new_active)
                    st.rerun()
                if st.button("Xoá lớp", icon=":material/delete:", key=f"delete_class_{room.id}", use_container_width=True):
                    _confirm_delete_class(room.id, teacher_id, room.name)

            with st.expander("Quản lý học sinh", icon=":material/group:"):
                render_student_management(room.id, teacher_id)
