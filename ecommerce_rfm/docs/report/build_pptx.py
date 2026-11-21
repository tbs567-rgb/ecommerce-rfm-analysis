# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[3])

"""生成 19 页答辩 PPT（16:9，正文 ≥20pt）。"""
import os

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt
from PIL import Image

BASE = _ROOT + r"\ecommerce_rfm\docs\report"
FIG = os.path.join(BASE, "figs")
OUT = _ROOT + r"\ecommerce_rfm\docs\答辩PPT-电商客户价值分析.pptx"

NAVY = RGBColor(0x1F, 0x4E, 0x79)
BLUE = RGBColor(0x2E, 0x75, 0xB6)
LIGHT = RGBColor(0x9D, 0xC3, 0xE6)
SOFT = RGBColor(0xEA, 0xF1, 0xF8)
ORANGE = RGBColor(0xC5, 0x5A, 0x11)
GRAY = RGBColor(0x59, 0x59, 0x59)
DARK = RGBColor(0x26, 0x26, 0x26)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
LINE = RGBColor(0xD9, 0xE2, 0xEC)
FONT = "微软雅黑"

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
BLANK = prs.slide_layouts[6]


def _ea(run, font=FONT):
    rPr = run._r.get_or_add_rPr()
    ea = rPr.find(qn("a:ea"))
    if ea is None:
        ea = rPr.makeelement(qn("a:ea"), {})
        rPr.append(ea)
    ea.set("typeface", font)


def tx(s, x, y, w, h, text, size=20, bold=False, color=DARK,
       align=PP_ALIGN.LEFT, anchor=MSO_ANCHOR.TOP, spacing=1.25):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    p = tf.paragraphs[0]
    p.alignment = align
    p.line_spacing = spacing
    r = p.add_run()
    r.text = text
    r.font.size = Pt(size)
    r.font.bold = bold
    r.font.name = FONT
    r.font.color.rgb = color
    _ea(r)
    return tb


def rect(s, x, y, w, h, fill=SOFT, line=None, shape=MSO_SHAPE.ROUNDED_RECTANGLE, radius=0.06):
    sp = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    if fill is None:
        sp.fill.background()
    else:
        sp.fill.solid()
        sp.fill.fore_color.rgb = fill
    if line is None:
        sp.line.fill.background()
    else:
        sp.line.color.rgb = line
        sp.line.width = Pt(1)
    sp.shadow.inherit = False
    if shape == MSO_SHAPE.ROUNDED_RECTANGLE:
        try:
            sp.adjustments[0] = radius
        except Exception:
            pass
    return sp


def bullets(s, x, y, w, h, items, size=20, color=DARK, gap=10, marker="▪", mcolor=ORANGE):
    tb = s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = tb.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    for i, item in enumerate(items):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.line_spacing = 1.3
        p.space_after = Pt(gap)
        r1 = p.add_run()
        r1.text = marker + "  "
        r1.font.size = Pt(size)
        r1.font.name = FONT
        r1.font.color.rgb = mcolor
        _ea(r1)
        r2 = p.add_run()
        r2.text = item
        r2.font.size = Pt(size)
        r2.font.name = FONT
        r2.font.color.rgb = color
        _ea(r2)
    return tb


def pic(s, fname, x, y, w=None, h=None):
    path = os.path.join(FIG, fname)
    with Image.open(path) as im:
        iw, ih = im.size
    if w and not h:
        h = w * ih / iw
    elif h and not w:
        w = h * iw / ih
    return s.shapes.add_picture(path, Inches(x), Inches(y), Inches(w), Inches(h)), h


def new_slide(title, lead=None, page=None):
    s = prs.slides.add_slide(BLANK)
    rect(s, 0, 0, 0.16, 7.5, fill=NAVY, shape=MSO_SHAPE.RECTANGLE)
    tx(s, 0.82, 0.46, 11.8, 0.85, title, size=32, bold=True, color=NAVY)
    if lead:
        tx(s, 0.82, 1.3, 11.8, 0.55, lead, size=20, color=GRAY)
    rect(s, 0.82, 1.92, 11.7, 0.016, fill=LINE, shape=MSO_SHAPE.RECTANGLE)
    if page:
        tx(s, 12.2, 7.02, 0.8, 0.3, str(page), size=11, color=RGBColor(0x99, 0x99, 0x99), align=PP_ALIGN.RIGHT)
    return s


