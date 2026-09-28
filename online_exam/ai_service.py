import os
import time
import streamlit as st
from google import genai
from google.genai import types

_CACHED_WORKING_MODEL = None

def ask_ai_tutor(problem: dict, student_code: str, chat_history: list, user_message: str, trial_result: dict | None = None) -> str:
    """Gọi Google Gemini API (bản mới nhất google-genai) để gợi ý học sinh.
    Đã bổ sung đọc kết quả/lỗi chạy thử gần nhất (trial_result) để gia sư AI biết chính xác lỗi sai."""
    global _CACHED_WORKING_MODEL

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    
    if not api_key:
        return "Lỗi hệ thống: Chưa cấu hình GEMINI_API_KEY trong file .env hoặc st.secrets."

    client = genai.Client(api_key=api_key)

    trial_info = ""
    if trial_result:
        trial_info = "\n[KẾT QUẢ CHẠY THỬ GẦN NHẤT CỦA HỌC SINH]\n"
        if not trial_result.get("structure_ok"):
            trial_info += f"- Lỗi vi phạm cấu trúc: {'; '.join(trial_result.get('violations', []))}\n"
        else:
            trial_info += f"- Tỉ lệ test mẫu đạt: {trial_result.get('pass_ratio', 0) * 100:.0f}%\n"
            for i, r in enumerate(trial_result.get("results", []), start=1):
                status = "ĐẠT" if r.get("passed") else "CHƯA ĐẠT"
                actual = r.get("actual_output") or ""
                err = r.get("error_message") or ""
                trial_info += f"  + Test mẫu {i}: {status} | Thực tế in ra: '{actual}' | Lỗi hệ thống: '{err}'\n"

    system_prompt = f"""Bạn là một gia sư dạy lập trình Python tận tâm.
Đề bài học sinh đang giải: {problem.get('title')}
Mô tả đề bài: {problem.get('description')}
Code hiện tại của học sinh:
```python
{student_code}
```
{trial_info}

HƯỚNG DẪN TRẢ LỜI (bắt buộc tuân thủ):
1. Mỗi câu trả lời PHẢI HOÀN CHỈNH, không bao giờ bỏ lửng hoặc cắt ngang giữa chừng.
2. Trả lời ngắn gọn, tập trung vào đúng 1 vấn đề học sinh hỏi. Tối đa 5-8 câu mỗi lần.
3. Nếu cần giải thích nhiều bước, hãy chia nhỏ từng phần, hỏi học sinh xem hiểu chưa trước khi tiếp.
4. TUYỆT ĐỐI KHÔNG viết code giải hoàn chỉnh hoặc đưa ra đáp án trực tiếp.
5. Dùng pseudo-code ngắn (2-3 dòng) chỉ khi thật sự cần thiết.
6. Xưng hô là "Thầy/Cô" và gọi học sinh là "em".
7. Luôn giữ thái độ động viên, tích cực.
8. Nếu có [KẾT QUẢ CHẠY THỬ], hãy dùng đó để chỉ ra nguyên nhân cụ thể tại sao bài chưa đạt.
"""

    contents = []
    # Khởi tạo history messages (Lọc bỏ các tin nhắn rỗng hoặc "None" để không làm lỗi Google API)
    for msg in chat_history:
        role = "model" if msg.get("role") == "assistant" else "user"
        text_content = str(msg.get("content") or "").strip()
        if text_content and text_content != "None":
            contents.append({"role": role, "parts": [{"text": text_content}]})
    
    # Message mới nhất của user
    clean_user_message = str(user_message or "").strip()
    if clean_user_message:
        contents.append({"role": "user", "parts": [{"text": clean_user_message}]})

    # Danh sách các model đang hoạt động theo hướng dẫn mới nhất từ Google API
    all_models = [
        'gemini-3.8-flash',
        'gemini-3.5-flash',
        'gemini-flash-latest',
        'gemini-3.1-pro-preview',
    ]
    if _CACHED_WORKING_MODEL and _CACHED_WORKING_MODEL in all_models:
        model_list = [_CACHED_WORKING_MODEL] + [m for m in all_models if m != _CACHED_WORKING_MODEL]
    else:
        model_list = all_models
    
    errors = []
    for model_name in model_list:
        for attempt in range(2):
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=types.GenerateContentConfig(
                        system_instruction=system_prompt,
                        temperature=0.4,
                        max_output_tokens=1500,   # tăng từ 500 → 1500 để tránh cắt ngang
                    ),
                )
                # Lưu lại model thành công để lần sau ưu tiên dùng trước
                _CACHED_WORKING_MODEL = model_name
                text = response.text or ""
                # Bỏ dấu ** thừa ở cuối (thường do Markdown bị cắt ngang)
                text = text.rstrip()
                if text.endswith("**") and text.count("**") % 2 == 1:
                    text = text[:-2].rstrip()
                return text
            except Exception as e:
                err_str = str(e)
                # Nếu gặp lỗi 503 (quá tải tạm thời), thử lại sau 0.3s trước khi chuyển model
                if "503" in err_str and attempt == 0:
                    time.sleep(0.3)
                    continue
                errors.append(f"{model_name}: {err_str}")
                break
            
    # Nếu tất cả các model đều lỗi
    _CACHED_WORKING_MODEL = None
    return f"Xin lỗi, có lỗi kết nối tới AI.\n\nChi tiết lỗi của từng model:\n" + "\n".join(errors)
