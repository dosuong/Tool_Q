"""Luồng HS: Đăng nhập (username/password do GV cấp) -> Bảng điểm của tôi -> Làm bài (tab
theo từng câu, chấm thử/nộp riêng) -> Xem lại bài đã được tính điểm.

Không có mã lớp nữa — tài khoản đã gắn sẵn đúng lớp, hệ thống tự biết. Chưa có cookie "nhớ
đăng nhập" cho HS ở đợt này (khác GV) — F5 (tải lại trang) sẽ mất session_state và cần đăng
nhập lại (dữ liệu điểm/tiến độ không mất vì đã nằm trong Postgres, chỉ mất phiên đăng nhập)."""
import json
import re
from datetime import datetime, timezone

import streamlit as st

from online_exam import grading, service, student_auth, ui_style

_STATE_PREFIX = "se_"


def _reset_student_state():
    for k in list(st.session_state.keys()):
        if k.startswith(_STATE_PREFIX):
            del st.session_state[k]


def _aware(dt):
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def _exam_is_open_now(exam) -> bool:
    if not exam.is_published or exam.is_archived:
        return False
    now = datetime.now(timezone.utc)
    opens_at = _aware(exam.opens_at)
    if opens_at and now < opens_at:
        return False
    closes_at = _aware(exam.closes_at)
    if closes_at and now > closes_at:
        return False
    return True


def _exam_status_label(exam) -> str:
    if exam.is_archived:
        return "🔒 Đã lưu trữ/ẩn"
    if not exam.is_published:
        return "🚧 Chưa công bố"
    now = datetime.now(timezone.utc)
    opens_at = _aware(exam.opens_at)
    if opens_at and now < opens_at:
        return "⏳ Chưa mở"
    closes_at = _aware(exam.closes_at)
    if closes_at and now > closes_at:
        return "🔴 Đã đóng"
    return "🟢 Đang mở"


def render_student_flow():
    # 1. Thử khôi phục session từ URL (để học sinh F5 không bị mất session)
    if not st.session_state.get(f"{_STATE_PREFIX}student_id"):
        token = st.query_params.get("student_session")
        if token:
            student = student_auth.verify_student_token(token)
            if student:
                st.session_state[f"{_STATE_PREFIX}student_id"] = student.id
                st.session_state[f"{_STATE_PREFIX}class_id"] = student.class_id
                st.session_state[f"{_STATE_PREFIX}full_name"] = student.full_name
                st.session_state[f"{_STATE_PREFIX}token"] = token
                
    # 2. Ghim token vào URL liên tục để giữ session khi F5
    if st.session_state.get(f"{_STATE_PREFIX}student_id") and st.session_state.get(f"{_STATE_PREFIX}token"):
        if st.query_params.get("student_session") != st.session_state[f"{_STATE_PREFIX}token"]:
            st.query_params["student_session"] = st.session_state[f"{_STATE_PREFIX}token"]

    if not st.session_state.get(f"{_STATE_PREFIX}student_id"):
        _render_student_login()
        return
        
    if st.session_state.get(f"{_STATE_PREFIX}active_exam_id"):
        _render_take_exam(st.session_state[f"{_STATE_PREFIX}active_exam_id"])
    else:
        _render_scoreboard()


def _render_student_login():
    _, col_center, _ = st.columns([1, 1.2, 1])
    with col_center:
        with st.container(border=True, key="login_card"):
            st.markdown("## :material/school: PyGrader")
            st.markdown("#### Đăng nhập dành cho Học sinh")

            with st.form("se_login_form", border=False):
                username = st.text_input(ui_style.required_label("Tên đăng nhập"), key="se_login_username")
                password = st.text_input(ui_style.required_label("Mật khẩu"), type="password", key="se_login_password")
                submitted = st.form_submit_button(
                    "Đăng nhập", type="primary", icon=":material/login:", use_container_width=True,
                )
            if submitted:
                if not username.strip() or not password:
                    st.error("Nhập đủ tên đăng nhập và mật khẩu.")
                else:
                    student = student_auth.authenticate_student(username, password)
                    if student is None:
                        st.error("Tên đăng nhập hoặc mật khẩu không đúng.")
                    else:
                        st.session_state[f"{_STATE_PREFIX}student_id"] = student.id
                        st.session_state[f"{_STATE_PREFIX}class_id"] = student.class_id
                        st.session_state[f"{_STATE_PREFIX}full_name"] = student.full_name
                        
                        # Generate and save token
                        token = student_auth.generate_student_token(student)
                        st.session_state[f"{_STATE_PREFIX}token"] = token
                        st.query_params["student_session"] = token
                        
                        st.rerun()

            if st.button("← Tôi là giáo viên", key="se_back_to_teacher_btn", use_container_width=True):
                st.query_params.clear()
                st.rerun()


