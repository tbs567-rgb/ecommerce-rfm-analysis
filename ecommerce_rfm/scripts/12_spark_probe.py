# -*- coding: utf-8 -*-
"""12_spark_probe.py — 探测 Spark 4.3 从 MySQL 读回的表 schema（定 cast 依据）"""
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("probe").config("spark.ui.enabled", "false").getOrCreate()
spark.sparkContext.setLogLevel("ERROR")
URL = "jdbc:mysql://localhost:3306/ecommerce_rfm?useSSL=false&allowPublicKeyRetrieval=true&serverTimezone=UTC"
PROP = {"user": "root", "password": "123456", "driver": "com.mysql.cj.jdbc.Driver"}

t = spark.read.format("jdbc").option("url", URL).options(**PROP).option("dbtable", "transactions_raw").load()
print("== transactions_raw schema (as Spark 4.3 sees it) ==")
print(t.schema.simpleString())
t2 = spark.read.format("jdbc").option("url", URL).options(**PROP).option("dbtable", "transactions_clean").load()
print("== transactions_clean schema ==")
print(t2.schema.simpleString())
t3 = spark.read.format("jdbc").option("url", URL).options(**PROP).option("dbtable", "customer_rfm").load()
print("== customer_rfm schema ==")
print(t3.schema.simpleString())
spark.stop()
