@echo off
cd /d "%~dp0"
python -m venv .venv
call .venv\Scripts\activate
pip install -r requirements.txt
echo Cai dat xong! Lan sau chi can bam run.bat de mo app.
pause
