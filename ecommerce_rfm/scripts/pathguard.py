# -*- coding: utf-8 -*-
"""pathguard.py — 检查“包所在路径”是否适合本项目里的原生组件。

为什么需要：
  MySQL 8.0 在中文路径下启动会直接失败（Failed to set datadir）；
  Hadoop / Java 在含空格或 & % ^ ! 的路径下，偶尔会读不到配置文件。
  这些错误对不熟悉的人很难看懂，所以在第一步就用中文说清楚。

用法：
  python ecommerce_rfm\\scripts\\pathguard.py "D:\\bigdata_course_project\\03_runtime"
  返回码 0 = 正常；9 = 路径有硬性问题。
"""
import os
import sys


def check_path(root):
    """返回问题列表，空列表表示没问题。"""
    root = (root or "").rstrip("\\/")
    problems = []
    if not root.isascii():
        problems.append("路径里有中文（或其它非英文字符）")
    if " " in root:
        problems.append("路径里有空格")
    for ch in "&%^!":
        if ch in root:
            problems.append("路径里有特殊符号 %s" % ch)
    return problems


def report(root, problems):
    print()
    print("[路径有问题] 当前目录：%s" % root)
    for p in problems:
        print("   - %s" % p)
    print("   MySQL 8 在中文路径下会直接启动失败，Hadoop/Java 在含空格的路径下也可能读不到配置。")
    print("   处理办法：把【整个包】（不是只搬 03_runtime）移到纯英文、无空格的路径，例如")
    print("            D:\\bigdata_course_project")
    print("   搬完不用改任何配置，所有 bat 会自动适配新路径。")
    print()


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    problems = check_path(root)
    if problems:
        report(root, problems)
        return 9
    return 0


if __name__ == "__main__":
    sys.exit(main())
