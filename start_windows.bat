@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  where py >nul 2>&1
  if not errorlevel 1 (
    py -3 -m venv .venv
  ) else (
    python -m venv .venv
  )
  if errorlevel 1 (
    echo Could not create Python virtual environment.
    pause
    exit /b 1
  )
)
if not exist ".venv\.deps_installed" (
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 (
    echo Pip upgrade failed.
    pause
    exit /b 1
  )
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency installation failed. Retry next launch.
    pause
    exit /b 1
  )
  type nul > ".venv\.deps_installed"
)
".venv\Scripts\python.exe" pdf_to_image_pdf.py
if errorlevel 1 echo Application ended with an error.
pause