def _render_scoreboard():
    student_id = st.session_state[f"{_STATE_PREFIX}student_id"]
    class_id = st.session_state[f"{_STATE_PREFIX}class_id"]
    full_name = st.session_state[f"{_STATE_PREFIX}full_name"]
    room = service.get_class_by_id(class_id)
    class_name = room.name if room else ""

    top1, top2 = st.columns([5, 1])
    top1.title(f"Bảng điểm của tôi — {class_name}", icon=":material/leaderboard:")
    if top2.button("Thoát", icon=":material/logout:", key="se_exit_btn", use_container_width=True):
        _reset_student_state()
        if "student_session" in st.query_params:
            del st.query_params["student_session"]
        st.rerun()
    st.caption(full_name)

    # Cache bảng điểm trong session_state — tải 1 lần, các lần chuyển màn hình tiếp theo
    # đọc từ RAM thay vì query lại Supabase qua Internet (mỗi lần trước đây tốn ~4 SQL × 150ms).
    # Bị xoá tường minh sau mỗi lần HS Nộp bài chính thức hoặc lần đầu vào bài (create_enrollment).
    board_key = f"{_STATE_PREFIX}board_{student_id}"
    if board_key not in st.session_state:
        st.session_state[board_key] = service.get_student_scoreboard(student_id)
    board = st.session_state[board_key]

    if not board:
        st.info("Lớp chưa có bài kiểm tra nào.", icon=":material/info:")
        return

    for entry in board:
        exam, summary = entry["exam"], entry["summary"]
        with st.container(border=True):
            c1, c2 = st.columns([4, 1])
            c1.markdown(f"**{exam.title}** — {_exam_status_label(exam)}")
            if exam.description:
                c1.caption(exam.description)
            if summary is not None:
                c1.markdown(f"Điểm tổng: **{summary['total_score']:.2f} / {summary['max_total']:.2f}**")
                for row in summary["problems"]:
                    score_txt = f"{row['score']:.2f}" if row["score"] is not None else "—"
                    c1.caption(f"　{row['title']}: {score_txt} / {row['max_score']:.2f}")
            can_enter_new = _exam_is_open_now(exam)
            if can_enter_new or entry["enrolled"]:
                btn_label = "Vào làm bài" if can_enter_new else "Xem lại"
                if c2.button(btn_label, key=f"se_enter_{exam.id}", use_container_width=True):
                    st.session_state[f"{_STATE_PREFIX}active_exam_id"] = exam.id
                    # PRE-FETCH CACHE: Chèn dữ liệu đã load sẵn vào cache để màn hình Làm bài
                    # mở ra INSTANT (0ms DB delay) thay vì tốn ~300ms query lại.
                    st.session_state[f"{_STATE_PREFIX}ctx_{exam.id}"] = (exam, entry["enrollment"])
                    if entry["enrollment"] and all(entry["progress_map"].values()):
                        st.session_state[f"{_STATE_PREFIX}progress_{entry['enrollment'].id}"] = entry["progress_map"]
                    st.rerun()


def _render_countdown(remaining_seconds: float):
    deadline_epoch_ms = int((datetime.now(timezone.utc).timestamp() + remaining_seconds) * 1000)
    st.components.v1.html(
        f"""
        <div id="oe-countdown" style="font-size:1.3rem;font-weight:700;color:#DC2626;
            font-family:sans-serif;padding:8px 0;"></div>
        <script>
        const oeDeadline = {deadline_epoch_ms};
        function oeTick() {{
            const now = Date.now();
            let diff = Math.max(0, Math.floor((oeDeadline - now) / 1000));
            const m = Math.floor(diff / 60), s = diff % 60;
            const el = document.getElementById("oe-countdown");
            if (el) el.innerText = "⏱ Còn lại: " + m + " phút " + String(s).padStart(2, "0") + " giây";
            if (diff > 0) setTimeout(oeTick, 1000);
        }}
        oeTick();
        </script>
        """,
        height=40,
    )


