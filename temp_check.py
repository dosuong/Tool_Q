import codecs

path = r'e:\a_Personal_Project\Tool_Q\online_exam\service.py'
with codecs.open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Try to find the position of the bad unicode character
for i, line in enumerate(content.split('\n')):
    if '\u2222' in line or '?' in line:
        pass # we'll just check if it fails compilation

import py_compile
try:
    py_compile.compile(path, doraise=True)
    print("Compile OK")
except py_compile.PyCompileError as e:
    print(f"Error compiling: {e}")
