import sys
import codecs

path = r'e:\a_Personal_Project\Tool_Q\online_exam\service.py'

# 1. Read file and handle mixed encoding if any
try:
    with codecs.open(path, 'r', encoding='utf-8') as f:
        content = f.read()
except UnicodeDecodeError:
    with codecs.open(path, 'r', encoding='utf-16le') as f:
        content = f.read()
except Exception:
    with codecs.open(path, 'r', encoding='latin-1') as f:
        content = f.read()

# 2. Fix the corrupted part. 
if 'def bulk_create_students' in content:
    content = content[:content.find('def bulk_create_students')]

# 3. Add the clean bulk_create_students with correct UTF-8 encoding
new_func = '''
def bulk_create_students(teacher_id: int, class_id: int, students_data: list[dict]) -> list[dict]:
    \"\"\"Bulk create students with parallel bcrypt hashing and a single DB transaction to minimize latency.\"\"\"
    room = get_class(class_id, teacher_id)
    if room is None:
        raise ValueError("Không tìm thấy lớp hoặc không có quyền.")
        
    import concurrent.futures
    for d in students_data:
        d["raw_password"] = student_auth.generate_password()
        
    def _hash(pwd):
        return auth.hash_password(pwd)
        
    with concurrent.futures.ThreadPoolExecutor() as executor:
        hashes = list(executor.map(_hash, [d["raw_password"] for d in students_data]))
        
    for d, h in zip(students_data, hashes):
        d["password_hash"] = h
        
    results = []
    with get_session() as session:
        custom_usernames = [d["custom_username"] for d in students_data if d.get("custom_username")]
        existing = set()
        if custom_usernames:
            existing_rows = session.execute(
                select(Student.username).where(Student.username.in_(custom_usernames))
            ).scalars().all()
            existing = set(existing_rows)
            
        import random, string
        for data in students_data:
            custom_user = data.get("custom_username")
            if custom_user:
                if custom_user in existing:
                    suffix = "".join(random.choices(string.ascii_lowercase + string.digits, k=3))
                    username = f"{custom_user}{suffix}"
                    existing.add(username)
                else:
                    username = custom_user
                    existing.add(username)
            else:
                username = student_auth.generate_username(session)
                
            student = Student(
                class_id=class_id, username=username,
                password_hash=data["password_hash"], full_name=data["full_name"].strip(),
            )
            session.add(student)
            results.append({"student": student, "raw_password": data["raw_password"]})
            
        session.commit()
        for r in results:
            session.refresh(r["student"])
            
    _clear_read_caches()
    return results
'''

if not content.endswith('\n'):
    content += '\n'

with codecs.open(path, 'w', encoding='utf-8') as f:
    f.write(content + new_func)

print('Rewrite complete.')
