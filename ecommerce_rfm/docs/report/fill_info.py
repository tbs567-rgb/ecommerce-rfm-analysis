# -*- coding: utf-8 -*-
"""一键填写署名信息，并重新导出 PDF、刷新「提交材料」目录。

为什么需要这个脚本
------------------
报告封面、附录 A 分工表、PPT 末页里都留了「成员二/成员三/成员四」占位符，
手工在 Word / PowerPoint 里改容易顶乱版式（尤其封面表格和 1.5 倍行距）。
本脚本按 run 级别替换文字，格式、行距、表格列宽一律不动。

用法
----
1. 用记事本打开同目录的 info.json，把姓名 / 学号 / 班级 / 指导教师填全
2. 双击运行  D:\\graduation_project\\8_fill_info.bat
   或命令行：
   D:\\graduation_project\\python_env\\Scripts\\python.exe ^
       D:\\graduation_project\\ecommerce_rfm\\docs\\report\\fill_info.py
3. 只想看会改哪些地方、不写文件：加参数 --dry-run

脚本做的事
----------
  docx 封面  小组成员 / 学号 / 班级 / 指导教师
  docx 表 14 附录 A 分工表：成员二~四 → 真实姓名
  pptx 末页  成员二~四 → 真实姓名
  重新导出 PDF（Word / PowerPoint COM，保持与 docx/pptx 完全一致）
  把 6 份成果重新复制到 提交材料/ 并统一命名
"""

import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent          # ecommerce_rfm/docs/report
DOCS = HERE.parent                              # ecommerce_rfm/docs
ROOT = DOCS.parent.parent                       # graduation_project

DOCX = DOCS / "课程设计报告-基于RFM与K-means的电商客户价值分析.docx"
PPTX = DOCS / "答辩PPT-电商客户价值分析.pptx"
DOCX_PDF = HERE / "report_preview.pdf"
PPTX_PDF = HERE / "ppt_preview.pdf"
OUT = ROOT / "提交材料"

DRY = "--dry-run" in sys.argv
PLACEHOLDERS = [
    ("（成员二）", 1), ("（成员三）", 2), ("（成员四）", 3),   # 报告里的写法（带括号）
    ("成员二", 1), ("成员三", 2), ("成员四", 3),               # PPT 里的写法（不带括号）
]


# --------------------------------------------------------------------------- #
# info.json
# --------------------------------------------------------------------------- #
def load_info():
    path = HERE / "info.json"
    if not path.exists():
        sys.exit(f"缺少配置文件：{path}")
    info = json.loads(path.read_text(encoding="utf-8"))
    members = [m.strip() for m in info.get("members", [])]
    ids = [str(s).strip() for s in info.get("student_ids", [])]

    if len(members) != 4 or any(not m for m in members):
        sys.exit(
            f"请先把 {path} 里的 4 个姓名填全（第 1 位是组长）。\n"
            '示例： "members": ["陶柏杉", "张三", "李四", "王五"]'
        )
    if ids and (len(ids) != 4 or any(not s for s in ids)):
        sys.exit(
            f"请把 {path} 里的 student_ids 填满 4 个，或整体留空。\n"
            '示例： "student_ids": ["2021001", "2021002", "2021003", "2021004"]'
        )
    return {
        "members": members,
        "student_ids": ids,
        "class_name": info.get("class_name", "").strip(),
        "teacher": info.get("teacher", "").strip(),
    }


# --------------------------------------------------------------------------- #
# docx
# --------------------------------------------------------------------------- #
def set_para_text(p, text):
    """整段重写为 text，保留首个 run 的字体格式。"""
    if not p.runs:
        p.add_run(text)
        return
    p.runs[0].text = text
    for r in p.runs[1:]:
        r.text = ""


def replace_para(p, old, new):
    if old not in p.text:
        return False
    if any(old in r.text for r in p.runs):          # 占位符完整落在某个 run 里
        for r in p.runs:
            if old in r.text:
                r.text = r.text.replace(old, new)
    else:                                            # 被拆到多个 run，整段重写
        set_para_text(p, p.text.replace(old, new))
    return True


def row_by_label(table, label):
    """按首列标签找行，忽略全角空格（封面是「学　　号」这种排版）。"""
    key = label.replace(" ", "")
    for row in table.rows:
        if row.cells[0].text.replace("\u3000", "").replace(" ", "").strip() == key:
            return row
    return None


