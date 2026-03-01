@echo off
setlocal

REM Build desktop app into dist\LocalEngineeringAssistant\
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
  echo [ERROR] .venv not found. Create venv and install requirements first.
  exit /b 1
)

set PYTHON=.venv\Scripts\python.exe
set SPEC_NAME=LocalEngineeringAssistant

%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 exit /b 1

%PYTHON% -m PyInstaller ^
  --noconfirm ^
  --clean ^
  --windowed ^
  --name %SPEC_NAME% ^
  --paths . ^
  --add-data "examples;examples" ^
  --add-data "docs;docs" ^
  app\main.py

if errorlevel 1 exit /b 1

echo [OK] Build completed: dist\%SPEC_NAME%\
endlocal

