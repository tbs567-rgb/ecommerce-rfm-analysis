# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""01_explore.py — 数据探索：行数、字段、时间范围、缺失值、样例
UCI Online Retail 数据集（第2步交付：字段说明表、原始数据规模统计）
"""
import pandas as pd
import json, os

RAW = _ROOT + r"\ecommerce_rfm\data\raw\Online Retail.xlsx"
OUT = _ROOT + r"\ecommerce_rfm\outputs"

print("读取 Excel（约22MB，需要一点时间）...")
df = pd.read_excel(RAW, engine="openpyxl")

print("\n===== 基本规模 =====")
print(f"行数: {len(df):,}")
print(f"字段数: {len(df.columns)}")
print(f"字段: {list(df.columns)}")

print("\n===== 数据类型 =====")
print(df.dtypes.to_string())

print("\n===== 时间范围 =====")
print(f"InvoiceDate: {df['InvoiceDate'].min()}  ~  {df['InvoiceDate'].max()}")

print("\n===== 缺失值统计 =====")
na = df.isna().sum()
print(na[na > 0].to_string() if (na > 0).any() else "无缺失")

print("\n===== 关键口径初查 =====")
print(f"客户编号缺失行数: {df['CustomerID'].isna().sum():,}")
print(f"取消订单(InvoiceNo以C开头)行数: {df['InvoiceNo'].astype(str).str.startswith('C').sum():,}")
print(f"Quantity<=0 行数: {(df['Quantity'] <= 0).sum():,}")
print(f"UnitPrice<=0 行数: {(df['UnitPrice'] <= 0).sum():,}")
print(f"完全重复行数: {df.duplicated().sum():,}")
print(f"客户数(非空去重): {df['CustomerID'].dropna().nunique():,}")
print(f"订单数(InvoiceNo去重): {df['InvoiceNo'].nunique():,}")
print(f"商品数(StockCode去重): {df['StockCode'].nunique():,}")
print(f"国家数: {df['Country'].nunique()}  → {df['Country'].value_counts().head(5).to_dict()}")

print("\n===== 前5行样例 =====")
print(df.head(5).to_string())

# 保存字段说明与规模统计，供后续报告引用
meta = {
    "rows": int(len(df)),
    "cols": list(map(str, df.columns)),
    "dtypes": {k: str(v) for k, v in df.dtypes.items()},
    "date_min": str(df["InvoiceDate"].min()),
    "date_max": str(df["InvoiceDate"].max()),
    "na": {k: int(v) for k, v in na[na > 0].items()},
    "n_customers": int(df["CustomerID"].dropna().nunique()),
    "n_invoices": int(df["InvoiceNo"].nunique()),
    "n_products": int(df["StockCode"].nunique()),
    "n_cancelled": int(df["InvoiceNo"].astype(str).str.startswith("C").sum()),
    "n_qty_le0": int((df["Quantity"] <= 0).sum()),
    "n_price_le0": int((df["UnitPrice"] <= 0).sum()),
    "n_duplicated": int(df.duplicated().sum()),
}
os.makedirs(OUT, exist_ok=True)
with open(os.path.join(OUT, "explore_meta.json"), "w", encoding="utf-8") as f:
    json.dump(meta, f, ensure_ascii=False, indent=2)
print("\n已保存 → outputs/explore_meta.json")
