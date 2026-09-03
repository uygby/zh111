# -*- coding: utf-8 -*-
"""
轴承故障诊断系统 - 单文件整合版
================================
将项目所有核心模块（配置/数据加载/预处理/特征提取/分类/健康预测/
知识库/数据库/Flask后端）整合为一个 Python 文件，便于提交与演示。

启动：python bearing_system.py
访问：http://127.0.0.1:5000

依赖：numpy scipy scikit-learn flask flask-cors joblib
"""

import os
import sys
import re
import sqlite3
from datetime import datetime

import numpy as np
import scipy.io
from scipy import signal as scipy_signal
from scipy.fft import rfft, rfftfreq

# Windows 中文路径下 joblib 临时目录修复
if os.name == "nt":
    for cand in (r"C:\Windows\Temp", r"C:\Temp", r"C:\ProgramData\Temp"):
        try:
            os.makedirs(cand, exist_ok=True)
            os.environ["JOBLIB_TEMP_FOLDER"] = cand
            break
        except OSError:
            continue

from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.neighbors import KNeighborsClassifier
from sklearn.svm import SVC
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
import joblib

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

# ============================================================
# 一、全局配置
# ============================================================
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_ROOT, "data", "cwru")
MODELS_DIR = os.path.join(PROJECT_ROOT, "models")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "bearing_system.db")

SAMPLE_RATE = 12000
CHANNEL = "DE"
WINDOW_LENGTH = 1024
WINDOW_STRIDE = 512

CLASS_NAMES = {
    "Normal": "正常",
    "IR": "内圈故障",
    "B": "滚动体故障",
    "OR": "外圈故障",
}
CLASS_ORDER = ["B", "IR", "Normal", "OR"]

# ============================================================
# 二、数据加载
# ============================================================
def parse_cwru_filename(filename):
    """解析 CWRU 数据文件名，返回元信息字典"""
    name = os.path.basename(filename)
    m = re.match(r"^normal_(\d+)_(\d+)\.mat$", name, re.IGNORECASE)
    if m:
        return {"label": "Normal", "label_cn": CLASS_NAMES["Normal"],
                "diameter": None, "position": None,
                "load": int(m.group(1)), "sample_id": int(m.group(2)),
                "sample_rate": 12000, "end": "Drive"}
    m = re.match(r"^(12k|48k)_(Drive_End|Fan_End)_(IR|B|OR)(\d{3})(?:@(\d+))?_(\d)_(\d+)\.mat$",
                 name, re.IGNORECASE)
    if m:
        sr, end, label, diameter, position, load, sample_id = m.groups()
        label = label.upper()
        return {"label": label, "label_cn": CLASS_NAMES[label],
                "diameter": diameter,
                "position": position if label == "OR" else None,
                "load": int(load), "sample_id": int(sample_id),
                "sample_rate": 12000 if sr == "12k" else 48000,
                "end": "Drive" if "Drive" in end else "Fan"}
    raise ValueError(f"无法识别的 CWRU 文件名: {name}")


def list_data_files(data_dir=None):
    """列出数据目录下所有 .mat 文件"""
    data_dir = data_dir or DATA_DIR
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")
    return [os.path.join(data_dir, f) for f in sorted(os.listdir(data_dir))
            if f.lower().endswith(".mat")]


def load_mat_file(filepath, channel="DE"):
    """加载单个 .mat 文件，返回 (信号一维数组, 元信息字典)"""
    channel = channel.upper()
    data = scipy.io.loadmat(filepath)
    pattern = re.compile(rf"^X(\d+)_{channel}_time$")
    signal_key, sample_id = None, None
    for key in data:
        if pattern.match(key):
            signal_key = key
            sample_id = int(pattern.match(key).group(1))
            break
    if signal_key is None:
        raise ValueError(f"文件中未找到 {channel}_time 变量")
    signal = np.asarray(data[signal_key]).ravel().astype(np.float64)
    rpm = None
    rpm_key = f"X{sample_id}RPM"
    if rpm_key in data:
        rpm = float(np.asarray(data[rpm_key]).ravel()[0])
    meta = parse_cwru_filename(filepath)
    meta.update({"channel": channel, "rpm": rpm, "length": len(signal),
                 "filepath": filepath})
    return signal, meta


