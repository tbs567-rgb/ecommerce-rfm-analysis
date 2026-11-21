# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[3])

"""打包提交材料：源码 zip + 论文/PPT/视频集中到「提交材料」目录。"""
import glob
import os
import shutil
import zipfile

ROOT = _ROOT + r""
PROJ = os.path.join(ROOT, "ecommerce_rfm")
OUT = os.path.join(ROOT, "提交材料")
os.makedirs(OUT, exist_ok=True)

# ------------------------------------------------------------------ 源码 zip
ZIP = os.path.join(OUT, "4_项目源代码.zip")
if os.path.exists(ZIP):
    os.remove(ZIP)

files = []
files += [os.path.join(PROJ, "app.py"), os.path.join(PROJ, "README.md"),
          os.path.join(PROJ, ".streamlit", "config.toml"),
          os.path.join(ROOT, "requirements.txt"),
          os.path.join(ROOT, "部署与启动说明.md")]
files += sorted(glob.glob(os.path.join(PROJ, "scripts", "*.py")))
files += sorted(glob.glob(os.path.join(PROJ, "docs", "*.md")))
files += [os.path.join(PROJ, "docs", "需求说明-基于RFM与K-means聚类的电商客户价值分析.docx")]
files += sorted(glob.glob(os.path.join(PROJ, "docs", "report", "*.py")))
files += sorted(glob.glob(os.path.join(PROJ, "docs", "report", "*.json")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "*.md")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "*.csv")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "*.json")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "analysis", "*.csv")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "rfm", "*.csv")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "rfm", "*.json")))
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "segments", "*.csv")))
files += [os.path.join(PROJ, "outputs", "dashboard", "客户价值分析看板.html")]
files += sorted(glob.glob(os.path.join(PROJ, "outputs", "screenshots", "*.png")))
files += sorted(glob.glob(os.path.join(ROOT, "*.bat")))

with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as z:
    for f in files:
        if not os.path.exists(f):
            print("跳过（不存在）:", f)
            continue
        arc = os.path.join("项目源代码", os.path.relpath(f, ROOT))
        z.write(f, arc)
print("源码包：%s  %.2f MB  %d 个文件" % (ZIP, os.path.getsize(ZIP) / 1024 / 1024, len(files)))

# ------------------------------------------------------------------ 提交材料
copies = [
    (os.path.join(PROJ, "docs", "课程设计报告-基于RFM与K-means的电商客户价值分析.docx"),
     "1_课程设计报告.docx"),
    (os.path.join(PROJ, "docs", "report", "report_preview.pdf"),
     "1_课程设计报告（PDF版）.pdf"),
    (os.path.join(PROJ, "docs", "答辩PPT-电商客户价值分析.pptx"),
     "2_答辩PPT.pptx"),
    (os.path.join(PROJ, "docs", "report", "ppt_preview.pdf"),
     "2_答辩PPT（PDF版）.pdf"),
    (os.path.join(PROJ, "outputs", "演示录屏-客户价值分析系统.mp4"),
     "3_演示录屏.mp4"),
]
for src, name in copies:
    if not os.path.exists(src):
        print("缺少：", src)
        continue
    dst = os.path.join(OUT, name)
    shutil.copy2(src, dst)
    print("已复制：", name, "%.2f MB" % (os.path.getsize(dst) / 1024 / 1024))
