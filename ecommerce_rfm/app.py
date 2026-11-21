# -*- coding: utf-8 -*-
"""
app.py — 交互式可视化网页（课设第 8 步：Streamlit + Plotly）

三个页面：
  1. 销售概览      日期筛选 / 国家筛选 → 月度趋势、商品 Top10、国家分布
  2. 客户价值分析  RFM 分布、客户累计消费（帕累托/集中度）、客户特征表（可查询、可导出）
  3. 客户分群      群筛选 → 人数、消费贡献、RFM 画像热力图、RFM 3D 散点、名单导出

数据源：MySQL ecommerce_rfm（transactions_clean / customer_rfm / customer_segments）
口径：is_valid_purchase=1 AND is_special=0 AND Quantity>0（与 04_analysis.py 一致）
启动：双击项目根目录 6_open_streamlit.bat
"""
import os
import socket

import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import create_engine, text

# ----------------------------------------------------------------------------
# 页面配置
# ----------------------------------------------------------------------------
st.set_page_config(
    page_title="电商客户价值分析 · RFM + K-means",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

def _db_url():
    """优先用随包内置的绿色版 MySQL(3307)，其次退回本机安装版(3306)。
    也可用环境变量 RFM_DB_PORT 强制指定端口。"""
    forced = os.environ.get("RFM_DB_PORT")
    ports = [forced] if forced else ["3307", "3306"]
    for p in ports:
        try:
            with socket.create_connection(("127.0.0.1", int(p)), timeout=0.4):
                return ("mysql+pymysql://root:123456@127.0.0.1:%s"
                        "/ecommerce_rfm?charset=utf8mb4" % p)
        except OSError:
            continue
    return ("mysql+pymysql://root:123456@127.0.0.1:3307"
            "/ecommerce_rfm?charset=utf8mb4")


DB_URL = _db_url()

# 分群配色（与 08_dashboard.py 保持一致）
COLORS = {
    "重要价值客户": "#C0392B",
    "重要保持客户": "#E67E22",
    "重要挽留客户": "#8E44AD",
    "一般发展客户": "#2E86C1",
    "一般挽留客户": "#95A5A6",
    "一般客户": "#BDC3C7",
}
FONT = dict(family="Microsoft YaHei, PingFang SC, sans-serif", size=13)
# 数据首尾月天数不足，不参与月度比较
INCOMPLETE_MONTHS = {"2010-12", "2011-12"}


# ----------------------------------------------------------------------------
# 数据层（缓存）
# ----------------------------------------------------------------------------
@st.cache_resource
def get_engine():
    return create_engine(DB_URL, pool_pre_ping=True)


@st.cache_data(show_spinner="正在从 MySQL 读取交易明细…")
def load_transactions() -> pd.DataFrame:
    """有效购买明细（真实商品口径），仅取分析所需列。"""
    sql = """
        SELECT InvoiceNo, InvoiceDate, Country, CustomerID,
               amount, `year_month`, StockCode, Description, Quantity
        FROM transactions_clean
        WHERE is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0
    """
    with get_engine().connect() as conn:
        df = pd.read_sql(text(sql), conn)
    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    df["Description"] = df["Description"].fillna("(无描述)")
    return df


@st.cache_data(show_spinner="正在读取 RFM 与分群结果…")
def load_rfm() -> pd.DataFrame:
    with get_engine().connect() as conn:
        df = pd.read_sql(text("SELECT * FROM customer_rfm"), conn)
    return df


@st.cache_data(show_spinner="正在读取分群结果…")
def load_segments() -> pd.DataFrame:
    with get_engine().connect() as conn:
        df = pd.read_sql(text("SELECT * FROM customer_segments"), conn)
    return df


def check_db() -> bool:
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception as e:  # noqa: BLE001
        st.error(
            f"**无法连接 MySQL 数据库**（当前尝试：`{DB_URL.split('@')[-1]}`，root/123456）\n\n"
            f"错误信息：`{e}`\n\n"
            "排查：① 先双击项目根目录 `0_start_mysql.bat` 启动内置数据库；"
            "② 数据损坏时双击 `5_restore_mysql.bat` 重建；"
            "③ 若改过密码或端口，设置环境变量 `RFM_DB_PORT` 或修改 `app.py` 顶部 `_db_url()`。"
        )
        return False


# ----------------------------------------------------------------------------
# 侧边栏
# ----------------------------------------------------------------------------
with st.sidebar:
    st.markdown("### 📊 电商客户价值分析")
    st.caption("UCI Online Retail ｜ RFM + K-means")
    page = st.radio(
        "导航",
        ["📈 销售概览", "👥 客户价值分析", "🎯 客户分群"],
        label_visibility="collapsed",
    )
    st.divider()
    st.caption("数据口径：清洗后有效购买（剔除取消/退货/异常价/特殊商品码）")
    st.caption("金额单位：英镑 GBP ｜ 数据集时间：2010-12-01 ~ 2011-12-09")

if not check_db():
    st.stop()

tx = load_transactions()
rfm = load_rfm()
seg = load_segments()

# 全局日期范围
D_MIN, D_MAX = tx["InvoiceDate"].min().date(), tx["InvoiceDate"].max().date()
ALL_COUNTRIES = sorted(tx["Country"].unique().tolist())


def fmt_money(v: float) -> str:
    return f"£{v:,.0f}"


def log_hist(frame: pd.DataFrame, col: str, color: str, title: str,
             height: int, nbins: int = 40):
    """对数刻度直方图：先做 log10 变换再分箱，避免 Plotly 在 log 轴上分箱不均导致柱子消失。"""
    vals = np.log10(frame[col].clip(lower=1))
    fig = px.histogram(x=vals, nbins=nbins, color_discrete_sequence=[color])
    fig.update_xaxes(
        tickvals=[0, 1, 2, 3, 4, 5],
        ticktext=["£1", "£10", "£100", "£1k", "£10k", "£100k"],
        title=f"{col} (GBP · 对数刻度)",
    )
    fig.update_layout(title=title, yaxis_title="客户数", font=FONT,
                      height=height, bargap=0.03)
    return fig


# ============================================================================
# 页面 1：销售概览
# ============================================================================
if page == "📈 销售概览":
    st.markdown("## 销售概览")
    st.caption("回答：商家的销售情况有什么时间变化？哪些商品与国家贡献最大？")

    c1, c2, c3 = st.columns([2, 2, 1])
    with c1:
        date_range = st.date_input(
            "日期范围", value=(D_MIN, D_MAX), min_value=D_MIN, max_value=D_MAX, key="p1_date"
        )
    with c2:
        countries = st.multiselect(
            "国家筛选（不选 = 全部国家）", ALL_COUNTRIES, default=[], key="p1_country"
        )
    with c3:
        st.metric("筛选后国家数", len(countries) if countries else len(ALL_COUNTRIES))

    start = date_range[0] if isinstance(date_range, (tuple, list)) and len(date_range) > 0 else D_MIN
    end = date_range[1] if isinstance(date_range, (tuple, list)) and len(date_range) > 1 else D_MAX

    d = tx[(tx["InvoiceDate"].dt.date >= start) & (tx["InvoiceDate"].dt.date <= end)]
    if countries:
        d = d[d["Country"].isin(countries)]

    if d.empty:
        st.warning("当前筛选条件下没有数据，请放宽日期或国家范围。")
        st.stop()

    # ---- KPI ----
    revenue = d["amount"].sum()
    orders = d["InvoiceNo"].nunique()
    cust = d["CustomerID"].nunique()
    k1, k2, k3, k4 = st.columns(4)
    k1.metric("销售额", fmt_money(revenue))
    k2.metric("订单数", f"{orders:,}")
    k3.metric("有交易客户数", f"{cust:,}")
    k4.metric("客单价", fmt_money(revenue / orders if orders else 0))

    # ---- 图1：月度销售额趋势（不完整月单独标色）----
    m = (
        d.groupby("year_month")
        .agg(revenue=("amount", "sum"), orders=("InvoiceNo", "nunique"))
        .reset_index()
    )
    m["complete"] = ~m["year_month"].isin(INCOMPLETE_MONTHS)
    mc, mi = m[m["complete"]], m[~m["complete"]]

    fig1 = go.Figure()
    fig1.add_bar(
        x=mc["year_month"], y=mc["revenue"], name="完整月", marker_color="#2E86C1",
        hovertemplate="%{x}<br>销售额 £%{y:,.0f}<extra></extra>",
    )
    fig1.add_bar(
        x=mi["year_month"], y=mi["revenue"], name="不完整月（不参与比较）", marker_color="#F5B041",
        hovertemplate="%{x}（数据不完整）<br>销售额 £%{y:,.0f}<extra></extra>",
    )
    fig1.add_scatter(
        x=m["year_month"], y=m["orders"], name="订单数（右轴）", mode="lines+markers",
        line=dict(color="#C0392B", width=2), marker=dict(size=6), yaxis="y2",
        hovertemplate="%{x}<br>%{y:,} 单<extra></extra>",
    )
    fig1.update_layout(
        title="图1 · 月度销售额趋势（柱）与订单数（线）",
        xaxis_title="月份", yaxis_title="销售额 (GBP)", font=FONT, height=420,
        yaxis2=dict(title="订单数", overlaying="y", side="right", showgrid=False),
        legend=dict(orientation="h", y=1.12), bargap=0.25, hovermode="x unified",
    )
    st.plotly_chart(fig1, width="stretch", key="f1")
    peak = m.loc[m["revenue"].idxmax()]
    st.info(
        f"**解读**：筛选区间内销售额最高的是 **{peak['year_month']}（{fmt_money(peak['revenue'])}）**，"
        f"月度均值 {fmt_money(m['revenue'].mean())}。"
        + (" 橙色柱为首尾不完整月份，不能与完整月直接比较。" if len(mi) else "")
    )

    # ---- 图2：商品销售额 Top10 ----
    prod = (
        d.groupby("StockCode")
        .agg(revenue=("amount", "sum"), desc=("Description", "first"), qty=("Quantity", "sum"))
        .nlargest(10, "revenue")
        .sort_values("revenue")
        .reset_index()
    )
    fig2 = go.Figure(
        go.Bar(
            x=prod["revenue"],
            y=prod["StockCode"] + "：" + prod["desc"].str.slice(0, 22),
            orientation="h", marker_color="#48C9B0",
            hovertemplate="%{y}<br>销售额 £%{x:,.0f}<extra></extra>",
        )
    )
    fig2.update_layout(
        title="图2 · 商品销售额 Top10", xaxis_title="销售额 (GBP)", font=FONT, height=420,
    )
    st.plotly_chart(fig2, width="stretch", key="f2")
    top1 = prod.iloc[-1]
    st.info(
        f"**解读**：Top10 商品合计 {fmt_money(prod['revenue'].sum())}，"
        f"占筛选区间销售额的 **{prod['revenue'].sum() / revenue * 100:.1f}%**；"
        f"排名第一的是 `{top1['StockCode']}`（{top1['desc'][:30]}），销售额 {fmt_money(top1['revenue'])}。"
    )

    # ---- 图3：国家销售额分布（Top15）----
    cty = (
        d.groupby("Country").agg(revenue=("amount", "sum"), orders=("InvoiceNo", "nunique"))
        .sort_values("revenue", ascending=False).reset_index()
    )
    top15 = cty.head(15).sort_values("revenue")
    fig3 = go.Figure(
        go.Bar(
            x=top15["revenue"], y=top15["Country"], orientation="h", marker_color="#5DADE2",
            hovertemplate="%{y}<br>销售额 £%{x:,.0f}<extra></extra>",
        )
    )
    fig3.update_layout(
        title="图3 · 国家销售额分布（Top15）", xaxis_title="销售额 (GBP)", font=FONT, height=460,
    )
    st.plotly_chart(fig3, width="stretch", key="f3")
    uk_share = cty.iloc[0]["revenue"] / revenue * 100 if revenue else 0
    rest = cty.iloc[15:]
    st.info(
        f"**解读**：**{cty.iloc[0]['Country']}** 销售额 {fmt_money(cty.iloc[0]['revenue'])}，"
        f"占 {uk_share:.1f}%，业务高度集中于本土市场；"
        + (f"其余 {len(rest)} 个国家合计仅占 {rest['revenue'].sum() / revenue * 100:.1f}%。" if len(rest) else "")
    )

    with st.expander("查看国家销售额明细表 / 导出"):
        show = cty.rename(columns={"Country": "国家", "revenue": "销售额(GBP)", "orders": "订单数"})
        st.dataframe(show, width="stretch", hide_index=True)
        st.download_button(
            "⬇ 下载国家销售额 CSV",
            show.to_csv(index=False).encode("utf-8-sig"),
            "country_sales.csv", "text/csv", key="dl_cty",
        )


# ============================================================================
# 页面 2：客户价值分析
# ============================================================================
elif page == "👥 客户价值分析":
    st.markdown("## 客户价值分析")
    st.caption("回答：不同客户的购买频次、消费金额、最近购买时间差异有多大？销售是否依赖少数客户？")

    # ---- 图4：客户累计消费金额分布 + 帕累托集中度 ----
    spend = rfm.sort_values("M", ascending=False).reset_index(drop=True)
    spend["rank_pct"] = (spend.index + 1) / len(spend) * 100
    spend["cum_share"] = spend["M"].cumsum() / spend["M"].sum() * 100

    col_a, col_b = st.columns(2)
    with col_a:
        fig4a = log_hist(rfm, "M", "#2E86C1", "图4a · 客户累计消费金额分布（对数横轴）", 400, 50)
        st.plotly_chart(fig4a, width="stretch", key="f4a")
        med = rfm["M"].median()
        st.info(f"**解读**：客户消费中位数 **{fmt_money(med)}**，均值 {fmt_money(rfm['M'].mean())}，"
                f"长尾明显——少数高消费客户拉高了均值。")

    with col_b:
        fig4b = go.Figure()
        fig4b.add_scatter(
            x=spend["rank_pct"], y=spend["cum_share"], mode="lines",
            line=dict(color="#C0392B", width=3), fill="tozeroy",
            fillcolor="rgba(192,57,43,0.10)",
            hovertemplate="前 %{x:.1f}% 客户<br>贡献 %{y:.1f}% 销售额<extra></extra>",
        )
        fig4b.add_vline(x=20, line_dash="dash", line_color="#7F8C8D")
        top20_share = spend.loc[spend["rank_pct"] <= 20, "cum_share"].max()
        fig4b.add_annotation(
            x=20, y=top20_share, text=f"前20%贡献 {top20_share:.1f}%",
            showarrow=True, arrowhead=2, ax=40, ay=-30, font=dict(color="#C0392B", size=13),
        )
        fig4b.update_layout(
            title="图4b · 帕累托图：客户消费集中度",
            xaxis_title="客户累计占比 (%)", yaxis_title="累计销售额占比 (%)",
            font=FONT, height=400,
        )
        st.plotly_chart(fig4b, width="stretch", key="f4b")
        st.info(f"**解读**：**前 20% 的客户贡献了 {top20_share:.1f}% 的销售额**，"
                f"符合典型帕累托特征，说明维护高价值客户是营收关键。")

    st.divider()

    # ---- 图5：RFM 三指标分布（受下面的指标筛选联动）----
    st.markdown("#### RFM 分布与客户查询")
    f1, f2, f3 = st.columns([1, 1, 1])
    r_lo, r_hi = int(rfm["R"].min()), int(rfm["R"].quantile(0.99))
    f_lo, f_hi = int(rfm["F"].min()), int(rfm["F"].quantile(0.99))
    m_lo, m_hi = float(rfm["M"].min()), float(rfm["M"].quantile(0.99))
    with f1:
        r_range = st.slider("R · 最近购买距今天数", r_lo, r_hi, (r_lo, r_hi), key="p2_r")
    with f2:
        f_range = st.slider("F · 购买频次（订单数）", f_lo, f_hi, (f_lo, f_hi), key="p2_f")
    with f3:
        m_range = st.slider(
            "M · 累计消费 (GBP)", float(np.floor(m_lo)), float(np.ceil(m_hi)),
            (float(np.floor(m_lo)), float(np.ceil(m_hi))), key="p2_m",
        )

    view = rfm[
        rfm["R"].between(*r_range) & rfm["F"].between(*f_range) & rfm["M"].between(*m_range)
    ]
    st.caption(f"当前筛选命中 **{len(view):,}** 位客户（全量 {len(rfm):,} 位）")

    g1, g2, g3 = st.columns(3)
    for col, metric, label, color in [
        (g1, "R", "图5a · R 分布（越小越近）", "#E67E22"),
        (g2, "F", "图5b · F 分布（订单数）", "#48C9B0"),
        (g3, "M", "图5c · M 分布（对数轴）", "#2E86C1"),
    ]:
        with col:
            if metric == "M":
                fig = log_hist(view, "M", color, label, 300, 40)
            else:
                fig = px.histogram(view, x=metric, nbins=40, color_discrete_sequence=[color])
                fig.update_layout(
                    title=label, font=FONT, height=300, bargap=0.03,
                    xaxis_title=metric, yaxis_title="客户数",
                )
            st.plotly_chart(fig, width="stretch", key=f"f5{metric}")
    st.info(
        f"**解读**：筛选后 R 中位数 {view['R'].median() if len(view) else 0:.0f} 天、"
        f"F 中位数 {view['F'].median() if len(view) else 0:.0f} 单、"
        f"M 中位数 {fmt_money(view['M'].median() if len(view) else 0)}；"
        "R/F/M 均呈右偏长尾，因此聚类前需做 log1p 变换 + 标准化。"
    )

    st.divider()

    # ---- 客户特征表（客户查询 + 导出）----
    st.markdown("#### 客户特征表（可查询、可导出）")
    q = st.text_input("按客户编号查询（支持模糊匹配，如 1785）", value="", key="p2_q")
    table = view.copy()
    if q.strip():
        table = table[table["customer_id"].astype(str).str.contains(q.strip())]
    show = table.rename(columns={
        "customer_id": "客户ID", "R": "R(天)", "F": "F(次)", "M": "M(GBP)",
        "last_purchase": "最近购买", "first_purchase": "首次购买",
    }).sort_values("M(GBP)", ascending=False)
    st.dataframe(show, width="stretch", hide_index=True, height=340)
    st.download_button(
        f"⬇ 下载当前查询结果 CSV（{len(show):,} 行）",
        show.to_csv(index=False).encode("utf-8-sig"),
        "customer_rfm_filtered.csv", "text/csv", key="dl_rfm",
    )


# ============================================================================
# 页面 3：客户分群
# ============================================================================
else:
    st.markdown("## 客户分群")
    st.caption("回答：如何划分客户群体、各群体价值如何、应采取什么运营策略？（K-means k=3，轮廓系数 0.339）")

    all_labels = list(dict.fromkeys(seg.sort_values("M", ascending=False)["segment_label"]))
    picked = st.multiselect("客户群筛选（不选 = 全部）", all_labels, default=[], key="p3_sel")
    s = seg if not picked else seg[seg["segment_label"].isin(picked)]
    if s.empty:
        st.warning("请至少选择一个客户群。")
        st.stop()

    prof = (
        s.groupby("segment_label")
        .agg(n=("customer_id", "count"), M_sum=("M", "sum"),
             R_mean=("R", "mean"), F_mean=("F", "mean"), M_mean=("M", "mean"))
        .reset_index()
    )
    order = prof.sort_values("M_sum", ascending=False)["segment_label"].tolist()
    prof = prof.set_index("segment_label").loc[order].reset_index()
    cs = [COLORS.get(l, "#5D6D7E") for l in prof["segment_label"]]

    # ---- 图6：各群人数 ----
    c_l, c_r = st.columns(2)
    with c_l:
        fig6 = go.Figure(go.Bar(
            x=prof["segment_label"], y=prof["n"], marker_color=cs,
            text=prof["n"].map(lambda v: f"{v:,} 人"), textposition="outside",
            hovertemplate="%{x}<br>%{y:,} 人（%{customdata:.1f}%）<extra></extra>",
            customdata=prof["n"] / prof["n"].sum() * 100,
        ))
        fig6.update_layout(
            title="图6 · 各客户群人数", yaxis_title="客户数", font=FONT, height=400,
            yaxis_range=[0, prof["n"].max() * 1.18], xaxis_title="",
        )
        st.plotly_chart(fig6, width="stretch", key="f6")
        st.info(f"**解读**：{prof.iloc[0]['segment_label']}人数最少"
                f"（{prof.iloc[0]['n']:,} 人，{prof.iloc[0]['n'] / prof['n'].sum() * 100:.1f}%），"
                f"但属于高价值核心群体。")

    # ---- 图7：各群销售额贡献 ----
    with c_r:
        fig7 = go.Figure(go.Bar(
            x=prof["segment_label"], y=prof["M_sum"], marker_color=cs,
            text=(prof["M_sum"] / prof["M_sum"].sum() * 100).map(lambda v: f"{v:.1f}%"),
            textposition="outside",
            hovertemplate="%{x}<br>销售额 £%{y:,.0f}<extra></extra>",
        ))
        fig7.update_layout(
            title="图7 · 各客户群销售额贡献", yaxis_title="销售额 (GBP)", font=FONT, height=400,
            yaxis_range=[0, prof["M_sum"].max() * 1.18], xaxis_title="",
        )
        st.plotly_chart(fig7, width="stretch", key="f7")
        first = prof.iloc[0]
        st.info(f"**解读**：{first['segment_label']}仅占人数 "
                f"{first['n'] / prof['n'].sum() * 100:.1f}%，却贡献 **{first['M_sum'] / prof['M_sum'].sum() * 100:.1f}%** 的销售额。")

    st.divider()

    # ---- 图8：RFM 画像热力图（z-score，R 取负 → 颜色越深越优质）----
    st.markdown("#### 客户群体画像")
    z = prof[["R_mean", "F_mean", "M_mean"]].copy()
    z.columns = ["R（购买间隔）", "F（购买频次）", "M（消费金额）"]
    zz = (z - z.mean()) / z.std(ddof=0)
    zz["R（购买间隔）"] = -zz["R（购买间隔）"]  # R 越小越好 → 取负使"深色=优质"统一
    zz.insert(0, "客户群", prof["segment_label"])
    melt = zz.melt(id_vars="客户群", var_name="指标", value_name="z值")
    mat = melt.pivot(index="客户群", columns="指标", values="z值").loc[order]

    fig8 = px.imshow(
        mat, text_auto=".2f", aspect="auto",
        color_continuous_scale="RdYlGn", zmin=-2, zmax=2,
        labels=dict(color="z 分数"),
    )
    fig8.update_layout(
        title="图8 · 各客户群 RFM 画像热力图（z 分数；R 已取负，绿色=更优质）",
        font=FONT, height=380, xaxis_title="", yaxis_title="",
    )
    st.plotly_chart(fig8, width="stretch", key="f8")
    st.info(
        "**解读**：绿色越深代表该维度越优（R 已反向处理）。"
        "重要价值客户在 F、M 两维显著为正、R 显著为负（近期买过），是典型的『高价值活跃』画像；"
        "一般挽留客户则相反，属于长期未购、低贡献群体。"
    )

    # ---- 图9：RFM 聚类 3D 散点 ----
    samp = s.sample(min(len(s), 4000), random_state=42)
    fig9 = px.scatter_3d(
        samp, x="F", y="M", z="R", color="segment_label",
        color_discrete_map=COLORS, opacity=0.55,
        hover_data={"customer_id": True, "R": True, "F": True, "M": ":.0f"},
        labels={"F": "F 购买频次", "M": "M 消费金额 (GBP)", "R": "R 距今天数", "segment_label": "客户群"},
    )
    fig9.update_traces(marker=dict(size=3))
    fig9.update_layout(
        title="图9 · RFM 三维散点（按分群着色，可拖动旋转 / 滚轮缩放）",
        font=FONT, height=560,
        scene=dict(xaxis_title="F 频次", yaxis_title="M 金额", zaxis_title="R 天数（越小越近）"),
        legend=dict(orientation="h", y=1.02),
    )
    st.plotly_chart(fig9, width="stretch", key="f9")
    st.caption("注：为保证渲染流畅，散点最多抽样 4,000 位客户（随机种子 42，可复现）。")

    st.divider()

    # ---- 群画像表 + 运营建议 + 导出 ----
    st.markdown("#### 分群画像与运营建议")
    advice = {
        "重要价值客户": "会员体系维护、新品优先推荐、专属客服与生日关怀，防止流失",
        "重要保持客户": "交叉销售与套餐组合，提升购买频次；设定消费阶梯奖励",
        "重要挽留客户": "定向召回：个性化优惠券 + 老客专属活动，重点挽回",
        "一般发展客户": "二次购买引导（首单后 30 天内触达），提升复购率",
        "一般挽留客户": "控制触达成本，采用低成本自动化邮件/短信唤醒",
        "一般客户": "低频维护，纳入常规促销池，不做高成本投入",
    }
    view_tbl = prof.copy()
    view_tbl["人数占比"] = (view_tbl["n"] / view_tbl["n"].sum() * 100).map(lambda v: f"{v:.1f}%")
    view_tbl["销售额占比"] = (view_tbl["M_sum"] / view_tbl["M_sum"].sum() * 100).map(lambda v: f"{v:.1f}%")
    view_tbl["运营建议"] = view_tbl["segment_label"].map(advice).fillna("—")
    view_tbl = view_tbl.rename(columns={
        "segment_label": "客户群", "n": "人数", "R_mean": "R均值(天)",
        "F_mean": "F均值(次)", "M_mean": "M均值(GBP)", "M_sum": "销售额合计(GBP)",
    })[["客户群", "人数", "人数占比", "R均值(天)", "F均值(次)", "M均值(GBP)", "销售额合计(GBP)", "销售额占比", "运营建议"]]
    st.dataframe(
        view_tbl.style.format({"R均值(天)": "{:.0f}", "F均值(次)": "{:.1f}",
                               "M均值(GBP)": "£{:,.0f}", "销售额合计(GBP)": "£{:,.0f}"}),
        width="stretch", hide_index=True,
    )
    st.caption("建议均为基于历史数据的运营假设，未经 A/B 实验验证，不宣称实际提升效果。")

    exp = s[["customer_id", "segment_label", "R", "F", "M"]].rename(columns={
        "customer_id": "客户ID", "segment_label": "客户群", "R": "R(天)", "F": "F(次)", "M": "M(GBP)",
    }).sort_values("M(GBP)", ascending=False)
    st.download_button(
        f"⬇ 导出当前筛选客户名单 CSV（{len(exp):,} 行）",
        exp.to_csv(index=False).encode("utf-8-sig"),
        "customer_segments_export.csv", "text/csv", key="dl_seg",
    )

# ----------------------------------------------------------------------------
st.divider()
st.caption(
    "数据来源：UCI Machine Learning Repository — Online Retail（541,909 条原始交易，2010-12-01 ~ 2011-12-09）"
    " ｜ 技术栈：Python · Pandas · MySQL · Scikit-learn · Streamlit · Plotly ｜ 金额单位 GBP"
)