def _render_take_exam(exam_id: int):
    class_id = st.session_state[f"{_STATE_PREFIX}class_id"]
    student_id = st.session_state[f"{_STATE_PREFIX}student_id"]

    # Cache (Exam, Enrollment) — tránh 1 SQL RTT × 150ms mỗi lần rerun trang Làm bài.
    # Được xoá và tạo lại khi HS vào bài lần đầu (create_enrollment).
    ctx_key = f"{_STATE_PREFIX}ctx_{exam_id}"
    if ctx_key not in st.session_state:
        st.session_state[ctx_key] = service.load_take_exam_context(exam_id, class_id, student_id)
    exam, enrollment = st.session_state[ctx_key]

    if exam is None:
        st.error("Không tìm thấy bài kiểm tra.")
        return

    top1, top2 = st.columns([5, 1])
    top1.title(exam.title, icon=":material/edit_note:")
    if top2.button("← Bảng điểm", key="se_back_btn", use_container_width=True):
        st.session_state.pop(f"{_STATE_PREFIX}active_exam_id", None)
        st.rerun()
    if exam.description:
        st.caption(exam.description)

    can_enter_new = _exam_is_open_now(exam)

    if enrollment is None:
        if not can_enter_new:
            st.warning("Bài kiểm tra này hiện không mở.", icon=":material/lock:")
            return
        if exam.access_code:
            with st.form("se_access_form", border=True):
                pw = st.text_input("Nhập mật khẩu bài kiểm tra (giáo viên cung cấp)", type="password")
                ok = st.form_submit_button("Xác nhận", type="primary", icon=":material/key:")
            if not ok:
                return
            if not service.verify_exam_access(exam_id, pw):
                st.error("Sai mật khẩu.")
                return
        enrollment = service.create_enrollment(exam_id, student_id)
        # Cập nhật cache ctx với enrollment mới; xoá cache bảng điểm để lần sau
        # quay về bảng điểm sẽ thấy nút "Xem lại" thay vì "Vào làm bài".
        st.session_state[ctx_key] = (exam, enrollment)
        st.session_state.pop(f"{_STATE_PREFIX}board_{student_id}", None)

    deadline = service.compute_deadline(exam, enrollment)
    now = datetime.now(timezone.utc)
    time_up = deadline is not None and now > deadline
    read_only_all = time_up or not can_enter_new

    if deadline is not None and not time_up:
        _render_countdown((deadline - now).total_seconds())

    if read_only_all:
        reason = "đã hết thời gian làm bài" if time_up else "hiện đã bị ẩn/đóng"
        st.info(f"Bài kiểm tra {reason} — bạn chỉ xem lại được bài đã làm, không nộp thêm được.",
                icon=":material/lock:")

    # Cache danh sách câu hỏi — bất biến trong phiên thi (GV không thể sửa khi đã có bài nộp).
    problems_key = f"{_STATE_PREFIX}problems_{exam_id}"
    if problems_key not in st.session_state:
        st.session_state[problems_key] = service.load_exam_problems_for_student(exam_id)
    problems = st.session_state[problems_key]

    if not problems:
        st.info("Bài kiểm tra chưa có câu nào.", icon=":material/info:")
        return

    # Cache tiến độ tất cả câu — bị xoá sau mỗi lần Nộp bài chính thức (record_official_submission)
    # để rerun tiếp theo tải lại điểm/lượt nộp mới nhất từ DB.
    progress_key = f"{_STATE_PREFIX}progress_{enrollment.id}"
    if progress_key not in st.session_state:
        st.session_state[progress_key] = service.get_or_create_problem_progress_bulk(
            enrollment.id, [p["id"] for p in problems]
        )
    progress_map = st.session_state[progress_key]

    tabs = st.tabs([f"Câu {i + 1}" for i in range(len(problems))])
    for i, (tab, problem) in enumerate(zip(tabs, problems)):
        with tab:
            _render_problem_tab(i, exam, enrollment, problem, read_only_all, progress_map[problem["id"]])


