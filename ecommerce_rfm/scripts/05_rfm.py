# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""05_rfm.py — 第6步：计算 RFM 客户特征
R = 参考日期 - 客户最近一次有效购买日期（天）
F = 有效订单编号去重计数（按订单，不按明细行）
M = 有效购买金额求和
参考日期 = 数据中最后一个交易日期(2011-12-09)的次日 = 2011-12-10，保证可复现
产出：outputs/rfm/customer_rfm.csv + rfm_summary.json
"""
import pandas as pd
import os, json

PROC = _ROOT + r"\ecommerce_rfm\data\processed\online_retail_clean.pkl"
OUT = _ROOT + r"\ecommerce_rfm\outputs\rfm"
os.makedirs(OUT, exist_ok=True)

df = pd.read_pickle(PROC)
v = df[df["is_valid_purchase"]].copy()   # 有效购买口径（同第3步定义）

ref_date = v["InvoiceDate"].max().normalize() + pd.Timedelta(days=1)
print(f"参考日期: {ref_date.date()}（最后交易日 2011-12-09 次日）")

rfm = v.groupby("CustomerID").agg(
    R_value=("InvoiceDate", lambda s: (ref_date - s.max().normalize()).days),
    F_value=("InvoiceNo", "nunique"),          # 按订单去重 ← 关键口径
    M_value=("amount", "sum"),
    last_purchase=("InvoiceDate", "max"),
    first_purchase=("InvoiceDate", "min"),
).reset_index()
rfm["M_value"] = rfm["M_value"].round(2)
rfm = rfm.rename(columns={"R_value": "R", "F_value": "F", "M_value": "M"})

rfm.to_csv(os.path.join(OUT, "customer_rfm.csv"), index=False)

summary = {
    "ref_date": str(ref_date.date()),
    "n_customers": int(len(rfm)),
    "R": {"min": int(rfm.R.min()), "median": float(rfm.R.median()), "max": int(rfm.R.max()),
          "mean": round(float(rfm.R.mean()), 1)},
    "F": {"min": int(rfm.F.min()), "median": float(rfm.F.median()), "max": int(rfm.F.max()),
          "mean": round(float(rfm.F.mean()), 1)},
    "M": {"min": round(float(rfm.M.min()), 2), "median": round(float(rfm.M.median()), 2),
          "max": round(float(rfm.M.max()), 2), "mean": round(float(rfm.M.mean()), 2),
          "total": round(float(rfm.M.sum()), 2)},
    "valid_orders": int(v["InvoiceNo"].nunique()),
    "valid_rows": int(len(v)),
}
with open(os.path.join(OUT, "rfm_summary.json"), "w", encoding="utf-8") as f:
    json.dump(summary, f, ensure_ascii=False, indent=2)

print(rfm[["R", "F", "M"]].describe().round(1).to_string())
print(f"\n✅ RFM 完成：{len(rfm):,} 位客户 → outputs/rfm/customer_rfm.csv")
print(f"复核: 有效订单 {summary['valid_orders']:,} × 客户 {len(rfm):,} → F 合计 {int(rfm.F.sum()):,}（应等于有效订单数）")
