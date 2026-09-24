"""Trang GV: Kết quả bài kiểm tra online — bảng HS x điểm từng câu + tổng, xem chi tiết
từng lần nộp CHÍNH THỨC (không xem được nháp/chạy thử của HS — quyết định đã chốt), xuất
CSV, tải file/ZIP bài làm.

Danh sách lớp/bài ở trang này CỐ Ý bao gồm cả lớp/bài đã lưu trữ (khác trang "Tạo bài kiểm
tra online", nơi bài lưu trữ bị ẩn khỏi danh sách sửa) — GV vẫn cần tra cứu lại dữ liệu cũ.
"""
import io
import zipfile

import pandas as pd
import streamlit as st

from online_exam import service


def _build_results_zip(rows: list[dict]) -> bytes | None:
    buf = io.BytesIO()
    has_any = False
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for r in rows:
            safe_student = f"{r['student_name']}_{r['student_code']}".replace(" ", "_").replace("/", "_")
            for pp in r["per_problem"]:
                if pp["best_submission_id"] is None:
                    continue
                submission, _ = service.get_submission_with_results(pp["best_submission_id"])
                if submission is None:
                    continue
                safe_title = (pp["title"] or f"cau_{pp['problem_id']}").replace(" ", "_").replace("/", "_")
                zf.writestr(f"{safe_student}/{safe_title}.py", submission.code_text)
                has_any = True
    return buf.getvalue() if has_any else None


def _build_detailed_excel_bytes(rows: list[dict]) -> bytes:
    data = []
    for r in rows:
        student_name = r["student_name"]
        username = r["student_code"]
        for pp in r["per_problem"]:
            row_dict = {
                "Học sinh": student_name,
                "Tài khoản": username,
                "Bài": pp["title"],
                "Điểm": pp["score"] if pp["score"] is not None else 0.0,
                "Lượt nộp": pp["attempts_used"],
                "Trạng thái": "Chưa nộp",
                "Lỗi tại Test Case": "",
                "Chi tiết lỗi": ""
            }
            sub_id = pp["best_submission_id"]
            if sub_id:
                submission, results = service.get_submission_with_results(sub_id)
                if submission.passed_ratio == 1.0:
                    row_dict["Trạng thái"] = "Hoàn thành"
                else:
                    row_dict["Trạng thái"] = "Có lỗi"
                    # Tìm test case lỗi đầu tiên
                    for idx, res in enumerate(results, start=1):
                        if not res.passed:
                            row_dict["Lỗi tại Test Case"] = str(idx)
                            row_dict["Chi tiết lỗi"] = res.error_message or "Sai kết quả đầu ra (không khớp mong đợi)"
                            break
            data.append(row_dict)
            
    df_detail = pd.DataFrame(data)
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df_detail.to_excel(writer, index=False, sheet_name="ChiTietLoi")
    return buf.getvalue()

