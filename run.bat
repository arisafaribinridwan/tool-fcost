@echo off
setlocal
cd /d "%~dp0"

if exist ".\ExcelAutoTool.exe" (
    ".\ExcelAutoTool.exe"
    exit /b %errorlevel%
)

if exist ".\.venv\Scripts\python.exe" (
    ".\.venv\Scripts\python.exe" run.py
    exit /b %errorlevel%
)

py -3.14 run.py
if %errorlevel% equ 0 exit /b 0

python run.py
exit /b %errorlevel%
