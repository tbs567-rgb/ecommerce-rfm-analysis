# -*- coding: utf-8 -*-
"""02_clean_check.py — 清洗前细节检查：分类查清异常原因，为清洗决策提供依据"""
import pandas as pd

pd.set_option("display.width", 200)
RAW = r"D:\graduation_project\ecommerce_rfm\data\raw\Online Retail.xlsx"

df = pd.read_excel(RAW, engine="openpyxl")
df["InvoiceNo"] = df["InvoiceNo"].astype(str)

print("===== 1. 特殊 StockCode（非纯数字/字母前缀）=====")
# 商品编码一般是5位数字+可选字母；找出字母开头的特殊编码
codes = df["StockCode"].astype(str)
special = df[codes.str.match(r"^[A-Za-z]", na=False)]
print(special.groupby("StockCode").agg(n=("InvoiceNo", "size"), qty=("Quantity", "sum"),
      price=("UnitPrice", "mean")).sort_values("n", ascending=False).head(15).to_string())
print(f"特殊编码总行数: {len(special):,} ({len(special)/len(df)*100:.2f}%)")

print("\n===== 2. UnitPrice<=0 的行（按原因分类）=====")
bad_price = df[df["UnitPrice"] <= 0]
print(f"总行数: {len(bad_price):,}")
print("其中 Description 分布 top8:")
print(bad_price["Description"].value_counts().head(8).to_string())
print("其中是取消单(C开头)的行数:", bad_price["InvoiceNo"].str.startswith("C").sum())
print("其中缺客户编号的行数:", bad_price["CustomerID"].isna().sum())
print("样例:")
print(bad_price[["InvoiceNo","StockCode","Description","Quantity","UnitPrice","CustomerID"]].head(8).to_string())

print("\n===== 3. Quantity 极端值 =====")
print("Quantity 最小 5 行:")
print(df.nsmallest(5, "Quantity")[["InvoiceNo","StockCode","Description","Quantity","UnitPrice","CustomerID","InvoiceDate"]].to_string())
print("Quantity 最大 5 行:")
print(df.nlargest(5, "Quantity")[["InvoiceNo","StockCode","Description","Quantity","UnitPrice","CustomerID","InvoiceDate"]].to_string())
# 74215 那单 80995 件纸灯笼是知名异常单，查一下有没有对应冲销
big = df[(df["Quantity"] > 10000) | (df["Quantity"] < -10000)]
print(f"\n|Quantity|>10000 的行数: {len(big)}")
print(big[["InvoiceNo","StockCode","Description","Quantity","CustomerID","InvoiceDate"]].to_string())

print("\n===== 4. 完全重复行构成 =====")
dup = df[df.duplicated(keep=False)]
print(f"重复涉及行数: {len(dup):,}")
g = dup.groupby(["InvoiceNo","StockCode","Description","Quantity","InvoiceDate","UnitPrice","CustomerID"]).size()
print(f"重复组数: {len(g):,}，每组行数分布: {g.value_counts().to_dict()}")
print("同一订单同一商品同秒重复 → 录入型重复概率高。样例:")
print(dup.sort_values(["InvoiceNo","StockCode"]).head(6).to_string())

print("\n===== 5. 客户级消费金额分布（极端值影响预判）=====")
tmp = df.dropna(subset=["CustomerID"]).copy()
tmp["amount"] = tmp["Quantity"] * tmp["UnitPrice"]
cust = tmp.groupby("CustomerID")["amount"].sum().sort_values(ascending=False)
print("总消费 top5 客户:")
print(cust.head(5).round(2).to_string())
print(f"\n客户总数: {len(cust):,}")
print(f"Top 20% 客户({int(len(cust)*0.2):,}人) 消费占比: {cust.head(int(len(cust)*0.2)).sum()/cust.sum()*100:.1f}%")
print(f"最高消费额: {cust.iloc[0]:,.0f}  中位数: {cust.median():,.0f}")
