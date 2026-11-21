# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[3])

"""生成课程设计报告所需的统计指标与全部插图。

所有数字均从 MySQL ecommerce_rfm 库实时计算，输出：
  docs/report/stats.json   供正文引用的指标
  docs/report/figs/*.png   报告插图（200 dpi）
"""
import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
import pandas as pd
import pymysql

warnings.filterwarnings("ignore")
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams["font.size"] = 10

BASE = _ROOT + r"\ecommerce_rfm\docs\report"
FIG = os.path.join(BASE, "figs")
os.makedirs(FIG, exist_ok=True)

C_MAIN = "#1F4E79"
C_MID = "#2E75B6"
C_LIGHT = "#9DC3E6"
C_ACC = "#C55A11"
C_GRAY = "#7F7F7F"
SEG_COLORS = {"重要价值客户": "#1F4E79", "一般发展客户": "#2E75B6", "一般挽留客户": "#9DC3E6"}
SEG_ORDER = ["重要价值客户", "一般发展客户", "一般挽留客户"]

conn = pymysql.connect(host="localhost", user="root", password="123456",
                       database="ecommerce_rfm", charset="utf8mb4")

# ---------------------------------------------------------------- 统计指标
q = lambda sql: pd.read_sql(sql, conn)

raw_n = int(q("SELECT COUNT(*) c FROM transactions_raw")["c"][0])
clean_n = int(q("SELECT COUNT(*) c FROM transactions_clean")["c"][0])
flag = q("""
    SELECT
      SUM(CustomerID IS NULL) AS no_cust,
      SUM(Quantity <= 0)      AS neg_qty,
      SUM(is_special = 1)     AS special,
      SUM(is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0) AS valid_rows
    FROM transactions_clean
""").iloc[0]

valid = q("""
    SELECT COUNT(DISTINCT InvoiceNo) orders,
           COUNT(DISTINCT CustomerID) customers,
           COUNT(DISTINCT Country) countries,
           SUM(amount) revenue,
           SUM(Quantity) units,
           MIN(InvoiceDate) dmin, MAX(InvoiceDate) dmax
    FROM transactions_clean
    WHERE is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0
""").iloc[0]

funnel_n = q("""
    SELECT
      COUNT(*) AS step_clean,
      SUM(CustomerID IS NOT NULL) AS step_cust,
      SUM(CustomerID IS NOT NULL AND Quantity > 0) AS step_qty,
      SUM(CustomerID IS NOT NULL AND Quantity > 0 AND is_special = 0) AS step_special,
      SUM(CustomerID IS NOT NULL AND Quantity > 0 AND is_special = 0
          AND is_valid_purchase = 1) AS step_valid
    FROM transactions_clean
""").iloc[0]

monthly = q("""
    SELECT `year_month` ym, SUM(amount) revenue, COUNT(DISTINCT InvoiceNo) orders
    FROM transactions_clean
    WHERE is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0
    GROUP BY `year_month` ORDER BY `year_month`
""")

top_prod = q("""
    SELECT Description name, SUM(amount) revenue, SUM(Quantity) units
    FROM transactions_clean
    WHERE is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0
      AND Description IS NOT NULL
    GROUP BY Description ORDER BY revenue DESC LIMIT 10
""")

by_country = q("""
    SELECT Country c, SUM(amount) revenue
    FROM transactions_clean
    WHERE is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0
    GROUP BY Country ORDER BY revenue DESC
""")

rfm = q("SELECT customer_id, R, F, M, first_purchase, last_purchase FROM customer_rfm")
seg = q("SELECT customer_id, R, F, M, cluster, segment_label FROM customer_segments")
ksel = pd.read_csv(_ROOT + r"\ecommerce_rfm\outputs\segments\k_selection.csv")

# 客单价 / 复购 / 帕累托
aov = float(valid.revenue) / float(valid.orders)
repeat = float((rfm.F >= 2).sum()) / len(rfm) * 100
m_sorted = np.sort(rfm.M.values)[::-1]
k20 = max(1, int(len(m_sorted) * 0.2))
pareto20 = float(m_sorted[:k20].sum() / m_sorted.sum() * 100)

# 假设检验：价值差异由频次还是客单价驱动
rfm["aov"] = rfm.M / rfm.F
corr_m_f = float(np.corrcoef(np.log1p(rfm.M), np.log1p(rfm.F))[0, 1])
corr_m_aov = float(np.corrcoef(np.log1p(rfm.M), np.log1p(rfm.aov))[0, 1])
corr_r_f = float(np.corrcoef(rfm.R, rfm.F)[0, 1])

