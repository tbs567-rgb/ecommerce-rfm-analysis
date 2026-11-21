# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[3])

"""把正文内容组装为符合课程要求的 Word 报告。

格式：A4；页边距上下 2.54cm、左右 3.17cm；正文宋体小四、1.5 倍行距；
一级标题黑体三号；图下表上；页脚页码；自动目录域。
"""
import os
import sys

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_LINE_SPACING
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn
from docx.shared import Cm, Pt, RGBColor
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from content_ch1_2 import BLOCKS as B12
from content_ch3_4 import BLOCKS as B34
from content_ch5 import BLOCKS as B5
from content_ch6_7 import BLOCKS as B67

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figs")
SHOT = _ROOT + r"\ecommerce_rfm\outputs\screenshots"
OUT = _ROOT + r"\ecommerce_rfm\docs\课程设计报告-基于RFM与K-means的电商客户价值分析.docx"

SONG, HEI, MONO = "宋体", "黑体", "Consolas"
BODY_PT = 12  # 小四
CAP_PT = 10.5  # 五号

doc = Document()

# ------------------------------------------------------------------ 页面设置
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(2.54)
sec.left_margin = sec.right_margin = Cm(3.17)
sec.header_distance = Cm(1.5)
sec.footer_distance = Cm(1.5)
sec.different_first_page_header_footer = True
TEXT_W = 21 - 3.17 * 2


def set_font(run, name=SONG, size=BODY_PT, bold=False, color=None):
    run.font.name = name
    run.font.size = Pt(size)
    run.font.bold = bold
    run.font.color.rgb = RGBColor(0, 0, 0) if color is None else color
    rpr = run._element.get_or_add_rPr()
    rfonts = rpr.find(qn("w:rFonts"))
    if rfonts is None:
        rfonts = OxmlElement("w:rFonts")
        rpr.append(rfonts)
    rfonts.set(qn("w:ascii"), name)
    rfonts.set(qn("w:hAnsi"), name)
    rfonts.set(qn("w:eastAsia"), name)


def para(text="", *, font=SONG, size=BODY_PT, bold=False, align="just",
         indent_chars=2, before=0, after=0, spacing=1.5, style=None, keep=False):
    p = doc.add_paragraph(style=style) if style else doc.add_paragraph()
    pf = p.paragraph_format
    pf.alignment = {"just": WD_ALIGN_PARAGRAPH.JUSTIFY, "center": WD_ALIGN_PARAGRAPH.CENTER,
                    "left": WD_ALIGN_PARAGRAPH.LEFT, "right": WD_ALIGN_PARAGRAPH.RIGHT}[align]
    pf.space_before = Pt(before)
    pf.space_after = Pt(after)
    if spacing == 1.5:
        pf.line_spacing_rule = WD_LINE_SPACING.ONE_POINT_FIVE
    else:
        pf.line_spacing = spacing
    if indent_chars:
        pf.first_line_indent = Pt(size * indent_chars)
    if keep:
        pf.keep_with_next = True
    if text:
        set_font(p.add_run(text), font, size, bold)
    return p


def add_field(p, instr, placeholder=""):
    r1 = p.add_run(); f1 = OxmlElement("w:fldChar"); f1.set(qn("w:fldCharType"), "begin"); r1._r.append(f1)
    r2 = p.add_run(); it = OxmlElement("w:instrText"); it.set(qn("xml:space"), "preserve"); it.text = instr
    r2._r.append(it)
    r3 = p.add_run(); f3 = OxmlElement("w:fldChar"); f3.set(qn("w:fldCharType"), "separate"); r3._r.append(f3)
    if placeholder:
        set_font(p.add_run(placeholder), SONG, BODY_PT)
    r5 = p.add_run(); f5 = OxmlElement("w:fldChar"); f5.set(qn("w:fldCharType"), "end"); r5._r.append(f5)


# ------------------------------------------------------------------ 样式
st = doc.styles["Normal"]
st.font.name = SONG
st.font.size = Pt(BODY_PT)
st.element.rPr.rFonts.set(qn("w:eastAsia"), SONG)

