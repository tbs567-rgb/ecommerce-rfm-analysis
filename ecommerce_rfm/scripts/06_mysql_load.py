# -*- coding: utf-8 -*-
"""06_mysql_load.py — 第4步：MySQL 建表并导入
建三张表：transactions_raw / transactions_clean / customer_rfm
（customer_segments 待第7步 K-means 聚类完成后写入）
导入后做行数与金额核对。
"""
import pandas as pd
import pymysql, os, json, time
from sqlalchemy import create_engine, text

USER, PWD, HOST, PORT, DB = "root", "123456", "localhost", 3306, "ecommerce_rfm"
OUT = r"D:\graduation_project\ecommerce_rfm\outputs"

# ---- 1. 建库 ----
conn0 = pymysql.connect(host=HOST, port=PORT, user=USER, password=PWD, charset="utf8mb4")
with conn0.cursor() as c:
    c.execute(f"CREATE DATABASE IF NOT EXISTS {DB} DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
    c.execute(f"SELECT VERSION()")
    ver = c.fetchone()[0]
conn0.close()
print(f"MySQL {ver} 连接成功，数据库 {DB} 就绪")

engine = create_engine(f"mysql+pymysql://{USER}:{PWD}@{HOST}:{PORT}/{DB}?charset=utf8mb4",
                       pool_recycle=3600)

DDL = [
"""CREATE TABLE IF NOT EXISTS transactions_raw (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  invoice_no VARCHAR(20) NOT NULL,
  stock_code VARCHAR(32) NOT NULL,
  description VARCHAR(255) NULL,
  quantity INT NOT NULL,
  invoice_date DATETIME NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  customer_id INT NULL,
  country VARCHAR(64),
  KEY idx_cust (customer_id),
  KEY idx_date (invoice_date),
  KEY idx_inv (invoice_no)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS transactions_clean (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  invoice_no VARCHAR(20) NOT NULL,
  stock_code VARCHAR(32) NOT NULL,
  description VARCHAR(255) NULL,
  quantity INT NOT NULL,
  invoice_date DATETIME NOT NULL,
  unit_price DECIMAL(10,2) NOT NULL,
  customer_id INT NULL,
  country VARCHAR(64),
  amount DECIMAL(12,2) NOT NULL,
  has_customer TINYINT NOT NULL DEFAULT 0,
  is_cancelled TINYINT NOT NULL DEFAULT 0,
  is_return TINYINT NOT NULL DEFAULT 0,
  is_bad_price TINYINT NOT NULL DEFAULT 0,
  is_special TINYINT NOT NULL DEFAULT 0,
  is_valid_purchase TINYINT NOT NULL DEFAULT 0,
  order_month CHAR(7),
  KEY idx_cust (customer_id),
  KEY idx_date (invoice_date),
  KEY idx_inv (invoice_no),
  KEY idx_valid (is_valid_purchase)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
"""CREATE TABLE IF NOT EXISTS customer_rfm (
  customer_id INT PRIMARY KEY,
  R SMALLINT NOT NULL,
  F INT NOT NULL,
  M DECIMAL(12,2) NOT NULL,
  last_purchase DATETIME NOT NULL,
  first_purchase DATETIME NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4""",
]
with engine.begin() as c:
    for ddl in DDL:
        c.execute(text(ddl))
print("三张核心表结构就绪（customer_segments 待聚类后建）")

def fast_load(df, table):
    t0 = time.time()
    df.to_sql(table, engine, if_exists="append", index=False, method="multi", chunksize=2000)
    print(f"  {table}: {len(df):,} 行导入完成，耗时 {time.time()-t0:.0f}s")

# ---- 2. transactions_raw（原样 541,909）----
print("导入 transactions_raw ...")
raw = pd.read_excel(r"D:\graduation_project\ecommerce_rfm\data\raw\Online Retail.xlsx", engine="openpyxl")
raw["InvoiceNo"] = raw["InvoiceNo"].astype(str)
raw["StockCode"] = raw["StockCode"].astype(str)
raw = raw.rename(columns={
    "InvoiceNo": "invoice_no", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "UnitPrice": "unit_price",
    "CustomerID": "customer_id", "Country": "country"})
raw["customer_id"] = raw["customer_id"].astype("Int64")
fast_load(raw, "transactions_raw")
del raw

# ---- 3. transactions_clean（536,641 + 标记）----
print("导入 transactions_clean ...")
clean = pd.read_pickle(r"D:\graduation_project\ecommerce_rfm\data\processed\online_retail_clean.pkl")
clean = clean.rename(columns={
    "InvoiceNo": "invoice_no", "StockCode": "stock_code", "Description": "description",
    "Quantity": "quantity", "InvoiceDate": "invoice_date", "UnitPrice": "unit_price",
    "CustomerID": "customer_id", "Country": "country"})
clean["customer_id"] = clean["customer_id"].astype("Int64")
clean = clean[["invoice_no","stock_code","description","quantity","invoice_date","unit_price",
               "customer_id","country","amount","has_customer","is_cancelled","is_return",
               "is_bad_price","is_special","is_valid_purchase","year_month"]].rename(columns={"year_month": "order_month"})
for col in ["has_customer","is_cancelled","is_return","is_bad_price","is_special","is_valid_purchase"]:
    clean[col] = clean[col].astype(int)
fast_load(clean, "transactions_clean")
del clean

# ---- 4. customer_rfm（4,334）----
print("导入 customer_rfm ...")
rfm = pd.read_csv(r"D:\graduation_project\ecommerce_rfm\outputs\rfm\customer_rfm.csv")
rfm["CustomerID"] = rfm["CustomerID"].astype(int)
rfm = rfm.rename(columns={"CustomerID": "customer_id", "R": "R", "F": "F", "M": "M"})
rfm = rfm[["customer_id","R","F","M","last_purchase","first_purchase"]]
fast_load(rfm, "customer_rfm")

# ---- 5. 核对 ----
print("\n===== 导入核对 =====")
checks = {}
with engine.connect() as c:
    checks["raw_rows"] = c.execute(text("SELECT COUNT(*) FROM transactions_raw")).scalar()
    checks["clean_rows"] = c.execute(text("SELECT COUNT(*) FROM transactions_clean")).scalar()
    checks["rfm_rows"] = c.execute(text("SELECT COUNT(*) FROM customer_rfm")).scalar()
    checks["clean_valid"] = c.execute(text("SELECT COUNT(*) FROM transactions_clean WHERE is_valid_purchase=1")).scalar()
    checks["valid_amount"] = float(c.execute(text("SELECT ROUND(SUM(amount),2) FROM transactions_clean WHERE is_valid_purchase=1")).scalar())
    checks["valid_orders"] = c.execute(text("SELECT COUNT(DISTINCT invoice_no) FROM transactions_clean WHERE is_valid_purchase=1")).scalar()
    checks["rfm_total_M"] = float(c.execute(text("SELECT ROUND(SUM(M),2) FROM customer_rfm")).scalar())
    checks["rfm_F_sum"] = c.execute(text("SELECT SUM(F) FROM customer_rfm")).scalar()
    checks["diff_raw_clean"] = checks["raw_rows"] - checks["clean_rows"]
    # 抽样核对：customer 17850 的最后一笔
    samp = c.execute(text("""SELECT invoice_no, stock_code, quantity, amount FROM transactions_clean
        WHERE customer_id=17850 AND is_valid_purchase=1 ORDER BY invoice_date DESC LIMIT 3""")).fetchall()

print(f"raw {checks['raw_rows']:,} | clean {checks['clean_rows']:,} | 差 {checks['diff_raw_clean']:,}(=去重5,268) | rfm {checks['rfm_rows']:,}")
print(f"有效购买 {checks['clean_valid']:,} 行 / {checks['valid_orders']:,} 单 / £{checks['valid_amount']:,}")
print(f"RFM 合计 M £{checks['rfm_total_M']:,}（应=有效购买金额）| F 合计 {checks['rfm_F_sum']:,}（应=有效订单数）")
print("抽样 customer 17850:", samp)

ok = (checks["diff_raw_clean"] == 5268 and checks["clean_valid"] == 391153
      and abs(checks["valid_amount"] - checks["rfm_total_M"]) < 1 and checks["rfm_F_sum"] == checks["valid_orders"])
checks["all_ok"] = bool(ok)
print("\n✅ 核对全部通过" if ok else "\n⚠️ 存在不一致，需检查")

with open(os.path.join(OUT, "mysql_check.json"), "w", encoding="utf-8") as f:
    json.dump(checks, f, ensure_ascii=False, indent=2)