def fill_docx(info):
    from docx import Document

    doc = Document(str(DOCX))
    changed = 0

    # 1) 封面表格
    cover = doc.tables[0]
    members_line = "、".join(info["members"])
    ids_line = "、".join(info["student_ids"])

    row = row_by_label(cover, "小组成员")
    if row:
        for p in row.cells[1].paragraphs:
            if "成员" in p.text or "、" in p.text:
                if not DRY:
                    set_para_text(p, members_line)
                print(f"  封面 小组成员 → {members_line}")
                changed += 1

    for label, value, shown in [
        ("学号", ids_line, "（info.json 未填，保持不变）"),
        ("班级", info["class_name"], "（info.json 未填，保持不变）"),
        ("指导教师", info["teacher"], "（info.json 未填，保持不变）"),
    ]:
        if not value:
            print(f"  封面 {label}   {shown}")
            continue
        row = row_by_label(cover, label)
        if not row:
            print(f"  ! 封面找不到「{label}」行，跳过")
            continue
        for p in row.cells[1].paragraphs:
            if DRY:
                print(f"  封面 {label} → {value}（当前：{p.text.strip() or '空'}）")
            else:
                set_para_text(p, value)
                print(f"  封面 {label} → {value}")
        changed += 1

    # 2) 附录 A 分工表 + 全文其余占位符
    for table in doc.tables:
        for row in table.rows:
            if row.cells[0].text.strip() in ("（成员二）", "成员二", "（成员三）", "成员三", "（成员四）", "成员四"):
                name = info["members"][["二", "三", "四"].index(row.cells[0].text.strip()[-2]) + 1]
                for p in row.cells[0].paragraphs:
                    if not DRY:
                        set_para_text(p, name)
                print(f"  分工表 {row.cells[0].text.strip()} → {name}")
                changed += 1

    for p in doc.paragraphs:
        for old, idx in PLACEHOLDERS:
            if old in p.text:
                new = info["members"][idx]
                if not DRY:
                    replace_para(p, old, new)
                print(f"  正文 {old} → {new}")
                changed += 1

    if DRY:
        print(f"\n[预览模式] 共 {changed} 处将被修改，未写入任何文件。")
        return changed

    doc.save(str(DOCX))
    print(f"  已保存 {DOCX.name}")
    return changed


# --------------------------------------------------------------------------- #
# pptx
# --------------------------------------------------------------------------- #
def iter_text_frames(shapes):
    for sh in shapes:
        if sh.has_text_frame:
            yield sh.text_frame
        if getattr(sh, "has_table", False) and sh.has_table:
            for row in sh.table.rows:
                for cell in row.cells:
                    yield cell.text_frame
        if sh.shape_type == 6:                      # GROUP
            yield from iter_text_frames(sh.shapes)


def fill_pptx(info):
    from pptx import Presentation

    prs = Presentation(str(PPTX))
    changed = 0
    for no, slide in enumerate(prs.slides, 1):
        for tf in iter_text_frames(slide.shapes):
            for p in tf.paragraphs:
                for old, idx in PLACEHOLDERS:
                    if old in p.text:
                        new = info["members"][idx]
                        if any(old in r.text for r in p.runs):
                            for r in p.runs:
                                if old in r.text:
                                    if not DRY:
                                        r.text = r.text.replace(old, new)
                        elif p.runs:
                            merged = p.text.replace(old, new)
                            if not DRY:
                                p.runs[0].text = merged
                                for r in p.runs[1:]:
                                    r.text = ""
                        print(f"  第 {no} 页 {old} → {new}")
                        changed += 1

    if DRY:
        return changed
    prs.save(str(PPTX))
    print(f"  已保存 {PPTX.name}")
    return changed


# --------------------------------------------------------------------------- #
# 导出 PDF + 刷新提交材料
# --------------------------------------------------------------------------- #
def export_pdf():
    import win32com.client as win32

    word = None
    try:
        word = win32.Dispatch("Word.Application")
        word.Visible = False
        word.DisplayAlerts = 0
        doc = word.Documents.Open(str(DOCX))
        doc.Fields.Update()
        if doc.TablesOfContents.Count:
            doc.TablesOfContents(1).Update()
        doc.Repaginate()
        pages = doc.ComputeStatistics(2)            # wdStatisticPages
        words = doc.ComputeStatistics(0)            # wdStatisticWords
        doc.SaveAs2(str(DOCX_PDF), FileFormat=17)   # wdFormatPDF
        doc.Close(False)
        print(f"  报告 PDF 已导出（{pages} 页 / {words} 字）")
    finally:
        if word is not None:
            try:
                word.Quit()
            except Exception:
                pass

    ppt = None
    try:
        ppt = win32.Dispatch("PowerPoint.Application")
        pres = ppt.Presentations.Open(str(PPTX), WithWindow=False)
        pres.SaveAs(str(PPTX_PDF), 32)              # ppSaveAsPDF
        slides = pres.Slides.Count
        pres.Close()
        print(f"  PPT PDF 已导出（{slides} 页）")
    finally:
        if ppt is not None:
            try:
                ppt.Quit()
            except Exception:
                pass


def refresh_out():
    OUT.mkdir(parents=True, exist_ok=True)
    pairs = [
        (DOCX, "1_课程设计报告.docx"),
        (DOCX_PDF, "1_课程设计报告（PDF版）.pdf"),
        (PPTX, "2_答辩PPT.pptx"),
        (PPTX_PDF, "2_答辩PPT（PDF版）.pdf"),
    ]
    for src, dst in pairs:
        if src.exists():
            shutil.copy2(src, OUT / dst)
            print(f"  已同步 {dst}")
        else:
            print(f"  ! 缺少 {src.name}")


# --------------------------------------------------------------------------- #
def main():
    print("=" * 62)
    info = load_info()
    print("成员：" + "、".join(info["members"]))
    print("=" * 62)

    print("\n[1/4] 填写报告 ...")
    fill_docx(info)
    print("\n[2/4] 填写答辩 PPT ...")
    fill_pptx(info)

    if DRY:
        print("\n预览结束。确认无误后去掉 --dry-run 再运行一次即可写入。")
        return

    print("\n[3/4] 重新导出 PDF（会短暂启动 Word / PowerPoint，请勿手动关闭）...")
    export_pdf()
    print("\n[4/4] 同步到提交材料目录 ...")
    refresh_out()

    print("\n" + "=" * 62)
    print("完成。记得打开报告看一眼封面版式，并在附录 A 手写签名。")
    print(f"提交目录：{OUT}")


if __name__ == "__main__":
    main()
