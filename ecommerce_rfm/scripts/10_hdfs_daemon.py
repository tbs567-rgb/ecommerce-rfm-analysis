# -*- coding: utf-8 -*-
"""10_hdfs_daemon.py — 启动 HDFS NameNode + DataNode 并保持进程存活
用法：后台运行本脚本（run_in_background），脚本退出 = HDFS 停止
"""
import subprocess, os, sys, time

ENV = os.environ.copy()
ENV["JAVA_HOME"] = r"D:\graduation_project\bigdata\jdk-11.0.32.1+1"
ENV["HADOOP_HOME"] = r"D:\graduation_project\bigdata\hadoop-3.3.6"
ENV["PATH"] = r"D:\graduation_project\bigdata\hadoop-3.3.6\bin;" + ENV["PATH"]
HDFS = r"D:\graduation_project\bigdata\hadoop-3.3.6\bin\hdfs.cmd"

print("starting NameNode...", flush=True)
nn = subprocess.Popen([HDFS, "namenode"], env=ENV,
                      stdout=open(r"D:\graduation_project\bigdata\logs_nn.out", "ab"),
                      stderr=subprocess.STDOUT)
time.sleep(8)
print("starting DataNode...", flush=True)
dn = subprocess.Popen([HDFS, "datanode"], env=ENV,
                      stdout=open(r"D:\graduation_project\bigdata\logs_dn.out", "ab"),
                      stderr=subprocess.STDOUT)

while True:
    nn_alive = nn.poll() is None
    dn_alive = dn.poll() is None
    if not nn_alive or not dn_alive:
        print(f"process exited: namenode_alive={nn_alive} datanode_alive={dn_alive}", flush=True)
        break
    time.sleep(15)
sys.exit(1)
