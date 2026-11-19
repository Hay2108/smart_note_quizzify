@echo off
setlocal
chcp 65001 >nul

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%smart_note_backend"
set "PYTHON_EXE="

rem 1) Ưu tiên môi trường ảo (.venv) trong smart_note_backend hoặc thư mục gốc
if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
    goto :python_found
)
if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"
    goto :python_found
)

rem 2) Kiểm tra python trong PATH (loại trừ Windows Store alias chưa cài Python)
where python >nul 2>&1
if %errorlevel% equ 0 (
    python --version >nul 2>&1
    if %errorlevel% equ 0 (
        set "PYTHON_EXE=python"
        goto :python_found
    )
)

rem 3) Fallback đường dẫn Python mặc định trên máy phát triển
if exist "C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\python.exe" (
    set "PYTHON_EXE=C:\Users\admin\AppData\Local\Python\pythoncore-3.14-64\python.exe"
    goto :python_found
)

echo [LỖI] Không tìm thấy trình thông dịch Python!
echo Vui lòng cài đặt Python 3.11+ hoặc tạo môi trường ảo .venv và cài thư viện:
echo   python -m venv .venv
echo   .venv\Scripts\python.exe -m pip install -r requirements.txt
echo.
pause
exit /b 1

:python_found
cd /d "%BACKEND_DIR%"
if %errorlevel% neq 0 (
    echo [LỖI] Không tìm thấy thư mục backend tại: "%BACKEND_DIR%"
    pause
    exit /b 1
)

if not exist "smart_note.db" (
    echo [Khởi tạo] Chưa thấy smart_note.db, đang khởi tạo SQLite bằng database.py...
    "%PYTHON_EXE%" database.py
    if %errorlevel% neq 0 (
        echo.
        echo [LỖI] Khởi tạo SQLite thất bại. Vui lòng kiểm tra cài đặt thư viện trong requirements.txt.
        pause
        exit /b 1
    )
)

if not exist ".env" (
    echo [Lưu ý] Chưa tìm thấy file smart_note_backend\.env.
    echo Hãy sao chép .env.example thành .env và điền GEMINI_API_KEY hoặc OPENAI_API_KEY để sử dụng AI.
    echo.
)

echo ===================================================
echo   Smart Note ^& Quizzify - FastAPI Backend Server
echo   Python  : "%PYTHON_EXE%"
echo   Endpoint: http://127.0.0.1:8000/api/v1/upload
echo   Health  : http://127.0.0.1:8000/health
echo   Swagger : http://127.0.0.1:8000/docs
echo ===================================================

"%PYTHON_EXE%" -m uvicorn app.main:app --reload --reload-include "*.env" --host 127.0.0.1 --port 8000
if %errorlevel% neq 0 (
    echo.
    echo [LỖI] Không thể khởi động hoặc Backend dừng với mã lỗi %errorlevel%.
    echo Hãy kiểm tra lại thư viện đã cài đặt bằng lệnh:
    echo   "%PYTHON_EXE%" -m pip install -r "%ROOT_DIR%requirements.txt"
    echo.
    pause
    exit /b 1
)
