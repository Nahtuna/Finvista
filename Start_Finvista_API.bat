@echo off
title Finvista API Launcher
echo ==========================================================
echo        🚀 FINVISTA QUANT PRO - REST API GATEWAY 🚀
echo ==========================================================
echo Dang khoi tao phan he may chu tai chinh (Chi chay API)...

rem Strictly use the global system Python which is fully loaded with libraries
set PYTHON_CMD=python
echo [System] Su dung Python he thong (Python 3.12.6 Global).

echo [System] Dang khoi dong FastAPI Backend tren cong 8008...
start "Finvista Quant Backend" "%PYTHON_CMD%" run.py api

echo ==========================================================
echo * FastAPI API Gateway: http://127.0.0.1:8008
echo * Interactive Swagger Docs: http://127.0.0.1:8008/docs
echo ==========================================================
pause
