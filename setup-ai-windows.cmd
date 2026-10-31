@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto install
where py >nul 2>nul
if errorlevel 1 goto python_fallback
py -3.12 --version >nul 2>nul
if errorlevel 1 goto default_python
py -3.12 -m venv .venv
if errorlevel 1 goto failed
goto install
:default_python
py -3 -m venv .venv
if errorlevel 1 goto failed
goto install
:python_fallback
python -m venv .venv
if errorlevel 1 goto failed
:install
echo Installing CPU AI dependencies. This may take several minutes.
".venv\Scripts\python.exe" -m pip install torch==2.5.1 torchvision==0.20.1 --index-url https://download.pytorch.org/whl/cpu
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m pip install -r requirements-ai.txt
if errorlevel 1 goto failed
".venv\Scripts\python.exe" -m app.setup_ai
if errorlevel 1 goto failed
echo AI installed. Model download sends no private media.
echo Run start-windows.cmd to open QTC AI VIDEO EDITOR.
pause
exit /b 0
:failed
echo Setup failed. Use Python 3.12 x64 and check your Internet connection.
pause
exit /b 1
