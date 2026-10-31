@echo off
setlocal
cd /d "%~dp0"
where ffmpeg >nul 2>nul
if errorlevel 1 goto missing_ffmpeg
where ffprobe >nul 2>nul
if errorlevel 1 goto missing_ffmpeg
if exist ".venv\Scripts\python.exe" goto dependencies
where py >nul 2>nul
if errorlevel 1 goto use_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto dependencies
:use_python
python -m venv .venv
if errorlevel 1 goto failed
:dependencies
".venv\Scripts\python.exe" -c "import fastapi,uvicorn,numpy,multipart" >nul 2>nul
if not errorlevel 1 goto launch
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failed
:launch
echo Open http://localhost:8000 in your browser.
echo Keep this window open. Press Ctrl+C to stop.
".venv\Scripts\python.exe" -m uvicorn app.main:app --host 0.0.0.0 --port 8000
if errorlevel 1 goto failed
exit /b 0
:missing_ffmpeg
echo Install FFmpeg and ensure both ffmpeg and ffprobe are on PATH.
echo See WINDOWS.md for instructions.
pause
exit /b 1
:failed
echo Startup failed. Check Python 3.10+, dependencies, and whether port 8000 is busy.
pause
exit /b 1
