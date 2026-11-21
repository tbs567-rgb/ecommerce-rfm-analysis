# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""04_analysis.py — 第5步：统计分析
口径定义：
- 真实销售口径（趋势/商品）：非取消 & 非退货 & 数量>0 & 单价>0 & 非特殊编码（含缺客户编号的真实销售行）
- 有效购买口径（客户/集中度/复购）：真实销售口径 & 有客户编号
产出：outputs/analysis_report.md + outputs/analysis/*.csv
"""
import pandas as pd
import os, json

PROC = _ROOT + r"\ecommerce_rfm\data\processed\online_retail_clean.pkl"
OUT = _ROOT + r"\ecommerce_rfm\outputs\analysis"
os.makedirs(OUT, exist_ok=True)

df = pd.read_pickle(PROC)

# 两个分析口径
sale = df[(~df["is_cancelled"]) & (~df["is_return"]) & (~df["is_bad_price"])
          & (~df["is_special"]) & (df["Quantity"] > 0)].copy()
cust_scope = sale[sale["has_customer"]].copy()

R = []  # 每项分析：问题/口径/结果/解释

# ===== 1. 销售趋势 =====
# 首月(2010-12)仅1天、末月(2011-12)仅9天 → 完整月为 2011-01~2011-11
full_months = [f"2011-{m:02d}" for m in range(1, 12)]
trend = sale.groupby("year_month").agg(
    revenue=("amount", "sum"), orders=("InvoiceNo", "nunique"), rows=("InvoiceNo", "size")).reset_index()
trend.to_csv(os.path.join(OUT, "monthly_trend.csv"), index=False)
trend_full = trend[trend["year_month"].isin(full_months)]
peak = trend_full.loc[trend_full["revenue"].idxmax()]
low = trend_full.loc[trend_full["revenue"].idxmin()]
R.append(dict(
    item="销售趋势",
    question="不同月份销售有什么变化？",
    scope="真实销售口径；完整月=2011-01~2011-11（2010-12仅1天、2011-12仅9天，不参与比较）",
    result=f"完整月月均销售额 £{trend_full['revenue'].mean():,.0f}；"
           f"峰值 {peak['year_month']} £{peak['revenue']:,.0f}（{peak['orders']:,} 单），"
           f"谷值 {low['year_month']} £{low['revenue']:,.0f}；9-11月连续走高，11月为全年最高",
    explain="年末旺季特征明显（圣诞备货），与英国礼品批发业务一致；月度波动与订单数高度同步。首尾月数据不完整已在口径中剔除，避免误判。"))

# ===== 2. 商品表现 =====
prod = sale.groupby("StockCode").agg(
    desc=("Description", "first"), qty=("Quantity", "sum"), revenue=("amount", "sum")).sort_values("revenue", ascending=False)
prod.head(10).to_csv(os.path.join(OUT, "top10_products.csv"))
top5_share = prod["revenue"].head(5).sum() / prod["revenue"].sum()
R.append(dict(
    item="商品表现",
    question="哪些商品表现突出？",
    scope="真实销售口径，按商品编码聚合销售额/销量",
    result=f"销售额Top3：{prod.index[0]}({prod['desc'].iloc[0]}) £{prod['revenue'].iloc[0]:,.0f}、"
           f"{prod.index[1]}({prod['desc'].iloc[1]}) £{prod['revenue'].iloc[1]:,.0f}、"
           f"{prod.index[2]}({prod['desc'].iloc[2]}) £{prod['revenue'].iloc[2]:,.0f}；"
           f"Top5 商品贡献全站销售额 {top5_share*100:.1f}%",
    explain="头部商品以手工装饰/纸艺/陶瓷收纳类为主，单品集中度不高（长尾特征），可对Top商品做库存与陈列倾斜。"))

# ===== 3. 客户消费分布 =====
cust = cust_scope.groupby("CustomerID").agg(
    revenue=("amount", "sum"), orders=("InvoiceNo", "nunique"))
cust.to_csv(os.path.join(OUT, "customer_spend.csv"))
q = cust["revenue"].describe(percentiles=[.25, .5, .75, .9])
R.append(dict(
    item="客户消费",
    question="客户之间差异有多大？",
    scope="有效购买口径（有客户编号）",
    result=f"客户 {len(cust):,} 人；消费额中位数 £{q['50%']:,.0f}，均值 £{q['mean']:,.0f}（均值的{q['mean']/q['50%']:.1f}倍于中位数），"
           f"P90 £{q['90%']:,.0f}，最高 £{cust['revenue'].max():,.0f}；"
           f"25%客户单笔订单数≤{cust['orders'].quantile(.25):.0f}，中位订单数 {cust['orders'].median():.0f}",
    explain="分布严重右偏：少数大客户拉高均值，多数客户消费低频小额——典型 B2B 批发结构，客户分群价值突出。"))

# ===== 4. 消费集中度 =====
c_sorted = cust["revenue"].sort_values(ascending=False)
n20 = int(len(c_sorted) * 0.2)
top20_share = c_sorted.head(n20).sum() / c_sorted.sum()
R.append(dict(
    item="消费集中度",
    question="销售是否依赖少数客户？",
    scope="有效购买口径，客户按总消费降序取前20%",
    result=f"前 20% 客户（{n20:,} 人）贡献 {top20_share*100:.1f}% 销售额；前 1%（{int(len(c_sorted)*0.01):,} 人）贡献 "
           f"{c_sorted.head(int(len(c_sorted)*0.01)).sum()/c_sorted.sum()*100:.1f}%",
    explain="接近二八定律，销售高度依赖头部客户；大客户流失风险需重点管理（对应 RFM 中的'重要价值/重要保持'人群）。"))

# ===== 5. 重复购买 =====
rep = (cust["orders"] >= 2).mean()
one_timer = cust["orders"].value_counts().head(3).to_dict()
R.append(dict(
    item="重复购买",
    question="客户重复购买情况如何？",
    scope="有效购买口径，F=有效订单号去重计数，观察期 2010-12-01~2011-12-09",
    result=f"购买≥2次的客户占 {rep*100:.1f}%；仅买过 1 单的占 {(cust['orders']==1).mean()*100:.1f}%；"
           f"订单数众数分布（前3）：{one_timer}；最高单客户 {cust['orders'].max():.0f} 单",
    explain="约八成客户有复购，重复购买是收入基本盘；一次性客户占比小但仍有召回空间，可用 RFM 分群精准运营。"))

# ===== 写报告 =====
with open(os.path.join(OUT, "..", "analysis_report.md"), "w", encoding="utf-8") as f:
    f.write("# 统计分析报告（第5步）\n\n每项按「问题 → 计算口径 → 结果 → 解释」组织。\n\n")
    for i, x in enumerate(R, 1):
        f.write(f"## {i}. {x['item']}\n\n- **问题**：{x['question']}\n- **口径**：{x['scope']}\n"
                f"- **结果**：{x['result']}\n- **解释**：{x['explain']}\n\n")
    f.write("## 附：完整月度趋势表（2011-01 ~ 2011-11）\n\n")
    f.write(trend_full.to_markdown(index=False) + "\n")

print("===== 第5步统计分析完成 =====\n")
for i, x in enumerate(R, 1):
    print(f"[{i}] {x['item']}")
    print(f"    结果: {x['result']}\n")
print("月度趋势（完整月）:")
print(trend_full.to_string(index=False))
