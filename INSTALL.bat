@echo off
chcp 65001 >nul
title if-blog-auto 完全インストール

echo.
echo ============================================================
echo   if-blog-auto 完全インストール
echo ============================================================
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo [エラー] Python が見つかりません
    echo Python 3.11以上をインストールしてください
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Run the installer
echo Python を検出しました
echo インストールを開始します...
echo.

python install_all.py

echo.
echo ============================================================
echo   インストール完了
echo ============================================================
echo.
pause
