# -*- coding: utf-8 -*-
"""08_dashboard.py — 第8步：交互式可视化看板
Plotly 生成单文件自包含 HTML（内嵌 plotly.js，离线可开）：
- KPI 卡片：销售额/客户/订单/复购率
- 月度趋势（不完整月份橙色标注）
- Top10 商品条形图
- 客户分群人数 vs 销售额贡献（双图）
- RFM 散点（M-F，log 轴，按分群着色，点图例可筛选群体）
配色遵循中国股市惯例无涉；金额单位 GBP。
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import os

OUT = r"D:\graduation_project\ecommerce_rfm\outputs"
DASH = r"D:\graduation_project\ecommerce_rfm\outputs\dashboard"
os.makedirs(DASH, exist_ok=True)

trend = pd.read_csv(os.path.join(OUT, "analysis", "monthly_trend.csv"))
top10 = pd.read_csv(os.path.join(OUT, "analysis", "top10_products.csv"))
seg = pd.read_csv(os.path.join(OUT, "segments", "customer_segments.csv")).rename(columns={"CustomerID": "customer_id"})
prof = pd.read_csv(os.path.join(OUT, "segments", "cluster_summary.csv"))

# ---- 图1：月度趋势（不完整月标橙）----
trend["complete"] = trend["year_month"].isin([f"2011-{m:02d}" for m in range(1, 12)])
t1 = trend[trend["complete"]]; t0 = trend[~trend["complete"]]
fig1 = go.Figure()
fig1.add_bar(x=t1["year_month"], y=t1["revenue"], marker_color="#2E86C1",
             name="完整月", hovertemplate="%{x}<br>销售额 £%{y:,.0f}<br>%{customdata:,} 单",
             customdata=t1["orders"])
fig1.add_bar(x=t0["year_month"], y=t0["revenue"], marker_color="#F5B041",
             name="不完整月(剔除比较)", hovertemplate="%{x} 数据不完整<br>销售额 £%{y:,.0f}",
             customdata=t0["orders"])
fig1.update_layout(title="月度销售趋势（真实商品销售口径）", xaxis_title="月份", yaxis_title="销售额 (GBP)",
                   height=380, showlegend=True, bargap=0.25)

# ---- 图2：Top10 商品 ----
top10s = top10.sort_values("revenue")
fig2 = go.Figure(go.Bar(x=top10s["revenue"], y=top10s["StockCode"] + "：" + top10s["desc"].str.slice(0, 22),
                        orientation="h", marker_color="#48C9B0",
                        hovertemplate="%{y}<br>销售额 £%{x:,.0f}<extra></extra>"))
fig2.update_layout(title="销售额 Top10 商品", xaxis_title="销售额 (GBP)", height=400)

# ---- 图3：分群人数 & 图4：分群销售额贡献 ----
prof_s = prof.sort_values("M_sum", ascending=False)
labels = prof_s["segment_label"]
colors = {"重要价值客户": "#C0392B", "重要保持客户": "#E67E22", "重要挽留客户": "#8E44AD",
          "一般发展客户": "#2E86C1", "一般挽留客户": "#95A5A6", "一般客户": "#BDC3C7"}
cs = [colors.get(l, "#5D6D7E") for l in labels]
fig3 = go.Figure(go.Pie(labels=labels, values=prof_s["n"], hole=0.45, marker_colors=cs,
                        hovertemplate="%{label}<br>%{value:,} 人（%{percent}）<extra></extra>"))
fig3.update_layout(title="客户分群人数占比", height=380)
fig4 = go.Figure(go.Bar(x=labels, y=prof_s["M_sum"], marker_color=cs,
                        hovertemplate="%{x}<br>销售额 £%{y:,.0f}<extra></extra>"))
fig4.update_layout(title="各群体销售额贡献", yaxis_title="销售额 (GBP)", height=380)

# ---- 图5：RFM 散点（F × M，log 轴，按群体着色 → 点图例筛选）----
seg_p = seg.merge(prof[["cluster", "segment_label"]].rename(columns={"segment_label": "lab"}),
                  on="cluster", how="left")
seg_p["label"] = seg_p["segment_label"]
fig5 = go.Figure()
for lab in ["重要价值客户", "一般发展客户", "一般挽留客户"]:
    d = seg_p[seg_p["label"] == lab]
    fig5.add_scatter(x=d["F"], y=d["M"], mode="markers", name=lab,
                     marker=dict(size=7, opacity=0.55, color=colors.get(lab, "#5D6D7E")),
                     hovertemplate="客户 %{customdata[0]}<br>F %{x} 单<br>M £%{customdata[1]:,.0f}<br>R %{customdata[2]} 天<extra>" + lab + "</extra>",
                     customdata=np.stack([d["customer_id"], d["M"], d["R"]], axis=-1))
fig5.update_layout(title="客户 F × M 散点（按分群着色，点击图例筛选群体）",
                   xaxis_title="购买频次 F（订单数）", yaxis_title="消费金额 M (GBP, 对数轴)",
                   yaxis_type="log", height=460)

# ---- KPI ----
total_m = prof_s["M_sum"].sum()
kpi = f"""
<div style="display:flex;gap:16px;margin:8px 0 18px 0;">
 <div style="flex:1;background:#1a5276;color:#fff;border-radius:10px;padding:14px 18px;">
   <div style="font-size:13px;opacity:.8;">有效销售总额（GBP）</div><div style="font-size:26px;font-weight:700;">£{total_m:,.0f}</div></div>
 <div style="flex:1;background:#21618c;color:#fff;border-radius:10px;padding:14px 18px;">
   <div style="font-size:13px;opacity:.8;">有效客户数</div><div style="font-size:26px;font-weight:700;">{len(seg):,}</div></div>
 <div style="flex:1;background:#2874a6;color:#fff;border-radius:10px;padding:14px 18px;">
   <div style="font-size:13px;opacity:.8;">有效订单数</div><div style="font-size:26px;font-weight:700;">18,402</div></div>
 <div style="flex:1;background:#2e86c1;color:#fff;border-radius:10px;padding:14px 18px;">
   <div style="font-size:13px;opacity:.8;">重要价值客户贡献</div><div style="font-size:26px;font-weight:700;">67.8%</div></div>
