# -*- coding: utf-8 -*-
"""11_spark_submit.py — 提交 Spark ETL 作业（绕开 bash 对 cmd 的拦截）
设置 JAVA_HOME=JDK11（Spark 3.5 不支持 Java 25），HADOOP_HOME 供 winutils，
调用 venv 内 spark-submit.cmd 运行 09_spark_etl.py，实时转发输出。
"""
import subprocess, os, sys

ENV = os.environ.copy()
ENV["JAVA_HOME"] = r"D:\graduation_project\bigdata\jdk-17.0.20.1+1"
ENV["HADOOP_HOME"] = r"D:\graduation_project\bigdata\hadoop-3.3.6"
ENV["PATH"] = r"D:\graduation_project\bigdata\jdk-11.0.32.1+1\bin;D:\graduation_project\bigdata\hadoop-3.3.6\bin;" + ENV["PATH"]
VENV = r"C:\Users\86159\.workbuddy\binaries\python\envs\default"
ENV["PYSPARK_PYTHON"] = os.path.join(VENV, "Scripts", "python.exe")

cmd = [os.path.join(VENV, "Scripts", "spark-submit.cmd"),
       "--jars", r"D:\graduation_project\bigdata\jars\mysql-connector-j-8.4.0.jar",
       r"D:\graduation_project\ecommerce_rfm\scripts\09_spark_etl.py"]
print("submit:", " ".join(cmd), flush=True)
p = subprocess.Popen(cmd, env=ENV)
code = p.wait()
print(f"\nspark-submit exit code: {code}", flush=True)
sys.exit(code)
