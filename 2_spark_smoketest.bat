@echo off
rem ===== 2. Spark smoke test (read HDFS, count rows) =====
rem Requires HDFS running first (run 1_start_hdfs.bat)
echo [Spark] submitting smoke test job (about 1-2 min)...
D:\graduation_project\bigdata\spark-4.3.0-bin-hadoop3\bin\spark-submit.cmd file:///D:/graduation_project/ecommerce_rfm/scripts/13_spark_smoketest.py
echo.
echo [DONE] Look for: [SMOKE] HDFS CSV rows = 541909 ... PASS
pause
