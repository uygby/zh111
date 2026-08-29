"""
故障分类模块
============
基于提取的振动特征训练机器学习分类模型，实现轴承故障类型识别
（正常 / 内圈故障 / 滚动体故障 / 外圈故障）。

支持算法：KNN、SVM、随机森林
提供：数据加载、训练、评估（含交叉验证与混淆矩阵）、模型保存/加载
"""
import os
import numpy as np

# Windows 下若用户名为中文，joblib 多进程临时目录需使用 ASCII 路径，
# 否则 multiprocessing 序列化路径会触发 UnicodeEncodeError。
if os.name == "nt":
    _joblib_tmp = os.environ.get("JOBLIB_TEMP_FOLDER")
    if not _joblib_tmp:
        for cand in (r"C:\Windows\Temp", r"C:\Temp", r"C:\ProgramData\Temp"):
            try:
                os.makedirs(cand, exist_ok=True)
                with open(os.path.join(cand, ".w"), "w") as f:
                    f.write("")
                os.remove(os.path.join(cand, ".w"))
                os.environ["JOBLIB_TEMP_FOLDER"] = cand
                break
            except OSError:
                continue

from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import (
    accuracy_score, classification_report, confusion_matrix,
)
import joblib

from . import config

# 类别与标签映射（保持与特征数据一致）
CLASS_ORDER = ["B", "IR", "Normal", "OR"]


def load_features(path: str = None) -> tuple:
    """
    加载特征矩阵。

    参数：
      path : feature_matrix.npz 路径，默认使用 data/processed/feature_matrix.npz

    返回：
      X : (n_samples, n_features)
      y : (n_samples,) 类别标签
      names : 类别名列表
    """
    path = path or os.path.join(config.PROJECT_ROOT, "data", "processed", "feature_matrix.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"特征文件不存在: {path}\n请先运行 scripts/build_features.py 生成特征数据"
        )
    d = np.load(path)
    X, y = d["X"], d["y"]
    names = sorted(np.unique(y), key=lambda c: CLASS_ORDER.index(c) if c in CLASS_ORDER else 99)
    return X, y, names


def get_models() -> dict:
    """
    返回候选分类模型字典（均已包装为 特征标准化 + 分类器 的 Pipeline）。

    说明：SVM/KNN 对特征尺度敏感，必须先做 StandardScaler 标准化；
    随机森林基于树模型，不依赖缩放，但统一走 Pipeline 保持接口一致。
    """
    return {
        "KNN": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", KNeighborsClassifier(n_neighbors=5)),
        ]),
        "SVM": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", SVC(kernel="rbf", C=10, gamma="scale")),
        ]),
        "RandomForest": Pipeline([
            ("scaler", StandardScaler()),
            ("clf", RandomForestClassifier(
                n_estimators=200, max_depth=None, random_state=42, n_jobs=-1
            )),
        ]),
    }


def train_evaluate(X: np.ndarray, y: np.ndarray, model=None,
                   test_size: float = 0.2, random_state: int = 42) -> dict:
    """
    训练并评估单个模型，返回指标与训练好的模型。

    返回字典：
      model         : 训练好的模型
      accuracy      : 测试集准确率
      report        : 分类报告（字符串）
      conf_matrix   : 混淆矩阵 (ndarray)
      y_true/y_pred : 测试集真实/预测标签
    """
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    result = {
        "model": model,
        "accuracy": accuracy_score(y_test, y_pred),
        "report": classification_report(y_test, y_pred, zero_division=0),
        "conf_matrix": confusion_matrix(y_test, y_pred),
        "y_true": y_test,
        "y_pred": y_pred,
        "X_train": X_train, "X_test": X_test, "y_train": y_train,
    }
    return result


def cross_validate(X: np.ndarray, y: np.ndarray, model,
                   cv: int = 5, random_state: int = 42) -> np.ndarray:
    """K 折交叉验证，返回各折准确率数组"""
    from sklearn.model_selection import cross_val_score
    scores = cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)
    return scores


def save_model(model, filename: str = "fault_classifier.pkl") -> str:
    """保存模型到 models/ 目录，返回保存路径"""
    path = os.path.join(config.MODELS_DIR, filename)
    os.makedirs(config.MODELS_DIR, exist_ok=True)
    joblib.dump(model, path)
    return path


def load_model(filename: str = "fault_classifier.pkl"):
    """从 models/ 目录加载模型"""
    path = os.path.join(config.MODELS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"模型不存在: {path}")
    return joblib.load(path)


if __name__ == "__main__":
    X, y, names = load_features()
    print(f"特征数据: X={X.shape}, 类别={names}")
    for name, model in get_models().items():
        res = train_evaluate(X, y, model)
        print(f"\n===== {name} =====")
        print(f"测试集准确率: {res['accuracy']:.4f}")
        scores = cross_validate(X, y, model, cv=5)
        print(f"5 折交叉验证: {scores.mean():.4f} ± {scores.std():.4f}")
