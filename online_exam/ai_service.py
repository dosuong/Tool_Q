import os
from openai import OpenAI

def get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        # Check streamlit secrets as a fallback if not in normal env vars
        import streamlit as st
        if "OPENAI_API_KEY" in st.secrets:
            api_key = st.secrets["OPENAI_API_KEY"]
    
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

def ask_ai_tutor(problem: dict, student_code: str, chat_history: list, user_message: str) -> str:
    """Gọi OpenAI API để gợi ý học sinh, ép AI đóng vai gia sư không spoiler đáp án."""
    client = get_openai_client()
    if not client:
        return "Lỗi hệ thống: Chưa cấu hình OPENAI_API_KEY trong file .env hoặc st.secrets."

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

    messages = [{"role": "system", "content": system_prompt}]
    
    # Gắn thêm lịch sử chat
    for msg in chat_history:
        messages.append({"role": msg["role"], "content": msg["content"]})
        
    messages.append({"role": "user", "content": user_message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Dùng gpt-4o-mini tối ưu chi phí và tốc độ
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Xin lỗi, có lỗi kết nối tới AI: {str(e)}"