# ============================================================
# 三、信号预处理
# ============================================================
def bandpass_filter(x, fs=None, lowcut=None, highcut=None, order=4):
    """Butterworth 带通滤波"""
    if lowcut is None and highcut is None:
        return x.copy()
    fs = fs or SAMPLE_RATE
    nyq = 0.5 * fs
    if lowcut is not None and highcut is not None:
        btype, freqs = "bandpass", [lowcut, highcut]
    elif lowcut is not None:
        btype, freqs = "highpass", [lowcut]
    else:
        btype, freqs = "lowpass", [highcut]
    freqs = [min(f, nyq * 0.99) for f in freqs]
    if freqs[0] <= 0:
        return x.copy()
    b, a = scipy_signal.butter(order, freqs, btype=btype, fs=fs)
    return scipy_signal.filtfilt(b, a, x)


def detrend_signal(x):
    """去除线性趋势"""
    return scipy_signal.detrend(x, type="linear")


def sliding_window(x, window_length=None, stride=None):
    """滑动窗口切片，返回 (n_windows, window_length) 数组"""
    window_length = window_length or WINDOW_LENGTH
    stride = stride or WINDOW_STRIDE
    n = len(x)
    if n < window_length:
        raise ValueError(f"信号长度 {n} 小于窗口长度 {window_length}")
    n_windows = (n - window_length) // stride + 1
    idx = np.arange(window_length)[None, :] + stride * np.arange(n_windows)[:, None]
    return x[idx]


def zscore_normalize(x):
    """z-score 标准化"""
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        std = x.std()
        return np.zeros_like(x) if std == 0 else (x - x.mean()) / std
    elif x.ndim == 2:
        means = x.mean(axis=1, keepdims=True)
        stds = x.std(axis=1, keepdims=True)
        stds[stds == 0] = 1.0
        return (x - means) / stds
    raise ValueError("仅支持一维或二维数组")


def preprocess_signal(x, fs=None, lowcut=None, highcut=None,
                      window_length=None, stride=None, normalize="zscore"):
    """完整预处理：滤波 -> 去趋势 -> 切片 -> 标准化"""
    y = x
    if lowcut is not None or highcut is not None:
        y = bandpass_filter(y, fs=fs, lowcut=lowcut, highcut=highcut)
    y = detrend_signal(y)
    windows = sliding_window(y, window_length=window_length, stride=stride)
    if normalize == "zscore":
        windows = zscore_normalize(windows)
    elif normalize == "minmax":
        mins = windows.min(axis=1, keepdims=True)
        maxs = windows.max(axis=1, keepdims=True)
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0
        windows = (windows - mins) / ranges
    return windows


# ============================================================
# 四、特征提取（20维 = 12时域 + 8频域）
# ============================================================
TIME_FEATURES = ["mean", "abs_mean", "std", "variance", "rms", "peak_to_peak",
                 "peak", "kurtosis", "skewness", "crest_factor",
                 "impulse_factor", "margin_factor"]
FREQ_FEATURES = ["spec_mean", "spec_std", "spec_centroid", "spec_rms",
                 "spec_peak_amp", "spec_peak_freq", "spec_kurtosis", "spec_skewness"]
ALL_FEATURES = TIME_FEATURES + FREQ_FEATURES


def time_domain_features(x):
    """计算12维时域特征"""
    x = np.asarray(x, dtype=np.float64)
    abs_x = np.abs(x)
    mean = x.mean()
    abs_mean = abs_x.mean()
    std = x.std()
    rms = np.sqrt(np.mean(x ** 2))
    peak = np.max(abs_x)
    if std > 0:
        kurtosis = np.mean((x - mean) ** 4) / (std ** 4)
        skewness = np.mean((x - mean) ** 3) / (std ** 3)
        crest_factor = peak / rms
        impulse_factor = peak / abs_mean if abs_mean > 0 else 0.0
        margin_factor = peak / (np.mean(np.sqrt(abs_x)) ** 2) if abs_mean > 0 else 0.0
    else:
        kurtosis = skewness = crest_factor = impulse_factor = margin_factor = 0.0
    return {"mean": mean, "abs_mean": abs_mean, "std": std, "variance": x.var(),
            "rms": rms, "peak_to_peak": x.max() - x.min(), "peak": peak,
            "kurtosis": kurtosis, "skewness": skewness,
            "crest_factor": crest_factor, "impulse_factor": impulse_factor,
            "margin_factor": margin_factor}


