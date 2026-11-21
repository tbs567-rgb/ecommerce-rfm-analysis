@echo off
chcp 936 >nul 2>nul
title 启动 HDFS - NameNode 与 DataNode
set PY=%~dp0python_env\Scripts\python.exe
if not exist "%PY%" set PY=python

echo ============================================================
echo   正在启动 HDFS 分布式文件系统
echo   约需 30 秒，本窗口请勿关闭
echo ============================================================
echo.

start "HDFS-Daemon" /min "%PY%" "%~dp0ecommerce_rfm\scripts\10_hdfs_daemon.py"

echo [1/2] 守护进程已在后台启动，等待就绪...
ping -n 31 127.0.0.1 >nul

echo [2/2] 当前 Java 进程：
"%~dp0bigdata\jdk-11.0.32.1+1\bin\jps.exe"
echo.
echo [OK] 上面能看到 NameNode 和 DataNode 就是启动成功。
echo      后台那个 HDFS-Daemon 窗口（已最小化）不要关：关掉 HDFS 就停，
echo      Spark 读数据会直接报错。
echo      管理界面：http://localhost:9870
echo      停止命令：双击 9_stop_hdfs.bat
pause
