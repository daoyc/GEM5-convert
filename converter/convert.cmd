@echo off
setlocal
if "%~1"=="" (
  echo Usage: convert.cmd GEM5_SOURCE [options]
  exit /b 2
)
where py.exe >nul 2>nul
if not errorlevel 1 (
  py -3 -B "%~dp0convert_model.py" %*
  exit /b
)
if exist "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" (
  "%USERPROFILE%\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe" -B "%~dp0convert_model.py" %*
  exit /b
)
python -B "%~dp0convert_model.py" %*
