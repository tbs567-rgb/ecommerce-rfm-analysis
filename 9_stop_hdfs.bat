@echo off
rem ===== 9. Stop HDFS (kill NameNode + DataNode by PID) =====
for /f "tokens=1" %%i in ('"%~dp0bigdata\jdk-11.0.32.1+1\bin\jps.exe" ^| findstr /C:"NameNode" /C:"DataNode"') do (
    echo killing PID %%i ...
    taskkill /PID %%i /F >nul 2>&1
)
echo [OK] HDFS stopped.
pause