for name, size in (("Heading 1", 16), ("Heading 2", 14), ("Heading 3", 12)):
    s = doc.styles[name]
    s.font.name = HEI
    s.font.size = Pt(size)
    s.font.bold = True
    s.font.color.rgb = RGBColor(0, 0, 0)
    s.element.rPr.rFonts.set(qn("w:eastAsia"), HEI)
    s.element.rPr.rFonts.set(qn("w:ascii"), HEI)
    s.element.rPr.rFonts.set(qn("w:hAnsi"), HEI)

# ------------------------------------------------------------------ 封面
for _ in range(3):
    para("", indent_chars=0)

para("《大数据技术》课程设计报告", font=HEI, size=22, bold=True, align="center", indent_chars=0, after=30)

para("基于 RFM 模型与 K-means 聚类的", font=HEI, size=20, bold=True, align="center", indent_chars=0, after=4)
para("电商客户价值分析", font=HEI, size=20, bold=True, align="center", indent_chars=0, after=48)

info = [("课程名称", "大数据技术"), ("项目类型", "数据分析与挖掘"),
        ("小组成员", "陶柏杉、（成员二）、（成员三）、（成员四）"),
        ("学　　号", "　　　　　　　　　　　　　　"),
        ("班　　级", "　　　　　　　　　　　　　　"),
        ("指导教师", "　　　　　　　　　　　　　　")]
t = doc.add_table(rows=len(info), cols=2)
t.alignment = WD_TABLE_ALIGNMENT.CENTER
t.autofit = False
for i, (k, v) in enumerate(info):
    for j, txt in enumerate((k, v)):
        cell = t.cell(i, j)
        cell.width = Cm(3.2 if j == 0 else 11.2)
        p = cell.paragraphs[0]
        p.paragraph_format.space_before = Pt(3)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.5
        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
        set_font(p.add_run(txt), SONG, 12)
        if j == 1 and txt.strip() == "":
            tcPr = cell._tc.get_or_add_tcPr()
            bd = OxmlElement("w:tcBorders")
            btm = OxmlElement("w:bottom")
            btm.set(qn("w:val"), "single"); btm.set(qn("w:sz"), "6")
            btm.set(qn("w:space"), "0"); btm.set(qn("w:color"), "808080")
            bd.append(btm); tcPr.append(bd)

for _ in range(4):
    para("", indent_chars=0)
para("2026 年 11 月", font=SONG, size=14, align="center", indent_chars=0)

# ------------------------------------------------------------------ 摘要
_abs = para("摘　要", font=HEI, size=16, bold=True, align="center", indent_chars=0, before=0, after=12)
_abs.paragraph_format.page_break_before = True

ABS = [
    "随着电商行业从流量竞争转向存量运营，如何从海量交易记录中识别客户价值、制定差异化策略，成为在线零售商的核心问题。本文以 UCI 机器学习库公开的 Online Retail 数据集为对象，共 541,909 条真实交易记录，构建了一条从数据采集、清洗、分布式存储、统计建模到交互式可视化的完整分析链路。",
    "数据预处理阶段定义了 7 条清洗规则，依次处理完全重复、缺失客户编号、取消与退货订单、异常单价与特殊业务行，最终得到 391,153 条有效购买记录，覆盖 4,334 位客户、18,402 张订单与 37 个国家（地区），有效销售额 8,737,227.64 英镑。存储阶段采用 HDFS 暂存原始文件、MySQL 承载结构化结果的分工方案，设计四张表并通过客户编号建立血缘关系，同时针对高频查询补充主键与索引，实测典型查询耗时由 0.3686 秒降至 0.0009 秒。",
    "分析阶段先以描述性统计与时间序列分析刻画经营结构，再构建 RFM 模型量化客户价值，最后用 K-means 完成聚类。为避免单一实现带来的偏差，同一套清洗与聚合逻辑分别用 PySpark 与 Pandas 实现并逐项对账，六项核心指标完全一致。建模前提出四条假设并逐条验证：前 20% 客户贡献 74.58% 的销售额，二八分布成立；消费金额与购买频次的相关系数为 0.807，高于与客单价的 0.677，频次是主要驱动因素；最近购买间隔与购买频次的相关系数为 −0.564，负相关成立；第四季度月均销售额高出其他季度 31.08%，季节效应成立。肘部法与轮廓系数一致指向 k = 3，聚类得到 748 位重要价值客户、1,710 位一般发展客户与 1,876 位一般挽留客户，分别贡献 67.81%、24.49% 与 7.70% 的销售额，轮廓系数为 0.3387。",
    "可视化阶段开发了三页面交互系统，共 12 张图表，支持日期、国家、RFM 区间与客户群体的组合筛选，并提供名单与明细的 CSV 导出；同时保留一套单文件离线看板，保证无外网环境下也能完整演示。项目最终打包为可在新机器上一键运行的交付物，包含 Hadoop 3.3.6、Spark 4.3.0、Python 运行时、数据库备份与七个启动脚本。",
]
for t_ in ABS:
    para(t_)

