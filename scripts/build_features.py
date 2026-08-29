"""
数据准备脚本：原始振动数据 -> 特征矩阵
=======================================
将 CWRU 原始 .mat 数据经「切片 -> 特征提取」转换为机器学习可用的
特征矩阵与标签，输出到 data/processed/ 目录。

输出：
  data/processed/features.csv        特征矩阵（带样本ID/标签列）
  data/processed/feature_matrix.npz  特征矩阵 numpy 压缩包（供模型训练）
  data/processed/dataset_summary.json 数据统计摘要

用法：
  python scripts/build_features.py
"""
import os
import json
import numpy as np
import pandas as pd

# 确保能导入 src 包
import sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from src import config
from src.data_loader import load_mat_file, list_data_files
from src.preprocessing import preprocess_signal
from src.feature_extraction import extract_features, feature_names


def build_dataset(data_dir=None, channel="DE", window_length=None, stride=None,
                  lowcut=None, highcut=None, normalize="zscore"):
    """
    构建特征数据集。

    参数：
      data_dir      : CWRU 数据目录
      channel       : 通道
      window_length : 切片窗口长度
      stride        : 滑动步长
      lowcut/highcut: 带通滤波截止频率
      normalize     : 标准化方式

    返回：
      (feature_matrix, labels, metas)
        feature_matrix : (n_samples, n_features)
        labels         : (n_samples,) 故障类型标签
        metas          : list[dict] 每条样本的元信息
    """
    files = list_data_files(data_dir)
    all_rows = []
    all_labels = []
    all_metas = []

    for fp in files:
        signal, meta = load_mat_file(fp, channel=channel)
        windows = preprocess_signal(
            signal, fs=config.SAMPLE_RATE,
            lowcut=lowcut, highcut=highcut,
            window_length=window_length, stride=stride,
            normalize=normalize,
        )
        feats = extract_features(windows, fs=config.SAMPLE_RATE)
        n = windows.shape[0]

        all_rows.append(feats)
        all_labels.extend([meta["label"]] * n)
        for i in range(n):
            m = dict(meta)
            m["window_index"] = i
            all_metas.append(m)

        print(f"{os.path.basename(fp)}: {n} 个窗口 -> 特征矩阵 {feats.shape}")

    feature_matrix = np.vstack(all_rows)
    labels = np.array(all_labels)
    return feature_matrix, labels, all_metas


def main():
    data_dir = config.DATA_DIR
    processed_dir = os.path.join(config.PROJECT_ROOT, "data", "processed")
    os.makedirs(processed_dir, exist_ok=True)

    print("=" * 60)
    print("开始构建特征数据集")
    print(f"数据目录: {data_dir}")
    print(f"参数: 窗口={config.WINDOW_LENGTH}, 步长={config.WINDOW_STRIDE}, "
          f"通道={config.CHANNEL}")
    print("=" * 60)

    X, y, metas = build_dataset(data_dir=data_dir, channel=config.CHANNEL)
    print(f"\n特征矩阵: {X.shape}, 标签: {y.shape}")

    # 类别统计
    unique, counts = np.unique(y, return_counts=True)
    summary = {"n_samples": int(len(y)), "n_features": int(X.shape[1])}
    print("\n类别分布：")
    for lab, cnt in zip(unique, counts):
        print(f"  {lab}: {cnt} 个样本")
        summary[f"class_{lab}"] = int(cnt)

    # 保存为 CSV（带可读标签）
    df = pd.DataFrame(X, columns=feature_names())
    df.insert(0, "label", y)
    df.insert(1, "file", [m["filepath"].split(os.sep)[-1] for m in metas])
    csv_path = os.path.join(processed_dir, "features.csv")
    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    print(f"\n已保存: {csv_path}")

    # 保存为 numpy 压缩包（供模型训练直接加载）
    npz_path = os.path.join(processed_dir, "feature_matrix.npz")
    np.savez_compressed(npz_path, X=X, y=y)
    print(f"已保存: {npz_path}")

    # 保存统计摘要
    json_path = os.path.join(processed_dir, "dataset_summary.json")
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)
    print(f"已保存: {json_path}")


if __name__ == "__main__":
    main()