def frequency_domain_features(x, fs=None):
    """计算8维频域特征"""
    x = np.asarray(x, dtype=np.float64)
    fs = fs or SAMPLE_RATE
    n = len(x)
    fft_vals = np.fft.rfft(x)
    mag = np.abs(fft_vals) / n
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)
    mag, freqs = mag[1:], freqs[1:]
    if len(mag) == 0:
        return {f: 0.0 for f in FREQ_FEATURES}
    spec_mean = mag.mean()
    spec_std = mag.std()
    spec_rms = np.sqrt(np.mean(mag ** 2))
    spec_centroid = np.sum(freqs * mag) / mag.sum() if mag.sum() > 0 else 0.0
    peak_idx = np.argmax(mag)
    if spec_std > 0:
        spec_kurtosis = np.mean((mag - spec_mean) ** 4) / (spec_std ** 4)
        spec_skewness = np.mean((mag - spec_mean) ** 3) / (spec_std ** 3)
    else:
        spec_kurtosis = spec_skewness = 0.0
    return {"spec_mean": spec_mean, "spec_std": spec_std,
            "spec_centroid": spec_centroid, "spec_rms": spec_rms,
            "spec_peak_amp": mag[peak_idx], "spec_peak_freq": freqs[peak_idx],
            "spec_kurtosis": spec_kurtosis, "spec_skewness": spec_skewness}


def extract_features(x, fs=None, as_dict=False):
    """提取全部特征（时域+频域）"""
    x = np.asarray(x, dtype=np.float64)
    fs = fs or SAMPLE_RATE
    if x.ndim == 1:
        feats = {}
        feats.update(time_domain_features(x))
        feats.update(frequency_domain_features(x, fs))
        return feats if as_dict else np.array([feats[f] for f in ALL_FEATURES])
    elif x.ndim == 2:
        rows = []
        for i in range(x.shape[0]):
            feats = {}
            feats.update(time_domain_features(x[i]))
            feats.update(frequency_domain_features(x[i], fs))
            rows.append([feats[f] for f in ALL_FEATURES])
        return np.array(rows, dtype=np.float64)
    raise ValueError("仅支持一维或二维数组")


def feature_names():
    return list(ALL_FEATURES)


# ============================================================
# 五、故障分类（KNN / SVM / 随机森林）
# ============================================================
def load_features(path=None):
    """加载特征矩阵 (X, y, names)"""
    path = path or os.path.join(PROJECT_ROOT, "data", "processed", "feature_matrix.npz")
    if not os.path.exists(path):
        raise FileNotFoundError(f"特征文件不存在: {path}")
    d = np.load(path)
    X, y = d["X"], d["y"]
    names = sorted(np.unique(y), key=lambda c: CLASS_ORDER.index(c) if c in CLASS_ORDER else 99)
    return X, y, names


def get_models():
    """返回候选分类模型字典（标准化+分类器 Pipeline）"""
    return {
        "KNN": Pipeline([("scaler", StandardScaler()),
                         ("clf", KNeighborsClassifier(n_neighbors=5))]),
        "SVM": Pipeline([("scaler", StandardScaler()),
                         ("clf", SVC(kernel="rbf", C=10, gamma="scale"))]),
        "RandomForest": Pipeline([("scaler", StandardScaler()),
                                  ("clf", RandomForestClassifier(n_estimators=200, max_depth=None,
                                                                 random_state=42, n_jobs=-1))]),
    }


