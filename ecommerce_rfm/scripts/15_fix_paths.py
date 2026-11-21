# -*- coding: utf-8 -*-
"""归拢后统一替换旧路径引用：D:\graduation_project\bigdata / D:\graduation_project\ecommerce_rfm → D:\graduation_project\..."""
import os

ROOT = r"D:\graduation_project"
PAIRS = [
    (rb"D:\graduation_project\bigdata",       rb"D:\graduation_project\bigdata"),
    (b"D:/graduation_project/bigdata",        b"D:/graduation_project/bigdata"),
    (rb"D:\graduation_project\ecommerce_rfm", rb"D:\graduation_project\ecommerce_rfm"),
    (b"D:/graduation_project/ecommerce_rfm",  b"D:/graduation_project/ecommerce_rfm"),
]
SKIP_DIRS = {"hadoop-3.3.6\\share", "spark-4.3.0-bin-hadoop3\\jars",
             "hadoop-3.3.6/share", "spark-4.3.0-bin-hadoop3/jars",
             "python_env", "__pycache__"}
EXTS = {".py", ".md", ".cmd", ".xml", ".bat", ".ini", ".html",
        ".properties", ".sh", ".cfg", ".txt", ".json", ".log"}

changed = []
for dirpath, dirs, files in os.walk(ROOT):
    rel_dir = os.path.relpath(dirpath, ROOT)
    if any(s in rel_dir for s in SKIP_DIRS):
        dirs[:] = []
        continue
    for fn in files:
        if os.path.splitext(fn)[1].lower() not in EXTS:
            continue
        p = os.path.join(dirpath, fn)
        try:
            with open(p, "rb") as f:
                data = f.read()
        except OSError:
            continue
        nd = data
        for a, b in PAIRS:
            nd = nd.replace(a, b)
        if nd != data:
            with open(p, "wb") as f:
                f.write(nd)
            changed.append(os.path.relpath(p, ROOT))

print("changed files:")
for c in sorted(changed):
    print(" ", c)
print("total:", len(changed))
