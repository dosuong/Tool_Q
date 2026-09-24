"""UI quản lý tài khoản HS trong 1 lớp — gắn vào trang "Quản lý lớp" (mỗi lớp 1 expander),
không phải trang điều hướng riêng. GV tạo tài khoản từng người hoặc hàng loạt từ file Excel
(username/password tự sinh), xem danh sách, reset mật khẩu, xoá/lưu trữ."""
import io

import pandas as pd
import streamlit as st

from online_exam import service

_EXCEL_MIME = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


@st.dialog("Xoá học sinh")
def _confirm_delete_student(student_id: int, teacher_id: int, name: str, class_id: int):
    st.write(f"Xoá học sinh **'{name}'**? Nếu đã có bài nộp, hệ thống sẽ **lưu trữ/ẩn** thay vì xoá hẳn để không mất dữ liệu điểm.")
    col1, col2 = st.columns(2)
    if col1.button("Huỷ", use_container_width=True, key="cancel_delete_student"):
        st.rerun()
    if col2.button("Xác nhận", icon=":material/delete:", use_container_width=True, key="confirm_delete_student"):
        result = service.delete_or_archive_student(student_id, teacher_id)
        st.session_state[f"_student_action_msg_{class_id}"] = (
            f"Đã xoá học sinh '{name}'." if result == "deleted" else f"'{name}' đã có bài nộp — đã lưu trữ/ẩn thay vì xoá."
        )
        st.rerun()


def _df_to_excel_bytes(df: pd.DataFrame) -> bytes:
    buf = io.BytesIO()
    df.to_excel(buf, index=False, engine="openpyxl")
    return buf.getvalue()


def _render_bulk_import(class_id: int, teacher_id: int):
    reset_key = f"_bulk_upload_reset_{class_id}"
    st.session_state.setdefault(reset_key, 0)
    result_key = f"_bulk_upload_result_{class_id}"

    with st.expander("Tạo nhiều học sinh cùng lúc từ file Excel", icon=":material/upload_file:"):
        st.caption(
            "File Excel cần các cột **STT**, **Họ**, **Tên**, **Ngày sinh** (dòng đầu là tiêu đề cột) — "
            "tải file mẫu bên dưới để đúng định dạng."
        )
        sample_bytes = _df_to_excel_bytes(pd.DataFrame({
            "STT": [1, 2], "Họ": ["Nguyễn Văn", "Trần Thị"], "Tên": ["An", "Bình"], "Ngày sinh": ["01/01/2005", "15/06/2006"]
        }))
        st.download_button(
            "Tải file mẫu (Excel)", data=sample_bytes, file_name="mau_danh_sach_hoc_sinh.xlsx",
            mime=_EXCEL_MIME, key=f"bulk_sample_dl_{class_id}",
        )

        uploader_key = f"bulk_excel_upload_{class_id}_{st.session_state[reset_key]}"
        excel_file = st.file_uploader("Upload file Excel danh sách học sinh", type=["xlsx"], key=uploader_key)

        create_clicked = st.button(
            "Tạo tài khoản hàng loạt", icon=":material/group_add:", key=f"bulk_create_btn_{class_id}",
            disabled=excel_file is None,
        )
        if create_clicked and excel_file is not None:
            try:
                df_in = pd.read_excel(excel_file)
            except Exception as e:
                st.error(f"Không đọc được file Excel: {e}")
            else:
                cols_normalized = {str(c).strip().lower(): c for c in df_in.columns}
                stt_col = cols_normalized.get("stt")
                ho_col = cols_normalized.get("họ")
                ten_col = cols_normalized.get("tên")
                dob_col = cols_normalized.get("ngày sinh")
                
                if not ho_col or not ten_col or not dob_col:
                    st.error(
                        "File cần có đủ các cột 'Họ', 'Tên', 'Ngày sinh' (dòng đầu là tiêu đề cột) — tải file mẫu ở trên để đúng định dạng."
                    )
                else:
                    import unicodedata
                    rows_out = []
                    for idx, row in df_in.iterrows():
                        ho = str(row[ho_col]).strip()
                        ten = str(row[ten_col]).strip()
                        if not ten or ten.lower() == "nan":
                            continue
                            
                        # Ghép họ tên
                        ho = ho if ho.lower() != "nan" else ""
                        full_name = f"{ho} {ten}".strip()
                        
                        # Xử lý ngày sinh ra chuỗi ddmmyyyy
                        dob_raw = row[dob_col]
                        if isinstance(dob_raw, pd.Timestamp):
                            dob_str = dob_raw.strftime("%d%m%Y")
                        else:
                            dob_str = str(dob_raw).replace("/", "").replace("-", "").strip()
                            if dob_str.lower() == "nan":
                                dob_str = ""
                                
                        # Sinh username
                        stt_val = row[stt_col] if stt_col else idx + 1
                        
                        # Xử lý tên không dấu
                        nfkd = unicodedata.normalize('NFKD', ten)
                        ten_no_accent = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
                        ten_no_accent = ten_no_accent.replace("đ", "d").replace(" ", "")
                        
                        custom_user = f"{stt_val}{ten_no_accent}{dob_str}"
                        
                        student, raw_password = service.create_student(teacher_id, class_id, full_name, custom_username=custom_user)
                        
                        rows_out.append({
                            "STT": stt_val, "Họ Tên HS": full_name,
                            "Tài khoản": student.username, "Mật khẩu": raw_password,
                        })
                    if not rows_out:
                        st.warning("Không có dòng hợp lệ nào trong file (cột Tên trống hết).", icon=":material/warning:")
                    else:
                        st.session_state[result_key] = _df_to_excel_bytes(pd.DataFrame(rows_out))
                        st.session_state[f"_bulk_upload_count_{class_id}"] = len(rows_out)
                        st.rerun()

        if result_key in st.session_state:
            count = st.session_state.get(f"_bulk_upload_count_{class_id}", 0)
            st.success(f"Đã tạo {count} tài khoản — tải file kết quả bên dưới (chỉ tải được 1 lần).", icon=":material/check_circle:")
            downloaded = st.download_button(
                "Tải file kết quả (STT, Họ Tên HS, Tài khoản, Mật khẩu)",
                data=st.session_state[result_key], file_name="tai_khoan_hoc_sinh.xlsx",
                mime=_EXCEL_MIME, key=f"bulk_result_dl_{class_id}",
            )
            if downloaded:
                st.session_state.pop(result_key, None)
                st.session_state.pop(f"_bulk_upload_count_{class_id}", None)
                st.session_state[reset_key] += 1
                st.rerun()