p = doc.add_paragraph()
p.paragraph_format.line_spacing = 1.5
p.paragraph_format.space_before = Pt(6)
set_font(p.add_run("关键词："), HEI, BODY_PT, True)
set_font(p.add_run("客户价值分析；RFM 模型；K-means 聚类；Spark；数据可视化"), SONG, BODY_PT)

# ------------------------------------------------------------------ 目录
_toc = para("目　录", font=HEI, size=16, bold=True, align="center", indent_chars=0, before=0, after=18)
_toc.paragraph_format.page_break_before = True
p = doc.add_paragraph()
p.paragraph_format.line_spacing = 1.5
add_field(p, r' TOC \o "1-2" \h \z \u ', "（目录将在打开文档时自动生成，若未显示请右键选择“更新域”）")

# Word 打开时自动更新域
settings = doc.settings.element
settings.append(parse_xml(r'<w:updateFields %s w:val="true"/>' % nsdecls("w")))

# ------------------------------------------------------------------ 页眉页脚
hdr = sec.header.paragraphs[0]
hdr.alignment = WD_ALIGN_PARAGRAPH.CENTER
set_font(hdr.add_run("《大数据技术》课程设计报告"), SONG, 9)

ftr = sec.footer.paragraphs[0]
ftr.alignment = WD_ALIGN_PARAGRAPH.CENTER
add_field(ftr, " PAGE ", "1")
for r in ftr.runs:
    set_font(r, SONG, 9)


# ------------------------------------------------------------------ 表格与图片
def shade(cell, hex_color):
    tcPr = cell._tc.get_or_add_tcPr()
    tcPr.append(parse_xml(r'<w:shd %s w:val="clear" w:color="auto" w:fill="%s"/>'
                          % (nsdecls("w"), hex_color)))


def set_table_borders(table):
    tbl = table._tbl
    tblPr = tbl.tblPr
    borders = OxmlElement("w:tblBorders")
    for edge in ("top", "left", "bottom", "right", "insideH", "insideV"):
        el = OxmlElement("w:%s" % edge)
        el.set(qn("w:val"), "single")
        el.set(qn("w:sz"), "4")
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "595959")
        borders.append(el)
    tblPr.append(borders)


def add_table(caption, headers, rows, widths=None):
    cap = para(caption, font=HEI, size=CAP_PT, bold=False, align="center",
               indent_chars=0, before=6, after=3, spacing=1.0, keep=True)
    table = doc.add_table(rows=1, cols=len(headers))
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    set_table_borders(table)
    total = sum(widths) if widths else TEXT_W
    widths = widths or [TEXT_W / len(headers)] * len(headers)
    scale = TEXT_W / total

    hdr_cells = table.rows[0].cells
    for i, h in enumerate(headers):
        hdr_cells[i].width = Cm(widths[i] * scale)
        p = hdr_cells[i].paragraphs[0]
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.line_spacing = 1.0
        p.paragraph_format.space_before = Pt(2)
        p.paragraph_format.space_after = Pt(2)
        set_font(p.add_run(h), HEI, 9.5, True)
        shade(hdr_cells[i], "E7EEF6")

    trPr = table.rows[0]._tr.get_or_add_trPr()
    trPr.append(parse_xml(r'<w:tblHeader %s/>' % nsdecls("w")))
    trPr.append(parse_xml(r'<w:cantSplit %s/>' % nsdecls("w")))

    for row in rows:
        new_row = table.add_row()
        new_row._tr.get_or_add_trPr().append(parse_xml(r'<w:cantSplit %s/>' % nsdecls("w")))
        cells = new_row.cells
        for i, val in enumerate(row):
            cells[i].width = Cm(widths[i] * scale)
            p = cells[i].paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER if i != 2 or len(headers) < 4 else WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.line_spacing = 1.0
            p.paragraph_format.space_before = Pt(2)
            p.paragraph_format.space_after = Pt(2)
            set_font(p.add_run(str(val)), SONG, 9.5)
        cells[0].paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER

    para("", indent_chars=0, spacing=1.0, after=6)


