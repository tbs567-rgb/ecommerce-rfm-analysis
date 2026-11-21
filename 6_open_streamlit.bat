@echo off
chcp 65001 >nul
title 电商客户价值分析 - Streamlit 交互网页
cd /d "D:\graduation_project"
echo ============================================================
echo   Streamlit 交互式分析网页（课设第 8 步）
echo   浏览器将自动打开：http://localhost:8501
echo   关闭本窗口即停止服务
echo ============================================================
echo.
"python_env\Scripts\streamlit.exe" run "ecommerce_rfm\app.py" --server.port 8501
pause