def _is_redundant_title(title: str, index: int) -> bool:
    """True nếu GV gõ chính tên câu trùng với số thứ tự tự sinh (vd đặt tên "Câu 1" cho câu 1)
    — tránh hiện lặp "Câu 1: Câu 1". Không đụng tới các tên có ý nghĩa khác như "Cộng hai số"."""
    normalized = re.sub(r"\s+", "", title.strip().lower())
    return normalized in (f"câu{index + 1}", f"cau{index + 1}")


@st.fragment
def _render_problem_tab(index: int, exam, enrollment, problem: dict, read_only_all: bool, progress):
    header = f"Câu {index + 1}"
    title = problem.get("title", "")
    if title and not _is_redundant_title(title, index):
        header += f": {title}"
    st.markdown(f"#### {header}")
    if problem.get("description"):
        st.markdown(problem["description"])
    st.divider()

    sample_tcs = [tc for tc in problem["test_cases"] if tc.get("is_sample")]
    max_attempts = problem.get("max_attempts")
    attempts_left_txt = (
        "không giới hạn" if max_attempts is None
        else f"{max(max_attempts - progress.attempts_used, 0)}/{max_attempts}"
    )
    best_txt = f"{float(progress.best_score):.2f}" if progress.best_score is not None else "—"

    m1, m2, m3 = st.columns(3)
    m1.metric("Điểm tối đa", f"{problem['max_score']:.2f}")
    m2.metric("Lượt nộp còn lại", attempts_left_txt)
    m3.metric("Điểm cao nhất hiện tại", best_txt)

    attempts_exhausted = max_attempts is not None and progress.attempts_used >= max_attempts
    is_locked = read_only_all or attempts_exhausted
    pkey = f"se_p_{exam.id}_{problem['id']}"

    if not is_locked:
        code_text, submission_mode, original_filename = _render_code_input(exam, pkey, progress)

        col_trial, col_submit = st.columns(2)
        if col_trial.button("Chạy thử (chỉ test mẫu)", key=f"{pkey}_trial_btn", use_container_width=True):
            if not code_text.strip():
                st.error("Chưa có code để chạy thử.")
            else:
                with st.spinner("Đang chấm thử..."):
                    result = grading.grade_problem(code_text, problem, sample_tcs)
                service.record_trial_submission(progress.id, submission_mode, code_text, original_filename, result)
                _render_trial_result(result, sample_tcs)

        # Giao diện Chatbot AI (chỉ hiện nếu bài kiểm tra bật tính năng và chưa bị khoá nộp)
        if getattr(exam, "allow_ai_assistant", False):
            st.divider()
            with st.expander("🤖 Trợ lý AI (Gia sư ảo)", expanded=False):
                chat_key = f"{_STATE_PREFIX}chat_{enrollment.id}_{problem['id']}"
                if chat_key not in st.session_state:
                    st.session_state[chat_key] = []
                
                # Hiển thị lịch sử chat
                for msg in st.session_state[chat_key]:
                    with st.chat_message(msg["role"]):
                        st.markdown(msg["content"])
                
                # Khung nhập chat
                if user_prompt := st.chat_input("Hỏi AI gợi ý về code của bạn..."):
                    # Hiện ngay câu hỏi của user
                    with st.chat_message("user"):
                        st.markdown(user_prompt)
                    st.session_state[chat_key].append({"role": "user", "content": user_prompt})
                    
                    # Gọi AI Service
                    with st.chat_message("assistant"):
                        with st.spinner("AI đang suy nghĩ..."):
                            from online_exam.ai_service import ask_ai_tutor
                            ai_response = ask_ai_tutor(problem, code_text, st.session_state[chat_key][:-1], user_prompt)
                        st.markdown(ai_response)
                    st.session_state[chat_key].append({"role": "assistant", "content": ai_response})

        if col_submit.button("Nộp câu này", type="primary", key=f"{pkey}_submit_btn", use_container_width=True):
            if not code_text.strip():
                st.error("Chưa có code để nộp.")
            else:
                with st.spinner("Đang chấm bài..."):
                    result = grading.grade_problem(code_text, problem, problem["test_cases"])
                try:
                    submission = service.record_official_submission(
                        progress.id, problem, exam, enrollment, submission_mode, code_text, original_filename, result,
                    )
                except service.SubmissionBlocked as e:
                    st.error(str(e), icon=":material/block:")
                else:
                    n_sample = len(sample_tcs)
                    sample_pass = sum(1 for r in result["results"] if r["is_sample"] and r["passed"])
                    hidden_total = len(result["results"]) - n_sample
                    hidden_pass = sum(1 for r in result["results"] if not r["is_sample"] and r["passed"])
                    st.success(
                        f"Đã nộp — điểm lần này: {float(submission.final_score):.2f}/{problem['max_score']:.2f} "
                        f"(test mẫu {sample_pass}/{n_sample}, test ẩn {hidden_pass}/{hidden_total})",
                        icon=":material/check_circle:",
                    )
                    # Xoá cache tiến độ + bảng điểm để full rerun tiếp theo tải lại điểm/lượt
                    # nộp mới nhất từ DB, thay vì đọc dữ liệu cũ từ session_state.
                    _sid = st.session_state.get(f"{_STATE_PREFIX}student_id")
                    st.session_state.pop(f"{_STATE_PREFIX}progress_{enrollment.id}", None)
                    st.session_state.pop(f"{_STATE_PREFIX}board_{_sid}", None)
                    st.rerun(scope="app")
    else:
        reason = "hết thời gian làm bài" if read_only_all else "đã dùng hết lượt nộp"
        st.info(f"Câu này hiện chỉ xem được ({reason}) — không nộp thêm được.", icon=":material/lock:")

    if progress.best_submission_id:
        # KHÔNG dùng lại mẹo "chỉ query khi expander đang mở": st.expander(key=...) KHÔNG ghi
        # trạng thái đóng/mở vào session_state, nên điều kiện đó luôn sai và HS chỉ thấy khung
        # rỗng. Thay vào đó cứ vẽ bình thường — chi phí đã được xử lý bằng cách cache
        # service.get_submission_with_results (dữ liệu bài đã nộp là bất biến sau khi ghi).
        with st.expander("Xem bài đã nộp (bản được tính điểm)", icon=":material/history:"):
            _render_official_review(progress.best_submission_id, problem, sample_tcs)


