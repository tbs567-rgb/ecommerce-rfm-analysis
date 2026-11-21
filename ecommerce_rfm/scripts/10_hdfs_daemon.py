# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""10_hdfs_daemon.py — 启动 HDFS NameNode + DataNode 并保持进程存活
用法：后台运行本脚本（run_in_background），脚本退出 = HDFS 停止
"""
import subprocess, os, sys, time, re

ENV = os.environ.copy()
ENV["JAVA_HOME"] = _ROOT + r"\bigdata\jdk-11.0.32.1+1"
ENV["HADOOP_HOME"] = _ROOT + r"\bigdata\hadoop-3.3.6"
ENV["PATH"] = _ROOT + r"\bigdata\hadoop-3.3.6\bin;" + ENV["PATH"]
HDFS = _ROOT + r"\bigdata\hadoop-3.3.6\bin\hdfs.cmd"


def sync_hadoop_conf():
    """启动前把 XML 里的数据目录改写成当前实际路径。

    换盘符、换解压目录后不用手工改配置；路径没变时是空操作。
    """
    conf_dir = os.path.join(_ROOT, "bigdata", "hadoop-3.3.6", "etc", "hadoop")
    base = os.path.join(_ROOT, "bigdata", "data").replace("\\", "/")
    # Hadoop 在 Windows 上要求 /D:/xxx 这种带前导斜杠的写法；
    # 写成 D:/xxx 会被当成 scheme "D"，报 "not accessible or do not exist"。
    if not base.startswith("/"):
        base = "/" + base
    wants = {
        "dfs.namenode.name.dir": base + "/namenode",
        "dfs.datanode.data.dir": base + "/datanode",
        "hadoop.tmp.dir": base + "/tmp",
    }
    for fn in ("hdfs-site.xml", "core-site.xml"):
        p = os.path.join(conf_dir, fn)
        if not os.path.exists(p):
            continue
        with open(p, encoding="utf-8", errors="ignore") as f:
            s = f.read()
        old = s
        for key, val in wants.items():
            pat = r"(<name>" + re.escape(key) + r"</name>\s*<value>)([^<]*)(</value>)"
            s = re.sub(pat, lambda m, v=val: m.group(1) + v + m.group(3), s)
        if s != old:
            with open(p, "w", encoding="utf-8") as f:
                f.write(s)
            print("[conf] %s 已对齐到 %s" % (fn, base), flush=True)


sync_hadoop_conf()

print("starting NameNode...", flush=True)
nn = subprocess.Popen([HDFS, "namenode"], env=ENV,
                      stdout=open(_ROOT + r"\bigdata\logs_nn.out", "ab"),
                      stderr=subprocess.STDOUT)
time.sleep(8)
print("starting DataNode...", flush=True)
dn = subprocess.Popen([HDFS, "datanode"], env=ENV,
                      stdout=open(_ROOT + r"\bigdata\logs_dn.out", "ab"),
                      stderr=subprocess.STDOUT)

while True:
    nn_alive = nn.poll() is None
    dn_alive = dn.poll() is None
    if not nn_alive or not dn_alive:
        print(f"process exited: namenode_alive={nn_alive} datanode_alive={dn_alive}", flush=True)
        break
    time.sleep(15)
sys.exit(1)
