@echo off
cd /d %~dp0
if not exist .venv py -m venv .venv
call .venv\Scripts\activate.bat
python -m pip install -r backend\requirements.txt
python -m uvicorn backend.main:app --reload