# ------------------------------------------------------------------ 1 封面
s = prs.slides.add_slide(BLANK)
rect(s, 0, 0, 13.333, 7.5, fill=NAVY, shape=MSO_SHAPE.RECTANGLE)
rect(s, 0.9, 2.02, 0.9, 0.07, fill=ORANGE, shape=MSO_SHAPE.RECTANGLE)
tx(s, 0.9, 2.25, 11.4, 0.7, "《大数据技术》课程设计", size=24, color=LIGHT)
tx(s, 0.9, 2.95, 11.6, 1.5, "基于 RFM 与 K-means 的\n电商客户价值分析", size=40, bold=True, color=WHITE, spacing=1.2)
tx(s, 0.9, 4.95, 11.4, 0.5, "54 万条真实交易 · Hadoop + Spark 分布式链路 · 三页面交互系统", size=20, color=LIGHT)
tx(s, 0.9, 6.35, 6.0, 0.4, "第 4 组　｜　2026 年 11 月", size=18, color=RGBColor(0xBD, 0xD7, 0xEE))

# ------------------------------------------------------------------ 2 目录
s = new_slide("目录", "CONTENTS", 2)
toc = [("01", "选题背景与目标", "为什么做、要解决什么问题"),
       ("02", "数据与总体架构", "54 万条数据、五层技术链路"),
       ("03", "关键技术与实现", "清洗、存储、Spark 双链路对账"),
       ("04", "分析结果与可视化", "RFM、K-means、三页面系统"),
       ("05", "总结与分工", "成果、不足、小组分工")]
for i, (no, t1, t2) in enumerate(toc):
    y = 2.2 + i * 1.0
    tx(s, 0.85, y, 0.9, 0.6, no, size=26, bold=True, color=ORANGE)
    tx(s, 1.75, y - 0.03, 4.6, 0.5, t1, size=24, bold=True, color=NAVY)
    tx(s, 6.5, y + 0.05, 6.0, 0.45, t2, size=18, color=GRAY)

# ------------------------------------------------------------------ 3 背景
s = new_slide("选题背景：从抢流量到经营存量", "Why this topic", 3)
bullets(s, 0.85, 2.25, 7.4, 4.2, [
    "获客成本上升，电商转向存量运营",
    "4,334 位客户中，少数人贡献多数销售额",
    "经验分群覆盖不了 54 万条交易",
    "Spark 能否真正解决一个业务问题",
], size=20, gap=18)
rect(s, 8.7, 2.25, 3.85, 2.55, fill=SOFT)
tx(s, 9.0, 2.5, 3.3, 1.0, "74.6%", size=54, bold=True, color=NAVY)
tx(s, 9.0, 3.5, 3.3, 1.1, "的销售额来自\n前 20% 的客户", size=20, color=GRAY, spacing=1.35)
rect(s, 8.7, 5.05, 3.85, 1.15, fill=WHITE, line=LINE)
tx(s, 9.0, 5.24, 3.3, 0.8, "典型二八分布\n分层运营有据可依", size=17, color=BLUE, spacing=1.3)

# ------------------------------------------------------------------ 4 目标与假设
s = new_slide("分析目标与四条假设", "先提问题，再跑算法", 4)
qs = [("卖得怎么样", "月度趋势 / 商品 / 国家结构"),
      ("客户值多少", "RFM 三维量化客户价值"),
      ("怎么分群", "K-means 聚类 + 业务命名"),
      ("怎么运营", "分层策略与投入强度")]
