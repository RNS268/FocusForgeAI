@echo off
setlocal
python -m pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm --name StudyGuardAI --windowed --add-data "config;config" app.py
echo Build complete: dist\StudyGuardAI\
