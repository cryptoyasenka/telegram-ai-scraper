@echo off
chcp 65001 >nul
title TG Parser

:: Check if venv exists, create if not
if not exist ".venv\Scripts\python.exe" (
    echo [*] First run — setting up...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -e . >nul 2>&1
    echo [+] Installed!
    echo.
    echo    Next step: run "tgp auth" to connect your Telegram account.
    echo    Then restart this script.
    echo.
    pause
    exit /b
)

call .venv\Scripts\activate.bat

:: Open browser after 2 seconds
start "" cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8765"

:: Start server
echo [*] TG Parser → http://127.0.0.1:8765
echo     Press Ctrl+C to stop
echo.
tgp serve
