"""
全局配置文件
=============
集中管理项目路径、采样率、信号处理参数等常量，
供数据加载、预处理、特征提取等模块统一引用。
"""

import os

# ---------- 项目路径 ----------
# 本文件位于 src/ 下，项目根目录为其上一级
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "cwru")   # CWRU 原始数据目录
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")        # 模型保存目录

# ---------- 信号参数 ----------
SAMPLE_RATE = 12000        # CWRU 12k 驱动端数据采样频率 (Hz)
CHANNEL = "DE"             # 默认使用驱动端 (Drive End) 加速度信号

# ---------- 切片（滑动窗口）参数 ----------
WINDOW_LENGTH = 1024       # 单个样本的窗口长度（点数）
WINDOW_STRIDE = 512        # 滑动窗口步长（点数）
# 说明：12kHz 采样下，1024 点约对应 0.085 秒振动数据，
# 覆盖多个旋转周期（1797 RPM 时转频约 29.95 Hz），足以表征故障冲击特征。

# ---------- 故障类别定义 ----------
# 类别标签 -> 中文名（供可视化与展示使用）
CLASS_NAMES = {
    "Normal": "正常",
    "IR": "内圈故障",
    "B": "滚动体故障",
    "OR": "外圈故障",
}