# 季节效应
monthly["dt"] = pd.to_datetime(monthly.ym + "-01")
monthly["quarter"] = monthly.dt.dt.quarter
qsum = monthly.groupby("quarter").revenue.sum()
q_mean_month = monthly.groupby("quarter").revenue.mean()
season_ratio = float(q_mean_month.get(4, 0) / q_mean_month.drop(4).mean() * 100 - 100)

stats = {
    "raw_rows": raw_n,
    "clean_rows": clean_n,
    "dup_removed": raw_n - clean_n,
    "no_customer_rows": int(flag.no_cust),
    "negative_rows": int(flag.neg_qty),
    "special_rows": int(flag.special),
    "valid_rows": int(flag.valid_rows),
    "funnel": {
        "clean": int(funnel_n.step_clean),
        "has_customer": int(funnel_n.step_cust),
        "positive_qty": int(funnel_n.step_qty),
        "non_special": int(funnel_n.step_special),
        "valid": int(funnel_n.step_valid),
    },
    "revenue": round(float(valid.revenue), 2),
    "orders": int(valid.orders),
    "customers": int(valid.customers),
    "countries": int(valid.countries),
    "units": int(valid.units),
    "date_min": str(valid.dmin)[:10],
    "date_max": str(valid.dmax)[:10],
    "months": len(monthly),
    "aov": round(aov, 2),
    "repeat_rate": round(repeat, 2),
    "pareto_top20_share": round(pareto20, 2),
    "corr_M_F": round(corr_m_f, 3),
    "corr_M_AOV": round(corr_m_aov, 3),
    "corr_R_F": round(corr_r_f, 3),
    "q4_premium_pct": round(season_ratio, 2),
    "quarter_revenue": {int(k): round(float(v), 2) for k, v in qsum.items()},
    "rfm_mean": {c: round(float(rfm[c].mean()), 2) for c in "RFM"},
    "rfm_median": {c: round(float(rfm[c].median()), 2) for c in "RFM"},
    "peak_month": str(monthly.loc[monthly.revenue.idxmax(), "ym"]),
    "peak_revenue": round(float(monthly.revenue.max()), 2),
    "uk_share": round(float(by_country[by_country.c == "United Kingdom"].revenue.sum()
                             / by_country.revenue.sum() * 100), 2),
    "silhouette_k3": float(ksel.loc[ksel.k == 3, "silhouette"].iloc[0]),
    "segments": {},
}
for lbl in SEG_ORDER:
    s = seg[seg.segment_label == lbl]
    stats["segments"][lbl] = {
        "n": int(len(s)),
        "share_n": round(len(s) / len(seg) * 100, 2),
        "R": round(float(s.R.mean()), 1),
        "F": round(float(s.F.mean()), 1),
        "M": round(float(s.M.mean()), 2),
        "revenue": round(float(s.M.sum()), 2),
        "share_rev": round(float(s.M.sum() / seg.M.sum() * 100), 2),
    }

with open(os.path.join(BASE, "stats.json"), "w", encoding="utf-8") as f:
    json.dump(stats, f, ensure_ascii=False, indent=2)
print(json.dumps({k: v for k, v in stats.items() if k != "segments"}, ensure_ascii=False, indent=1))
for k, v in stats["segments"].items():
    print(k, v)

# ---------------------------------------------------------------- 图 1 架构
fig, ax = plt.subplots(figsize=(10, 10.6))
ax.set_xlim(0, 10)
ax.set_ylim(0, 11)
ax.axis("off")


def box(x, y, w, h, text, sub="", fc="#EAF1F8", ec=C_MID, fs=10.5, sfs=8.8):
    ax.add_patch(mpatches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.12",
                                         linewidth=1.0, edgecolor=ec, facecolor=fc))
    ax.text(x + w / 2, y + h / 2 + (0.14 if sub else 0), text, ha="center", va="center",
            fontsize=fs, color="#1A1A1A")
    if sub:
        ax.text(x + w / 2, y + h / 2 - 0.26, sub, ha="center", va="center", fontsize=sfs, color="#595959")


def arrow(x1, y1, x2, y2):
    ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle="-|>", mutation_scale=12,
                                 linewidth=1.0, color=C_GRAY, shrinkA=0, shrinkB=0))


