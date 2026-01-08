@echo off
chcp 65001 >nul
title Gemini Video Generator

echo.
echo ============================================================
echo   Gemini Video Generator
echo ============================================================
echo.

REM Check Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv" (
    echo Installing dependencies...
    pip install -r requirements.txt -q
)

REM Check for .env
if not exist "../.env" (
    echo [WARNING] .env file not found
    echo Please create .env with GOOGLE_AI_API_KEY=your_key
    echo.
)

REM Run test
echo Running environment check...
python test_workflow.py --check-only
if errorlevel 1 (
    echo.
    echo [ERROR] Environment check failed
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   Environment OK - Ready to generate videos!
echo ============================================================
echo.
echo Usage:
echo   python main.py --input "Your blog text..."
echo   python main.py --file article.txt
echo   python main.py --url "https://example.com/article"
echo.
echo Options:
echo   --scenes N    : Number of scenes (default: 6)
echo   --voice TYPE  : Voice type (default, calm, warm, etc.)
echo   --output NAME : Output filename
echo.

pause
