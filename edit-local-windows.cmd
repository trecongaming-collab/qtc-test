@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" goto setup
where ffmpeg >nul 2>nul
if errorlevel 1 goto missing_ffmpeg
where ffprobe >nul 2>nul
if errorlevel 1 goto missing_ffmpeg
".venv\Scripts\python.exe" -m app.desktop
if errorlevel 1 pause
exit /b
:setup
echo Run setup-ai-windows.cmd first.
pause
exit /b 1
:missing_ffmpeg
echo Install FFmpeg and ensure ffmpeg and ffprobe are on PATH.
pause
exit /b 1
