"""Trang GV: Tạo/sửa bài kiểm tra online (nhiều câu). Dùng chung UI cho cả tạo mới
và sửa (chọn bài có sẵn hoặc để trống để tạo mới) — giống pattern trang "Quản lý
khung mẫu" cũ, nhưng lưu xuống Postgres qua online_exam.service thay vì JSON.

KHÔNG viết lại logic chấm bài — mọi thứ liên quan tới chạy code (Sinh đáp án tự
động, Chạy thử đề) đều gọi thẳng grader.runner / grader.ast_checker, y hệt cách
trang Quản lý khung mẫu (app.py) đã làm.
"""
import json
import tempfile
from pathlib import Path

import pandas as pd
import streamlit as st

from grader.ast_checker import check_structure
from grader.models import TestCase
from grader.runner import grade_one, run_capture_only, run_function_capture_only
from online_exam import service, ui_style

CONSTRUCT_OPTIONS = ["For", "While", "ListComp", "Recursion"]
_POLICY_OPTIONS = ["best", "average"]
_BLANK_PROBLEM = {
    "id": None, "title": "", "description": "", "max_score": 10.0, "penalty_percent_per_submit": 0.0,
    "max_attempts": 3, "function_name": None,
    "required_constructs": [], "forbidden_constructs": [], "forbidden_imports": [], "forbidden_calls": [],
    "test_cases": [{"id": None, "input": "", "expected_output": "", "is_sample": True, "timeout": 5, "note": ""}],
}


def _new_problem() -> dict:
    return json.loads(json.dumps(_BLANK_PROBLEM))  # deep copy đơn giản


def _test_cases_to_df(test_cases: list[dict]) -> pd.DataFrame:
    return pd.DataFrame([
        {
            "is_sample": bool(tc.get("is_sample")),
            "input": tc.get("input", ""),
            "expected_output": tc.get("expected_output", ""),
            "call_args": json.dumps(tc["call_args"], ensure_ascii=False) if tc.get("call_args") is not None else "",
            "expected_return": (
                json.dumps(tc["expected_return"], ensure_ascii=False) if tc.get("expected_return") is not None else ""
            ),
            "timeout": tc.get("timeout", 5),
            "note": tc.get("note", ""),
        }
        for tc in test_cases
    ])


def _df_row_to_test_case_dict(row, existing_id=None) -> dict:
    tc = {
        "id": existing_id,
        "is_sample": bool(row.get("is_sample")),
        "input": row.get("input", "") or "",
        "expected_output": row.get("expected_output", "") or "",
        "timeout": float(row.get("timeout") or 5),
        "note": row.get("note", "") or "",
    }
    call_args_str = (row.get("call_args") or "").strip()
    expected_return_str = (row.get("expected_return") or "").strip()
    if call_args_str:
        tc["call_args"] = json.loads(call_args_str)
        tc["call_kwargs"] = {}
    if expected_return_str:
        tc["expected_return"] = json.loads(expected_return_str)
    return tc


def _run_preview(code_text: str, problem_data: dict, test_case_rows: list[dict]):
    """Chấm thử code GV tự viết với TOÀN BỘ test case (mẫu + ẩn) của 1 câu, dùng
    đúng engine grade_one/check_structure — ephemeral, không lưu DB."""
    with tempfile.TemporaryDirectory(prefix="oe_preview_") as tmp:
        code_path = Path(tmp) / "solution_preview.py"
        code_path.write_text(code_text, encoding="utf-8")

        ok, violations = check_structure(
            code_text,
            problem_data.get("required_constructs") or [],
            problem_data.get("forbidden_constructs") or [],
            problem_data.get("forbidden_imports") or [],
            problem_data.get("forbidden_calls") or [],
        )
        if ok:
            st.success("Đạt yêu cầu cấu trúc code.", icon=":material/verified:")
        else:
            st.error("Vi phạm cấu trúc: " + "; ".join(violations), icon=":material/rule:")

        function_name = problem_data.get("function_name") or None
        for i, tc_dict in enumerate(test_case_rows, start=1):
            tc = TestCase(
                input=tc_dict.get("input", ""), expected_output=tc_dict.get("expected_output", ""),
                timeout=tc_dict.get("timeout", 5.0), note=tc_dict.get("note", ""),
                call_args=tc_dict.get("call_args"), call_kwargs=tc_dict.get("call_kwargs"),
                expected_return=tc_dict.get("expected_return"),
            )
            result = grade_one(code_path, tc, i, "Chạy thử đề", function_name)
            label = f"Test {i}" + (" (mẫu)" if tc_dict.get("is_sample") else " (ẩn)")
            if result.passed:
                st.success(f"{label}: Đạt", icon=":material/check_circle:")
            else:
                st.error(f"{label}: {result.short_message}", icon=":material/close:")