def train_evaluate(X, y, model=None, test_size=0.2, random_state=42):
    """训练并评估单个模型"""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y)
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)
    return {"model": model, "accuracy": accuracy_score(y_test, y_pred),
            "report": classification_report(y_test, y_pred, zero_division=0),
            "conf_matrix": confusion_matrix(y_test, y_pred),
            "y_true": y_test, "y_pred": y_pred}


def cross_validate(X, y, model, cv=5):
    """K折交叉验证"""
    return cross_val_score(model, X, y, cv=cv, scoring="accuracy", n_jobs=-1)


def save_model(model, filename="fault_classifier.pkl"):
    """保存模型到 models/ 目录"""
    path = os.path.join(MODELS_DIR, filename)
    os.makedirs(MODELS_DIR, exist_ok=True)
    joblib.dump(model, path)
    return path


def load_model(filename="fault_classifier.pkl"):
    """从 models/ 目录加载模型"""
    path = os.path.join(MODELS_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"模型不存在: {path}")
    return joblib.load(path)


# ============================================================
# 六、健康趋势预测与预警
# ============================================================
def build_health_series(signal, window=None, stride=None, metric="rms"):
    """沿信号滑动窗口构建健康指标时序"""
    window = window or WINDOW_LENGTH
    stride = stride or WINDOW_STRIDE
    n = len(signal)
    n_windows = (n - window) // stride + 1
    values = []
    for i in range(n_windows):
        seg = signal[i * stride: i * stride + window]
        if metric == "rms":
            values.append(float(np.sqrt(np.mean(seg ** 2))))
        elif metric == "kurtosis":
            values.append(float(np.mean((seg - seg.mean()) ** 4) / (seg.std() ** 4))
                          if seg.std() > 0 else 0.0)
        else:
            raise ValueError(f"不支持的指标: {metric}")
    return np.array(values)


def trend_predict(series, forecast_steps=20, degree=1):
    """多项式回归拟合趋势并外推"""
    series = np.asarray(series, dtype=np.float64)
    n = len(series)
    x_hist = np.arange(n, dtype=np.float64)
    coef = np.polyfit(x_hist, series, degree)
    x_fc = np.arange(n, n + forecast_steps, dtype=np.float64)
    return x_hist, series, x_fc, np.polyval(coef, x_fc), coef


def health_score(metric_value, baseline, threshold):
    """健康指标映射为0~100健康度"""
    if threshold <= baseline:
        raise ValueError("预警阈值必须大于基准值")
    score = 100.0 * (1.0 - (metric_value - baseline) / (threshold - baseline))
    return float(np.clip(score, 0.0, 100.0))


def predict_health(signal, metric="rms", forecast_steps=30,
                   threshold_percentile=90.0, window=None, stride=None):
    """完整健康趋势预测与预警流程"""
    series = build_health_series(signal, window=window, stride=stride, metric=metric)
    threshold = float(np.percentile(series, threshold_percentile))
    baseline = float(np.min(series))
    x_hist, y_hist, x_fc, y_fc, coef = trend_predict(series, forecast_steps)
    current_score = health_score(series[-1], baseline, threshold)
    forecast_end = y_fc[-1]
    forecast_score = health_score(forecast_end, baseline, threshold)
    return {"metric": metric, "series": series,
            "x_history": x_hist, "y_history": y_hist,
            "x_forecast": x_fc, "y_forecast": y_fc,
            "baseline": baseline, "threshold": threshold,
            "current_value": float(series[-1]), "forecast_value": forecast_end,
            "current_health": current_score, "forecast_health": forecast_score,
            "trend_slope": float(coef[0]), "warning": bool(forecast_end >= threshold),
            "coef": coef}


