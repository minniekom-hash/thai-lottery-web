@echo off
title Thai Lottery Web Server + Cloudflare Public Online Tunnel
echo ========================================================
echo   Starting Thai Government Lottery Web Application...
echo   1. Local Server: http://localhost:5000
echo   2. Creating Public Online URL (Cloudflare Tunnel)...
echo ========================================================
echo.
cd /d "%~dp0"

start /b python app.py
timeout /t 3 /nobreak >nul

echo Starting Public Tunnel...
.\cloudflared.exe tunnel --url http://127.0.0.1:5000
pause
