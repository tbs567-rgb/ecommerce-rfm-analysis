# -*- coding: utf-8 -*-
"""冒烟测试：独立 Spark 4.3.0 (spark-submit) 从 HDFS 读原始数据计数"""
from pyspark.sql import SparkSession

spark = (SparkSession.builder
         .appName("bigdata-smoketest")
         .master("local[2]")
         .getOrCreate())

df = spark.read.csv("hdfs://localhost:9000/ecommerce/raw/online_retail_raw.csv",
                    header=True, inferSchema=False)
n = df.count()
print(f"[SMOKE] HDFS CSV rows = {n}  (expect 541909)")
print("[SMOKE] " + ("PASS" if n == 541909 else "FAIL"))
spark.stop()
