@echo off
cd /d "%~dp0"
call .venv\Scripts\activate
streamlit run demo_stress_test.py
