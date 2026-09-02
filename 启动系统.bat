@echo off
chcp 65001 >nul
title 轴承故障诊断系统
echo ========================================
echo   轴承故障诊断系统 正在启动...
echo ========================================
echo.

cd /d "%~dp0"

start "" http://127.0.0.1:5000

python bearing_system.py

pause