ax.text(5, 10.55, "电商客户价值分析系统总体架构", ha="center", fontsize=13, color=C_MAIN, weight="bold")
layers = [(9.55, "数据源层"), (7.75, "计算层"), (5.95, "存储层"), (4.15, "分析层"), (2.35, "应用层")]
for y, name in layers:
    ax.text(0.12, y + 0.32, name, fontsize=9.5, color="#FFFFFF", ha="left", va="center",
            bbox=dict(boxstyle="round,pad=0.3", fc=C_MAIN, ec="none"))

box(0.6, 9.35, 3.9, 0.9, "UCI Online Retail 原始数据", "541,909 行 × 8 列，CSV 格式")
box(5.2, 9.35, 3.9, 0.9, "HDFS 分布式存储", "/ecommerce/raw，副本数 1")
box(0.6, 7.55, 3.9, 0.95, "PySpark 4.3 分布式计算", "清洗 · 聚合 · RFM 汇总")
box(5.2, 7.55, 3.9, 0.95, "Pandas 单机基线", "同口径复算，逐项对账")
box(2.6, 5.75, 4.8, 0.95, "MySQL 8.0 · ecommerce_rfm", "原始表 / 清洗表 / RFM 表 / 分群表")
box(1.4, 3.95, 3.3, 0.95, "RFM 模型", "分位打分 · 客户价值量化")
box(5.3, 3.95, 3.3, 0.95, "K-means 聚类", "肘部法 + 轮廓系数定 k")
box(0.6, 2.15, 3.9, 0.95, "Streamlit 交互系统", "三页面 · 筛选 / 查询 / 导出")
box(5.2, 2.15, 3.9, 0.95, "Plotly 离线看板", "单文件 HTML，断网可演示")
box(2.6, 0.45, 4.8, 0.75, "结论：三类客户分层与差异化运营建议", "", fc="#DCE6F1", ec=C_MAIN, fs=10)

arrow(2.55, 9.35, 2.55, 8.55)
arrow(7.15, 9.35, 7.15, 8.55)
arrow(2.55, 7.55, 4.2, 6.75)
arrow(7.15, 7.55, 5.8, 6.75)
arrow(5.0, 5.75, 3.05, 4.93)
arrow(5.0, 5.75, 6.95, 4.93)
arrow(3.05, 3.95, 3.05, 3.13)
arrow(6.95, 3.95, 6.95, 3.13)
arrow(3.05, 2.15, 4.2, 1.22)
arrow(6.95, 2.15, 5.8, 1.22)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig01_architecture.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 2 清洗漏斗
fig, ax = plt.subplots(figsize=(8.6, 4.4))
steps = ["原始记录", "去除完全重复", "剔除缺失客户", "剔除退货/负数量", "剔除特殊行", "有效购买记录"]
vals = [raw_n, int(funnel_n.step_clean), int(funnel_n.step_cust), int(funnel_n.step_qty),
        int(funnel_n.step_special), int(funnel_n.step_valid)]
colors = [C_MAIN, "#2A5F8F", C_MID, "#4A8BC2", C_LIGHT, "#BDD7EE"]
bars = ax.barh(range(len(steps))[::-1], vals, color=colors, height=0.62, edgecolor="white")
for i, (v, s) in enumerate(zip(vals, steps)):
    ax.text(v + 6000, len(steps) - 1 - i, f"{v:,}", va="center", fontsize=9.5, color="#333333")
ax.set_yticks(range(len(steps))[::-1])
ax.set_yticklabels(steps, fontsize=9.5)
ax.set_xlim(0, raw_n * 1.14)
ax.set_xlabel("记录数（条）", fontsize=9.5)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.set_title("数据清洗各环节记录数变化", fontsize=11, color=C_MAIN, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig02_clean_funnel.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 3 月度趋势
fig, ax1 = plt.subplots(figsize=(9.6, 4.3))
x = np.arange(len(monthly))
colors = [C_ACC if i == len(monthly) - 1 else C_MID for i in range(len(monthly))]
ax1.bar(x, monthly.revenue / 1000, color=colors, width=0.66, label="销售额")
ax1.set_ylabel("销售额（千英镑）", fontsize=9.5)
ax1.set_xticks(x)
ax1.set_xticklabels(monthly.ym, rotation=60, fontsize=8)
ax1.spines[["top"]].set_visible(False)
ax2 = ax1.twinx()
ax2.plot(x, monthly.orders, color="#7F7F7F", marker="o", markersize=3.2, linewidth=1.3, label="订单数")
ax2.set_ylabel("订单数（单）", fontsize=9.5, labelpad=14)
ax2.spines[["top"]].set_visible(False)

ax1.set_title("2010 年 12 月—2011 年 12 月销售额与订单数月度趋势", fontsize=11, color=C_MAIN, pad=10)
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="upper left", fontsize=9, frameon=False)
ax1.grid(axis="y", linestyle=":", alpha=0.35)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig03_monthly.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 4 商品 Top10
fig, ax = plt.subplots(figsize=(9.0, 4.3))
p = top_prod.iloc[::-1]
labels = [s[:26] + "…" if len(s) > 26 else s for s in p.name]
ax.barh(range(len(p)), p.revenue / 1000, color=C_MID, height=0.62)
for i, v in enumerate(p.revenue / 1000):
    ax.text(v + 1.5, i, f"{v:,.0f}", va="center", fontsize=8.6, color="#333333")
