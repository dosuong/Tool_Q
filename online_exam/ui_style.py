"""CSS + tiện ích giao diện DÙNG CHUNG cho toàn bộ app — trang đăng nhập GV, app GV sau khi
đăng nhập, và luồng HS (`ui_student_exam.py`). Trước đây có 2 khối CSS tách rời (1 khối lớn
trong `app.py` chỉ áp dụng SAU gate đăng nhập nên trang login hoàn toàn không có style, và 1
khối nhỏ riêng trong `ui_student_exam.py`) — gộp lại đây để 3 nơi luôn nhất quán, và trang login
cũng được style đầy đủ như phần còn lại của app.

Thứ tự rule trong `inject_global_css()` CÓ Ý NGHĨA: rule chung (màu chữ, nền nút mặc định) phải
đứng TRƯỚC rule cụ thể theo `st-key-*` (nút xoá đỏ, nút sinh đáp án xanh...) — CSS có cùng độ
đặc hiệu (specificity) thì rule đứng SAU thắng, nên đảo thứ tự sẽ làm mất màu riêng của các nút
đó.
"""
import streamlit as st
import streamlit.components.v1 as components

def _inject_tab_hack():
    # Hack để cho phép gõ phím Tab trong textarea của Streamlit (mặc định Tab sẽ chuyển focus)
    components.html(
        """
        <script>
        const doc = window.parent.document;
        doc.addEventListener('keydown', function(e) {
            if (e.target.tagName.toLowerCase() === 'textarea' && e.key === 'Tab') {
                e.preventDefault();
                const ta = e.target;
                const start = ta.selectionStart;
                const end = ta.selectionEnd;
                // Chèn 4 dấu cách
                ta.value = ta.value.substring(0, start) + "    " + ta.value.substring(end);
                // Đặt lại con trỏ
                ta.selectionStart = ta.selectionEnd = start + 4;
                // Kích hoạt sự kiện input để React của Streamlit nhận diện thay đổi
                ta.dispatchEvent(new Event('input', {bubbles: true}));
            }
        });
        </script>
        """,
        height=0,
        width=0,
    )


def required_label(text: str) -> str:
    """Gắn dấu * đỏ vào label của 1 field bắt buộc — dùng cú pháp màu có sẵn của Streamlit
    trong label widget (`:red[...]`), không cần CSS riêng."""
    return f"{text} :red[*]"


