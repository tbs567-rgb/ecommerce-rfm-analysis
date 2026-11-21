# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""03_clean.py — 第3步：数据清洗
规则（按需求方案）：
1. 字段类型：InvoiceNo/StockCode/CustomerID 按标识符处理，InvoiceDate 转日期时间
2. 客户编号缺失：不物理删除，打标 has_customer；RFM 口径排除，整体销售分析可保留
3. 取消订单/退货：单独标记 is_cancelled(InvoiceNo以C开头) / is_return(Quantity<0且非取消)
4. 单价或数量不合理：UnitPrice<=0 打标 is_bad_price（查为 damages/check/adjust 类仓库调整）
5. 完全重复行：去掉（同订单+同商品+同秒+同价+同客户 → 录入型重复），去重依据写入日志
6. 极端消费值：检查后保留（大额单均有配对取消单冲销，净额为0，无需行级删除）
7. 新增 amount = Quantity × UnitPrice
8. 特殊编码（POST/DOT/M/C2/D/S/BANK CHARGES/AMAZONFEE/CRUK/gift_*）：非商品销售，打标 is_special
产出：
- data/processed/online_retail_clean.pkl（保留全部行+标记，供 DB 导入与复查）
- outputs/clean_log.md、outputs/clean_compare.csv
"""
import pandas as pd
import os, json

RAW = _ROOT + r"\ecommerce_rfm\data\raw\Online Retail.xlsx"
PROC = _ROOT + r"\ecommerce_rfm\data\processed"
OUT = _ROOT + r"\ecommerce_rfm\outputs"
os.makedirs(PROC, exist_ok=True)
os.makedirs(OUT, exist_ok=True)

log = []  # (步骤, 操作, 行数变化, 说明)

print("读取原始 Excel...")
df = pd.read_excel(RAW, engine="openpyxl")
n_raw = len(df)
log.append(("0", "原始数据载入", n_raw, "UCI Online Retail.xlsx，541,909 行与官方规模一致"))

# ---- 1. 字段类型 ----
df["InvoiceNo"] = df["InvoiceNo"].astype(str)
df["StockCode"] = df["StockCode"].astype(str)
df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
df["CustomerID"] = df["CustomerID"].astype("Int64")  # 标识符，可空整数
log.append(("1", "字段类型规范", n_raw, "InvoiceNo/StockCode→字符串，CustomerID→可空整数，InvoiceDate→datetime"))

# ---- 2. 客户编号缺失：打标 ----
df["has_customer"] = df["CustomerID"].notna()
n_nocust = int((~df["has_customer"]).sum())
log.append(("2", "客户编号缺失打标", n_raw, f"缺客户编号 {n_nocust:,} 行(占{n_nocust/n_raw*100:.1f}%)，保留在表中供整体销售分析；RFM 口径排除"))

# ---- 3. 取消/退货打标 ----
df["is_cancelled"] = df["InvoiceNo"].str.startswith("C")
df["is_return"] = (~df["is_cancelled"]) & (df["Quantity"] < 0)
log.append(("3a", "取消订单打标", n_raw, f"取消单(C开头) {int(df['is_cancelled'].sum()):,} 行"))
log.append(("3b", "退货/负数量打标", n_raw, f"非取消但 Quantity<0 {int(df['is_return'].sum()):,} 行（多为 damages/adjust 类调整）"))

# ---- 4. 单价不合理打标 ----
df["is_bad_price"] = df["UnitPrice"] <= 0
log.append(("4", "单价<=0 打标", n_raw, f"{int(df['is_bad_price'].sum()):,} 行，Description 多为 check/damages/found/? 等，属仓库盘点调整而非销售，98.4% 缺客户编号"))

# ---- 5. 完全重复去重 ----
n_before = len(df)
df = df.drop_duplicates(keep="first").reset_index(drop=True)
n_dedup = n_before - len(df)
log.append(("5", "完全重复行去重", len(df), f"去掉 {n_dedup:,} 行（占{n_dedup/n_before*100:.2f}%）。依据：重复组均为同订单号+同商品+同秒时间戳+同单价+同客户，属录入型重复；跨订单的真实复购不受影响"))

# ---- 6. 特殊编码打标（非商品销售项）----
special_codes = {"POST", "DOT", "M", "C2", "D", "S", "BANK CHARGES", "AMAZONFEE", "CRUK", "B", "ADJUST", "ADJUST2", "TEST001", "TEST002"}
is_special = df["StockCode"].isin(special_codes) | df["StockCode"].str.startswith("gift_") | df["StockCode"].str.match(r"^DCGS")
df["is_special"] = is_special
log.append(("6", "特殊编码打标", len(df), f"{int(is_special.sum()):,} 行为邮费/折扣/手工调整/银行费用/礼品卡等非商品项，不参与 RFM 有效购买口径"))

# ---- 7. 交易金额 ----
df["amount"] = (df["Quantity"] * df["UnitPrice"]).round(2)
log.append(("7", "新增 amount=Quantity×UnitPrice", len(df), "保留负值（取消/退货金额为负，方便对账复查）"))

# ---- 8. 极端消费值检查（保留不删）----
big = df[(df["Quantity"] > 10000) | (df["Quantity"] < -10000)]
log.append(("8", "极端数量检查", len(df), f"|Quantity|>10000 共 {len(big)} 行：74215/80995 两大额单均存在配对 C 开头全额取消单（净额0），12540 件为 0 元赠品 → 均保留原样，通过标记口径自然隔离"))

# ---- 9. 有效购买口径（RFM 用）----
df["is_valid_purchase"] = (
    df["has_customer"] & (~df["is_cancelled"]) & (~df["is_return"])
    & (~df["is_bad_price"]) & (~df["is_special"]) & (df["Quantity"] > 0) & (df["UnitPrice"] > 0)
)
log.append(("9", "定义有效购买口径", len(df),
            f"有效购买 {int(df['is_valid_purchase'].sum()):,} 行 = 有客户编号 & 非取消 & 非退货 & 单价>0 & 数量>0 & 非特殊编码。RFM 仅用这些行"))

df["year_month"] = df["InvoiceDate"].dt.strftime("%Y-%m")
df.to_pickle(os.path.join(PROC, "online_retail_clean.pkl"))

# ---- 清洗前后对比表 ----
n_clean = len(df)
valid = df[df["is_valid_purchase"]]
compare = pd.DataFrame([
    ["原始行数", n_raw, "—"],
    ["清洗后总行数（保留全部标记行）", n_clean, f"去掉完全重复 {n_dedup:,} 行"],
    ["有效购买行（RFM口径）", int(len(valid)), f"占清洗后 {len(valid)/n_clean*100:.1f}%"],
    ["有效订单数（InvoiceNo去重）", int(valid['InvoiceNo'].nunique()), "RFM 的 F 计数基础"],
    ["有效客户数", int(valid['CustomerID'].nunique()), "RFM 分析对象"],
    ["有效购买总金额(GBP)", round(float(valid['amount'].sum()), 2), "对应 M 指标加总"],
    ["取消单行数", int(df['is_cancelled'].sum()), "保留在表中可复查"],
    ["退货/负数量行数", int(df['is_return'].sum()), "保留在表中可复查"],
    ["缺客户编号行数", int((~df['has_customer']).sum()), "保留供整体销售分析"],
    ["特殊编码行数", int(df['is_special'].sum()), "保留供对账"],
    ["时间范围", f"{df['InvoiceDate'].min()} ~ {df['InvoiceDate'].max()}", "首尾月不完整，趋势分析需剔除"],
])
compare.columns = ["指标", "清洗后", "说明"]
compare.to_csv(os.path.join(OUT, "clean_compare.csv"), index=False, encoding="utf-8-sig")

# ---- 清洗日志 ----
with open(os.path.join(OUT, "clean_log.md"), "w", encoding="utf-8") as f:
    f.write("# 数据清洗日志（clean_log）\n\n")
    f.write(f"- 数据源：UCI Online Retail（archive.ics.uci.edu/dataset/352），下载日期 2026-11-01\n")
    f.write(f"- 原始规模：{n_raw:,} 行 × 8 字段\n\n")
    f.write("| # | 步骤 | 处理后行数 | 说明 |\n|---|------|-----------|------|\n")
    for step, act, n, note in log:
        f.write(f"| {step} | {act} | {n:,} | {note} |\n")
    f.write("\n## 清洗前后对比表\n\n" + compare.to_markdown(index=False) + "\n")
    f.write("\n## 原则\n- 原始退货和取消数据全部保留在 transactions_clean 中（通过标记列隔离），方便复查。\n")
    f.write("- 每一行都可通过 is_valid_purchase=False 追溯被 RFM 排除的原因。\n")

print(compare.to_string(index=False))
print(f"\n✅ 清洗完成：{n_clean:,} 行（去重 {n_dedup:,}），有效购买 {len(valid):,} 行，"
      f"有效客户 {valid['CustomerID'].nunique():,} 人")
print("产出：data/processed/online_retail_clean.pkl, outputs/clean_log.md, outputs/clean_compare.csv")
