"""回读验证特征矩阵文件"""
import pandas as pd
import numpy as np

# 回读 CSV
df = pd.read_csv("data/processed/features.csv")
print("=== CSV 回读 ===")
print(f"形状: {df.shape}")
print("列名:", list(df.columns[:6]), "...")
print(df.head(3).to_string())
print()

# 加载 npz
d = np.load("data/processed/feature_matrix.npz")
print("=== npz 回读 ===")
print(f"X: {d['X'].shape}, y: {d['y'].shape}")
labels, counts = np.unique(d["y"], return_counts=True)
print("标签分布:", dict(zip(labels, counts)))
