@echo off
setlocal
pushd "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Install dependencies once with: uv sync --locked
    popd
    exit /b 1
)
if not exist ".env" copy /y ".env.example" ".env" >nul
if not exist ".env" (
    echo Could not create .env. Check the folder permissions.
    popd
    exit /b 1
)
".venv\Scripts\python.exe" -m app
set "run_exit_code=%ERRORLEVEL%"
popd
exit /b %run_exit_code%