def inject_global_css():
    st.markdown(
        """
        <style>
            /* ====== CHỮ CHUNG TOÀN GIAO DIỆN — đặt ĐẦU TIÊN, các rule màu cụ thể bên dưới
               (nút xoá đỏ, nút sinh đáp án xanh...) phải thắng rule này ở đúng phần tử của nó ====== */
            html, body, p, div, label, li,
            [data-testid="stMarkdownContainer"] p,
            [data-testid="stWidgetLabel"] p {
                color: #111827 !important;
                font-weight: 500 !important;
            }

            /* Chữ báo lỗi đậm/đỏ rõ hơn mặc định của Streamlit */
            div[data-testid="stAlert"] p,
            div[data-testid="stAlertContentError"] p,
            div[data-testid="stAlertContentError"] {
                color: #B91C1C !important;
                font-weight: 600 !important;
            }

            /* Nền mặc định cho mọi nút bấm — trước đây gần như trong suốt, khó phân biệt.
               Đặt TRƯỚC các rule màu riêng (xoá=đỏ, sinh đáp án=xanh) để không bị đảo priority. */
            .stButton button, [data-testid="stFormSubmitButton"] button,
            [data-testid="stDownloadButton"] button {
                background-color: #EFF6FF !important;
                border: 1px solid #BFDBFE !important;
                font-weight: 600 !important;
            }
            .stButton button:hover, [data-testid="stFormSubmitButton"] button:hover,
            [data-testid="stDownloadButton"] button:hover {
                background-color: #DBEAFE !important;
                border-color: #93C5FD !important;
            }
            .stButton button[kind="primary"], [data-testid="stFormSubmitButton"] button[kind="primary"] {
                background-color: #2563EB !important;
                border-color: #2563EB !important;
            }
            .stButton button[kind="primary"] p, .stButton button[kind="primary"] span,
            [data-testid="stFormSubmitButton"] button[kind="primary"] p,
            [data-testid="stFormSubmitButton"] button[kind="primary"] span {
                color: #FFFFFF !important;
            }
            .stButton button[kind="primary"]:hover, [data-testid="stFormSubmitButton"] button[kind="primary"]:hover {
                background-color: #1D4ED8 !important;
                border-color: #1D4ED8 !important;
            }

            /* Khung đăng nhập (GV lẫn HS) — card gọn, căn giữa, vừa 1 màn hình không cần
               cuộn: giảm margin/padding và siết khoảng cách giữa các phần tử bên trong. */
            div.st-key-login_card {
                padding: 1.25rem 1.5rem !important;
                border-radius: 16px !important;
                box-shadow: 0 4px 16px rgba(0, 0, 0, 0.06) !important;
                margin-top: 0.5rem !important;
            }
            div.st-key-login_card [data-testid="stVerticalBlock"] {
                gap: 0.5rem !important;
            }
            div.st-key-login_card hr {
                margin: 0.5rem 0 !important;
            }

            /* Làm nổi bật tên ứng dụng PyGrader ở form đăng nhập (H2) */
            div.st-key-login_card h2 {
                text-align: center !important;
                color: #2563EB !important; /* Màu xanh Primary */
                margin-top: 0 !important;
                margin-bottom: 0.2rem !important;
                font-weight: 800 !important; 
                font-size: 1.8rem !important; 
            }

            /* Tiêu đề Đăng nhập phụ (H4) */
            div.st-key-login_card h4 {
                text-align: center !important;
                color: #4B5563 !important; 
                margin-top: 0 !important;
                margin-bottom: 1.25rem !important;
                font-weight: 600 !important;
                font-size: 1.1rem !important; 
            }

            /* Tách biệt nút chuyển đổi tài khoản (Học sinh/Giáo viên) ra xa một chút */
            div.st-key-goto_student_mode_btn,
            div.st-key-se_back_to_teacher_btn {
                margin-top: 1.25rem !important;
            }

            /* Chữ trong ô nhập email và password ở form đăng nhập to và đen đậm hơn */
            div.st-key-login_email input,
            div.st-key-login_password input,
            div.st-key-se_login_username input,
            div.st-key-se_login_password input {
                font-size: 1.15rem !important; /* to vừa phải */
                font-weight: 600 !important;   /* đậm vừa phải */
                color: #000000 !important;     /* đen tuyền */
            }

            /* Ẩn div rỗng do st.markdown/st.html tạo ra ở đầu trang */
            div[data-testid="stMarkdownContainer"]:empty { display: none !important; }
            .element-container:has(> style) { display: none !important; }
            html, body { font-size: 18px !important; }
            /* Giữ nguyên kích thước tiêu đề như trước khi tăng base size */
            div[data-testid="stMarkdownContainer"] > h1, h1 { font-size: 36px !important; }
            div[data-testid="stMarkdownContainer"] > h2, h2 { font-size: 28px !important; }
            div[data-testid="stMarkdownContainer"] > h3, h3 { font-size: 22px !important; }

            /* Giảm tối đa khoảng trống thừa ở trên cùng của trang và Sidebar */
            .main .block-container {padding-top: 1.5rem !important; padding-bottom: 3rem !important; max-width: 1200px !important;}

            [data-testid="stSidebarHeader"] {padding: 1rem 1rem 0 1rem !important;}
            [data-testid="stSidebarUserContent"] {padding-top: 0 !important;}
            [data-testid="stSidebarContent"] {padding-top: 0 !important;}

            header[data-testid="stHeader"] {height: 3rem !important;}
            [data-testid="stHeader"] > div {padding-top: 0.5rem !important;}

            /* Phóng to và tạo kiểu cho PyGrader header và caption ở sidebar */
            [data-testid="stSidebar"] h3 {
                font-size: 24px !important;
                font-weight: 800 !important;
                color: #1F2937 !important;
                margin-bottom: 5px !important;
            }
            [data-testid="stSidebar"] h3 span.material-symbols-rounded {
                font-size: 26px !important;
                margin-right: 5px !important;
            }
            [data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
                font-size: 17px !important;
                color: #4B5563 !important;
                line-height: 1.5 !important;
                margin-bottom: 20px !important;
            }

            div[data-testid="stMetric"] {
                background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 10px;
                padding: 0.7rem 1rem;
            }
            section[data-testid="stSidebar"] {background: #F9FAFB;}

            [data-testid="stExpander"] details[open] > summary {
                background: #EEF2FF;
                border-radius: 8px;
            }

            /* ====== SIDEBAR NAVIGATION ====== */
            [data-testid="stPageLink"] a {
                transition: all 0.2s ease !important;
                border-radius: 8px !important;
                display: flex !important;
                justify-content: flex-start !important;
                align-items: center !important;
                gap: 12px !important;
                margin: 4px 0 !important;
                padding: 10px 16px !important;
                width: 100% !important;
                background-color: transparent !important;
                color: #4B5563 !important;
                font-weight: 500 !important;
                text-decoration: none !important;
                font-size: 1rem !important;
            }
            [data-testid="stPageLink"] a p, [data-testid="stPageLink"] a span {
                font-size: 1rem !important;
            }
            [data-testid="stPageLink"] a:hover {
                background-color: #DBEAFE !important;
                color: #2563EB !important;
            }

            /* ====== NÚT XÓA (mặc định đỏ nhạt, hover đỏ đậm) ====== */
            div.st-key-delete_template_btn button,
            div.st-key-delete_confirm_btn button,
            div.st-key-tab2_uploader_clear_btn button,
            div.st-key-tab3_uploader_clear_btn button {
                background-color: #FEF2F2 !important;
                border: 1px solid #FECACA !important;
                transition: all 0.2s ease !important;
            }
            /* Bắt buộc dùng `button > div` để chỉ tác động vào lớp bọc ngoài cùng,
               tránh ép độ dài 100% lên lớp bọc chữ bên trong làm đẩy icon ra rìa */
            div.st-key-delete_template_btn button > div,
            div.st-key-delete_confirm_btn button > div,
            div.st-key-tab2_uploader_clear_btn button > div,
            div.st-key-tab3_uploader_clear_btn button > div {
                display: flex !important;
                justify-content: center !important;
                align-items: center !important;
                gap: 0 !important;
            }
            div.st-key-delete_template_btn button p,
            div.st-key-delete_confirm_btn button p,
            div.st-key-tab2_uploader_clear_btn button p,
            div.st-key-tab3_uploader_clear_btn button p {
                display: none !important;
            }
            div.st-key-delete_template_btn button span,
            div.st-key-delete_confirm_btn button span,
            div.st-key-tab2_uploader_clear_btn button span,
            div.st-key-tab3_uploader_clear_btn button span {
                color: #EF4444 !important;
            }

            div.st-key-delete_template_btn button:hover,
            div.st-key-delete_confirm_btn button:hover,
            div.st-key-tab2_uploader_clear_btn button:hover,
            div.st-key-tab3_uploader_clear_btn button:hover {
                background-color: #FEE2E2 !important;
                border-color: #FCA5A5 !important;
                transform: translateY(-1px);
                box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.15) !important;
            }
            div.st-key-delete_template_btn button:hover span,
            div.st-key-delete_template_btn button:hover p,
            div.st-key-delete_confirm_btn button:hover span,
            div.st-key-delete_confirm_btn button:hover p,
            div.st-key-tab2_uploader_clear_btn button:hover span,
            div.st-key-tab2_uploader_clear_btn button:hover p,
            div.st-key-tab3_uploader_clear_btn button:hover span,
            div.st-key-tab3_uploader_clear_btn button:hover p {
                color: #DC2626 !important;
            }

            /* ====== NÚT XÓA có chữ (module thi online) — đỏ nhạt, hover đỏ đậm, GIỮ nguyên chữ
               (khác khối nút xóa icon-only ở trên) — dùng [class*=...] vì các nút này có key gắn
               theo id lớp/câu/bài/học sinh (động), không phải 1 key cố định duy nhất ====== */
            div[class*="st-key-delete_class_"] button,
            div.st-key-confirm_delete_class button,
            div.st-key-oe_delete_exam_btn button,
            div[class*="st-key-oe_remove_problem_"] button,
            div[class*="st-key-delete_student_"] button,
            div.st-key-confirm_delete_student button {
                background-color: #FEF2F2 !important;
                border: 1px solid #FECACA !important;
                transition: all 0.2s ease !important;
            }
            div[class*="st-key-delete_class_"] button p,
            div[class*="st-key-delete_class_"] button span,
            div.st-key-confirm_delete_class button p,
            div.st-key-confirm_delete_class button span,
            div.st-key-oe_delete_exam_btn button p,
            div.st-key-oe_delete_exam_btn button span,
            div[class*="st-key-oe_remove_problem_"] button p,
            div[class*="st-key-oe_remove_problem_"] button span,
            div[class*="st-key-delete_student_"] button p,
            div[class*="st-key-delete_student_"] button span,
            div.st-key-confirm_delete_student button p,
            div.st-key-confirm_delete_student button span {
                color: #EF4444 !important;
            }
            div[class*="st-key-delete_class_"] button:hover,
            div.st-key-confirm_delete_class button:hover,
            div.st-key-oe_delete_exam_btn button:hover,
            div[class*="st-key-oe_remove_problem_"] button:hover,
            div[class*="st-key-delete_student_"] button:hover,
            div.st-key-confirm_delete_student button:hover {
                background-color: #FEE2E2 !important;
                border-color: #FCA5A5 !important;
                transform: translateY(-1px);
                box-shadow: 0 4px 6px -1px rgba(239, 68, 68, 0.15) !important;
            }
            div[class*="st-key-delete_class_"] button:hover p,
            div[class*="st-key-delete_class_"] button:hover span,
            div.st-key-confirm_delete_class button:hover p,
            div.st-key-confirm_delete_class button:hover span,
            div.st-key-oe_delete_exam_btn button:hover p,
            div.st-key-oe_delete_exam_btn button:hover span,
            div[class*="st-key-oe_remove_problem_"] button:hover p,
            div[class*="st-key-oe_remove_problem_"] button:hover span,
            div[class*="st-key-delete_student_"] button:hover p,
            div[class*="st-key-delete_student_"] button:hover span,
            div.st-key-confirm_delete_student button:hover p,
            div.st-key-confirm_delete_student button:hover span {
                color: #DC2626 !important;
            }

            /* ====== UPLOAD BUTTON & GEN BUTTON — hover xanh lá nhạt ====== */
            [data-testid="stFileUploader"] button:hover,
            div.st-key-gen_program_btn button:hover,
            div.st-key-gen_function_btn button:hover {
                background-color: #F0FDF4 !important;
                border-color: #86EFAC !important;
                color: #16A34A !important;
            }
            [data-testid="stFileUploader"] button:hover span,
            [data-testid="stFileUploader"] button:hover p,
            div.st-key-gen_program_btn button:hover span,
            div.st-key-gen_program_btn button:hover p,
            div.st-key-gen_function_btn button:hover span,
            div.st-key-gen_function_btn button:hover p {
                color: #16A34A !important;
            }

            /* ====== Tab ngang danh sách câu (trang Làm bài của HS) — giãn cách + tăng vùng
               bấm, mặc định Streamlit hơi sát nhau, dễ bấm nhầm câu khác trên di động ====== */
            [data-baseweb="tab-list"] {
                gap: 6px !important;
                margin-bottom: 10px !important;
            }
            button[data-baseweb="tab"] {
                padding: 10px 22px !important;
                font-size: 1.05rem !important;
                font-weight: 600 !important;
            }
            [data-baseweb="tab-highlight"] {
                height: 3px !important;
            }
        </style>
        """,
        unsafe_allow_html=True,
    )
    _inject_tab_hack()