ax.set_yticks(range(len(p)))
ax.set_yticklabels(labels, fontsize=8.6)
ax.set_xlabel("销售额（千英镑）", fontsize=9.5)
ax.set_xlim(0, p.revenue.max() / 1000 * 1.16)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.set_title("销售额排名前 10 的商品", fontsize=11, color=C_MAIN, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig04_top10_products.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 5 国家分布
fig, ax = plt.subplots(figsize=(9.0, 4.4))
c10 = by_country.head(10).iloc[::-1]
total_rev = by_country.revenue.sum()
ax.barh(range(len(c10)), c10.revenue / 1000, color=[C_MAIN if i == len(c10) - 1 else C_MID
                                                   for i in range(len(c10))], height=0.62)
for i, v in enumerate(c10.revenue):
    ax.text(v / 1000 + 30, i, f"{v / 1000:,.0f}（{v / total_rev * 100:.1f}%）", va="center",
            fontsize=8.6, color="#333333")
ax.set_yticks(range(len(c10)))
ax.set_yticklabels(c10.c, fontsize=9)
ax.set_xlabel("销售额（千英镑）", fontsize=9.5)
ax.set_xlim(0, c10.revenue.max() / 1000 * 1.22)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="x", linestyle=":", alpha=0.4)
ax.set_title("销售额排名前 10 的国家（地区）", fontsize=11, color=C_MAIN, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig05_country.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 6 金额分布
fig, ax = plt.subplots(figsize=(8.4, 4.0))
ax.hist(np.log10(rfm.M.clip(lower=1)), bins=42, color=C_MID, edgecolor="white", linewidth=0.6)
ticks = [1, 2, 3, 4, 5]
ax.set_xticks(ticks)
ax.set_xticklabels(["10", "100", "1k", "10k", "100k"], fontsize=9)
ax.set_xlabel("客户累计消费 M（英镑，对数刻度）", fontsize=9.5)
ax.set_ylabel("客户数（人）", fontsize=9.5)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", linestyle=":", alpha=0.4)
ax.axvline(np.log10(rfm.M.median()), color=C_ACC, linestyle="--", linewidth=1.2)
ax.text(np.log10(rfm.M.median()) + 0.08, ax.get_ylim()[1] * 0.9,
        f"中位数 £{rfm.M.median():,.0f}", fontsize=9, color=C_ACC)
ax.set_title("客户累计消费金额分布（对数横轴）", fontsize=11, color=C_MAIN, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig06_amount_dist.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 7 帕累托
fig, ax = plt.subplots(figsize=(8.6, 4.2))
share_cum = np.cumsum(m_sorted) / m_sorted.sum() * 100
pct_cust = np.arange(1, len(m_sorted) + 1) / len(m_sorted) * 100
ax.plot(pct_cust, share_cum, color=C_MAIN, linewidth=1.8, label="累计销售额占比")
ax.plot([0, 100], [0, 100], color=C_GRAY, linestyle="--", linewidth=1.0, label="绝对平均线")
ax.axvline(20, color=C_ACC, linestyle=":", linewidth=1.2)
ax.scatter([20], [pareto20], color=C_ACC, zorder=5, s=28)
ax.annotate(f"前 20% 客户贡献 {pareto20:.1f}%",
            xy=(20, pareto20), xytext=(30, pareto20 - 22), fontsize=9.5, color=C_ACC,
            arrowprops=dict(arrowstyle="->", color=C_ACC, lw=1.0))
ax.set_xlabel("客户累计占比（%，按消费额降序）", fontsize=9.5)
ax.set_ylabel("累计销售额占比（%）", fontsize=9.5)
ax.set_xlim(0, 100)
ax.set_ylim(0, 102)
ax.legend(loc="lower right", fontsize=9, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(linestyle=":", alpha=0.4)
ax.set_title("客户消费额帕累托图", fontsize=11, color=C_MAIN, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig07_pareto.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 8 RFM 分布
fig, axes = plt.subplots(1, 3, figsize=(10.2, 3.4))
specs = [("R", "最近购买间隔 R（天）", "#1F4E79", 60),
         ("F", "购买频次 F（次）", "#2E75B6", 40),
         ("M", "累计消费 M（英镑）", "#9DC3E6", 50)]
for ax, (col, title, color, bins) in zip(axes, specs):
    data = rfm[col]
    if col == "M":
        data = np.log10(data.clip(lower=1))
        ax.set_xlabel("log10(M)", fontsize=9)
    else:
        ax.set_xlabel(title, fontsize=9)
    ax.hist(data, bins=bins, color=color, edgecolor="white", linewidth=0.4)
    ax.set_title(f"{col} 分布", fontsize=10.5, color=C_MAIN)
    ax.set_ylabel("客户数", fontsize=9)
    ax.tick_params(labelsize=8.4)
    ax.spines[["top", "right"]].set_visible(False)
    ax.axvline(data.median(), color=C_ACC, linestyle="--", linewidth=1.0)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig08_rfm_dist.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 9 选 k
fig, ax1 = plt.subplots(figsize=(7.4, 3.9))
ax1.plot(ksel.k, ksel.SSE, marker="o", color=C_MAIN, linewidth=1.6, label="SSE（簇内平方和）")
ax1.set_xlabel("聚类数 k", fontsize=9.5)
ax1.set_ylabel("SSE", fontsize=9.5, color=C_MAIN)
ax1.set_xticks(ksel.k)
ax1.spines[["top"]].set_visible(False)
ax2 = ax1.twinx()
ax2.plot(ksel.k, ksel.silhouette, marker="s", color=C_ACC, linewidth=1.6, label="轮廓系数")
ax2.set_ylabel("轮廓系数", fontsize=9.5, color=C_ACC)
ax2.spines[["top"]].set_visible(False)
for _, r in ksel.iterrows():
    ax2.annotate(f"{r.silhouette:.4f}", (r.k, r.silhouette), textcoords="offset points",
                 xytext=(0, 8), ha="center", fontsize=8.2, color=C_ACC)
ax1.axvline(3, color=C_GRAY, linestyle=":", linewidth=1.0)
ax1.set_title("肘部法与轮廓系数选 k", fontsize=11, color=C_MAIN, pad=10)
h1, l1 = ax1.get_legend_handles_labels()
h2, l2 = ax2.get_legend_handles_labels()
ax1.legend(h1 + h2, l1 + l2, loc="center right", fontsize=8.8, frameon=False)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig09_k_selection.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 10 聚类散点
fig, axes = plt.subplots(1, 2, figsize=(10.4, 4.2))
pairs = [("R", "M", "最近购买间隔 R（天）", "累计消费 M（英镑）", False, True),
         ("F", "M", "购买频次 F（次）", "累计消费 M（英镑）", True, True)]
seg_colors2 = {"重要价值客户": "#1F4E79", "一般发展客户": "#C55A11", "一般挽留客户": "#A6A6A6"}
for ax, (xc, yc, xl, yl, logx, logy) in zip(axes, pairs):
    for lbl in SEG_ORDER:
        s = seg[seg.segment_label == lbl]
        ax.scatter(s[xc], s[yc].clip(lower=1), s=9, alpha=0.5, color=seg_colors2[lbl],
                   label=f"{lbl}（{len(s)} 人）", edgecolors="none")
    if logx:
        ax.set_xscale("log")
    if logy:
        ax.set_yscale("log")
    ax.set_xlabel(xl, fontsize=9.2)
    ax.set_ylabel(yl + "（对数刻度）", fontsize=9.2)
    ax.tick_params(labelsize=8.2)
    ax.spines[["top", "right"]].set_visible(False)
    ax.grid(linestyle=":", alpha=0.35)
axes[0].set_title("（a）最近购买间隔与消费金额", fontsize=10, color=C_MAIN)
axes[1].set_title("（b）购买频次与消费金额", fontsize=10, color=C_MAIN)
axes[1].legend(fontsize=8.2, frameon=False, loc="lower right")
fig.suptitle("K-means 聚类结果（k=3）", fontsize=11.5, color=C_MAIN, y=1.0)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig10_cluster_scatter.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 11 群画像热力图
prof = seg.groupby("segment_label")[["R", "F", "M"]].mean().loc[SEG_ORDER]
z = (prof - prof.mean()) / prof.std(ddof=0)
z.loc[:, "R"] = -z.loc[:, "R"]  # R 越小越好，取负使数值越大代表价值越高
fig, ax = plt.subplots(figsize=(6.4, 3.6))
im = ax.imshow(z.values, cmap="RdYlBu_r", aspect="auto", vmin=-1.6, vmax=1.6)
ax.set_xticks(range(3))
ax.set_xticklabels(["R（近度）", "F（频度）", "M（额度）"], fontsize=9.5)
ax.set_yticks(range(len(SEG_ORDER)))
ax.set_yticklabels(SEG_ORDER, fontsize=9.5)
for i in range(len(SEG_ORDER)):
    for j, col in enumerate(["R", "F", "M"]):
        v = prof.iloc[i][col]
        txt = f"{v:,.0f}" if col == "M" else f"{v:.1f}"
        ax.text(j, i, txt, ha="center", va="center", fontsize=9,
                color="white" if abs(z.values[i, j]) > 0.9 else "#333333")
ax.set_title("三类客户 RFM 均值画像（底色为标准化得分）", fontsize=10.5, color=C_MAIN, pad=10)
cb = plt.colorbar(im, ax=ax, fraction=0.035, pad=0.02)
cb.set_label("标准化得分（R 已正向化）", fontsize=8.4)
cb.ax.tick_params(labelsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig11_heatmap.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 12 人数与贡献
fig, ax = plt.subplots(figsize=(8.2, 3.6))
x = np.arange(len(SEG_ORDER))
n_share = [stats["segments"][s]["share_n"] for s in SEG_ORDER]
r_share = [stats["segments"][s]["share_rev"] for s in SEG_ORDER]
w = 0.34
b1 = ax.bar(x - w / 2, n_share, w, label="客户人数占比", color=C_LIGHT)
b2 = ax.bar(x + w / 2, r_share, w, label="销售额贡献占比", color=C_MAIN)
for b in list(b1) + list(b2):
    ax.text(b.get_x() + b.get_width() / 2, b.get_height() + 1.2, f"{b.get_height():.1f}%",
            ha="center", fontsize=9, color="#333333")
ax.set_xticks(x)
ax.set_xticklabels(SEG_ORDER, fontsize=9.5)
ax.set_ylabel("占比（%）", fontsize=9.5)
ax.set_ylim(0, 78)
ax.legend(fontsize=9, frameon=False)
ax.spines[["top", "right"]].set_visible(False)
ax.grid(axis="y", linestyle=":", alpha=0.4)
ax.set_title("三类客户的人数占比与销售额贡献对比", fontsize=11, color=C_MAIN, pad=10)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig12_share.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

# ---------------------------------------------------------------- 图 13 相关性
fig, ax = plt.subplots(figsize=(5.4, 4.0))
corr = rfm[["R", "F", "M", "aov"]].corr(method="spearman")
labels = ["R", "F", "M", "客单价"]
im = ax.imshow(corr.values, cmap="RdBu_r", vmin=-1, vmax=1)
ax.set_xticks(range(4)); ax.set_xticklabels(labels, fontsize=9.5)
ax.set_yticks(range(4)); ax.set_yticklabels(labels, fontsize=9.5)
for i in range(4):
    for j in range(4):
        ax.text(j, i, f"{corr.values[i, j]:.2f}", ha="center", va="center", fontsize=8.6,
                color="white" if abs(corr.values[i, j]) > 0.6 else "#333333")
ax.set_title("RFM 与客单价的 Spearman 相关系数", fontsize=10.5, color=C_MAIN, pad=10)
cb = plt.colorbar(im, ax=ax, fraction=0.042, pad=0.02)
cb.ax.tick_params(labelsize=8)
plt.tight_layout()
plt.savefig(os.path.join(FIG, "fig13_corr.png"), dpi=200, bbox_inches="tight", facecolor="white")
plt.close()

conn.close()
print("\n图片已生成：", len([f for f in os.listdir(FIG) if f.endswith('.png')]), "张")