def page_exam_results(teacher_id: int):
    st.subheader("Kết quả bài kiểm tra online", icon=":material/leaderboard:", divider="gray")

    classes = service.list_classes(teacher_id, include_archived=True)
    if not classes:
        st.info("Chưa có lớp nào — hãy tạo lớp và bài kiểm tra trước.", icon=":material/info:")
        return
    class_names = {c.id: c.name + (" (đã lưu trữ)" if c.is_archived else "") for c in classes}
    class_id = st.selectbox(
        "Lớp", options=list(class_names.keys()), format_func=lambda cid: class_names[cid], key="oer_class_choice",
    )

    exams = service.list_exams(teacher_id, class_id=class_id, include_archived=True)
    if not exams:
        st.info("Lớp này chưa có bài kiểm tra nào.", icon=":material/info:")
        return
    exam_names = {e.id: e.title + (" (đã lưu trữ)" if e.is_archived else "") for e in exams}
    exam_id = st.selectbox(
        "Bài kiểm tra", options=list(exam_names.keys()), format_func=lambda eid: exam_names[eid],
        key="oer_exam_choice",
    )

    data = service.get_exam_results_table(exam_id, teacher_id)
    if data is None:
        st.error("Không có quyền xem bài này.")
        return

    rows = data["rows"]
    if not rows:
        st.info("Chưa có học sinh nào tham gia bài kiểm tra này.", icon=":material/info:")
        return

    table_rows = []
    for r in rows:
        row = {"Học sinh": r["student_name"], "Tài khoản": r["student_code"]}
        
        # Tính số câu đúng tuyệt đối
        num_correct = 0
        total_problems = len(r["per_problem"])
        for pp in r["per_problem"]:
            if pp["score"] is not None and abs(pp["score"] - pp["max_score"]) < 1e-6:
                num_correct += 1
                
        row["Số câu đúng"] = f"{num_correct}/{total_problems}"
        row["Tổng điểm"] = round(r['total_score'], 2)  # Lưu số để Excel hiểu
        
        for pp in r["per_problem"]:
            row[pp["title"]] = round(pp['score'], 2) if pp["score"] is not None else 0.0
            
        table_rows.append(row)
        
    df = pd.DataFrame(table_rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    c1, c2, c3 = st.columns(3)
    
    # 1. Bảng điểm tổng quát (Excel)
    buf_summary = io.BytesIO()
    with pd.ExcelWriter(buf_summary, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="TongHop")
    c1.download_button(
        "Tải kết quả tổng quát (Excel)", data=buf_summary.getvalue(), file_name="bang_diem_tong_quat.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/download:", use_container_width=True,
    )
    
    # 2. Chi tiết lỗi (Excel)
    excel_bytes = _build_detailed_excel_bytes(rows)
    c2.download_button(
        "Tải kết quả chi tiết lỗi (Excel)", data=excel_bytes, file_name="chi_tiet_loi_tung_cau.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        icon=":material/bug_report:", use_container_width=True,
    )
    
    # 3. ZIP bài làm
    zip_bytes = _build_results_zip(rows)
    if zip_bytes:
        c3.download_button(
            "Tải bài làm (ZIP)", data=zip_bytes, file_name="bai_lam_hoc_sinh.zip",
            mime="application/zip", icon=":material/folder_zip:", use_container_width=True,
        )

    st.subheader("Chi tiết theo học sinh", icon=":material/person_search:", divider="gray")
    for r in rows:
        header = f"{r['student_name']} ({r['student_code']}) — Tổng: {r['total_score']:.2f}"
        with st.expander(header, icon=":material/person:"):
            for pp in r["per_problem"]:
                score_txt = f"{pp['score']:.2f}" if pp["score"] is not None else "—"
                st.markdown(
                    f"**{pp['title']}** — điểm: {score_txt}/{pp['max_score']:.2f} — "
                    f"số lần nộp: {pp['attempts_used']}"
                )
                submissions = service.list_official_submissions(r["enrollment_id"], pp["problem_id"])
                if not submissions:
                    st.caption("Chưa nộp lần nào.")
                    st.divider()
                    continue

                sub_options = {
                    s.id: f"Lần {s.attempt_number} — {float(s.final_score):.2f} điểm"
                          + (" ⭐ (tính điểm)" if s.id == pp["best_submission_id"] else "")
                    for s in submissions
                }
                sel_key = f"oer_sub_sel_{r['enrollment_id']}_{pp['problem_id']}"
                chosen_id = st.selectbox(
                    "Xem lần nộp", options=list(sub_options.keys()), format_func=lambda sid: sub_options[sid],
                    key=sel_key,
                )
                chosen = next(s for s in submissions if s.id == chosen_id)
                st.code(chosen.code_text, language="python")
                st.download_button(
                    "Tải file .py", data=chosen.code_text.encode("utf-8"),
                    file_name=chosen.original_filename or f"{pp['title']}_lan{chosen.attempt_number}.py".replace(" ", "_"),
                    mime="text/x-python", key=f"oer_dl_{chosen.id}",
                )
                st.divider()
