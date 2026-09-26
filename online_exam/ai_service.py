import os
import google.generativeai as genai
import streamlit as st

def ask_ai_tutor(problem: dict, student_code: str, chat_history: list, user_message: str) -> str:
    """Gọi Google Gemini API để gợi ý học sinh, ép AI đóng vai gia sư không spoiler đáp án."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        if "GEMINI_API_KEY" in st.secrets:
            api_key = st.secrets["GEMINI_API_KEY"]
    
    if not api_key:
        return "Lỗi hệ thống: Chưa cấu hình GEMINI_API_KEY trong file .env hoặc st.secrets."

    genai.configure(api_key=api_key)

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

    model = genai.GenerativeModel(
        model_name="gemini-1.5-flash",
        system_instruction=system_prompt
    )
    
    # Chuyển đổi lịch sử chat sang định dạng của Gemini (OpenAI dùng 'assistant', Gemini dùng 'model')
    history = []
    for msg in chat_history:
        role = "model" if msg["role"] == "assistant" else "user"
        history.append({"role": role, "parts": [msg["content"]]})
        
    chat = model.start_chat(history=history)

    try:
        response = chat.send_message(user_message)
        return response.text
    except Exception as e:
        return f"Xin lỗi, có lỗi kết nối tới AI: {str(e)}"
