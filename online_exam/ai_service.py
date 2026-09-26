import os
import streamlit as st
from google import genai
from google.genai import types

def ask_ai_tutor(problem: dict, student_code: str, chat_history: list, user_message: str) -> str:
    """Gọi Google Gemini API (bản mới nhất google-genai) để gợi ý học sinh."""
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
4. Chỉ đưa ra gợi ý, giải thích khái niệm, hoặc cung cấp đoạn mã giả (pseudo-code) cực kỳ ngắn gọn nếu thật sự cần thiết.
5. Luôn giữ thái độ động viên, tích cực. Xưng hô là "AI" hoặc "Thầy/Cô" và gọi học sinh là "bạn" hoặc "em".
"""

    contents = []
    # Khởi tạo history messages
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        contents.append(
            types.Content(role=role, parts=[types.Part.from_text(text=msg["content"])])
        )
    
    # Message mới nhất của user
    contents.append(
        types.Content(role="user", parts=[types.Part.from_text(text=user_message)])
    )

    try:
        # Sử dụng model mới nhất (gemini-2.0-flash hoặc gemini-1.5-flash)
        # Google đã deprecate các model cũ ở v1beta
        response = client.models.generate_content(
            model='gemini-2.5-flash', # Try latest 2.5 or fallback below
            contents=contents,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.7,
            ),
        )
        return response.text
    except Exception:
        try:
            # Fallback 1.5 flash
            response = client.models.generate_content(
                model='gemini-1.5-flash',
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.7,
                ),
            )
            return response.text
        except Exception as e2:
            return f"Xin lỗi, có lỗi kết nối tới AI: {str(e2)}"
