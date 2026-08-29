"""
SQLite 数据库模块
==================
管理系统数据库（data/bearing_system.db），包含四张表（对应方案设计 3.6）：

  - sensor_data    : 振动传感器时序数据
  - fault_sample   : 故障样本记录
  - fault_knowledge: 故障知识库（诊断后写入）
  - alarm_record   : 告警记录

提供：初始化建表、故障知识库初始化、诊断/告警记录写入与查询。
"""
import os
import sqlite3
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(PROJECT_ROOT, "data", "bearing_system.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    vibration_value REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS fault_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sample_time TEXT NOT NULL,
    label TEXT NOT NULL,
    fault_type TEXT NOT NULL,
    feature_vector TEXT NOT NULL,
    confidence REAL
);

CREATE TABLE IF NOT EXISTS fault_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fault_type TEXT NOT NULL UNIQUE,
    name TEXT,
    cause TEXT,
    features_desc TEXT,
    advice TEXT,
    checks TEXT
);

CREATE TABLE IF NOT EXISTS alarm_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL,
    alarm_type TEXT NOT NULL,
    description TEXT NOT NULL
);
"""

# 故障知识库（与 src/knowledge_base.py 保持一致）
KNOWLEDGE_ROWS = [
    ("Normal", "正常", "轴承处于正常运行状态", "振动能量与冲击特征正常，峭度接近3",
     "设备运行正常，按计划定期巡检与润滑维护即可", "保持润滑周期;定期监测振动趋势"),
    ("IR", "内圈故障", "内圈滚道点蚀/剥落/疲劳裂纹，装配过紧或润滑不良",
     "峭度与峰值因子显著升高，频谱出现内圈故障特征频率 BPFI",
     "建议停机检修，检查内圈滚道；早期密切监控，中重度更换轴承", "检查内圈滚道;核查装配过盈与润滑;更换轴承(重度)"),
    ("B", "滚动体故障", "滚动体表面点蚀/剥落/裂纹，润滑失效或异物压痕",
     "冲击特征明显，峭度显著增大，频谱出现滚动体故障特征频率 BSF",
     "建议停机检查滚动体表面，滚动体故障发展快应尽早更换轴承", "检查滚动体点蚀/剥落;排查润滑失效与异物;尽早更换轴承"),
    ("OR", "外圈故障", "外圈滚道点蚀/剥落，承载区受力集中或安装不正",
     "周期性冲击稳定，峭度升高，频谱出现外圈故障特征频率 BPFO",
     "建议检修外圈滚道与轴承座配合面，中度以上更换轴承", "检查外圈滚道;检查轴承座配合与对中;更换轴承(中度以上)"),
]


def get_connection():
    """获取数据库连接"""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """初始化数据库表结构，并填充故障知识库"""
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        # 填充知识库（存在则忽略）
        for row in KNOWLEDGE_ROWS:
            conn.execute(
                "INSERT OR IGNORE INTO fault_knowledge "
                "(fault_type, name, cause, features_desc, advice, checks) "
                "VALUES (?,?,?,?,?,?)",
                row,
            )
        conn.commit()
    finally:
        conn.close()


def insert_fault_sample(label, fault_type, feature_vector, confidence):
    """记录一条诊断样本"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO fault_sample "
            "(sample_time, label, fault_type, feature_vector, confidence) "
            "VALUES (?,?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), label,
             fault_type, str(feature_vector), confidence),
        )
        conn.commit()
    finally:
        conn.close()


def insert_alarm(device_id, alarm_type, description):
    """记录一条告警"""
    conn = get_connection()
    try:
        conn.execute(
            "INSERT INTO alarm_record "
            "(timestamp, device_id, alarm_type, description) VALUES (?,?,?,?)",
            (datetime.now().isoformat(timespec="seconds"), device_id,
             alarm_type, description),
        )
        conn.commit()
    finally:
        conn.close()


def query_fault_samples(limit=50):
    """查询最近的诊断样本"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM fault_sample ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_alarms(limit=50):
    """查询最近的告警记录"""
    conn = get_connection()
    try:
        rows = conn.execute(
            "SELECT * FROM alarm_record ORDER BY id DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_knowledge():
    """查询故障知识库"""
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM fault_knowledge").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


if __name__ == "__main__":
    init_db()
    print(f"数据库初始化完成: {DB_PATH}")
    print(f"知识库记录数: {len(query_knowledge())}")
    print(f"诊断记录: {len(query_fault_samples())}, 告警记录: {len(query_alarms())}")
