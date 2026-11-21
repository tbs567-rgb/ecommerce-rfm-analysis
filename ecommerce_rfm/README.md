# 基于 RFM 与 K-means 的电商客户价值分析

以 UCI Online Retail 真实交易数据（541,909 条，英国在线零售商 2010-12 ~ 2011-12）为对象，
完成「采集 → 清洗 → 分布式存储 → 统计分析 → 聚类挖掘 → 交互式可视化」全链路，
用 RFM 模型 + K-means 把 4,334 位有消费记录的客户分为三类，并给出分层运营建议。

---

## 一、运行环境（已在包内固化）

| 组件 | 版本 | 说明 |
|---|---|---|
| Python | 3.13.14 | 包内自带 `python_runtime` + `python_env`，无需另装 |
| JDK | 11.0.31 / 17.0.19 | Hadoop 用 11，Spark 4.x 要求 17，两者并存 |
| Hadoop | 3.3.6 | HDFS 伪分布式，NameNode 端口 9870 |
| Spark | 4.3.0 | `spark-4.3.0-bin-hadoop3`，PySpark 4.3.0 |
| MySQL | 8.0.38 | 库名 `ecommerce_rfm`，账号 root / 123456 |
| DBeaver | 26.2.4 CE | 数据库可视化管理（随包内置） |

Python 关键依赖：pandas 3.1.0、scikit-learn 1.9.1、plotly 7.1.0、streamlit 1.67.0、
SQLAlchemy 2.1.6、PyMySQL、pyspark 4.3.0。完整清单见 `../requirements.txt`。

## 二、依赖安装（重建环境时才需要）

```bash
pip install -r ../requirements.txt -i https://mirrors.aliyun.com/pypi/simple/
```

包内 `python_env` 已装好全部依赖，正常使用**不需要**执行上面这条命令。

## 三、一键运行

在运行包根目录（与 `0_start_mysql.bat` 同级的那一层）下双击：

| 脚本 | 作用 |
|---|---|
| `0_start_mysql.bat` | 启动内置绿色版 MySQL（3307，必须先跑） |
| `6_open_streamlit.bat` | 打开三页面交互分析系统（localhost:8501） |
| `4_open_dashboard.bat` | 打开离线 HTML 看板（无网也能演示） |
| `1_start_hdfs.bat` | 启动 HDFS（NameNode + DataNode） |
| `2_spark_smoketest.bat` | Spark 读 HDFS 冒烟测试，输出 PASS 即链路正常 |
| `3_run_full_etl.bat` | 跑完整 Spark ETL（清洗 + 统计 + RFM 写回 MySQL） |
| `5_restore_mysql.bat` | 重新导入数据库备份 |
| `9_stop_hdfs.bat` | 停止 HDFS |

手动跑单个脚本：

```bash
cd /d 运行包根目录
python_env\Scripts\python.exe ecommerce_rfm\scripts\07_kmeans.py
```

## 四、目录结构

```
ecommerce_rfm/
├── README.md                 本文件
├── app.py                    Streamlit 三页面交互系统（可视化层）
├── .streamlit/config.toml    端口/主题配置
├── data/
│   ├── raw/                  原始数据（online_retail_raw.csv）
│   └── processed/            清洗后样本
├── scripts/                  全部分析代码（按执行序号编排，见下表）
├── docs/                     需求说明、表结构说明、大数据链路说明、运行手册
└── outputs/
    ├── analysis/             月度趋势、Top 商品、国家分布等统计结果
    ├── rfm/                  RFM 明细与分布
    ├── segments/             K-means 分群结果与选 k 评估
    ├── dashboard/            离线 HTML 看板
    └── screenshots/          三页面运行截图
```

### 代码模块索引（对应课程要求的 src/ 分层）

| 规范目录 | 本项目文件 | 职责 |
|---|---|---|
| `src/preprocessing/` | `scripts/01_explore.py`、`02_clean_check.py`、`03_clean.py` | 数据探查、清洗规则、清洗前后对比 |
| `src/storage/` | `scripts/06_mysql_load.py`、`10_hdfs_daemon.py`、`11_spark_submit.py` | 建表 DDL、MySQL 导入、HDFS 启停、Spark 提交 |
| `src/analysis/` | `scripts/04_analysis.py`、`05_rfm.py`、`07_kmeans.py` | 统计分析、RFM 打分、K-means 聚类与评估 |
| `src/analysis/`（分布式） | `scripts/09_spark_etl.py`、`13_spark_smoketest.py` | Spark on HDFS 清洗/统计/RFM，与 Pandas 基线对账 |
| `src/visualization/` | `scripts/08_dashboard.py`、`app.py` | Plotly 离线看板、Streamlit 交互系统 |

## 五、执行顺序

```
01_explore → 02_clean_check → 03_clean → 06_mysql_load
                                    ↓
              04_analysis → 05_rfm → 07_kmeans → 08_dashboard
                                    ↓
              09_spark_etl（分布式重算，结果写回 MySQL 对账）
```

## 六、关键口径

- 有效购买：`is_valid_purchase = 1 AND is_special = 0 AND Quantity > 0`
- 退货单（Quantity<0）、取消单（InvoiceNo 以 C 开头）、缺失 CustomerID 的行不计入 RFM
- R = 参考日期（最大有效购买日次日）− 最近一次购买日；F = 去重订单数；M = 消费金额合计
- 聚类前对 R/F/M 做标准化（R 取负向，使"数值大 = 价值高"方向一致），k 由肘部法 + 轮廓系数确定

## 七、结果核对基准

| 指标 | 数值 |
|---|---|
| 原始记录 | 541,909 |
| 清洗后记录 | 536,641 |
| 有效销售额 | £8,737,228 |
| 有效订单数 | 18,402 |
| 有效客户数 | 4,334 |
| 分群 | 重要价值 748 / 一般发展 1,710 / 一般挽留 1,876 |
| 轮廓系数（k=3） | 0.3387 |

Pandas 与 Spark 两条链路对以上数字逐项比对，`outputs/spark_check.json` 中 `"pass": true`。