for i, (q, d) in enumerate(qs):
    x = 0.85 + (i % 2) * 3.15
    y = 2.2 + (i // 2) * 1.35
    rect(s, x, y, 2.95, 1.15, fill=SOFT)
    tx(s, x + 0.22, y + 0.15, 2.6, 0.4, q, size=20, bold=True, color=NAVY)
    tx(s, x + 0.22, y + 0.62, 2.6, 0.4, d, size=15, color=GRAY)
rect(s, 7.35, 2.2, 5.2, 4.4, fill=WHITE, line=LINE)
tx(s, 7.6, 2.38, 4.8, 0.4, "四条可检验假设", size=20, bold=True, color=ORANGE)
hs = ["H1　前 20% 客户贡献 ≥70% 销售额",
      "H2　价值差异主要由频次驱动",
      "H3　R 与 F 呈负相关",
      "H4　Q4 月均销售额显著更高"]
for i, h in enumerate(hs):
    tx(s, 7.6, 2.95 + i * 0.88, 4.7, 0.7, h, size=19, color=DARK, spacing=1.2)

# ------------------------------------------------------------------ 5 数据规模
s = new_slide("数据来源与规模", "UCI Online Retail · 真实交易流水，非模拟数据", 5)
cards = [("541,909", "原始交易记录", "8 个字段"),
         ("13", "个自然月", "2010-12 ~ 2011-12"),
         ("37", "个国家（地区）", "英国本土占 82.9%"),
         ("391,153", "清洗后有效记录", "占原始 72.2%")]
for i, (big, mid, small) in enumerate(cards):
    x = 0.85 + i * 3.0
    rect(s, x, 2.3, 2.75, 2.2, fill=SOFT)
    tx(s, x + 0.22, 2.5, 2.35, 0.8, big, size=34, bold=True, color=NAVY)
    tx(s, x + 0.22, 3.3, 2.35, 0.4, mid, size=17, color=DARK)
    tx(s, x + 0.22, 3.72, 2.35, 0.5, small, size=14, color=GRAY)
tx(s, 0.85, 4.95, 11.6, 0.9, "数据自带真实噪声：退货、取消单、缺失客户编号、异常单价、邮费与调账行",
   size=21, color=DARK)
tx(s, 0.85, 5.55, 11.6, 0.9, "正好用来检验清洗流程是否可靠，而不是拿一份“已经很干净”的数据做演示",
   size=19, color=GRAY)

# ------------------------------------------------------------------ 6 架构
s = new_slide("总体架构：五层技术链路", "数据源 → 计算 → 存储 → 分析 → 应用", 6)
p, h = pic(s, "fig01_architecture.png", 4.15, 2.02, h=5.25)

# ------------------------------------------------------------------ 7 清洗
s = new_slide("数据清洗：541,909 → 391,153", "7 条规则，每一步都能追溯", 7)
p, h = pic(s, "fig02_clean_funnel.png", 0.85, 2.15, w=7.55)
bullets(s, 8.55, 2.25, 4.0, 4.5, [
    "7 条规则覆盖四类噪声",
    "无客户 ID 记录单列口径",
    "每步命中行数写入日志",
], size=18, gap=20)
tx(s, 0.85, 6.45, 7.6, 0.45, "交易口径保留 536,641 条，客户口径只用 391,153 条", size=15, color=ORANGE)

# ------------------------------------------------------------------ 8 存储
s = new_slide("存储设计：四张表 + 索引优化", "MySQL 承载结果，HDFS 暂存原始文件", 8)
tabs = [("transactions_raw", "541,909", "原始明细留档"),
        ("transactions_clean", "536,641", "清洗明细 + 7 个标记位"),
        ("customer_rfm", "4,334", "客户级 R / F / M"),
        ("customer_segments", "4,334", "簇编号 + 群标签")]
for i, (n, c, d) in enumerate(tabs):
    y = 2.18 + i * 1.05
    rect(s, 0.85, y, 6.9, 0.9, fill=SOFT)
    tx(s, 1.05, y + 0.1, 3.5, 0.4, n, size=17, bold=True, color=NAVY)
    tx(s, 4.6, y + 0.13, 1.1, 0.4, c, size=17, bold=True, color=ORANGE)
    tx(s, 5.75, y + 0.18, 1.9, 0.4, d, size=13, color=GRAY)
rect(s, 8.15, 2.18, 4.35, 2.1, fill=WHITE, line=LINE)
tx(s, 8.4, 2.35, 3.9, 0.4, "同一查询，加索引前后", size=17, color=GRAY)
tx(s, 8.4, 2.75, 1.7, 0.6, "0.3686s", size=24, bold=True, color=GRAY)
tx(s, 10.05, 2.8, 0.5, 0.5, "→", size=24, color=ORANGE)
tx(s, 10.5, 2.75, 1.8, 0.6, "0.0009s", size=24, bold=True, color=NAVY)
tx(s, 8.4, 3.5, 3.9, 0.6, "提升约 400 倍（53 万行，按客户查询）", size=14, color=GRAY, spacing=1.3)
tx(s, 8.15, 4.6, 4.35, 1.7, "Spark JDBC 建表不带主键/\n索引，落库后统一补 11 条 DDL", size=17, color=DARK, spacing=1.4)

# ------------------------------------------------------------------ 9 Spark
s = new_slide("Spark 不是摆设：双链路逐项对账", "同一份数据，分布式与单机各算一遍", 9)
steps = [("HDFS", "原始 CSV 上传\n/ecommerce/raw"),
         ("Spark 4.3", "清洗 · 聚合 · RFM\n写回 MySQL"),
         ("Pandas 基线", "同口径复算\n六项指标比对")]
for i, (t1, t2) in enumerate(steps):
    x = 0.85 + i * 3.95
    rect(s, x, 2.25, 3.35, 1.55, fill=SOFT if i < 2 else WHITE, line=None if i < 2 else LINE)
    tx(s, x + 0.25, 2.42, 2.9, 0.45, t1, size=21, bold=True, color=NAVY)
    tx(s, x + 0.25, 2.95, 2.9, 0.7, t2, size=15, color=GRAY, spacing=1.3)
    if i < 2:
        tx(s, x + 3.4, 2.78, 0.5, 0.5, "›", size=28, bold=True, color=ORANGE)
checks = [("原始记录", "541,909"), ("清洗记录", "536,641"), ("有效记录", "391,153"),
          ("销售额", "£8,737,227.64"), ("订单数", "18,402"), ("客户数", "4,334")]
for i, (k, v) in enumerate(checks):
    col, row = i % 3, i // 3
    x = 0.85 + col * 3.95
    y = 4.15 + row * 0.95
    tx(s, x, y, 1.5, 0.4, k, size=16, color=GRAY)
    tx(s, x + 1.5, y - 0.03, 2.3, 0.45, v, size=19, bold=True, color=NAVY)
tx(s, 0.85, 6.2, 11.6, 0.5, "六项指标完全一致 —— 分布式结果可信，而非“跑通了但不知道对不对”", size=20, color=ORANGE)

# ------------------------------------------------------------------ 10 月度趋势
s = new_slide("销售结构：9—11 月是旺季", "13 个月趋势，最后一个月数据不完整已单独标注", 10)
p, h = pic(s, "fig03_monthly.png", 0.7, 2.1, w=8.5)
bullets(s, 9.35, 2.3, 3.7, 4.0, [
    "11 月 £113.65 万为峰值",
    "Q4 月均高出 31.08%",
    "12 月仅 9 天，非下滑",
], size=18, gap=18)

# ------------------------------------------------------------------ 11 商品与国家
s = new_slide("商品与国家：两个被平均掩盖的真相", "按销售额排序，会高估批发订单的影响", 11)
p, h = pic(s, "fig04_top10_products.png", 0.6, 2.05, w=6.35)
p, h = pic(s, "fig05_country.png", 7.15, 2.05, w=6.35)
tx(s, 0.6, 6.55, 6.3, 0.5, "第一名 80,995 件来自单笔批发订单", size=15, color=ORANGE)
tx(s, 7.15, 6.55, 6.3, 0.5, "英国本土 82.9%，海外长尾分散", size=15, color=ORANGE)

# ------------------------------------------------------------------ 12 RFM
s = new_slide("RFM 建模：三个指标都严重右偏", "R 越小越好，F、M 越大越好", 12)
p, h = pic(s, "fig08_rfm_dist.png", 0.75, 2.05, w=9.0)
bullets(s, 10.0, 2.2, 3.0, 4.2, [
    "R 中位数 51 天\n均值 93.2 天",
    "F 中位数 2 次\n均值 4.25 次",
    "M 中位数 £663\n均值 £2,016",
], size=15, gap=14)
tx(s, 0.85, 6.35, 11.5, 0.5, "均值远高于中位数 → 必须先标准化，否则聚类会被少数大客户主导", size=19, color=ORANGE)

# ------------------------------------------------------------------ 13 帕累托 + 假设
s = new_slide("假设验证：四条全部成立", "分析不是跑算法，而是回答问题", 13)
p, h = pic(s, "fig07_pareto.png", 0.6, 2.1, w=6.5)
res = [("H1", "前 20% 贡献 74.58%", True),
       ("H2", "M–F 相关 0.807 ＞ M–客单价 0.677", True),
       ("H3", "R–F 相关 −0.564", True),
       ("H4", "Q4 月均高 31.08%", True)]
for i, (h_, txt, ok) in enumerate(res):
    y = 2.25 + i * 1.1
    tx(s, 7.5, y, 0.85, 0.5, h_, size=20, bold=True, color=ORANGE)
    tx(s, 8.3, y + 0.02, 4.5, 0.5, txt, size=17, color=DARK)
    tx(s, 7.5, y + 0.45, 4.9, 0.4, "✓ 成立" if ok else "✗ 不成立", size=15, color=RGBColor(0x3B, 0x6D, 0x11))

# ------------------------------------------------------------------ 14 选 k
s = new_slide("K-means：用两个指标一起定 k", "肘部法看拐点，轮廓系数看分离度", 14)
p, h = pic(s, "fig09_k_selection.png", 0.85, 2.2, w=7.0)
rect(s, 8.3, 2.25, 4.15, 1.75, fill=SOFT)
tx(s, 8.55, 2.4, 3.7, 0.4, "k = 3 时轮廓系数最高", size=16, color=GRAY)
tx(s, 8.55, 2.78, 3.7, 0.7, "0.3387", size=36, bold=True, color=NAVY)
tx(s, 8.55, 3.45, 3.7, 0.4, "k=4: 0.3361 ｜ k=5: 0.3181", size=14, color=GRAY)
tx(s, 8.3, 4.3, 4.2, 2.3, "0.34 属于中等偏弱：客户价值是连续变量，\n人为切分必有边界样本。\n\n判断标准不是系数高低，而是能否指导运营。",
   size=16, color=DARK, spacing=1.4)

# ------------------------------------------------------------------ 15 分群
s = new_slide("分群结果：748 / 1,710 / 1,876", "人数与贡献严重错位，这正是运营切入点", 15)
p, h = pic(s, "fig10_cluster_scatter.png", 0.55, 2.05, w=7.7)
p, h = pic(s, "fig12_share.png", 8.45, 2.15, w=4.55)
tx(s, 8.45, 5.1, 4.4, 1.3, "17.3% 的客户\n贡献 67.8% 的销售额", size=18, bold=True, color=NAVY, spacing=1.35)
tx(s, 0.55, 5.55, 7.6, 0.5, "三个群体沿 F–M 对角线分层清晰", size=15, color=GRAY)

# ------------------------------------------------------------------ 16 画像与策略
s = new_slide("群画像与运营策略", "同一套指标，三种投入强度", 16)
p, h = pic(s, "fig11_heatmap.png", 0.7, 2.2, w=6.3)
strat = [("重要价值", "保", "专属客服 / 优先发货 / R 值预警", NAVY),
         ("一般发展", "提", "交叉销售 / 满减凑单 / 补货提醒", BLUE),
         ("一般挽留", "唤", "限时券 / 清仓推送 / 邮件触达", RGBColor(0x8E, 0xA9, 0xC0))]
for i, (name, act, detail, c) in enumerate(strat):
    y = 2.25 + i * 1.4
    rect(s, 7.3, y, 5.3, 1.2, fill=WHITE, line=LINE)
    tx(s, 7.5, y + 0.12, 1.3, 0.4, name, size=17, bold=True, color=c)
    tx(s, 8.75, y + 0.1, 0.6, 0.5, act, size=22, bold=True, color=ORANGE)
    tx(s, 7.5, y + 0.62, 4.9, 0.5, detail, size=14, color=GRAY)

# ------------------------------------------------------------------ 17 系统
s = new_slide("交互系统：三个页面，12 张图", "Streamlit + Plotly，支持筛选 / 查询 / 导出", 17)
for i, f in enumerate(["shot_p1.png", "shot_p2.png", "shot_p3.png"]):
    x = 0.75 + i * 4.15
    pic(s, f, x, 2.05, w=3.85)
labels = ["页面一 · 销售概览", "页面二 · 客户价值", "页面三 · 客户分群"]
for i, l in enumerate(labels):
    tx(s, 0.75 + i * 4.15, 6.75, 3.85, 0.4, l, size=14, color=GRAY, align=PP_ALIGN.CENTER)

# ------------------------------------------------------------------ 18 总结
s = new_slide("项目成果与不足", "做完的、没做好的，都写清楚", 18)
tx(s, 0.85, 2.15, 5.6, 0.45, "完成", size=22, bold=True, color=NAVY)
bullets(s, 0.85, 2.65, 5.7, 3.8, [
    "54 万条数据清洗入库，7 条规则全程留痕",
    "Hadoop + Spark 落地，与 Pandas 六项指标一致",
    "RFM + K-means 分三群，轮廓系数 0.3387",
    "三页面 12 图 + 离线看板，一键脚本可复现",
], size=17, gap=12)
tx(s, 7.0, 2.15, 5.6, 0.45, "不足", size=22, bold=True, color=ORANGE)
bullets(s, 7.0, 2.65, 5.6, 3.8, [
    "无成本数据，只能算贡献不能算利润",
    "13 个月仅一个周期，季节结论稳健性有限",
    "K-means 需预设 k，边界样本归属模糊",
    "仍是离线批处理，不具备实时性",
], size=17, gap=12, mcolor=GRAY)
tx(s, 0.85, 5.95, 11.6, 0.5, "下一步：接入成本数据、加定时调度，从离线报表走向日常运营",
   size=19, color=ORANGE)

# ------------------------------------------------------------------ 19 分工
s = new_slide("小组分工与演示安排", "现场演示 8 分钟 + 提问 3 分钟", 19)
rows = [("陶柏杉", "组长", "总体设计、架构、报告统稿、答辩主讲", "30%"),
        ("成员二", "数据工程师", "采集清洗、HDFS、MySQL 与索引", "25%"),
        ("成员三", "算法工程师", "RFM、K-means、模型评估", "25%"),
        ("成员四", "可视化", "Streamlit 三页面、PPT 与录屏", "20%")]
tx(s, 0.85, 2.15, 2.0, 0.4, "姓名", size=16, color=GRAY)
tx(s, 2.55, 2.15, 2.0, 0.4, "角色", size=16, color=GRAY)
tx(s, 4.6, 2.15, 6.0, 0.4, "承担工作", size=16, color=GRAY)
tx(s, 10.9, 2.15, 1.2, 0.4, "占比", size=16, color=GRAY)
rect(s, 0.85, 2.55, 11.6, 0.02, fill=LINE, shape=MSO_SHAPE.RECTANGLE)
for i, (n, r, w, pct) in enumerate(rows):
    y = 2.7 + i * 0.85
    tx(s, 0.85, y, 1.7, 0.4, n, size=18, bold=True, color=NAVY)
    tx(s, 2.55, y, 2.0, 0.4, r, size=16, color=GRAY)
    tx(s, 4.6, y, 6.2, 0.4, w, size=16, color=DARK)
    tx(s, 10.9, y, 1.2, 0.4, pct, size=18, bold=True, color=ORANGE)
rect(s, 0.85, 6.25, 11.6, 0.75, fill=SOFT)
tx(s, 1.1, 6.42, 11.1, 0.4, "演示顺序：销售概览 → 客户价值 → 客户分群 → 现场跑 Spark 冒烟测试", size=16, color=NAVY)

prs.save(OUT)
print("已生成：", OUT)
print("页数：", len(prs.slides))
print("大小：%.2f MB" % (os.path.getsize(OUT) / 1024 / 1024))
