@echo off
chcp 936 >nul 2>nul
title Spark 冒烟测试（从 HDFS 读数据计数）
setlocal
set "ROOT=%~dp0"
set "SPARK=%ROOT%bigdata\spark-4.3.0-bin-hadoop3\bin\spark-submit.cmd"
set "PYFILE=%ROOT%ecommerce_rfm\scripts\13_spark_smoketest.py"

if not exist "%SPARK%" (
    echo [错误] 找不到 Spark：%SPARK%
    pause
    exit /b 1
)

set "PYFILE_U=%PYFILE:\=/%"

echo ============================================================
echo   Spark 冒烟测试：读取 HDFS 上的原始 CSV 并统计行数
echo   预期结果：[SMOKE] HDFS CSV rows = 541909 ... PASS
echo   HDFS 没启动会自动拉起，约 1 分钟
echo ============================================================
echo.

rem 先探测 HDFS 的 9000 端口，不通就自动拉起守护进程
netstat -an | findstr ":9000" | findstr "LISTENING" >nul 2>&1
if errorlevel 1 (
    echo [提示] HDFS 未启动，正在自动启动（约 30 秒）...
    start "HDFS-Daemon" /min "%ROOT%python_env\Scripts\python.exe" "%ROOT%ecommerce_rfm\scripts\10_hdfs_daemon.py"
    ping -n 31 127.0.0.1 >nul
)

call "%SPARK%" "file:///%PYFILE_U%"

echo.
echo [DONE] 看到 PASS 说明 HDFS + Spark 链路正常。
pause