def _render_code_input(exam, pkey: str, progress):
    mode_options = []
    if exam.allow_code_editor:
        mode_options.append("editor")
    if exam.allow_file_upload:
        mode_options.append("upload")
    if not mode_options:
        mode_options = ["editor"]

    if len(mode_options) > 1:
        mode = st.radio(
            "Cách nộp", mode_options, horizontal=True, key=f"{pkey}_mode",
            format_func=lambda m: "Viết code trực tiếp" if m == "editor" else "Upload file .py",
        )
    else:
        mode = mode_options[0]

    if mode == "upload":
        uploaded = st.file_uploader("Upload file .py", type=["py"], key=f"{pkey}_upload")
        code_text = uploaded.getvalue().decode("utf-8", errors="replace") if uploaded else ""
        original_filename = uploaded.name if uploaded else None
        return code_text, "upload", original_filename

    default_code = progress.draft_code or ""
    code_text = st.text_area("Viết code Python ở đây", value=default_code, height=280, key=f"{pkey}_code")
    if st.button("Lưu nháp", icon=":material/save:", key=f"{pkey}_save_draft_btn"):
        service.save_draft(progress.id, code_text)
        st.toast("Đã lưu nháp.", icon=":material/check_circle:")
    return code_text, "editor", None


import html

def _build_results_table_html(test_cases: list[dict], results_by_tc_id: dict) -> str:
    """CHỈ ĐƯỢC gọi với test case MẪU (is_sample=True) — bảng này hiện chi tiết đầy đủ (mong
    đợi/thực tế/đạt-hay-không) cho từng dòng, không có cơ chế che giấu. Test ẩn phải được lọc
    ra TRƯỚC khi gọi hàm này (xem _render_official_review) và chỉ báo tổng số đúng/tổng dạng
    aggregate — không được đưa test ẩn vào đây dù chỉ để che cột 'Mong đợi', vì cột 'Thực tế'
    và 'Kết quả' (Đạt/Chưa đạt) vẫn sẽ lộ ra."""
    table_html = """<style>
.result-table { width: 100%; border-collapse: collapse; margin-bottom: 15px; font-size: 0.95rem; }
.result-table th, .result-table td { border: 1px solid #e5e7eb; padding: 10px; text-align: left; }
.result-table th { background-color: #f9fafb; font-weight: 600; color: #374151; }
.row-pass { background-color: #f0fdf4; }
.row-fail { background-color: #fef2f2; }
.text-pass { color: #166534; font-weight: 600; }
.text-fail { color: #991b1b; font-weight: 600; }
.code-font { font-family: monospace; white-space: pre-wrap; }
</style>
<table class="result-table">
<thead>
<tr>
<th style="width: 10%;">Test</th>
<th style="width: 35%;">Mong đợi</th>
<th style="width: 35%;">Thực tế</th>
<th style="width: 20%;">Kết quả</th>
</tr>
</thead>
<tbody>
"""
    
    for i, tc in enumerate(test_cases, start=1):
        tc_id = tc.get("id")
        res = results_by_tc_id.get(tc_id)
        if not res:
            continue

        passed = res['passed']
        row_class = "row-pass" if passed else "row-fail"
        text_class = "text-pass" if passed else "text-fail"
        result_text = "Đạt" if passed else "Chưa đạt"

        actual = res.get('actual_output') or ""
        error_msg = res.get('error_message') or ""
        actual_display = actual.strip()
        if not actual_display and error_msg:
            actual_display = f"Lỗi: {error_msg}"
        actual_html = f"<div class='code-font'>{html.escape(actual_display)}</div>"

        expected_txt = tc.get("expected_output") or (
            json.dumps(tc.get("expected_return"), ensure_ascii=False)
            if tc.get("expected_return") is not None else ""
        )
        expected_html = f"<div class='code-font'>{html.escape(expected_txt)}</div>"

        table_html += f"""<tr class="{row_class}">
<td>{i}</td>
<td>{expected_html}</td>
<td>{actual_html}</td>
<td class="{text_class}">{result_text}</td>
</tr>
"""

    table_html += "</tbody></table>"
    return table_html

