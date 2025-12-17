@echo off
echo Cleaning up orphaned dev server processes...

REM Kill any node processes running on port 1420
for /f "tokens=5" %%a in ('netstat -aon ^| findstr :1420 ^| findstr LISTENING') do (
    echo Killing process %%a on port 1420...
    taskkill /F /PID %%a 2>nul
)

REM Kill any Vite dev server processes
for /f "tokens=2" %%a in ('tasklist ^| findstr "vite"') do (
    echo Killing Vite process %%a...
    taskkill /F /PID %%a 2>nul
)

REM Kill any orphaned Tauri processes
for /f "tokens=2" %%a in ('tasklist ^| findstr "qubes-gui"') do (
    echo Killing qubes-gui process %%a...
    taskkill /F /PID %%a 2>nul
)

echo Cleanup complete!
timeout /t 2 >nul
