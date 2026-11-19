@echo off
setlocal
chcp 65001 >nul

set "ROOT_DIR=%~dp0"
set "BACKEND_DIR=%ROOT_DIR%smart_note_backend"
set "PYTHON_EXE="

rem 1) Ưu tiên môi trường ảo (.venv) ở thư mục gốc hoặc smart_note_backend
if exist "%ROOT_DIR%.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%ROOT_DIR%.venv\Scripts\python.exe"
    goto :python_found
)
if exist "%BACKEND_DIR%\.venv\Scripts\python.exe" (
    set "PYTHON_EXE=%BACKEND_DIR%\.venv\Scripts\python.exe"
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
cd /d "%ROOT_DIR%"
if %errorlevel% neq 0 (
    echo [LỖI] Không thể chuyển vào thư mục gốc: "%ROOT_DIR%"
    pause
    exit /b 1
)

echo ===================================================
echo   Smart Note ^& Quizzify - Streamlit Frontend UI
echo   Python : "%PYTHON_EXE%"
echo   URL    : http://localhost:8501
echo ===================================================

"%PYTHON_EXE%" -m streamlit run app.py
if %errorlevel% neq 0 (
    echo.
    echo [LỖI] Không thể khởi động hoặc Frontend dừng với mã lỗi %errorlevel%.
    echo Hãy kiểm tra lại thư viện đã cài đặt bằng lệnh:
    echo   "%PYTHON_EXE%" -m pip install -r "%ROOT_DIR%requirements.txt"
    echo.
    pause
    exit /b 1
)
