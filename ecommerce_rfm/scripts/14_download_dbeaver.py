# -*- coding: utf-8 -*-
"""多线程分块下载器：绕开单连接限速（记忆经验：多连接速度可叠加）"""
import os, sys, time, urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

URL = "https://ghfast.top/https://github.com/dbeaver/dbeaver/releases/download/26.2.4/dbeaver-ce-26.2.4-windows-x86_64.zip"
OUT = r"D:\graduation_project\bigdata\tools_dbeaver.zip"
PART_DIR = OUT + ".parts"
N_THREADS = 16
CHUNK = 4 * 1024 * 1024  # 每片 4MB

os.makedirs(PART_DIR, exist_ok=True)

# 拿总大小
req = urllib.request.Request(URL, method="HEAD")
with urllib.request.urlopen(req, timeout=30) as r:
    total = int(r.headers["Content-Length"])
print(f"total: {total/1048576:.1f} MB, {N_THREADS} threads, chunk {CHUNK//1048576}MB", flush=True)

ranges = [(s, min(s + CHUNK, total) - 1) for s in range(0, total, CHUNK)]

def fetch(i, s, e):
    part = os.path.join(PART_DIR, f"{i:05d}.part")
    if os.path.exists(part) and os.path.getsize(part) == e - s + 1:
        return 0  # 已完成
    for attempt in range(5):
        try:
            req = urllib.request.Request(URL, headers={"Range": f"bytes={s}-{e}"})
            with urllib.request.urlopen(req, timeout=60) as r, open(part, "wb") as f:
                while True:
                    buf = r.read(256 * 1024)
                    if not buf:
                        break
                    f.write(buf)
            if os.path.getsize(part) == e - s + 1:
                return 1
        except Exception:
            time.sleep(2 + attempt * 3)
    raise RuntimeError(f"chunk {i} failed")

done_bytes = sum(os.path.getsize(os.path.join(PART_DIR, f))
                 for f in os.listdir(PART_DIR) if f.endswith(".part"))
t0 = time.time()
with ThreadPoolExecutor(N_THREADS) as ex:
    futs = {ex.submit(fetch, i, s, e): (i, s, e) for i, (s, e) in enumerate(ranges)}
    n = 0
    for fut in as_completed(futs):
        fut.result()
        n += 1
        if n % 8 == 0:
            now = sum(os.path.getsize(os.path.join(PART_DIR, f))
                      for f in os.listdir(PART_DIR) if f.endswith(".part"))
            speed = (now - done_bytes) / max(time.time() - t0, 1) / 1024
            print(f"progress {now/1048576:.0f}/{total/1048576:.0f} MB  avg {speed:.0f} KB/s", flush=True)

# 合并
with open(OUT, "wb") as out:
    for i in range(len(ranges)):
        with open(os.path.join(PART_DIR, f"{i:05d}.part"), "rb") as p:
            out.write(p.read())
got = os.path.getsize(OUT)
print(f"DONE {got}/{total} {'OK' if got == total else 'SIZE MISMATCH!'}", flush=True)
if got == total:
    import shutil
    shutil.rmtree(PART_DIR)
