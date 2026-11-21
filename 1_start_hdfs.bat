@echo off
rem ===== 1. Start HDFS (NameNode + DataNode) =====
rem Python env is bundled in python_env\ (project-local copy)
set PY=D:\graduation_project\python_env\Scripts\python.exe
if not exist "%PY%" set PY=python
echo [1/2] Starting HDFS NameNode + DataNode (background)...
"%PY%" D:\graduation_project\ecommerce_rfm\scripts\10_hdfs_daemon.py
echo [2/2] Waiting 25s for daemons...
timeout /t 25 /nobreak >nul
D:\graduation_project\bigdata\jdk-11.0.32.1+1\bin\jps.exe
echo.
echo [OK] If you see NameNode and DataNode above, HDFS is running.
echo      Web UI: http://localhost:9870
pause
