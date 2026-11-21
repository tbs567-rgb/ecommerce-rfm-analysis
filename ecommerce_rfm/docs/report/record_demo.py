# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[3])

"""录制 Streamlit 三页面演示视频。

通过 Edge 的 CDP 真实操作页面（滚动、切换页签），按实际时间戳逐帧捕获，
再用 ffmpeg 合成 25fps MP4，播放节奏与真实操作一致。
"""
import base64
import io
import json
import os
import subprocess
import sys
import time
import urllib.request

sys.path.insert(0, r"D:\tmp_pdf_lib")
import websocket  # noqa: E402
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
import imageio_ffmpeg  # noqa: E402

EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PORT = 9346
URL = "http://localhost:8501"
W, H = 1440, 810
FPS = 25
DURATION = 62
OUT = _ROOT + r"\ecommerce_rfm\outputs\演示录屏-客户价值分析系统.mp4"
TMP = r"D:\tmp_pdf_lib\frames"
os.makedirs(TMP, exist_ok=True)


def start_edge():
    subprocess.Popen([
        EDGE, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
        "--force-device-scale-factor=1", "--window-size=%d,%d" % (W, H),
        f"--remote-debugging-port={PORT}",
        r"--user-data-dir=D:\tmp_pdf_lib\edge_rec_" + str(int(time.time())),
        "about:blank",
    ])
    for _ in range(40):
        time.sleep(0.5)
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/json/version", timeout=2):
                return True
        except Exception:
            continue
    return False


def new_target():
    req = urllib.request.Request(f"http://127.0.0.1:{PORT}/json/new?{URL}", method="PUT")
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.load(r)


class CDP:
    def __init__(self, ws_url):
        self.ws = websocket.create_connection(ws_url, timeout=180)
        self.mid = 0

    def send(self, method, params=None):
        self.mid += 1
        self.ws.send(json.dumps({"id": self.mid, "method": method, "params": params or {}}))
        while True:
            msg = json.loads(self.ws.recv())
            if msg.get("id") == self.mid:
                return msg

    def js(self, expr):
        return self.send("Runtime.evaluate", {"expression": expr, "returnByValue": True})

    def shot(self):
        res = self.send("Page.captureScreenshot", {"format": "jpeg", "quality": 82})
        return base64.b64decode(res["result"]["data"])


def click_label(c, text):
    expr = ("(() => {const ls=[...document.querySelectorAll('label')];"
            f"const el=ls.find(e=>e.textContent.includes('{text}'));"
            "if(!el) return 'NOT_FOUND'; el.click(); return 'CLICKED';})()")
    r = c.js(expr)
    return r.get("result", {}).get("result", {}).get("value")


def title_card(path):
    im = Image.new("RGB", (W, H), (31, 78, 121))
    d = ImageDraw.Draw(im)
    f1 = ImageFont.truetype(r"C:\Windows\Fonts\msyhbd.ttc", 54)
    f2 = ImageFont.truetype(r"C:\Windows\Fonts\msyh.ttc", 26)
    d.rectangle([100, 300, 190, 310], fill=(197, 90, 17))
    d.text((100, 340), "电商客户价值分析系统", font=f1, fill=(255, 255, 255))
    d.text((100, 430), "RFM 模型 + K-means 聚类 ｜ 三页面交互演示", font=f2, fill=(189, 215, 238))
    d.text((100, 700), "《大数据技术》课程设计 ｜ 第 4 组", font=f2, fill=(157, 195, 230))
    im.save(path)


def main():
    if not start_edge():
        sys.exit("Edge CDP 启动失败")
    t0 = time.time()
    target = new_target()
    c = CDP(target["webSocketDebuggerUrl"])
    c.send("Page.enable")
    c.send("Emulation.setDeviceMetricsOverride",
           {"width": W, "height": H, "deviceScaleFactor": 1, "mobile": False})
    c.send("Page.navigate", {"url": URL})
    print("等待首屏渲染…")
    time.sleep(20)

    # 顺序执行的步骤：(动作, 参数, 持续秒数)
    steps = [
        ("wait", None, 2.5),
        ("scroll", 0, 1.0),
        ("scroll", 800, 4.0),
        ("scroll", 1600, 4.0),
        ("scroll", 0, 2.5),
        ("click", "客户价值分析", 0.8),
        ("wait_text", "客户价值分析", 7.0),
        ("scroll", 650, 4.0),
        ("scroll", 1400, 4.0),
        ("scroll", 0, 2.5),
        ("click", "客户分群", 0.8),
        ("wait_text", "客户分群", 7.0),
        ("scroll", 760, 4.0),
        ("scroll", 1500, 5.0),
        ("scroll", 0, 3.0),
        ("wait", None, 1.5),
    ]
    frames = []
    cur_y, tgt_y = 0, 0
    si = 0
    step_t0 = time.time()
    start = time.time()
    clicked = False

    while si < len(steps):
        el = time.time() - start
        act, arg, dur = steps[si]
        step_el = time.time() - step_t0
        if act == "scroll":
            tgt_y = arg
        elif act == "click":
            print("%.1fs 切换到 %s -> %s" % (el, arg, click_label(c, arg)))
            tgt_y = 0
        elif act == "wait_text":
            body = c.js("document.body.innerText")["result"]["result"].get("value", "")
            hit = ("如何划分客户群体" in body) if arg == "客户分群" else ("不同客户的购买频次" in body)
            if hit:
                if not globals().get("_reported_" + arg):
                    globals()["_reported_" + arg] = True
                    print("%.1fs 「%s」渲染完成" % (el, arg))
            else:
                dur = 0.4  # 继续等待
        dy = tgt_y - cur_y
        if abs(dy) > 1:
            cur_y += dy * 0.16
            c.js("(()=>{const m=document.querySelector('main.stMain')||document.querySelector('main');"
                 "if(m){m.scrollTop=%d;}return 1;})()" % int(cur_y))
        frames.append((el, c.shot()))
        if step_el >= dur:
            si += 1
            step_t0 = time.time()
        time.sleep(0.02)

    c.ws.close()
    print("捕获帧数：", len(frames), " 实际时长 %.1fs" % frames[-1][0])

    # 生成 25fps 帧序列（按时间戳取最近帧）
    title = os.path.join(TMP, "title.png")
    title_card(title)
    title_img = Image.open(title).convert("RGB")

    real_dur = frames[-1][0]
    n_out = int((real_dur + 1.0) * FPS)
    ts = [f[0] for f in frames]
    cache = {}
    ff = imageio_ffmpeg.get_ffmpeg_exe()
    cmd = [ff, "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "%dx%d" % (W, H),
           "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
           "-crf", "21", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL)

    hold_title = int(2.5 * FPS)
    for _ in range(hold_title):
        proc.stdin.write(title_img.tobytes())

    j = 0
    for i in range(n_out - hold_title):
        t = (i + hold_title) / FPS - 2.5
        while j + 1 < len(ts) and ts[j + 1] <= t:
            j += 1
        key = j
        img = cache.get(key)
        if img is None:
            img = Image.open(io.BytesIO(frames[j][1])).convert("RGB").resize((W, H))
            cache[key] = img
            if len(cache) > 40:
                cache.pop(min(cache))
        proc.stdin.write(img.tobytes())

    proc.stdin.close()
    proc.wait()
    print("视频已生成：", OUT, " %.1f MB" % (os.path.getsize(OUT) / 1024 / 1024))


if __name__ == "__main__":
    main()