def page_create_exam(teacher_id: int):
    st.subheader("Tạo bài kiểm tra online", icon=":material/edit_document:", divider="gray")

    if "oe_pending_exam_choice" in st.session_state:
        st.session_state["oe_exam_choice"] = st.session_state.pop("oe_pending_exam_choice")

    classes = service.list_classes(teacher_id)
    if not classes:
        st.info("Chưa có lớp nào — hãy tạo lớp ở trang 'Quản lý lớp' trước.", icon=":material/info:")
        return

    class_names = {c.id: c.name for c in classes}
    class_id = st.selectbox(
        "Lớp", options=list(class_names.keys()), format_func=lambda cid: class_names[cid], key="oe_class_choice",
    )

    exams = service.list_exams(teacher_id, class_id=class_id, include_archived=False)
    exam_options = {0: "— Tạo bài kiểm tra mới —"} | {e.id: e.title for e in exams}
    exam_id_choice = st.selectbox(
        "Chọn bài có sẵn để sửa (hoặc tạo mới)", options=list(exam_options.keys()),
        format_func=lambda eid: exam_options[eid], key="oe_exam_choice",
    )
    exam_id = exam_id_choice if exam_id_choice != 0 else None

    exam_data = service.load_exam_full(exam_id, teacher_id) if exam_id else None
    state_key = f"oe_problems_{class_id}_{exam_id or 'new'}"
    if state_key not in st.session_state:
        st.session_state[state_key] = (exam_data or {}).get("problems") or [_new_problem()]
    st.session_state.setdefault("oe_editor_version", 0)

    locked = service.is_exam_locked_for_editing(exam_id) if exam_id else False
    force_unlocked = bool((exam_data or {}).get("force_unlocked"))

    if exam_id:
        if st.button(
            "Xoá bài kiểm tra này", icon=":material/delete:", key="oe_delete_exam_btn",
            help="Chưa ai nộp bài thì xoá hẳn; đã có người nộp thì chỉ lưu trữ/ẩn.",
        ):
            result = service.delete_or_archive_exam(exam_id, teacher_id)
            st.session_state.pop(state_key, None)
            st.toast(
                "Đã xoá bài kiểm tra." if result == "deleted" else "Bài đã có người nộp — đã lưu trữ/ẩn thay vì xoá.",
                icon=":material/check_circle:",
            )
            st.rerun()

    if locked:
        st.warning(
            "Bài này đã có học sinh nộp bài chính thức — phần câu/test case đang bị KHOÁ để tránh 2 nhóm học "
            "sinh bị chấm theo 2 bộ đề khác nhau. Vẫn sửa được mô tả/khung giờ/mật khẩu bên dưới.",
            icon=":material/lock:",
        )
        if st.button("Mở khoá khẩn cấp (chỉ dùng khi phát hiện đề sai)", icon=":material/lock_open:", key="oe_force_unlock_btn"):
            service.force_unlock_exam_editing(exam_id, teacher_id)
            st.warning(
                "Đã mở khoá. Các bài đã nộp trước đó KHÔNG được tự động chấm lại. Ở chế độ này bạn chỉ SỬA "
                "được nội dung câu/test case đã có, không thêm/xoá được câu hay test case mới.",
                icon=":material/warning:",
            )
            st.rerun()
    elif force_unlocked:
        st.info(
            "Bài này đã được mở khoá khẩn cấp — chỉ sửa tại chỗ được câu/test case đã có, không thêm/xoá được.",
            icon=":material/info:",
        )

    can_add_remove = not locked and not force_unlocked

    # Khối thông tin chung là 1 FRAGMENT (không phải st.form): gõ/tick ở đây chỉ chạy lại
    # riêng khối này, không dựng lại cả trang. Cố ý KHÔNG dùng st.form vì form bắt buộc nút
    # lưu phải nằm bên trong nó — mà nút lưu cần nằm ở CUỐI trang cho dễ thao tác.
    # Mọi widget đều có key gắn theo (lớp + bài đang sửa) để phần Lưu ở cuối trang đọc lại
    # giá trị mới nhất qua st.session_state, và để khi đổi sang bài khác không bị Streamlit
    # giữ lại giá trị cũ (widget key trùng thì tham số value= bị bỏ qua).
    mkey = f"oe_meta_{class_id}_{exam_id or 'new'}"

    def _render_exam_meta():
        with st.container(border=True):
            st.markdown("**:material/settings: Thông tin & cấu hình chung**")
            col1, col2 = st.columns(2)
            col1.text_input(
                ui_style.required_label("Tiêu đề bài kiểm tra"),
                value=(exam_data or {}).get("title", ""), key=f"{mkey}_title",
            )
            col2.text_input(
                "Mô tả ngắn", value=(exam_data or {}).get("description", ""), key=f"{mkey}_desc",
            )

            c1, c2, c3, c4 = st.columns(4)
            c1.checkbox(
                "Cho phép code editor", value=(exam_data or {}).get("allow_code_editor", True),
                key=f"{mkey}_editor",
            )
            c2.checkbox(
                "Cho phép upload file", value=(exam_data or {}).get("allow_file_upload", True),
                key=f"{mkey}_upload",
            )
            c3.checkbox(
                "Bật Trợ lý AI", value=(exam_data or {}).get("allow_ai_assistant", False),
                key=f"{mkey}_ai_assistant", help="Cho phép học sinh chat với AI gia sư để nhận gợi ý."
            )
            default_policy = (exam_data or {}).get("final_score_policy", "best")
            if default_policy not in _POLICY_OPTIONS:
                default_policy = "best"
            c4.selectbox(
                "Chính sách điểm", _POLICY_OPTIONS, index=_POLICY_OPTIONS.index(default_policy),
                format_func=lambda p: "Điểm cao nhất" if p == "best" else "Điểm trung bình",
                key=f"{mkey}_policy",
            )
            c4, c5 = st.columns(2)
            c4.number_input(
                "Thời lượng làm bài (phút, để 0 = không giới hạn)", min_value=0,
                value=int((exam_data or {}).get("duration_minutes") or 0), key=f"{mkey}_duration",
            )
            c5.text_input(
                "Mật khẩu riêng cho bài kiểm tra (tuỳ chọn)",
                value=(exam_data or {}).get("access_code") or "", key=f"{mkey}_access",
                help="Để trống nếu chỉ cần mã lớp là làm được luôn.",
            )

    _render_exam_meta()

    st.subheader("Các câu", icon=":material/checklist:", divider="gray")
    problems_draft = st.session_state[state_key]

    def _render_one_problem(i: int):
        # Gắn state_key (namespace theo lớp+bài đang sửa) vào MỌI khoá widget của câu này —
        # nếu chỉ đánh số theo i, chuyển từ "tạo mới" sang "sửa bài khác" sẽ bị Streamlit giữ
        # lại giá trị cũ ở đúng vị trí i đó (widget key trùng thì value= bị bỏ qua), gây hiện
        # tượng ô đầu tiên hiển thị sai dữ liệu khi mở lại 1 bài đã lưu.
        problems_draft = st.session_state[state_key]
        if i >= len(problems_draft):
            return  # câu vừa bị xoá ở nơi khác, fragment này đã cũ
        problem = problems_draft[i]
        ver = st.session_state["oe_editor_version"]
        pkey = f"{state_key}_{i}"
        with st.container(border=True):
            header_col, remove_col = st.columns([5, 1])
            header_col.markdown(f"**Câu {i + 1}**")
            if can_add_remove and len(problems_draft) > 1:
                if remove_col.button("Xoá câu", icon=":material/close:", key=f"oe_remove_problem_{pkey}"):
                    problems_draft.pop(i)
                    st.session_state["oe_editor_version"] += 1
                    st.rerun()

            pc1, pc2, pc3 = st.columns(3)
            p_title = pc1.text_input(ui_style.required_label("Tên câu"), value=problem.get("title", ""), key=f"oe_p_title_{pkey}")
            p_description = st.text_area(
                "Mô tả / đề bài cho câu này (học sinh sẽ thấy khi mở đúng câu này)",
                value=problem.get("description", ""), height=120, key=f"oe_p_desc_{pkey}",
            )
            p_max_score = pc2.number_input(
                "Điểm tối đa", min_value=0.0, value=float(problem.get("max_score", 10)), key=f"oe_p_maxscore_{pkey}",
            )
            p_unlimited = pc3.checkbox(
                "Không giới hạn lượt nộp", value=problem.get("max_attempts") is None, key=f"oe_p_unlimited_{pkey}",
            )
            pc4, pc5 = st.columns(2)
            p_max_attempts = None
            if not p_unlimited:
                p_max_attempts = pc4.number_input(
                    "Số lần nộp tối đa", min_value=1, value=int(problem.get("max_attempts") or 3),
                    key=f"oe_p_maxattempts_{pkey}",
                )
            p_penalty = pc5.number_input(
                "% trừ điểm mỗi lần nộp sai", min_value=0.0, max_value=100.0,
                value=float(problem.get("penalty_percent_per_submit", 0)), key=f"oe_p_penalty_{pkey}",
            )
            p_function_name = st.text_input(
                "Tên hàm cho phép nộp dạng hàm (để trống nếu chỉ nhận chương trình)",
                value=problem.get("function_name") or "", key=f"oe_p_funcname_{pkey}",
            )

            with st.expander("Yêu cầu cấu trúc code (tuỳ chọn)", icon=":material/checklist:"):
                rc1, rc2 = st.columns(2)
                p_required = rc1.multiselect(
                    "Bắt buộc dùng", CONSTRUCT_OPTIONS, default=problem.get("required_constructs", []),
                    key=f"oe_p_required_{pkey}",
                )
                p_forbidden = rc2.multiselect(
                    "Cấm dùng", CONSTRUCT_OPTIONS, default=problem.get("forbidden_constructs", []),
                    key=f"oe_p_forbidden_{pkey}",
                )
                p_forbidden_imports_text = st.text_input(
                    "Cấm import (cách nhau bởi dấu phẩy)",
                    value=", ".join(problem.get("forbidden_imports", [])), key=f"oe_p_forbimp_{pkey}",
                )
                p_forbidden_calls_text = st.text_input(
                    "Cấm gọi hàm/phương thức (cách nhau bởi dấu phẩy)",
                    value=", ".join(problem.get("forbidden_calls", [])), key=f"oe_p_forbcall_{pkey}",
                )

            current_problem_meta = {
                "function_name": p_function_name or None,
                "required_constructs": p_required,
                "forbidden_constructs": p_forbidden,
                "forbidden_imports": [m.strip() for m in p_forbidden_imports_text.split(",") if m.strip()],
                "forbidden_calls": [m.strip() for m in p_forbidden_calls_text.split(",") if m.strip()],
            }

            with st.expander("Sinh đáp án tự động từ lời giải mẫu (tuỳ chọn)", icon=":material/auto_awesome:"):
                if p_function_name:
                    gen_mode = st.radio(
                        "Kiểu sinh đáp án",
                        ["Chương trình (đọc input, in ra)", "Hàm (gọi trực tiếp)"],
                        horizontal=True, key=f"oe_genmode_{pkey}",
                    )
                else:
                    gen_mode = "Chương trình (đọc input, in ra)"
                    st.caption(
                        "Chỉ có chế độ chương trình — điền 'Tên hàm cho phép nộp dạng hàm' ở trên nếu muốn "
                        "sinh đáp án bằng cách gọi hàm trực tiếp (bắt được cả print() bên trong hàm, kể cả "
                        "khi hàm không return gì)."
                    )

                sol_file = st.file_uploader("Upload file lời giải mẫu (.py)", type=["py"], key=f"oe_sol_{pkey}")

                if gen_mode.startswith("Chương trình"):
                    sample_inputs_text = st.text_area(
                        "Danh sách input mẫu (ngăn cách bằng dòng chỉ có ---)", height=120, key=f"oe_sampleinputs_{pkey}",
                    )
                    if st.button("Sinh đáp án", icon=":material/auto_awesome:", key=f"oe_gen_btn_program_{pkey}"):
                        if not sol_file:
                            st.error("Hãy upload file lời giải mẫu trước.")
                        else:
                            with tempfile.TemporaryDirectory(prefix="oe_solgen_") as tmp:
                                sol_path = Path(tmp) / "solution.py"
                                sol_path.write_bytes(sol_file.getbuffer())
                                inputs = sample_inputs_text.split("\n---\n") if sample_inputs_text.strip() else [""]
                                generated, has_error = [], False
                                for idx, inp in enumerate(inputs, start=1):
                                    out, err, rc = run_capture_only(sol_path, inp, timeout=5.0)
                                    if rc != 0 or err.strip():
                                        st.error(f"Input #{idx}: lời giải mẫu lỗi — {err.strip().splitlines()[-1] if err.strip() else 'lỗi không rõ'}")
                                        has_error = True
                                    else:
                                        generated.append({
                                            "id": None, "input": inp, "expected_output": out,
                                            "is_sample": False, "timeout": 5, "note": f"case {idx}",
                                        })
                                if not has_error:
                                    problem["test_cases"] = generated
                                    st.session_state["oe_editor_version"] += 1
                                    st.success(f"Đã sinh {len(generated)} đáp án.")
                                    st.rerun()
                else:
                    st.caption(
                        f"File lời giải mẫu cần định nghĩa đúng hàm tên **{p_function_name}**. Mỗi khối là 1 bộ "
                        "tham số gọi hàm (cú pháp JSON, vd `[3, 5]`, hoặc `[]` nếu hàm không nhận tham số), các "
                        "khối ngăn cách bằng dòng chỉ có `---`. Tự động điền cả `expected_return` (giá trị hàm "
                        "trả về) lẫn `expected_output` (nội dung `print()` xảy ra trong lúc gọi hàm, nếu có)."
                    )
                    sample_call_args_text = st.text_area(
                        "Danh sách call_args mẫu (mỗi khối 1 bộ tham số, ngăn cách bằng dòng chỉ có ---)",
                        height=120, key=f"oe_samplecallargs_{pkey}", placeholder="[]\n---\n[3, 5]",
                    )
                    if st.button("Sinh đáp án", icon=":material/auto_awesome:", key=f"oe_gen_btn_function_{pkey}"):
                        if not sol_file:
                            st.error("Hãy upload file lời giải mẫu trước.")
                        else:
                            with tempfile.TemporaryDirectory(prefix="oe_solgen_") as tmp:
                                sol_path = Path(tmp) / "solution.py"
                                sol_path.write_bytes(sol_file.getbuffer())
                                blocks = sample_call_args_text.split("\n---\n") if sample_call_args_text.strip() else []
                                generated, has_error = [], False
                                for idx, block in enumerate(blocks, start=1):
                                    try:
                                        call_args = json.loads(block.strip())
                                    except json.JSONDecodeError:
                                        st.error(f"Khối #{idx}: '{block.strip()}' không phải JSON hợp lệ (vd cần dạng [3, 5] hoặc []).")
                                        has_error = True
                                        continue
                                    ret_val, stdout_val, err = run_function_capture_only(
                                        sol_path, p_function_name, call_args, timeout=5.0,
                                    )
                                    if err:
                                        st.error(f"Khối #{idx}: lỗi khi gọi hàm — {err}")
                                        has_error = True
                                    else:
                                        generated.append({
                                            "id": None, "input": "", "expected_output": stdout_val,
                                            "call_args": call_args, "call_kwargs": {}, "expected_return": ret_val,
                                            "is_sample": False, "timeout": 5, "note": f"case {idx}",
                                        })
                                if not has_error and generated:
                                    problem["test_cases"] = generated
                                    st.session_state["oe_editor_version"] += 1
                                    st.success(f"Đã sinh {len(generated)} đáp án dạng hàm.")
                                    st.rerun()

            st.markdown("**Test case** — tick `is_sample` cho test mẫu (HS xem trước được), để trống là test ẩn")
            tc_df = _test_cases_to_df(problem.get("test_cases", []))
            edited_tc_df = st.data_editor(
                tc_df, num_rows=("dynamic" if can_add_remove else "fixed"), use_container_width=True,
                key=f"oe_tc_editor_{pkey}_{ver}", disabled=locked and not force_unlocked,
                column_config={
                    "is_sample": st.column_config.CheckboxColumn("test mẫu"),
                    "input": st.column_config.TextColumn("input (stdin)", width="medium"),
                    "expected_output": st.column_config.TextColumn("expected_output", width="medium"),
                    "call_args": st.column_config.TextColumn("call_args (JSON)", width="small"),
                    "expected_return": st.column_config.TextColumn("expected_return (JSON)", width="small"),
                    "timeout": st.column_config.NumberColumn("timeout (s)", min_value=1, max_value=60, width="small"),
                    "note": st.column_config.TextColumn("ghi chú", width="small"),
                },
            )

            existing_tc_ids = [tc.get("id") for tc in problem.get("test_cases", [])]
            current_test_cases = [
                _df_row_to_test_case_dict(row, existing_tc_ids[idx] if idx < len(existing_tc_ids) else None)
                for idx, (_, row) in enumerate(edited_tc_df.iterrows())
            ]

            with st.expander("Chạy thử đề (xem cả test ẩn — không lưu gì)", icon=":material/play_circle:"):
                preview_code = st.text_area("Dán code mẫu vào đây để chấm thử", height=150, key=f"oe_preview_code_{pkey}")
                if st.button("Chấm thử", icon=":material/play_arrow:", key=f"oe_preview_btn_{pkey}"):
                    if not preview_code.strip():
                        st.error("Hãy dán code vào trước.")
                    else:
                        _run_preview(preview_code, current_problem_meta, current_test_cases)

            # Ghi lại toàn bộ giá trị hiện tại (đã đọc từ widget) vào draft, dùng khi Lưu ở cuối trang.
            problems_draft[i] = {
                "id": problem.get("id"), "title": p_title, "description": p_description, "max_score": p_max_score,
                "penalty_percent_per_submit": p_penalty, "max_attempts": p_max_attempts,
                **current_problem_meta,
                "test_cases": current_test_cases,
            }

    for _i in range(len(problems_draft)):
        _render_one_problem(_i)

    if can_add_remove:
        if st.button("Thêm câu", icon=":material/add:", key="oe_add_problem_btn"):
            problems_draft.append(_new_problem())
            st.session_state["oe_editor_version"] += 1
            st.rerun()

    st.divider()
    if st.session_state.get("_oe_saved_msg"):
        st.success(st.session_state.pop("_oe_saved_msg"), icon=":material/check_circle:")

    col_save, col_pub = st.columns(2)
    save_clicked = col_save.button(
        "Lưu bài kiểm tra", type="primary", icon=":material/save:",
        key="oe_save_btn", use_container_width=True,
        help="Lưu cả thông tin chung ở trên lẫn toàn bộ các câu.",
    )
    if exam_id:
        is_published = (exam_data or {}).get("is_published", False)
        label = "Ẩn bài kiểm tra" if is_published else "Công bố"
        icon = ":material/visibility_off:" if is_published else ":material/publish:"
        if col_pub.button(label, icon=icon, key="oe_publish_toggle_btn", use_container_width=True):
            service.set_exam_published(exam_id, teacher_id, not is_published)
            st.rerun()
        st.caption("Công bố dùng **bản đã lưu gần nhất** — vừa sửa gì thì bấm Lưu trước.")
    else:
        col_pub.caption("Lưu trước, sau đó chọn lại bài vừa tạo để Công bố.")

    if save_clicked:
        # Đọc lại giá trị mới nhất của khối cấu hình qua session_state (khối đó là fragment
        # riêng nên biến cục bộ của nó không dùng lại được ở đây).
        title = st.session_state.get(f"{mkey}_title", "") or ""
        description = st.session_state.get(f"{mkey}_desc", "") or ""
        duration_minutes = st.session_state.get(f"{mkey}_duration", 0) or 0
        access_code = st.session_state.get(f"{mkey}_access", "") or ""
        if not title.strip():
            st.error("Nhập tiêu đề bài kiểm tra.")
        elif not any(p["title"].strip() for p in problems_draft):
            st.error("Cần ít nhất 1 câu có tên.")
        else:
            exam_meta = {
                "title": title, "description": description,
                "allow_code_editor": st.session_state.get(f"{mkey}_editor", True),
                "allow_file_upload": st.session_state.get(f"{mkey}_upload", True),
                "allow_ai_assistant": st.session_state.get(f"{mkey}_ai_assistant", False),
                "duration_minutes": duration_minutes or None,
                "access_code": access_code.strip() or None,
                "final_score_policy": st.session_state.get(f"{mkey}_policy", "best"),
            }
            new_exam_id = service.save_exam(teacher_id, class_id, exam_meta, problems_draft, exam_id)
            st.session_state.pop(state_key, None)
            # Dọn luôn các khoá widget của khối cấu hình: nếu vừa tạo bài MỚI, namespace
            # "..._new" còn sót giá trị cũ sẽ tự điền vào lần tạo bài mới kế tiếp.
            for k in [k for k in st.session_state if k.startswith(f"{mkey}_")]:
                st.session_state.pop(k, None)
            st.session_state["oe_pending_exam_choice"] = new_exam_id
            st.session_state["_oe_saved_msg"] = "Đã lưu bài kiểm tra (chưa công bố cho học sinh)."
            st.rerun()