def render_student_management(class_id: int, teacher_id: int):
    msg_key = f"_student_action_msg_{class_id}"
    if msg_key in st.session_state:
        st.toast(st.session_state.pop(msg_key), icon=":material/check_circle:")

    new_cred_key = f"_new_student_cred_{class_id}"
    if new_cred_key in st.session_state:
        username, password, full_name = st.session_state.pop(new_cred_key)
        st.success(
            f"Đã tạo tài khoản cho **{full_name}** — chỉ hiện **1 lần**, hãy copy/in ngay:",
            icon=":material/check_circle:",
        )
        st.code(f"Tên đăng nhập: {username}\nMật khẩu: {password}", language=None)

    with st.form(f"create_student_form_{class_id}", border=True):
        full_name = st.text_input("Họ tên học sinh", key=f"new_student_name_{class_id}")
        submitted = st.form_submit_button("Tạo tài khoản", icon=":material/person_add:")
    if submitted:
        if not full_name.strip():
            st.error("Nhập họ tên học sinh.")
        else:
            student, raw_password = service.create_student(teacher_id, class_id, full_name)
            st.session_state[new_cred_key] = (student.username, raw_password, student.full_name)
            st.rerun()

    _render_bulk_import(class_id, teacher_id)

    students = service.list_students(class_id, teacher_id)
    if not students:
        st.info("Lớp chưa có học sinh nào.", icon=":material/info:")
        return

    search_term = st.text_input("🔍 Tìm kiếm học sinh (theo tên hoặc tài khoản)", key=f"search_student_{class_id}")
    
    import unicodedata
    def _normalize_search(text: str) -> str:
        if not text:
            return ""
        # Remove accents for accent-insensitive search
        nfkd = unicodedata.normalize('NFKD', text)
        no_accent = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
        return no_accent.replace("đ", "d")
        
    search_norm = _normalize_search(search_term)

    visible_count = 0
    for s in students:
        if search_norm:
            name_norm = _normalize_search(s.full_name)
            if search_norm not in name_norm and search_norm not in s.username.lower():
                continue
        
        visible_count += 1
        with st.container(border=True):
            col_info, col_reset, col_delete = st.columns([3, 1, 1])
            col_info.markdown(f"**{s.full_name}** — tài khoản `{s.username}`")
            if col_reset.button("Reset mật khẩu", icon=":material/key:", key=f"reset_pw_{s.id}", use_container_width=True):
                new_password = service.reset_student_password(s.id, teacher_id)
                st.session_state[f"_reset_pw_shown_{s.id}"] = new_password
                st.rerun()
            if col_delete.button("Xoá", icon=":material/delete:", key=f"delete_student_{s.id}", use_container_width=True):
                _confirm_delete_student(s.id, teacher_id, s.full_name, class_id)

            reset_shown_key = f"_reset_pw_shown_{s.id}"
            if reset_shown_key in st.session_state:
                st.info(
                    f"Mật khẩu mới cho **{s.full_name}** (chỉ hiện 1 lần): `{st.session_state.pop(reset_shown_key)}`",
                    icon=":material/key:",
                )
                
    if visible_count == 0 and search_term:
        st.info("Không tìm thấy học sinh nào khớp với từ khoá tìm kiếm.", icon=":material/search:")