def _render_trial_result(result: dict, sample_tcs: list[dict]):
    if not result["structure_ok"]:
        st.error("Vi phạm yêu cầu cấu trúc code: " + "; ".join(result["violations"]), icon=":material/rule:")
    else:
        st.success("Cấu trúc code hợp lệ.", icon=":material/check_circle:")
    
    if sample_tcs:
        results_by_tc_id = {r["test_case_id"]: r for r in result["results"]}
        html_str = _build_results_table_html(sample_tcs, results_by_tc_id)
        st.markdown(html_str, unsafe_allow_html=True)
    else:
        st.info("Câu này không có test mẫu để chạy (nhưng cấu trúc code đã được kiểm tra).", icon=":material/info:")


def _render_official_review(submission_id: int, problem: dict, sample_tcs: list[dict]):
    submission, results = service.get_submission_with_results(submission_id)
    if submission is None:
        st.info("Không tìm thấy bài đã nộp.")
        return
    st.markdown(f"Điểm: **{float(submission.final_score):.2f} / {problem['max_score']:.2f}**")

    # Test ẩn KHÔNG được đưa vào bảng chi tiết (xem docstring _build_results_table_html) —
    # chỉ báo tổng số đúng/tổng dạng aggregate, đúng quy tắc đã chốt từ đầu dự án.
    sample_ids = {tc["id"] for tc in sample_tcs}
    results_by_tc_id = {
        r.test_case_id: {"passed": r.passed, "actual_output": r.actual_output, "error_message": r.error_message}
        for r in results if r.test_case_id in sample_ids
    }
    if sample_tcs:
        html_str = _build_results_table_html(sample_tcs, results_by_tc_id)
        st.markdown(html_str, unsafe_allow_html=True)

    hidden_results = [r for r in results if r.test_case_id not in sample_ids]
    if hidden_results:
        hidden_pass = sum(1 for r in hidden_results if r.passed)
        st.info(f"Test ẩn: {hidden_pass}/{len(hidden_results)} đúng (không hiển thị chi tiết).",
                icon=":material/visibility_off:")

    file_name = submission.original_filename or f"{(problem['title'] or 'bai_lam').replace(' ', '_')}.py"
    st.download_button(
        "Tải lại bài làm (.py)", data=submission.code_text.encode("utf-8"), file_name=file_name,
        mime="text/x-python", key=f"se_dl_{submission.id}",
    )
    if submission.submission_mode == "editor":
        with st.expander("Xem code đã nộp", icon=":material/code:"):
            st.code(submission.code_text, language="python")