# ============================================================
# 七、故障知识库与规则推理
# ============================================================
KNOWLEDGE_BASE = {
    "Normal": {"name": "正常",
        "cause": "轴承处于正常运行状态，振动能量与冲击特征处于正常水平。",
        "features": "峭度接近3，RMS较低，频谱无明显故障特征频率分量。",
        "advice": "设备运行正常，按计划开展定期巡检与润滑维护即可。",
        "checks": ["保持润滑周期", "定期监测振动趋势"]},
    "IR": {"name": "内圈故障",
        "cause": "内圈滚道出现点蚀、剥落或疲劳裂纹，常见于装配过紧、润滑不良、异物进入或长期过载。",
        "features": "振动信号存在周期性冲击，峭度与峰值因子显著升高，频谱出现内圈故障特征频率BPFI及其谐波。",
        "advice": "建议安排停机检修，检查内圈滚道表面；早期密切监控，中重度更换轴承。",
        "checks": ["检查内圈滚道剥落/点蚀", "核查装配过盈与润滑", "更换轴承（重度时）"]},
    "B": {"name": "滚动体故障",
        "cause": "滚动体表面出现点蚀、剥落或裂纹，常见于润滑失效、疲劳、异物压痕。",
        "features": "冲击特征明显且随工况波动，峭度显著增大；频谱出现滚动体故障特征频率BSF及其谐波。",
        "advice": "建议停机检查滚动体表面；滚动体故障发展较快，应尽早更换轴承。",
        "checks": ["检查滚动体点蚀/剥落", "排查润滑失效与异物", "尽早更换轴承"]},
    "OR": {"name": "外圈故障",
        "cause": "外圈滚道出现点蚀、剥落，常见于外圈承载区受力集中、安装不正或腐蚀。",
        "features": "周期性冲击稳定，峭度升高；频谱出现外圈故障特征频率BPFO及其谐波。",
        "advice": "建议检修外圈滚道与轴承座配合面；中度以上建议更换轴承。",
        "checks": ["检查外圈滚道剥落", "检查轴承座配合与对中", "更换轴承（中度以上）"]},
}


def get_fault_info(fault_type):
    if fault_type not in KNOWLEDGE_BASE:
        raise ValueError(f"未知故障类型: {fault_type}")
    return KNOWLEDGE_BASE[fault_type]


def severity_from_features(features):
    """基于峭度等特征判断严重程度：轻度/中度/重度"""
    if features is None:
        return "轻度"
    kurtosis = features.get("kurtosis", 3.0)
    rms = features.get("rms", 0.0)
    if kurtosis >= 8.0:
        return "重度"
    if kurtosis >= 5.0:
        return "中度"
    if kurtosis >= 4.0 and rms > 0.3:
        return "中度"
    return "轻度"


def reason(fault_type, features=None):
    """故障推理主入口：输出结构化运维建议"""
    info = get_fault_info(fault_type)
    severity = severity_from_features(features) if features else "轻度"
    if severity == "重度":
        priority = "紧急：建议立即停机并更换轴承，防止故障扩大。"
    elif severity == "中度":
        priority = "较急：建议近期安排检修，加强监测频次。"
    else:
        priority = "常规：纳入例行检修计划，持续监测趋势。"
    return {"fault_type": fault_type, "fault_name": info["name"],
            "cause": info["cause"], "features_desc": info["features"],
            "severity": severity, "advice": priority + "\n" + info["advice"],
            "checks": info["checks"]}


# ============================================================
# 八、SQLite 数据库
# ============================================================
SCHEMA = """
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL, channel TEXT NOT NULL, vibration_value REAL NOT NULL);
CREATE TABLE IF NOT EXISTS fault_sample (
    id INTEGER PRIMARY KEY AUTOINCREMENT, sample_time TEXT NOT NULL,
    label TEXT NOT NULL, fault_type TEXT NOT NULL,
    feature_vector TEXT NOT NULL, confidence REAL);
CREATE TABLE IF NOT EXISTS fault_knowledge (
    id INTEGER PRIMARY KEY AUTOINCREMENT, fault_type TEXT NOT NULL UNIQUE,
    name TEXT, cause TEXT, features_desc TEXT, advice TEXT, checks TEXT);
CREATE TABLE IF NOT EXISTS alarm_record (
    id INTEGER PRIMARY KEY AUTOINCREMENT, timestamp TEXT NOT NULL,
    device_id TEXT NOT NULL, alarm_type TEXT NOT NULL, description TEXT NOT NULL);
"""

