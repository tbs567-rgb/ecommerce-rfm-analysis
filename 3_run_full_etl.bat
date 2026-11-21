@echo off
rem ===== 3. Run full Spark ETL (clean -> stats -> RFM -> MySQL, 10-15 min) =====
rem Requires HDFS running (1_start_hdfs.bat) and MySQL running (root/123456)
set PY=D:\graduation_project\python_env\Scripts\python.exe
if not exist "%PY%" set PY=python
echo [Spark] submitting full ETL (10-15 min, do not close)...
"%PY%" D:\graduation_project\ecommerce_rfm\scripts\11_spark_submit.py
echo.
echo [DONE] Check reconciliation lines: all "OK" means success.
pause
