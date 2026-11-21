# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""09_spark_etl.py — Spark 分布式链路（替换/验证 Pandas 清洗-统计-RFM）
链路：HDFS 原始 CSV → PySpark 清洗（口径同 03_clean.py）→ 写 MySQL
      → PySpark 统计（月度趋势/Top商品/客户分布/集中度/复购）→ customer_rfm（口径同 05_rfm.py）
末尾与 Pandas 版基线逐项对账。
运行：python 11_spark_submit.py
      （内部执行 spark-submit --jars <包根>/bigdata/jars/mysql-connector-j-8.4.0.jar 09_spark_etl.py）
"""
import sys, json
from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import (StructType, StructField, StringType, IntegerType,
                               DoubleType, TimestampType)

MYSQL_PORT = int(_os.environ.get("MYSQL_PORT", "3307"))
MYSQL_URL = ("jdbc:mysql://localhost:%d/ecommerce_rfm?useSSL=false"
             "&allowPublicKeyRetrieval=true&rewriteBatchedStatements=true"
             "&useUnicode=true&characterEncoding=utf8&serverTimezone=UTC" % MYSQL_PORT)
MYSQL_PROP = {"user": "root", "password": "123456", "driver": "com.mysql.cj.jdbc.Driver"}
SPECIAL = ["POST", "DOT", "M", "C2", "D", "S", "BANK CHARGES", "AMAZONFEE", "CRUK", "B", "ADJUST", "ADJUST2", "TEST001", "TEST002"]

spark = (SparkSession.builder.appName("ecommerce_rfm_etl")
         .config("spark.sql.shuffle.partitions", "8")
         .config("spark.driver.memory", "2g")
         .getOrCreate())
spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("InvoiceNo", StringType(), True),
    StructField("StockCode", StringType(), True),
    StructField("Description", StringType(), True),
    StructField("Quantity", IntegerType(), True),
    StructField("InvoiceDate", TimestampType(), True),
    StructField("UnitPrice", DoubleType(), True),
    StructField("CustomerID", IntegerType(), True),
    StructField("Country", StringType(), True),
])

# ===== 1. 读 HDFS 原始数据 =====
raw = (spark.read.csv("hdfs://localhost:9000/ecommerce/raw/online_retail_raw.csv",
                      schema=schema, header=True, timestampFormat="yyyy-MM-dd HH:mm:ss"))
n_raw = raw.count()
print(f"[Spark] raw rows = {n_raw}")
assert n_raw == 541909, f"raw 行数 {n_raw} != 541909"

# ===== 2. 清洗（口径同 03_clean.py）=====
df = (raw
      .withColumn("has_customer", F.col("CustomerID").isNotNull().cast("int"))
      .withColumn("is_cancelled", F.col("InvoiceNo").startswith("C").cast("int"))
      .withColumn("is_return", ((~F.col("InvoiceNo").startswith("C")) & (F.col("Quantity") < 0)).cast("int"))
      .withColumn("is_bad_price", (F.col("UnitPrice") <= 0).cast("int"))
      .withColumn("is_special", (F.col("StockCode").isin(SPECIAL)
                                 | F.col("StockCode").startswith("gift_")
                                 | F.col("StockCode").rlike("^DCGS")).cast("int")))
df = df.dropDuplicates()  # 全列去重 = pandas drop_duplicates(keep='first')，行数等价
df = (df.withColumn("amount", F.round(F.col("Quantity") * F.col("UnitPrice"), 2))
        .withColumn("year_month", F.date_format("InvoiceDate", "yyyy-MM"))
        .withColumn("is_valid_purchase",
                    ((F.col("has_customer") == 1) & (F.col("is_cancelled") == 0)
                     & (F.col("is_return") == 0) & (F.col("is_bad_price") == 0)
                     & (F.col("is_special") == 0) & (F.col("Quantity") > 0)
                     & (F.col("UnitPrice") > 0)).cast("int")))
n_clean = df.count()
n_valid = df.filter("is_valid_purchase = 1").count()
valid_amt = df.filter("is_valid_purchase = 1").agg(F.round(F.sum("amount"), 2)).collect()[0][0]
n_orders = df.filter("is_valid_purchase = 1").select("InvoiceNo").distinct().count()
print(f"[Spark] clean = {n_clean}, valid = {n_valid}, valid_amount = {valid_amt}, valid_orders = {n_orders}")

# ===== 3. 写 MySQL（DROP 后由 Spark 自建表，createTableColumnTypes 显式类型）=====
import pymysql
c0 = pymysql.connect(host="localhost", port=MYSQL_PORT, user="root", password="123456",
                     database="ecommerce_rfm", charset="utf8mb4")
with c0.cursor() as cur:
    for t in ["transactions_raw", "transactions_clean", "customer_rfm"]:
        cur.execute(f"DROP TABLE IF EXISTS {t}")
c0.commit(); c0.close()

RAW_TYPES = ("InvoiceNo VARCHAR(20), StockCode VARCHAR(32), Description VARCHAR(255), "
             "Quantity INT, InvoiceDate TIMESTAMP, UnitPrice DECIMAL(10,2), "
             "CustomerID INT, Country VARCHAR(64)")
CLEAN_TYPES = RAW_TYPES + (", amount DECIMAL(12,2), has_customer TINYINT, is_cancelled TINYINT, "
                           "is_return TINYINT, is_bad_price TINYINT, is_special TINYINT, "
                           "is_valid_purchase TINYINT, year_month VARCHAR(7)")
RFM_TYPES = ("customer_id INT, R SMALLINT, F INT, M DECIMAL(12,2), "
             "last_purchase TIMESTAMP, first_purchase TIMESTAMP")

raw_out = raw.select("InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate",
                     "UnitPrice", "CustomerID", "Country")
clean_cols = ["InvoiceNo", "StockCode", "Description", "Quantity", "InvoiceDate", "UnitPrice",
              "CustomerID", "Country", "amount", "has_customer", "is_cancelled", "is_return",
              "is_bad_price", "is_special", "is_valid_purchase", "year_month"]
clean_out = df.select(*clean_cols)

def jdbc_write(dfo, table, types, batch=10000):
    (dfo.write.format("jdbc").option("url", MYSQL_URL).options(**MYSQL_PROP)
     .option("dbtable", table).option("createTableColumnTypes", types)
     .option("batchsize", str(batch)).mode("overwrite").save())

jdbc_write(raw_out, "transactions_raw", RAW_TYPES)
jdbc_write(clean_out, "transactions_clean", CLEAN_TYPES)
print("[Spark] MySQL 写入完成")

# ===== 4. 统计分析（口径同 04_analysis.py：真实销售口径）=====
sale = df.filter("is_cancelled = 0 AND is_return = 0 AND is_bad_price = 0 AND is_special = 0 AND Quantity > 0")
trend = (sale.groupBy(F.date_format("InvoiceDate", "yyyy-MM").alias("year_month"))
         .agg(F.round(F.sum("amount"), 2).alias("revenue"),
              F.countDistinct("InvoiceNo").alias("orders"),
              F.count("*").alias("rows")).orderBy("year_month"))
trend.coalesce(1).write.mode("overwrite").option("header", "true").csv("hdfs://localhost:9000/ecommerce/analysis/monthly_trend")

prod = (sale.groupBy("StockCode")
        .agg(F.first("Description").alias("desc"), F.sum("Quantity").alias("qty"),
             F.round(F.sum("amount"), 2).alias("revenue")).orderBy(F.desc("revenue")).limit(10))
prod.coalesce(1).write.mode("overwrite").option("header", "true").csv("hdfs://localhost:9000/ecommerce/analysis/top10_products")
print("[Spark] 趋势/商品分析完成")

# ===== 5. RFM（口径同 05_rfm.py：参考日期=max有效购买日次日，F按订单去重）=====
v = df.filter("is_valid_purchase = 1")
ref = v.agg(F.max("InvoiceDate")).collect()[0][0]
print(f"[Spark] ref_date = {ref.date()} (+1 day)")
rfm = (v.groupBy("CustomerID")
       .agg(F.datediff(F.date_sub(F.lit(ref), -1), F.to_date(F.max("InvoiceDate"))).alias("R"),
            F.countDistinct("InvoiceNo").alias("F"),
            F.round(F.sum("amount"), 2).alias("M"),
            F.max("InvoiceDate").alias("last_purchase"),
            F.min("InvoiceDate").alias("first_purchase")))
n_rfm = rfm.count()
f_sum = rfm.agg(F.sum("F")).collect()[0][0]
print(f"[Spark] rfm rows = {n_rfm}, F sum = {f_sum}")

jdbc_write(rfm.selectExpr("CustomerID as customer_id", "R", "F", "M", "last_purchase", "first_purchase"),
           "customer_rfm", RFM_TYPES, batch=5000)
print("[Spark] customer_rfm 写入完成")

# ===== 5.5 补齐主键与索引 =====
# Spark JDBC 建表不带主键/索引，落库后统一补，保证前端按客户/日期/国家过滤时走索引
DDL_INDEX = [
    "ALTER TABLE transactions_raw ADD COLUMN id BIGINT AUTO_INCREMENT PRIMARY KEY FIRST",
    "CREATE INDEX idx_raw_invoice ON transactions_raw(InvoiceNo)",
    "CREATE INDEX idx_raw_customer ON transactions_raw(CustomerID)",
    "CREATE INDEX idx_raw_date ON transactions_raw(InvoiceDate)",
    "ALTER TABLE transactions_clean ADD COLUMN id BIGINT AUTO_INCREMENT PRIMARY KEY FIRST",
    "CREATE INDEX idx_clean_customer ON transactions_clean(CustomerID)",
    "CREATE INDEX idx_clean_invoice ON transactions_clean(InvoiceNo)",
    "CREATE INDEX idx_clean_date ON transactions_clean(InvoiceDate)",
    "CREATE INDEX idx_clean_country ON transactions_clean(Country)",
    "CREATE INDEX idx_clean_valid ON transactions_clean(is_valid_purchase)",
    "ALTER TABLE customer_rfm ADD PRIMARY KEY (customer_id)",
]
cx = pymysql.connect(host="localhost", port=MYSQL_PORT, user="root", password="123456",
                     database="ecommerce_rfm", charset="utf8mb4")
with cx.cursor() as cur:
    for stmt in DDL_INDEX:
        try:
            cur.execute(stmt)
        except Exception as e:
            print(f"[索引] 跳过（{e.args[0]}）：{stmt[:48]}")
cx.commit(); cx.close()
print("[Spark] 主键与索引已补齐")

# ===== 6. 对账 =====
expected = {"raw": 541909, "clean": 536641, "valid": 391153,
            "valid_amount": 8737227.64, "orders": 18402, "rfm": 4334}
checks = {"raw": n_raw, "clean": n_clean, "valid": n_valid,
          "valid_amount": float(valid_amt), "orders": n_orders, "rfm": n_rfm, "f_sum": int(f_sum)}
ok = (checks["raw"] == expected["raw"] and checks["clean"] == expected["clean"]
      and checks["valid"] == expected["valid"]
      and abs(checks["valid_amount"] - expected["valid_amount"]) < 1
      and checks["orders"] == expected["orders"] and checks["rfm"] == expected["rfm"]
      and checks["f_sum"] == expected["orders"])
print("\n===== Spark vs Pandas 基线对账 =====")
for k, v0 in expected.items():
    got = checks.get(k)
    mark = "OK " if (abs(got - v0) < 1 if isinstance(v0, float) else got == v0) else "FAIL"
    print(f"  [{mark}] {k}: Spark={got} vs Pandas基线={v0}")
print(f"  [{'OK ' if ok else 'FAIL'}] 全部一致" )
with open(_ROOT + r"\ecommerce_rfm\outputs\spark_check.json", "w", encoding="utf-8") as f:
    json.dump({"checks": checks, "expected": expected, "all_ok": bool(ok)}, f, ensure_ascii=False, indent=2)
spark.stop()
sys.exit(0 if ok else 2)