KNOWLEDGE_ROWS = [
    ("Normal", "正常", "轴承正常运行", "峭度接近3，振动正常", "定期巡检与润滑", "保持润滑;定期监测"),
    ("IR", "内圈故障", "内圈滚道点蚀/剥落", "峭度升高，BPFI特征频率", "停机检修，中重度更换", "检查内圈;核查润滑;更换轴承"),
    ("B", "滚动体故障", "滚动体点蚀/剥落", "冲击明显，BSF特征频率", "尽早更换轴承", "检查滚动体;排查润滑;更换轴承"),
    ("OR", "外圈故障", "外圈滚道点蚀/剥落", "冲击稳定，BPFO特征频率", "检修外圈，中度以上更换", "检查外圈;检查对中;更换轴承"),
]


def get_connection():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    try:
        conn.executescript(SCHEMA)
        for row in KNOWLEDGE_ROWS:
            conn.execute("INSERT OR IGNORE INTO fault_knowledge "
                         "(fault_type,name,cause,features_desc,advice,checks) VALUES (?,?,?,?,?,?)", row)
        conn.commit()
    finally:
        conn.close()


def insert_fault_sample(label, fault_type, feature_vector, confidence):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO fault_sample (sample_time,label,fault_type,feature_vector,confidence) "
                     "VALUES (?,?,?,?,?)",
                     (datetime.now().isoformat(timespec="seconds"), label, fault_type,
                      str(feature_vector), confidence))
        conn.commit()
    finally:
        conn.close()


def insert_alarm(device_id, alarm_type, description):
    conn = get_connection()
    try:
        conn.execute("INSERT INTO alarm_record (timestamp,device_id,alarm_type,description) VALUES (?,?,?,?)",
                     (datetime.now().isoformat(timespec="seconds"), device_id, alarm_type, description))
        conn.commit()
    finally:
        conn.close()


def query_fault_samples(limit=50):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM fault_sample ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_alarms(limit=50):
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM alarm_record ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


def query_knowledge():
    conn = get_connection()
    try:
        rows = conn.execute("SELECT * FROM fault_knowledge").fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ============================================================
# 九、Flask Web 应用
# ============================================================
_template_dir = os.path.join(PROJECT_ROOT, "web", "templates")
_static_dir = os.path.join(PROJECT_ROOT, "web", "static")
app = Flask(__name__, template_folder=_template_dir, static_folder=_static_dir)
CORS(app)

init_db()
MODEL = None
try:
    MODEL = load_model("fault_classifier.pkl")
    print("[INFO] 分类模型加载成功")
except Exception as e:
    print(f"[WARN] 分类模型加载失败: {e}")


def _load_signal(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在: {filename}")
    return load_mat_file(path, channel=CHANNEL)


def _decimate(x, max_points=3000):
    if len(x) <= max_points:
        return x
    idx = np.linspace(0, len(x) - 1, max_points).astype(int)
    return x[idx]


def _diagnose_from_signal(signal, filename):
    windows = preprocess_signal(signal, fs=SAMPLE_RATE, lowcut=None, highcut=None,
                                window_length=WINDOW_LENGTH, stride=WINDOW_STRIDE, normalize="zscore")
    mid = len(windows) // 2
    window = windows[mid]
    feats = extract_features(window, as_dict=True)
    if MODEL is not None:
        X = extract_features(windows)
        if hasattr(MODEL, "predict_proba"):
            proba = MODEL.predict_proba(X)
            avg_proba = proba.mean(axis=0)
            pred = MODEL.classes_[int(np.argmax(avg_proba))]
            confidence = float(avg_proba.max())
        else:
            preds = MODEL.predict(X)
            pred = str(np.bincount([np.where(MODEL.classes_ == p)[0][0] for p in preds]).argmax())
            pred = MODEL.classes_[int(pred)]
            confidence = float(np.mean(preds == pred))
    else:
        pred, confidence = "Normal", 0.0
    info = reason(pred, feats)
    insert_fault_sample(pred, info["fault_name"], feats, round(confidence, 4))
    if info["severity"] in ("中度", "重度"):
        insert_alarm("CWRU-DE-01", pred,
                     f"{info['fault_name']}（{info['severity']}），置信度 {confidence:.2f}")
    return {"filename": filename, "fault_type": pred, "fault_name": info["fault_name"],
            "confidence": round(confidence, 4), "severity": info["severity"],
            "features": {k: round(v, 6) for k, v in feats.items()},
            "cause": info["cause"], "advice": info["advice"], "checks": info["checks"]}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "model_loaded": MODEL is not None})


