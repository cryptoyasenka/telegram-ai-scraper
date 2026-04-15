@echo off
title TG Parser

cd /d "%~dp0"

:: Check Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo Python not found. Install from https://python.org
    pause
    exit /b 1
)

:: Create venv if missing
if not exist ".venv\Scripts\activate.bat" (
    echo Setting up...
    python -m venv .venv
    call .venv\Scripts\activate.bat
    pip install -e .
    echo.
    echo Installed!
) else (
    call .venv\Scripts\activate.bat
)

:: Check if auth is needed
if not exist "data\session.session" (
    echo.
    echo First time setup - Telegram authentication
    echo Go to https://my.telegram.org to get API ID and Hash
    echo.
    tgp auth
    echo.
)

:: Kill any existing server on port 8765
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
)

:: Open browser after 2 seconds
start "" /b cmd /c "timeout /t 2 /nobreak >nul && start http://127.0.0.1:8765"

:: Start server directly (bypass Rich console output)
echo.
echo TG Parser: http://127.0.0.1:8765
echo Close this window to stop.
echo.
.venv\Scripts\python.exe -m uvicorn web.app:app --host 127.0.0.1 --port 8765

echo.
echo Server stopped. Press any key to close.
pause >nul
