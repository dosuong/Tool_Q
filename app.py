import json
import os
import tempfile
from pathlib import Path

import pandas as pd
import pytest
import streamlit as st

from grader.exam_batch import group_by_bai
from grader.models import TestCase
from grader.pytest_plugin import GraderPlugin
from grader.runner import run_capture_only
from grader.templates_store import delete_template, list_templates, load_template, save_template

st.set_page_config(
    page_title="Tool_Q — Chấm bài Python tự động",
    page_icon=":material/fact_check:",
    layout="wide",
)

TEST_RUNNER_FILE = Path(__file__).parent / "grader" / "test_runner.py"
CONSTRUCT_OPTIONS = ["For", "While", "ListComp", "Recursion"]

st.markdown(
    """
    <style>
        .main .block-container {padding-top: 1.5rem; padding-bottom: 3rem; max-width: 1200px;}
        .stTabs [data-baseweb="tab-list"] {gap: 4px;}
        .stTabs [data-baseweb="tab"] {height: 42px; padding: 0 18px; font-weight: 600;}
        div[data-testid="stMetric"] {
            background: #F9FAFB; border: 1px solid #E5E7EB; border-radius: 10px;
            padding: 0.7rem 1rem;
        }
        section[data-testid="stSidebar"] {background: #F9FAFB;}
    </style>
    """,
    unsafe_allow_html=True,
)

st.title("Tool_Q — Chấm bài Python tự động", icon=":material/fact_check:")
st.caption("So khớp output · Kiểm tra cấu trúc code (AST) · Chấm hàng loạt bằng pytest")


def _make_test_case(tc_dict: dict) -> TestCase:
    return TestCase(
        input=tc_dict.get("input", ""),
        expected_output=tc_dict.get("expected_output", ""),
        timeout=tc_dict.get("timeout", 5.0),
        note=tc_dict.get("note", ""),
        ignore_trailing_whitespace=tc_dict.get("ignore_trailing_whitespace", True),
        call_args=tc_dict.get("call_args"),
        call_kwargs=tc_dict.get("call_kwargs"),
        expected_return=tc_dict.get("expected_return"),
    )


def _save_uploaded_files(uploaded_files, dest_dir: Path):
    seen = {}
    saved_paths = []
    for uf in uploaded_files:
        stem, suffix = Path(uf.name).stem, Path(uf.name).suffix
        n = seen.get(uf.name, 0)
        seen[uf.name] = n + 1
        final_name = uf.name if n == 0 else f"{stem}_{n + 1}{suffix}"
        dest = dest_dir / final_name
        dest.write_bytes(uf.getbuffer())
        saved_paths.append(dest)
    return saved_paths


def _build_cases_for_template(template: dict, saved_paths, bai_label: str):
    output_cases, structure_cases = [], []
    function_name = template.get("function_name") or None
    structural_rules = template.get("structural_rules") or {}
    has_structural_rules = any(
        structural_rules.get(k)
        for k in ("required_constructs", "forbidden_constructs", "forbidden_imports", "forbidden_calls")
    )
    safe_label = bai_label.replace(" ", "_")

    for sf in saved_paths:
        for i, tc_dict in enumerate(template.get("test_cases", []), start=1):
            tc = _make_test_case(tc_dict)
            output_cases.append({
                "student_file": sf,
                "test_case": tc,
                "case_index": i,
                "bai_label": bai_label,
                "function_name": function_name,
                "case_id": f"{safe_label}-{sf.stem}-case{i}",
            })
        if has_structural_rules:
            structure_cases.append({
                "student_file": sf,
                "structural_rules": structural_rules,
                "bai_label": bai_label,
                "case_id": f"{safe_label}-{sf.stem}-structure",
            })
    return output_cases, structure_cases


def _run_grading(output_cases, structure_cases, parallel: bool, workers: int):
    plugin = GraderPlugin(output_cases, structure_cases)
    progress = st.progress(0.0, text="Đang chấm bài...")

    def _cb(done, total):
        if total:
            progress.progress(min(done / total, 1.0))

    plugin.set_progress_callback(_cb)

    args = ["-q", "-p", "no:cacheprovider", str(TEST_RUNNER_FILE)]
    if parallel:
        args += ["-n", str(workers)]

    with st.spinner("pytest đang chạy..."):
        pytest.main(args, plugins=[plugin])
    progress.empty()
    return plugin.output_results, plugin.structure_results


