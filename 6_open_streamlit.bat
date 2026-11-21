@echo off
chcp 936 >nul 2>nul
title 电商客户价值分析 - Streamlit 交互网页
setlocal
set "ROOT=%~dp0"
cd /d "%ROOT%"

set "STREAMLIT_BROWSER_GATHER_USAGE_STATS=false"

if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>nul
    (
        echo [general]
        echo email = ""
    ) > "%USERPROFILE%\.streamlit\credentials.toml" 2>nul
)

echo ============================================================
echo   Streamlit 交互式分析网页（课设第 8 步）
echo   浏览器将自动打开：http://localhost:8501
echo   关闭本窗口即停止服务
echo ============================================================
echo.

"%ROOT%mysql_portable\bin\mysqladmin.exe" -h 127.0.0.1 -P 3307 -uroot -p123456 ping >nul 2>&1
if errorlevel 1 (
    echo [提示] 数据库没启动，页面会显示连接失败。
    echo        请先双击 0_start_mysql.bat，等它显示 OK 再回来。
    echo.
)

"%ROOT%python_env\Scripts\streamlit.exe" run "%ROOT%ecommerce_rfm\app.py" --server.port 8501

pause