</div>"""

cfg = {"displayModeBar": False, "responsive": True}
divs = "".join(
    f'<div style="background:#fff;border-radius:12px;box-shadow:0 1px 6px rgba(0,0,0,.08);padding:14px 16px;margin-bottom:18px;">{fig.to_html(full_html=False, include_plotlyjs=js, config=cfg)}</div>'
    for fig, js in [(fig1, True), (fig2, False), (fig3, False), (fig4, False), (fig5, False)])

html = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>电商客户价值分析看板 — RFM 与 K-means</title></head>
<body style="margin:0;background:#f4f6f8;font-family:'Microsoft YaHei',sans-serif;">
<div style="max-width:1080px;margin:0 auto;padding:20px 16px;">
<div style="background:linear-gradient(90deg,#154360,#1a5276);color:#fff;border-radius:12px;padding:18px 22px;margin-bottom:6px;">
<div style="font-size:22px;font-weight:700;">电商客户价值分析看板</div>
<div style="font-size:13px;opacity:.85;margin-top:4px;">UCI Online Retail ｜ 2010-12-01 ~ 2011-12-09 ｜ RFM + K-means(k=3) ｜ 数据口径：清洗后有效购买</div></div>
{kpi}
{divs}
<div style="font-size:12px;color:#7f8c8d;text-align:center;padding:6px 0 20px 0;">
注：2010-12（仅1天）与 2011-12（仅9天）数据不完整，已单独标色，不参与月度间比较；散点图 M 轴为对数刻度。</div>
</div></body></html>"""

path = os.path.join(DASH, "客户价值分析看板.html")
with open(path, "w", encoding="utf-8") as f:
    f.write(html)
print(f"✅ 看板已生成：{path}（{os.path.getsize(path)/1e6:.1f} MB，自包含离线可开）")