def _parallel_controls(key_prefix: str):
    col1, col2 = st.columns([1, 1])
    parallel = col1.checkbox("Chạy song song (pytest-xdist)", key=f"{key_prefix}_parallel")
    workers = 4
    if parallel:
        max_workers = max(os.cpu_count() or 1, 1)
        workers = col2.number_input(
            "Số luồng song song", min_value=1, max_value=max_workers,
            value=min(4, max_workers), key=f"{key_prefix}_workers",
            icon=":material/bolt:",
        )
    return parallel, workers


def _render_results(output_results, structure_results, key_prefix: str):
    if not output_results and not structure_results:
        st.info("Chưa có kết quả.", icon=":material/info:")
        return

    df = pd.DataFrame(output_results) if output_results else pd.DataFrame(
        columns=["student_name", "bai_label", "passed", "case_index"])
    struct_df = pd.DataFrame(structure_results) if structure_results else pd.DataFrame(
        columns=["student_name", "bai_label", "ok"])

    students = sorted(set(df["student_name"]).union(set(struct_df["student_name"])))

    summary_rows = []
    for student in students:
        sub = df[df["student_name"] == student]
        struct_sub = struct_df[struct_df["student_name"] == student]
        so_pass, tong = int(sub["passed"].sum()), len(sub)
        struct_ok = bool(struct_sub["ok"].all()) if len(struct_sub) else True
        has_struct = len(struct_sub) > 0
        full_pass = so_pass == tong and struct_ok
        summary_rows.append({
            "student": student, "so_pass": so_pass, "tong": tong,
            "struct_ok": struct_ok, "has_struct": has_struct, "full_pass": full_pass,
        })

    total_students = len(summary_rows)
    full_pass_count = sum(1 for r in summary_rows if r["full_pass"])
    rate = (full_pass_count / total_students * 100) if total_students else 0.0

    m1, m2, m3 = st.columns(3)
    m1.metric("Tổng học sinh", total_students, icon=":material/group:")
    m2.metric("Đạt toàn bộ", full_pass_count, icon=":material/check_circle:")
    m3.metric("Tỷ lệ đạt", f"{rate:.0f}%", icon=":material/percent:")

    st.subheader("Bảng tổng hợp", icon=":material/summarize:", divider="gray")
    only_failed = st.checkbox("Chỉ hiện học sinh chưa đạt toàn bộ", key=f"{key_prefix}_only_failed")

    display_rows = []
    for r in summary_rows:
        if only_failed and r["full_pass"]:
            continue
        display_rows.append({
            "Học sinh": r["student"],
            "Output": f"{r['so_pass']}/{r['tong']}",
            "Cấu trúc": "✓" if r["struct_ok"] else ("✗" if r["has_struct"] else "—"),
            "Kết quả": "Đạt" if r["full_pass"] else "Chưa đạt",
        })

    result_df = pd.DataFrame(display_rows)
    st.dataframe(result_df, use_container_width=True, hide_index=True)

    if not result_df.empty:
        csv_bytes = result_df.to_csv(index=False).encode("utf-8-sig")
        st.download_button(
            "Tải bảng điểm (CSV)", data=csv_bytes, icon=":material/download:",
            file_name="ket_qua_cham_bai.csv", mime="text/csv", key=f"{key_prefix}_csv",
        )

    st.subheader("Chi tiết theo học sinh", icon=":material/person_search:", divider="gray")
    for student in students:
        sub = df[df["student_name"] == student]
        struct_sub = struct_df[struct_df["student_name"] == student]
        all_pass = (bool(sub["passed"].all()) if len(sub) else True) and (
            bool(struct_sub["ok"].all()) if len(struct_sub) else True
        )
        expander_icon = ":material/check_circle:" if all_pass else ":material/cancel:"
        with st.expander(student, icon=expander_icon):
            for _, row in struct_sub.iterrows():
                if row["ok"]:
                    st.success(f"[{row['bai_label']}] Đạt yêu cầu cấu trúc code.", icon=":material/verified:")
                else:
                    st.error(
                        f"[{row['bai_label']}] Vi phạm cấu trúc: " + "; ".join(row["violations"]),
                        icon=":material/rule:",
                    )

            for _, row in sub.sort_values(["bai_label", "case_index"]).iterrows():
                st.markdown(
                    f"**[{row['bai_label']}] Test case {row['case_index']}** — {row.get('case_note', '')} "
                    f"_(kiểu: {row.get('mode_used', 'program')})_"
                )
                if row["passed"]:
                    st.success("Đạt", icon=":material/check_circle:")
                    continue
                if row["timed_out"]:
                    st.error(row["short_message"], icon=":material/schedule:")
                elif row["crashed"]:
                    st.error(f"Lỗi: {row['error_type']} tại dòng {row['error_line']}", icon=":material/bug_report:")
                    st.code(row["error_message"])
                    with st.expander("Xem traceback đầy đủ", icon=":material/terminal:"):
                        st.code(row["raw_stderr"], language="text")
                else:
                    st.warning(row["short_message"], icon=":material/compare_arrows:")
                    col1, col2 = st.columns(2)
                    key_suffix = f"{key_prefix}_{student}_{row['bai_label']}_{row['case_index']}".replace(" ", "_")
                    col1.text_area("Kỳ vọng", row["expected_output"], height=100, key=f"exp_{key_suffix}")
                    col2.text_area("Thực tế", row["actual_output"], height=100, key=f"act_{key_suffix}")
                    if row["diff_summary"]:
                        st.code(row["diff_summary"], language="diff")


