@echo off
chcp 65001 >nul
title TG Parser

cd /d "%~dp0"

:: Create venv if missing
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -e .
    echo [+] Installed!
) else (
    call .venv\Scripts\activate.bat
)

:: Open browser after 2 seconds
start "" /b cmd /c "timeout /t 2 /nobreak >nul && rundll32 url.dll,FileProtocolHandler http://127.0.0.1:8765"

:: Start server
echo.
echo [*] TG Parser: http://127.0.0.1:8765
echo     Close this window to stop the server.
echo.
tgp serve

:: If server crashes, show error
echo.
echo [!] Server stopped. Press any key to close.
pause >nul
