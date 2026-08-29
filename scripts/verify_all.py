"""整体验证：确认所有核心模块可正常导入与调用"""
import os
import sys

# 添加项目根目录到 sys.path（scripts/ 的上一级）
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src import data_loader
from src import preprocessing
from src import feature_extraction

print("=== 模块导入验证 ===")
print(f"[OK] config      : DATA_DIR={config.DATA_DIR}")
print(f"[OK] data_loader : parse_cwru_filename / load_mat_file / list_data_files")
print(f"[OK] preprocessing: bandpass_filter / sliding_window / zscore_normalize")
print(f"[OK] feature_extraction: extract_features, 特征数={len(feature_extraction.ALL_FEATURES)}")

# 端到端冒烟测试
files = data_loader.list_data_files()
sig, meta = data_loader.load_mat_file(files[0])
win = preprocessing.sliding_window(sig, 1024, 512)
feats = feature_extraction.extract_features(win[0], as_dict=True)
print(f"\n=== 端到端冒烟测试 ===")
print(f"[OK] 加载 {os.path.basename(meta['filepath'])}: 长度={meta['length']}, 标签={meta['label']}")
print(f"[OK] 切片 -> {win.shape}, 特征提取 -> {len(feats)} 维")

# 检查特征是否为有限数值
import numpy as np
X = feature_extraction.extract_features(win[:50])
assert np.isfinite(X).all(), "特征包含非有限值!"
print(f"[OK] 50 个样本特征矩阵 {X.shape}，所有值有限")
print("\n全部验证通过 ✔")
