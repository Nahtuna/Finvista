@echo off
title Finvista Dev Server
color 0A

echo ============================================
echo   FINVISTA - Starting all services
echo ============================================
echo.

echo [1/3] Cleaning up old processes on ports 8008 and 5173...
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":8008 " ^| findstr "LISTENING" 2^>nul') do taskkill /PID %%a /F >nul 2>&1
for /f "tokens=5" %%a in ('netstat -ano ^| findstr ":5173 " ^| findstr "LISTENING" 2^>nul') do taskkill /PID %%a /F >nul 2>&1

echo [2/3] Starting Backend API on port 8008...
start "Finvista Backend" cmd /k "cd /d %~dp0 && python run.py api"

timeout /t 2 /nobreak >nul

echo [3/3] Starting Frontend on port 5173...
start "Finvista Frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

echo.
echo ============================================
echo   Backend  ^-^> http://127.0.0.1:8008
echo   Frontend ^-^> http://127.0.0.1:5173
echo ============================================
pause
