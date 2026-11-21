@echo off
chcp 936 >nul 2>nul
title Spark 全链路 ETL（清洗 → 统计 → RFM → MySQL）
setlocal
set "ROOT=%~dp0"
set "PYTHONIOENCODING=gbk:replace"
set "PY=%ROOT%python_env\Scripts\python.exe"
if not exist "%PY%" set "PY=python"

echo ============================================================
echo   全链路 ETL：HDFS 原始数据 → Spark 清洗/聚合/RFM → MySQL
echo   预计 5-15 分钟，请勿关闭窗口
echo   前提：MySQL 要先开（0_start_mysql.bat）；HDFS 没开脚本会自己拉起来
echo ============================================================
echo.

"%PY%" "%ROOT%ecommerce_rfm\scripts\11_spark_submit.py"
set "RC=%ERRORLEVEL%"

echo.
if not "%RC%"=="0" (
    echo [失败] 退出码 %RC%，本次没有跑完。
    echo        完整日志：%ROOT%bigdata\_etl_last.log
    echo        最常见原因：MySQL 或 HDFS 没启动，或者后台窗口被关掉了。
    echo        重来一次：先跑 0_start_mysql.bat，再跑 1_start_hdfs.bat 等它显示 OK。
) else (
    echo [DONE] 上面 7 条对账都显示 OK 即为成功。
    echo        完整日志：%ROOT%bigdata\_etl_last.log
    echo        末尾如果出现 Failed to delete 某个 .jar 的 WARN，
    echo        是 Windows 临时文件被占用，不影响结果。
)
pause