def add_fig(fname, caption):
    path = os.path.join(SHOT, fname)
    if not os.path.exists(path):
        path = os.path.join(FIG, fname)
    with Image.open(path) as im:
        w, h = im.size
    max_h = 16.0 if fname.startswith("shot_") else 10.5
    width_cm = min(TEXT_W, 15.0)
    height_cm = width_cm * h / w
    if height_cm > max_h:
        height_cm = max_h
        width_cm = height_cm * w / h
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(4)
    p.paragraph_format.space_after = Pt(2)
    p.paragraph_format.keep_with_next = True
    p.add_run().add_picture(path, width=Cm(width_cm))
    para(caption, font=SONG, size=CAP_PT, align="center", indent_chars=0,
         before=0, after=10, spacing=1.0)


def add_code(text):
    p = doc.add_paragraph()
    pf = p.paragraph_format
    pf.left_indent = Cm(1.0)
    pf.line_spacing = 1.0
    pf.space_before = Pt(4)
    pf.space_after = Pt(8)
    pPr = p._p.get_or_add_pPr()
    pPr.append(parse_xml(r'<w:shd %s w:val="clear" w:color="auto" w:fill="F2F2F2"/>' % nsdecls("w")))
    set_font(p.add_run(text), MONO, 9)


# ------------------------------------------------------------------ 正文
BLOCKS = B12 + B34 + B5 + B67
first_h1 = True
for blk in BLOCKS:
    kind = blk[0]
    if kind == "h1":
        h = doc.add_paragraph(style="Heading 1")
        h.paragraph_format.page_break_before = True
        h.alignment = WD_ALIGN_PARAGRAPH.CENTER
        h.paragraph_format.space_before = Pt(6)
        h.paragraph_format.space_after = Pt(18)
        h.paragraph_format.line_spacing = 1.5
        set_font(h.add_run(blk[1]), HEI, 16, True)
    elif kind == "h2":
        h = doc.add_paragraph(style="Heading 2")
        h.paragraph_format.space_before = Pt(12)
        h.paragraph_format.space_after = Pt(6)
        h.paragraph_format.line_spacing = 1.5
        h.paragraph_format.keep_with_next = True
        set_font(h.add_run(blk[1]), HEI, 14, True)
    elif kind == "h3":
        h = doc.add_paragraph(style="Heading 3")
        h.paragraph_format.space_before = Pt(8)
        h.paragraph_format.space_after = Pt(4)
        set_font(h.add_run(blk[1]), HEI, 12, True)
    elif kind == "p":
        para(blk[1])
    elif kind == "fig":
        add_fig(blk[1], blk[2])
    elif kind == "table":
        add_table(blk[1], blk[2], blk[3], blk[4] if len(blk) > 4 else None)
    elif kind == "code":
        add_code(blk[1])
    elif kind == "ref":
        p = doc.add_paragraph()
        pf = p.paragraph_format
        pf.left_indent = Cm(0.74)
        pf.first_line_indent = Cm(-0.74)
        pf.line_spacing = 1.25
        pf.space_after = Pt(4)
        pf.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        set_font(p.add_run(blk[1]), SONG, CAP_PT)
    elif kind == "pb":
        continue

doc.save(OUT)

# ------------------------------------------------------------------ 估算
chars = sum(len(b[1]) for b in BLOCKS if b[0] == "p")
n_fig = sum(1 for b in BLOCKS if b[0] == "fig")
n_tab = sum(1 for b in BLOCKS if b[0] == "table")
print("已生成：", OUT)
print(f"正文段落字数 {chars:,}，图 {n_fig} 张，表 {n_tab} 个")
print(f"文件大小 {os.path.getsize(OUT) / 1024 / 1024:.2f} MB")
