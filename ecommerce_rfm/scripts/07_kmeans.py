# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""07_kmeans.py — 第7步：K-means 聚类
流程：
1. 读 customer_rfm（4,334 位客户）
2. R/F/M 右偏严重 → log1p 变换 → StandardScaler 标准化
3. 肘部法(SSE) + 轮廓系数，在 k=3~5 中选最优 k
4. K-means 聚类（random_state=42 保证可复现）
5. 簇画像（各簇 R/F/M 均值）→ 按特征映射运营标签
6. 写入 MySQL customer_segments 表，行数核对
产出：outputs/segments/customer_segments.csv、cluster_summary.csv、outputs/cluster_report.md、k_selection.csv
"""
import pandas as pd
import numpy as np
import json, os
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sqlalchemy import create_engine, text

PROC = _ROOT + r"\ecommerce_rfm\data\processed\online_retail_clean.pkl"
RFM = _ROOT + r"\ecommerce_rfm\outputs\rfm\customer_rfm.csv"
OUT = _ROOT + r"\ecommerce_rfm\outputs\segments"
os.makedirs(OUT, exist_ok=True)

rfm = pd.read_csv(RFM)
X_raw = rfm[["R", "F", "M"]].copy()
print(f"输入：{len(rfm):,} 位客户")

# 偏态处理：log1p（F、M 右偏），R 本身也偏（多数客户近期买过）
X_log = np.log1p(X_raw)
scaler = StandardScaler()
X = scaler.fit_transform(X_log)

# ---- 选 k：肘部 + 轮廓系数 ----
rows = []
for k in range(3, 6):
    km = KMeans(n_clusters=k, n_init=10, random_state=42).fit(X)
    sil = silhouette_score(X, km.labels_)
    rows.append({"k": k, "SSE": round(float(km.inertia_), 1), "silhouette": round(float(sil), 4)})
sel = pd.DataFrame(rows)
sel.to_csv(os.path.join(OUT, "k_selection.csv"), index=False)
best = sel.loc[sel["silhouette"].idxmax(), "k"]
print(sel.to_string(index=False))
print(f"轮廓系数最优 k = {best}")

# ---- 最终聚类 ----
km = KMeans(n_clusters=int(best), n_init=10, random_state=42)
rfm["cluster"] = km.fit_predict(X)

# ---- 簇画像 ----
prof = rfm.groupby("cluster").agg(
    n=("CustomerID", "size"),
    R_mean=("R", "mean"), F_mean=("F", "mean"), M_mean=("M", "mean"),
    M_sum=("M", "sum")).round(1).reset_index()
gR, gF, gM = rfm["R"].mean(), rfm["F"].mean(), rfm["M"].mean()

def label(row):
    hi = lambda v, g: v >= g
    r_hi, f_hi, m_hi = hi(row["R_mean"], gR), hi(row["F_mean"], gF), hi(row["M_mean"], gM)
    if (not r_hi) and f_hi and m_hi:  return "重要价值客户"     # 最近买、频次高、金额大
    if (not r_hi) and m_hi:           return "重要保持客户"     # 最近买过、金额大但频次不高
    if r_hi and f_hi and m_hi:        return "重要挽留客户"     # 曾经高价值，最近未买
    if (not r_hi) and (not m_hi):     return "一般发展客户"     # 最近买、小额低频（新客/潜力）
    if r_hi and (not m_hi):           return "一般挽留客户"     # 小额低频且久未买（流失）
    return "一般客户"

prof["segment_label"] = prof.apply(label, axis=1)
# 同名冲突防护：k 较大时可能出现重复标签，追加序号
if prof["segment_label"].duplicated().any():
    dup = prof["segment_label"].value_counts()
    for lab in dup[dup > 1].index:
        idx = prof.index[prof["segment_label"] == lab]
        for i, ix in enumerate(idx[1:], 2):
            prof.loc[ix, "segment_label"] = f"{lab}{i}"

seg_map = dict(zip(prof["cluster"], prof["segment_label"]))
rfm["segment_label"] = rfm["cluster"].map(seg_map)

# ---- 核对 ----
assert len(rfm) == 4334, "客户数变化！"
assert rfm["cluster"].notna().all()
print("\n簇画像（全局均值：R=%.0f F=%.1f M=£%.0f）:" % (gR, gF, gM))
print(prof.assign(M_share=(prof["M_sum"]/rfm["M"].sum()*100).round(1)).to_string(index=False))

rfm_out = rfm[["CustomerID", "R", "F", "M", "cluster", "segment_label", "last_purchase", "first_purchase"]]
rfm_out.to_csv(os.path.join(OUT, "customer_segments.csv"), index=False)
prof.to_csv(os.path.join(OUT, "cluster_summary.csv"), index=False)

# ---- 写 MySQL ----
_PORT = int(os.environ.get("MYSQL_PORT", "3307"))   # 随包绿色版 MySQL 默认 3307
engine = create_engine("mysql+pymysql://root:123456@localhost:%d/ecommerce_rfm?charset=utf8mb4" % _PORT)
with engine.begin() as c:
    c.execute(text("""CREATE TABLE IF NOT EXISTS customer_segments (
      customer_id INT PRIMARY KEY,
      R SMALLINT NOT NULL, F INT NOT NULL, M DECIMAL(12,2) NOT NULL,
      cluster INT NOT NULL, segment_label VARCHAR(50) NOT NULL,
      last_purchase DATETIME NOT NULL, first_purchase DATETIME NOT NULL,
      KEY idx_cluster (cluster)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"""))
    c.execute(text("DELETE FROM customer_segments"))  # 幂等重跑
seg = rfm_out.rename(columns={"CustomerID": "customer_id"})
seg.to_sql("customer_segments", engine, if_exists="append", index=False, method="multi", chunksize=2000)

with engine.connect() as c:
    n_db = c.execute(text("SELECT COUNT(*) FROM customer_segments")).scalar()
    chk = c.execute(text("""SELECT segment_label, COUNT(*) n, ROUND(AVG(R),0) R, ROUND(AVG(F),1) F,
        ROUND(AVG(M),0) M FROM customer_segments GROUP BY segment_label ORDER BY M DESC""")).fetchall()
print(f"\nMySQL customer_segments 行数: {n_db}（应=4,334）")
print("库内分群核对:")
for r in chk:
    print(f"  {r[0]}: {r[1]}人, R均值{r[2]:.0f}, F均值{r[3]}, M均值£{r[4]:,.0f}")

# ---- 聚类报告 ----
share = prof.assign(m_share=(prof["M_sum"]/rfm["M"].sum()*100).round(1))
with open(_ROOT + r"\ecommerce_rfm\outputs\cluster_report.md", "w", encoding="utf-8") as f:
    f.write("# K-means 聚类报告（第7步）\n\n")
    f.write("## 方法\n- 输入：4,334 位客户的 R/F/M\n- 右偏处理：log1p → StandardScaler 标准化\n")
    f.write("- 选 k：k=3~5 网格，肘部法(SSE) + 轮廓系数，取轮廓系数最优 k=%d\n" % best)
    f.write("- KMeans(n_clusters=%d, n_init=10, random_state=42)，结果可复现\n\n" % best)
    f.write("## 选 k 依据\n\n" + sel.to_markdown(index=False) + "\n\n")
    f.write("## 簇画像与运营标签（全局均值 R=%.0f 天，F=%.1f 单，M=£%.0f）\n\n" % (gR, gF, gM))
    f.write(share.to_markdown(index=False) + "\n\n")
    f.write("## 分群口径\n标签按各簇 R/F/M 均值相对全局均值的高低组合映射：\n")
    f.write("- 最近买过+高频+高额 → **重要价值**；最近买过+高额低频 → **重要保持**；久未买+高价值 → **重要挽留**；")
    f.write("最近买过+小额低频 → **一般发展**；久未买+小额低频 → **一般挽留**\n")
    f.write("## 运营建议\n")
    for _, r in prof.iterrows():
        lab = r["segment_label"]
        advice = {
            "重要价值客户": "VIP 维护：专属客服、优先发货、会员权益升级，防止被竞品挖走",
            "重要保持客户": "提频：大额但低频，用套装/满减/新品推送提升购买次数",
            "重要挽留客户": "召回：曾高价值但久未买，定向优惠+回访，优先级最高",
            "一般发展客户": "培养：新客/低频小额，首单复购券、爆款推荐养成习惯",
            "一般挽留客户": "低成本唤醒：便宜渠道批量触达，不投入过多资源",
            "一般客户": "观察：维持常规触达",
        }.get(lab, "常规维护")
        f.write(f"- **{lab}**（{int(r['n']):,} 人，贡献销售额 {share.loc[share['cluster']==r['cluster'],'m_share'].iloc[0]}%）：{advice}\n")

print("\n✅ 第7步完成：outputs/cluster_report.md, outputs/segments/*.csv, MySQL customer_segments")
