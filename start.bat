@echo off
chcp 65001 >nul
title TG Parser

cd /d "%~dp0"

:: Check Python is available
where python >nul 2>&1
if errorlevel 1 (
    echo [!] Python not found. Install from https://python.org
    echo     Make sure to check "Add to PATH" during installation.
    pause
    exit /b 1
)

:: Create venv if missing
if not exist ".venv\Scripts\activate.bat" (
    echo [*] Creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo [!] Failed to create virtual environment.
        pause
        exit /b 1
    )
    call .venv\Scripts\activate.bat
    echo [*] Installing dependencies (this may take a minute)...
    pip install -e .
    if errorlevel 1 (
        echo [!] Installation failed.
        pause
        exit /b 1
    )
    echo.
    echo [+] Installed successfully!
) else (
    call .venv\Scripts\activate.bat
)

:: Check if auth is needed
if not exist "data\session.session" (
    echo.
    echo ============================================
    echo   First time setup: Telegram authentication
    echo ============================================
    echo.
    echo   1. Go to https://my.telegram.org
    echo   2. Get your API ID and API Hash
    echo   3. Enter them below:
    echo.
    tgp auth
    if errorlevel 1 (
        echo [!] Authentication failed. Try again.
        pause
        exit /b 1
    )
    echo.
)

:: Kill any existing server on port 8765
for /f "tokens=5" %%a in ('netstat -ano ^| findstr :8765 ^| findstr LISTENING') do (
    taskkill /f /pid %%a >nul 2>&1
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