@app.route("/api/datasets", methods=["GET"])
def api_datasets():
    files = list_data_files()
    items = []
    for fp in files:
        name = os.path.basename(fp)
        try:
            meta = parse_cwru_filename(name)
            items.append({"filename": name, "label": meta["label"],
                          "label_cn": meta["label_cn"], "diameter": meta["diameter"],
                          "load": meta["load"]})
        except ValueError:
            items.append({"filename": name, "label": "?", "label_cn": "未知"})
    return jsonify(items)


@app.route("/api/signal/<path:filename>", methods=["GET"])
def api_signal(filename):
    try:
        signal, meta = _load_signal(filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404
    decimated = _decimate(signal, 3000)
    step = len(signal) // len(decimated)
    n = len(signal)
    mag = np.abs(rfft(signal)) / n
    freqs = rfftfreq(n, d=1 / SAMPLE_RATE)
    mask = freqs <= 6000
    f_mag = _decimate(mag[mask], 1500)
    f_freq = _decimate(freqs[mask], 1500)
    CWRU_RPM_MAP = {0: 1797, 1: 1772, 2: 1750, 3: 1730}
    meta = {k: v for k, v in meta.items() if k != "filepath"}
    if meta.get("rpm") is None:
        meta["rpm"] = CWRU_RPM_MAP.get(meta.get("load"), None)
    return jsonify({"filename": filename, "meta": meta,
                    "time": (np.arange(len(decimated)) * step / SAMPLE_RATE).tolist(),
                    "signal": decimated.tolist(),
                    "freq": f_freq.tolist(), "mag": f_mag.tolist(), "fs": SAMPLE_RATE})


@app.route("/api/diagnose", methods=["POST"])
def api_diagnose():
    data = request.get_json(force=True)
    filename = data.get("filename", "")
    try:
        signal, meta = _load_signal(filename)
        return jsonify(_diagnose_from_signal(signal, filename))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(force=True)
    filename = data.get("filename", "")
    metric = data.get("metric", "rms")
    try:
        signal, meta = _load_signal(filename)
        res = predict_health(signal, metric=metric, forecast_steps=30)
        return jsonify({"filename": filename, "metric": metric,
                        "series": res["series"].tolist(),
                        "x_history": res["x_history"].tolist(),
                        "y_history": res["y_history"].tolist(),
                        "x_forecast": res["x_forecast"].tolist(),
                        "y_forecast": res["y_forecast"].tolist(),
                        "threshold": round(res["threshold"], 4),
                        "baseline": round(res["baseline"], 4),
                        "current_value": round(res["current_value"], 4),
                        "forecast_value": round(res["forecast_value"], 4),
                        "current_health": round(res["current_health"], 1),
                        "forecast_health": round(res["forecast_health"], 1),
                        "warning": res["warning"]})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/reason", methods=["POST"])
def api_reason():
    data = request.get_json(force=True)
    try:
        return jsonify(reason(data.get("fault_type", "")))
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/knowledge", methods=["GET"])
def api_knowledge():
    return jsonify(query_knowledge())


@app.route("/api/records", methods=["GET"])
def api_records():
    return jsonify({"samples": query_fault_samples(30), "alarms": query_alarms(30)})


# ============================================================
# 十、主入口
# ============================================================
if __name__ == "__main__":
    print("=" * 50)
    print("轴承故障诊断系统（单文件整合版）")
    print(f"数据目录: {DATA_DIR}")
    print(f"数据库: {DB_PATH}")
    print("访问: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=False)
