"""
模型训练与评估脚本
==================
训练 KNN / SVM / 随机森林 三种分类模型，评估并保存最优模型。

评估方式：
  1. 普通随机划分（train_test_split，按样本分层）
  2. 按文件分组划分（GroupShuffleSplit，避免同一 .mat 文件的
     相邻窗口同时出现在训练/测试集造成的数据泄漏）

输出：
  models/fault_classifier.pkl   最优模型（随机森林）
  models/training_report.txt    训练评估报告
  models/confusion_matrix.png   混淆矩阵可视化（可选）
"""
import os
import sys
import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src import config
from src.classifier import load_features, get_models, train_evaluate, cross_validate, save_model


def main():
    # 1. 加载特征
    X, y, names = load_features()
    print(f"特征数据: X={X.shape}, 类别={names}")

    # 2. 加载文件分组信息（用于防泄漏评估）
    csv_path = os.path.join(config.PROJECT_ROOT, "data", "processed", "features.csv")
    groups = None
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        # 每个 .mat 文件作为一个分组
        groups = df["file"].values
        print(f"文件分组: {len(np.unique(groups))} 个 .mat 文件")

    # 3. 训练评估全部模型
    results = {}
    for name, model in get_models().items():
        print(f"\n===== {name} =====")
        res = train_evaluate(X, y, model, test_size=0.2, random_state=42)
        cv = cross_validate(X, y, model, cv=5)
        results[name] = {"result": res, "cv_mean": cv.mean(), "cv_std": cv.std()}
        print(f"测试集准确率: {res['accuracy']:.4f}")
        print(f"5 折交叉验证: {cv.mean():.4f} ± {cv.std():.4f}")

    # 4. 按文件分组的防泄漏评估（以随机森林为例）
    if groups is not None:
        print("\n===== 按文件分组评估（防数据泄漏） =====")
        from sklearn.model_selection import GroupShuffleSplit
        best_name = max(results, key=lambda k: results[k]["cv_mean"])
        best_model = results[best_name]["result"]["model"]
        print(f"评估模型: {best_name}")

        gss = GroupShuffleSplit(n_splits=1, test_size=0.2, random_state=42)
        train_idx, test_idx = next(gss.split(X, y, groups))
        best_model.fit(X[train_idx], y[train_idx])
        y_pred = best_model.predict(X[test_idx])
        from sklearn.metrics import accuracy_score
        acc = accuracy_score(y[test_idx], y_pred)
        print(f"按文件划分测试集准确率: {acc:.4f}")
        results["grouped_accuracy"] = acc

    # 5. 保存最优模型（按交叉验证均值）
    best_name = max(results.keys(), key=lambda k: results[k]["cv_mean"] if isinstance(results.get(k), dict) and "cv_mean" in results[k] else -1)
    best_model = results[best_name]["result"]["model"]
    save_path = save_model(best_model, "fault_classifier.pkl")
    print(f"\n最优模型: {best_name} -> 已保存到 {save_path}")

    # 6. 输出分类报告与混淆矩阵
    best_res = results[best_name]["result"]
    report_path = os.path.join(config.MODELS_DIR, "training_report.txt")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("轴承故障分类 - 训练评估报告\n")
        f.write("=" * 50 + "\n")
        f.write(f"数据: {X.shape[0]} 样本, {X.shape[1]} 特征\n")
        f.write(f"类别: {list(names)}\n\n")
        for name in results:
            if isinstance(results[name], dict) and "cv_mean" in results[name]:
                f.write(f"\n----- {name} -----\n")
                f.write(f"测试集准确率: {results[name]['result']['accuracy']:.4f}\n")
                f.write(f"5 折交叉验证: {results[name]['cv_mean']:.4f} ± {results[name]['cv_std']:.4f}\n")
                f.write("分类报告:\n")
                f.write(results[name]["result"]["report"])
        if "grouped_accuracy" in results:
            f.write(f"\n按文件分组测试集准确率: {results['grouped_accuracy']:.4f}\n")
    print(f"评估报告已保存: {report_path}")

    # 7. 混淆矩阵可视化
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        # 配置中文字体，避免中文显示为方块
        plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "SimSun"]
        plt.rcParams["axes.unicode_minus"] = False
        cm = best_res["conf_matrix"]
        fig, ax = plt.subplots(figsize=(6, 5))
        im = ax.imshow(cm, cmap="Blues")
        ax.set_xticks(range(len(names))); ax.set_yticks(range(len(names)))
        ax.set_xticklabels(names); ax.set_yticklabels(names)
        ax.set_xlabel("预测类别"); ax.set_ylabel("真实类别")
        ax.set_title(f"{best_name} 混淆矩阵 (准确率 {best_res['accuracy']:.3f})")
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                ax.text(j, i, str(cm[i, j]), ha="center", va="center",
                        color="white" if cm[i, j] > cm.max() / 2 else "black")
        fig.colorbar(im)
        cm_path = os.path.join(config.MODELS_DIR, "confusion_matrix.png")
        plt.tight_layout()
        plt.savefig(cm_path, dpi=150)
        print(f"混淆矩阵已保存: {cm_path}")
    except Exception as e:
        print(f"混淆矩阵图保存失败: {e}")


if __name__ == "__main__":
    main()