with st.sidebar:
    st.subheader("Tool_Q", icon=":material/fact_check:")
    st.caption("Chấm bài lập trình Python tự động cho giáo viên.")
    st.divider()
    st.markdown(
        ":material/folder_open: **Quản lý khung mẫu** — tạo đề, khai báo input/đáp án.\n\n"
        ":material/rule: **Chấm 1 đề** — chấm nhanh 1 bài tập lẻ.\n\n"
        ":material/library_books: **Chấm cả kỳ thi** — chấm nhiều đề cùng lúc."
    )
    st.divider()
    st.caption(f"Số khung mẫu hiện có: **{len(list_templates())}**")


tab_template, tab_grade_one, tab_exam = st.tabs([
    ":material/folder_open: Quản lý khung mẫu",
    ":material/rule: Chấm 1 đề",
    ":material/library_books: Chấm cả kỳ thi",
])

with tab_template:
    st.session_state.setdefault("editor_version", 0)
    if "pending_template_choice" in st.session_state:
        st.session_state["template_choice"] = st.session_state.pop("pending_template_choice")

    st.subheader("Chọn / tạo đề bài", icon=":material/description:", divider="gray")
    existing = list_templates()
    choice = st.selectbox(
        "Chọn đề có sẵn để sửa (hoặc để trống để tạo mới)", [""] + existing, key="template_choice",
    )
    default_template = load_template(choice) if choice else {}

    tc_state_key = f"tc_data_{choice or 'new'}"
    if tc_state_key not in st.session_state:
        st.session_state[tc_state_key] = default_template.get(
            "test_cases", [{"input": "", "expected_output": "", "timeout": 5, "note": ""}]
        )

    col_name, col_desc = st.columns([1, 2])
    name_input = col_name.text_input("Tên đề bài (dùng làm tên file lưu)", value=choice)
    description_input = col_desc.text_input("Mô tả ngắn", value=default_template.get("description", ""))

    if choice:
        with st.expander("Xoá khung mẫu này", icon=":material/delete:"):
            st.caption(f"Xoá vĩnh viễn đề '{choice}' — không thể hoàn tác.")
            confirm_delete = st.checkbox(f"Tôi chắc chắn muốn xoá '{choice}'", key="confirm_delete_template")
            if st.button(
                "Xoá khung mẫu này", type="secondary", icon=":material/delete_forever:",
                disabled=not confirm_delete, key="delete_template_btn",
            ):
                delete_template(choice)
                st.session_state.pop(f"tc_data_{choice}", None)
                st.session_state.pop("confirm_delete_template", None)
                st.session_state["pending_template_choice"] = ""
                st.session_state["editor_version"] += 1
                st.success(f"Đã xoá khung mẫu '{choice}'.")
                st.rerun()

    with st.container(border=True):
        st.markdown("**:material/checklist: Yêu cầu cấu trúc code (tuỳ chọn)**")
        default_rules = default_template.get("structural_rules", {}) or {}
        col_req, col_forb = st.columns(2)
        required = col_req.multiselect(
            "Bắt buộc dùng", CONSTRUCT_OPTIONS, default=default_rules.get("required_constructs", []),
        )
        forbidden = col_forb.multiselect(
            "Cấm dùng", CONSTRUCT_OPTIONS, default=default_rules.get("forbidden_constructs", []),
        )
        forbidden_imports_text = st.text_input(
            "Cấm import các thư viện (cách nhau bởi dấu phẩy)",
            value=", ".join(default_rules.get("forbidden_imports", [])),
        )
        forbidden_calls_text = st.text_input(
            "Cấm gọi hàm/phương thức có sẵn (cách nhau bởi dấu phẩy, vd: sorted, sort, min, max)",
            value=", ".join(default_rules.get("forbidden_calls", [])),
            help="Bắt bằng cách quét lời gọi hàm trong code, vd cấm 'sorted' sẽ chặn cả sorted(x) và bắt lỗi "
                 "nếu học sinh dùng x.sort() thì cần cấm thêm 'sort'.",
        )
        function_name_input = st.text_input(
            "Tên hàm cho phép nộp dạng hàm (để trống nếu chỉ nhận chương trình hoàn chỉnh)",
            value=default_template.get("function_name") or "", icon=":material/code:",
        )

    with st.expander("Sinh đáp án tự động từ file lời giải mẫu (tuỳ chọn)", icon=":material/auto_awesome:"):
        solution_file = st.file_uploader("Upload solution.py", type=["py"], key="solution_uploader")
        sample_inputs_text = st.text_area(
            "Danh sách input mẫu (mỗi input 1 khối, ngăn cách bằng dòng chỉ có ---)",
            height=120, key="sample_inputs",
        )
        if st.button("Sinh đáp án từ lời giải mẫu", icon=":material/auto_awesome:"):
            if not solution_file:
                st.error("Hãy upload file solution.py trước.")
            else:
                with tempfile.TemporaryDirectory(prefix="solgen_") as tmp:
                    sol_path = Path(tmp) / "solution.py"
                    sol_path.write_bytes(solution_file.getbuffer())
                    inputs = sample_inputs_text.split("\n---\n") if sample_inputs_text.strip() else [""]
                    generated, has_error = [], False
                    for idx, inp in enumerate(inputs, start=1):
                        out, err, rc = run_capture_only(sol_path, inp, timeout=5.0)
                        if rc != 0 or err.strip():
                            err_line = err.strip().splitlines()[-1] if err.strip() else "lỗi không rõ"
                            st.error(f"Input #{idx}: solution.py lỗi — {err_line}")
                            has_error = True
                        else:
                            generated.append(
                                {"input": inp, "expected_output": out, "timeout": 5, "note": f"case {idx}"}
                            )
                    if not has_error:
                        st.session_state[tc_state_key] = generated
                        st.session_state["editor_version"] += 1
                        st.success(f"Đã sinh {len(generated)} đáp án — đã điền vào bảng test case bên dưới.")
                        st.rerun()

    st.subheader("Test case", icon=":material/table_chart:", divider="gray")
    st.caption(
        "Sửa trực tiếp trong bảng. Cột `call_args`/`expected_return` chỉ cần điền nếu có cho phép nộp dạng hàm "
        "(dùng cú pháp JSON, vd `[3, 5]` và `8`)."
    )
    raw_cases = st.session_state[tc_state_key]
    edit_df = pd.DataFrame([
        {
            "input": tc.get("input", ""),
            "expected_output": tc.get("expected_output", ""),
            "call_args": json.dumps(tc["call_args"], ensure_ascii=False) if tc.get("call_args") is not None else "",
            "expected_return": (
                json.dumps(tc["expected_return"], ensure_ascii=False) if tc.get("expected_return") is not None else ""
            ),
            "timeout": tc.get("timeout", 5),
            "note": tc.get("note", ""),
        }
        for tc in raw_cases
    ])
    editor_key = f"test_case_editor_{choice or 'new'}_{st.session_state['editor_version']}"
    edited_df = st.data_editor(
        edit_df, num_rows="dynamic", use_container_width=True, key=editor_key,
        column_config={
            "input": st.column_config.TextColumn("input (stdin)", width="medium"),
            "expected_output": st.column_config.TextColumn("expected_output", width="medium"),
            "call_args": st.column_config.TextColumn("call_args (JSON)", width="small"),
            "expected_return": st.column_config.TextColumn("expected_return (JSON)", width="small"),
            "timeout": st.column_config.NumberColumn("timeout (s)", min_value=1, max_value=60, width="small"),
            "note": st.column_config.TextColumn("ghi chú", width="small"),
        },
    )

    with st.expander("Nâng cao: xem/nạp JSON trực tiếp", icon=":material/settings:"):
        preview = {
            "name": name_input,
            "description": description_input,
            "function_name": function_name_input or None,
            "structural_rules": {
                "required_constructs": required,
                "forbidden_constructs": forbidden,
                "forbidden_imports": [m.strip() for m in forbidden_imports_text.split(",") if m.strip()],
                "forbidden_calls": [m.strip() for m in forbidden_calls_text.split(",") if m.strip()],
            },
            "test_cases": raw_cases,
        }
        st.caption("Bản xem trước JSON sẽ được lưu (dựa trên dữ liệu đã nhập ở trên):")
        st.code(json.dumps(preview, ensure_ascii=False, indent=2), language="json")
        import_text = st.text_area("Dán 1 JSON khung mẫu khác vào đây rồi bấm Nạp", height=150, key="import_json")
        if st.button("Nạp JSON vào bảng test case", icon=":material/upload:"):
            try:
                imported = json.loads(import_text)
                st.session_state[tc_state_key] = imported.get("test_cases", [])
                st.session_state["editor_version"] += 1
                st.success("Đã nạp — cuộn lên xem bảng test case.")
                st.rerun()
            except Exception as e:
                st.error(f"JSON không hợp lệ: {e}")

    if st.button("Lưu khung mẫu", type="primary", icon=":material/save:"):
        if not name_input.strip():
            st.error("Cần nhập tên đề bài.")
        else:
            try:
                test_cases = []
                for idx, row in edited_df.iterrows():
                    tc = {
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
                    test_cases.append(tc)

                if not test_cases:
                    raise ValueError("Cần ít nhất 1 test case.")

                blank_rows = [
                    i + 1 for i, tc in enumerate(test_cases)
                    if not tc["expected_output"].strip() and tc.get("expected_return") is None
                ]
                if blank_rows:
                    st.warning(
                        f"Dòng test case {blank_rows} đang để trống `expected_output` (và không có "
                        "`expected_return`) — mọi bài nộp có in ra gì cũng sẽ bị coi là SAI. "
                        "Vẫn lưu, nhưng hãy kiểm tra lại nếu đây không phải chủ ý.",
                        icon=":material/warning:",
                    )

                data = {
                    "name": name_input,
                    "description": description_input,
                    "function_name": function_name_input or None,
                    "structural_rules": {
                        "required_constructs": required,
                        "forbidden_constructs": forbidden,
                        "forbidden_imports": [m.strip() for m in forbidden_imports_text.split(",") if m.strip()],
                        "forbidden_calls": [m.strip() for m in forbidden_calls_text.split(",") if m.strip()],
                    },
                    "test_cases": test_cases,
                }
                saved_name = save_template(name_input, data)
                st.session_state.pop(tc_state_key, None)
                st.session_state["pending_template_choice"] = saved_name
                st.session_state["editor_version"] += 1
                st.success(f"Đã lưu khung mẫu '{saved_name}'.")
                st.rerun()
            except Exception as e:
                st.error(f"Dữ liệu không hợp lệ ở bảng test case (dòng call_args/expected_return phải là JSON): {e}")

with tab_grade_one:
    st.subheader("Chấm bài cho 1 đề", icon=":material/rule:", divider="gray")
    templates = list_templates()
    if not templates:
        st.info("Chưa có khung mẫu nào — hãy tạo ở tab 'Quản lý khung mẫu' trước.", icon=":material/info:")
    else:
        selected = st.selectbox("Chọn đề bài", templates, key="tab2_template")
        template = load_template(selected)
        if template.get("description"):
            st.caption(template["description"])

        parallel, workers = _parallel_controls("tab2")

        uploaded_files = st.file_uploader(
            "Upload bài làm học sinh (.py)", type=["py"], accept_multiple_files=True, key="tab2_uploader",
        )
        if st.button("Chấm bài", disabled=not uploaded_files, key="tab2_run", type="primary",
                     icon=":material/play_arrow:"):
            with tempfile.TemporaryDirectory(prefix="grader_run_") as tmp:
                student_dir = Path(tmp) / "students"
                student_dir.mkdir()
                saved_paths = _save_uploaded_files(uploaded_files, student_dir)
                output_cases, structure_cases = _build_cases_for_template(
                    template, saved_paths, bai_label=template.get("name", selected)
                )
                results = _run_grading(output_cases, structure_cases, parallel, workers)
            st.session_state["tab2_results"] = results

        if "tab2_results" in st.session_state:
            _render_results(*st.session_state["tab2_results"], key_prefix="tab2")

with tab_exam:
    st.subheader("Chấm cả kỳ thi (nhiều đề cùng lúc)", icon=":material/library_books:", divider="gray")
    templates = list_templates()
    if not templates:
        st.info("Chưa có khung mẫu nào — hãy tạo ở tab 'Quản lý khung mẫu' trước.", icon=":material/info:")
    else:
        selected_templates = st.multiselect("Chọn các đề tham gia kỳ thi", templates, key="tab3_templates")
        mapping = {}
        if selected_templates:
            st.caption(
                "Gán số bài (bai1, bai2, ...) cho từng đề — theo quy ước tên file `<hoc_sinh>_bai<N>.py`"
            )
            cols = st.columns(len(selected_templates))
            for i, (tname, col) in enumerate(zip(selected_templates, cols), start=1):
                bai_num = col.number_input(f"'{tname}' = bai", min_value=1, value=i, key=f"tab3_bainum_{tname}")
                mapping[int(bai_num)] = tname

        parallel, workers = _parallel_controls("tab3")

        uploaded_files = st.file_uploader(
            "Upload toàn bộ bài làm học sinh (.py) — đặt tên theo quy ước <hoc_sinh>_bai<N>.py",
            type=["py"], accept_multiple_files=True, key="tab3_uploader",
        )

        if st.button("Chấm toàn bộ", disabled=not (uploaded_files and mapping), key="tab3_run", type="primary",
                     icon=":material/play_arrow:"):
            with tempfile.TemporaryDirectory(prefix="grader_exam_") as tmp:
                student_dir = Path(tmp) / "students"
                student_dir.mkdir()
                saved_paths = _save_uploaded_files(uploaded_files, student_dir)
                matched, unmatched = group_by_bai(saved_paths)

                if unmatched:
                    st.warning(
                        "Các file KHÔNG đúng quy ước tên (`<hoc_sinh>_bai<N>.py`), không được chấm: "
                        + ", ".join(f.name for f in unmatched)
                    )

                all_output_cases, all_structure_cases = [], []
                for bai_num, files in matched.items():
                    tname = mapping.get(bai_num)
                    if not tname:
                        st.warning(f"Không có đề nào được gán cho 'bai{bai_num}' — bỏ qua {len(files)} file.")
                        continue
                    tmpl = load_template(tname)
                    oc, sc = _build_cases_for_template(tmpl, files, bai_label=f"Bài {bai_num}")
                    all_output_cases += oc
                    all_structure_cases += sc

                if not all_output_cases:
                    st.error("Không có bài nào khớp với đề đã chọn để chấm.")
                else:
                    results = _run_grading(all_output_cases, all_structure_cases, parallel, workers)
                    st.session_state["tab3_results"] = results

        if "tab3_results" in st.session_state:
            _render_results(*st.session_state["tab3_results"], key_prefix="tab3")
