# -*- coding: utf-8 -*-
import os as _os
from pathlib import Path as _Path
_ROOT = str(_Path(__file__).resolve().parents[2])

"""11_spark_submit.py — 提交 Spark ETL 作业（自带环境自检 + 日志落盘）

做三件事：
1. 预检 MySQL(3307)：没启动就直接给中文提示，不让 Spark 白跑几十秒后写库才炸；
2. 预检 HDFS(9000)：没启动就自动拉起 10_hdfs_daemon.py 并等它就绪，
   同时用 WebHDFS 确认 /ecommerce/raw/online_retail_raw.csv 在不在；
3. 调 spark-submit 跑 09_spark_etl.py，输出原样打到屏幕并另存 bigdata\\_etl_last.log。

退出码：0 成功；4 MySQL 未启动；5 HDFS 未就绪；6 HDFS 原始数据缺失；其余为 Spark 返回码。
"""
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT = _ROOT
SPARK_HOME = ROOT + r"\bigdata\spark-4.3.0-bin-hadoop3"
VENV = ROOT + r"\python_env"
JAVA17 = ROOT + r"\bigdata\jdk-17.0.20.1+1"
HADOOP_HOME = ROOT + r"\bigdata\hadoop-3.3.6"
HDFS_DAEMON = ROOT + r"\ecommerce_rfm\scripts\10_hdfs_daemon.py"
ETL_PY = ROOT + r"\ecommerce_rfm\scripts\09_spark_etl.py"
MYSQL_JAR = ROOT + r"\bigdata\jars\mysql-connector-j-8.4.0.jar"
LOG = ROOT + r"\bigdata\_etl_last.log"

MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3307"))
HDFS_RPC_PORT = 9000
HDFS_HTTP_PORT = 9870
RAW_PATH = "/ecommerce/raw/online_retail_raw.csv"


def port_open(port, timeout=0.8):
    s = socket.socket()
    s.settimeout(timeout)
    try:
        return s.connect_ex(("127.0.0.1", port)) == 0
    finally:
        s.close()


def wait_port(port, seconds, progress=False):
    t0 = time.time()
    last = 0
    while time.time() - t0 < seconds:
        if port_open(port):
            return True
        waited = int(time.time() - t0)
        if progress and waited // 10 > last // 10:
            print("       ...已等 %d 秒" % waited, flush=True)
        last = waited
        time.sleep(2)
    return False


def hdfs_file_status(path, timeout=3):
    """用 NameNode 的 WebHDFS 查文件状态：200=存在，404=不存在，None=还没起来。"""
    url = "http://127.0.0.1:%d/webhdfs/v1%s?op=GETFILESTATUS" % (HDFS_HTTP_PORT, path)
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except urllib.error.HTTPError as e:
        return e.code
    except Exception:
        return None


def start_hdfs_daemon():
    """后台拉起 HDFS 守护进程（新开一个最小化窗口，和 1_start_hdfs.bat 一致）。

    守护进程自己的 stdout 丢掉，避免和 Spark 日志混在一起；
    真正的 NameNode/DataNode 日志在 bigdata\\logs_nn.out、logs_dn.out。
    """
    si = subprocess.STARTUPINFO()
    si.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    si.wShowWindow = 6  # SW_MINIMIZE
    subprocess.Popen([sys.executable, HDFS_DAEMON], cwd=ROOT,
                     stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                     startupinfo=si,
                     creationflags=getattr(subprocess, "CREATE_NEW_CONSOLE", 0x00000010))


def run_with_log(cmd, env):
    """跑 spark-submit，输出既上屏也写日志（按字节转发，不动编码）。"""
    print("submit:", " ".join(cmd), flush=True)
    stdout_bin = getattr(sys.stdout, "buffer", None)
    log = open(LOG, "wb")
    try:
        p = subprocess.Popen(cmd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        reader = getattr(p.stdout, "read1", p.stdout.read)
        while True:
            chunk = reader(4096)
            if not chunk:
                break
            log.write(chunk)
            log.flush()
            if stdout_bin is not None:
                stdout_bin.write(chunk)
                stdout_bin.flush()
        p.wait()
        return p.returncode
    finally:
        log.close()


def main():
    # ---- 预检 0：包所在路径是否适合 MySQL / Hadoop / Java ----
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    try:
        from pathguard import check_path, report as report_path_problem
    except Exception:
        check_path = None
    if check_path is not None:
        problems = check_path(ROOT)
        if problems:
            report_path_problem(ROOT, problems)
            return 7

    # ---- 预检 1：MySQL ----
    if not port_open(MYSQL_PORT):
        print("\n[停止] MySQL（127.0.0.1:%d）没有启动。" % MYSQL_PORT)
        print("       Spark 跑完也写不进库，所以先别跑。")
        print("       请双击 0_start_mysql.bat，看到 [OK] MySQL 已就绪 再回来。\n")
        return 4

    # ---- 预检 2：HDFS ----
    if not port_open(HDFS_RPC_PORT):
        print("[提示] HDFS 没在跑，正在自动启动（约 30 秒，别关那个最小化的窗口）...", flush=True)
        start_hdfs_daemon()
        if not wait_port(HDFS_RPC_PORT, 90, progress=True):
            print("\n[停止] HDFS 90 秒内没起来。")
            print("       请双击 1_start_hdfs.bat 手动启动，看清窗口里的报错再试。\n")
            return 5

    # ---- 预检 3：原始 CSV 是否还在 HDFS 里 ----
    code, t0 = None, time.time()
    while time.time() - t0 < 60:
        code = hdfs_file_status(RAW_PATH)
        if code == 200:
            break
        time.sleep(3)
    if code == 404:
        print("\n[停止] HDFS 里找不到 %s" % RAW_PATH)
        print("       HDFS 数据目录可能被清空/换过盘，需要重新导入原始数据。\n")
        return 6
    if code != 200:
        print("\n[停止] HDFS 已监听但 NameNode 还没就绪（WebHDFS 返回 %s）。" % code)
        print("       等一分钟再跑一次 3_run_full_etl.bat。\n")
        return 5

    print("[自检] MySQL 3307 OK ｜ HDFS 9000 OK ｜ 原始 CSV OK", flush=True)

    # ---- 提交 Spark 作业 ----
    env = os.environ.copy()
    env["JAVA_HOME"] = JAVA17
    env["HADOOP_HOME"] = HADOOP_HOME
    env["SPARK_HOME"] = SPARK_HOME
    env["PATH"] = JAVA17 + r"\bin;" + HADOOP_HOME + r"\bin;" + env["PATH"]
    env["PYSPARK_PYTHON"] = os.path.join(VENV, "Scripts", "python.exe")
    env["PYSPARK_DRIVER_PYTHON"] = env["PYSPARK_PYTHON"]

    cmd = [os.path.join(SPARK_HOME, "bin", "spark-submit.cmd"),
           "--jars", MYSQL_JAR,
           ETL_PY]
    code = run_with_log(cmd, env)
    print("\nspark-submit exit code: %d" % code, flush=True)

    if code == 0:
        print("[OK] 全链路跑通，日志已存：%s" % LOG)
    else:
        print("[失败] Spark 退出码 %d，完整日志：%s" % (code, LOG))
        print("       常见原因：HDFS/MySQL 中途被关、HDFS 里原始 CSV 丢失、端口被占用。")
    return code


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[中断] 用户取消")
        sys.exit(130)
