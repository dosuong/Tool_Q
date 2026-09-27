import os
import streamlit as st
from google import genai
from google.genai import types

_CACHED_WORKING_MODEL = None

def ask_ai_tutor(problem: dict, student_code: str, chat_history: list, user_message: str) -> str:
    """Gọi Google Gemini API (bản mới nhất google-genai) để gợi ý học sinh.
    Đã được tối ưu tốc độ phản hồi bằng cách cache model thành công và giới hạn max_output_tokens."""
    global _CACHED_WORKING_MODEL

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    
    if not api_key:
        return "Lỗi hệ thống: Chưa cấu hình GEMINI_API_KEY trong file .env hoặc st.secrets."

    client = genai.Client(api_key=api_key)

    system_prompt = f"""Bạn là một gia sư dạy lập trình Python tận tâm.
Đề bài học sinh đang giải: {problem.get('title')}
Mô tả đề bài: {problem.get('description')}
Code hiện tại của học sinh:
```python
{student_code}
```

Nhiệm vụ của bạn:
1. Giải đáp câu hỏi của học sinh về đoạn code trên.
2. Hướng dẫn học sinh tự tìm ra lỗi sai hoặc hướng giải.
3. TUYỆT ĐỐI KHÔNG viết sẵn code giải hoàn chỉnh hoặc đưa ra đáp án trực tiếp. 
4. Chỉ đưa ra gợi ý ngắn gọn, giải thích khái niệm, hoặc cung cấp đoạn mã giả (pseudo-code) cực kỳ ngắn gọn nếu thật sự cần thiết.
5. Luôn giữ thái độ động viên, tích cực. Xưng hô là "AI" hoặc "Thầy/Cô" và gọi học sinh là "bạn" hoặc "em".
"""

    contents = []
    # Khởi tạo history messages
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
    
    # Message mới nhất của user
    contents.append({"role": "user", "parts": [{"text": user_message}]})

    # Danh sách model dự phòng theo thứ tự ưu tiên
    all_models = ['gemini-2.5-flash', 'gemini-1.5-flash', 'gemini-flash-latest', 'gemini-2.5-pro', 'gemini-1.5-pro', 'gemini-pro']
    if _CACHED_WORKING_MODEL and _CACHED_WORKING_MODEL in all_models:
        # Đưa cached model lên đầu để đạt tốc độ cao nhất, nhưng vẫn giữ các model khác phía sau để dự phòng khi Google quá tải (lỗi 503)
        model_list = [_CACHED_WORKING_MODEL] + [m for m in all_models if m != _CACHED_WORKING_MODEL]
    else:
        model_list = all_models
    
    errors = []
    for model_name in model_list:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.5,
                    max_output_tokens=500,
                ),
            )
            # Lưu lại model thành công để lần sau ưu tiên dùng trước
            _CACHED_WORKING_MODEL = model_name
            return response.text
        except Exception as e:
            errors.append(f"{model_name}: {str(e)}")
            continue
            
    # Nếu tất cả các model đều lỗi
    _CACHED_WORKING_MODEL = None
    return f"Xin lỗi, có lỗi kết nối tới AI.\n\nChi tiết lỗi của từng model:\n" + "\n".join(errors)
