"""
轴承故障智能监测与诊断系统 - Flask 后端
========================================
提供 REST API：数据加载、故障诊断、健康预测、知识推理、记录查询，
并托管前端页面。

启动：python web/app.py   （默认 http://127.0.0.1:5000）
"""
import os
import sys
import numpy as np

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from src import config
from src.data_loader import list_data_files, load_mat_file, parse_cwru_filename
from src.preprocessing import preprocess_signal, sliding_window
from src.feature_extraction import extract_features, feature_names
from src.classifier import load_model
from src.health_prediction import predict_health
from src.knowledge_base import reason, get_fault_info
from web import database

app = Flask(__name__)
CORS(app)

# 启动时初始化数据库与加载模型
database.init_db()
MODEL = None
try:
    MODEL = load_model("fault_classifier.pkl")
    print("[INFO] 分类模型加载成功")
except Exception as e:
    print(f"[WARN] 分类模型加载失败: {e}，请先运行 scripts/train_classifier.py")


# ---------- 工具函数 ----------

def _load_signal(filename: str):
    """按文件名加载信号，返回 (signal, meta)"""
    data_dir = config.DATA_DIR
    path = os.path.join(data_dir, filename)
    if not os.path.exists(path):
        raise FileNotFoundError(f"数据文件不存在: {filename}")
    return load_mat_file(path, channel=config.CHANNEL)


def _decimate(x: np.ndarray, max_points: int = 3000) -> np.ndarray:
    """抽稀：超过最大点数时等间隔采样，便于前端展示"""
    if len(x) <= max_points:
        return x
    idx = np.linspace(0, len(x) - 1, max_points).astype(int)
    return x[idx]


def _diagnose_from_signal(signal: np.ndarray, filename: str) -> dict:
    """
    对一段信号执行完整诊断流程，返回结果字典。
    """
    # 1. 预处理 + 取一个代表窗口（取中间段，避开启动/末端噪声）
    windows = preprocess_signal(
        signal, fs=config.SAMPLE_RATE,
        lowcut=None, highcut=None,
        window_length=config.WINDOW_LENGTH,
        stride=config.WINDOW_STRIDE, normalize="zscore",
    )
    mid = len(windows) // 2
    window = windows[mid]

    # 2. 特征提取
    feats = extract_features(window, as_dict=True)

    # 3. 模型预测（多窗口投票提升稳定性）
    if MODEL is not None:
        X = extract_features(windows)
        probs = getattr(MODEL, "predict_proba", None)
        if probs is not None:
            proba = MODEL.predict_proba(X)
            avg_proba = proba.mean(axis=0)
            pred = MODEL.classes_[int(np.argmax(avg_proba))]
            confidence = float(avg_proba.max())
        else:
            preds = MODEL.predict(X)
            pred = str(np.bincount(
                [np.where(MODEL.classes_ == p)[0][0] for p in preds]
            ).argmax())
            pred = MODEL.classes_[int(pred)]
            confidence = float(np.mean(preds == pred))
    else:
        pred = "Normal"
        confidence = 0.0

    # 4. 知识推理（严重度 + 运维建议）
    info = reason(pred, feats)

    # 5. 记录入库
    database.insert_fault_sample(pred, info["fault_name"],
                                 feats, round(confidence, 4))
    if info["severity"] in ("中度", "重度"):
        database.insert_alarm(
            "CWRU-DE-01", pred,
            f"{info['fault_name']}（{info['severity']}），置信度 {confidence:.2f}",
        )

    return {
        "filename": filename,
        "fault_type": pred,
        "fault_name": info["fault_name"],
        "confidence": round(confidence, 4),
        "severity": info["severity"],
        "features": {k: round(v, 6) for k, v in feats.items()},
        "cause": info["cause"],
        "advice": info["advice"],
        "checks": info["checks"],
    }


# ---------- 页面 ----------

@app.route("/")
def index():
    return render_template("index.html")


# ---------- 数据 API ----------

@app.route("/api/health", methods=["GET"])
def api_health():
    return jsonify({"status": "ok", "model_loaded": MODEL is not None})


@app.route("/api/datasets", methods=["GET"])
def api_datasets():
    """返回可用数据集文件列表（含解析后的类别信息）"""
    files = list_data_files()
    items = []
    for fp in files:
        name = os.path.basename(fp)
        try:
            meta = parse_cwru_filename(name)
            items.append({
                "filename": name,
                "label": meta["label"],
                "label_cn": meta["label_cn"],
                "diameter": meta["diameter"],
                "load": meta["load"],
            })
        except ValueError:
            items.append({"filename": name, "label": "?", "label_cn": "未知"})
    return jsonify(items)


@app.route("/api/signal/<path:filename>", methods=["GET"])
def api_signal(filename):
    """返回振动波形与频谱数据（抽稀后）用于前端展示"""
    try:
        signal, meta = _load_signal(filename)
    except Exception as e:
        return jsonify({"error": str(e)}), 404

    t = np.arange(len(signal)) / config.SAMPLE_RATE
    decimated = _decimate(signal, 3000)
    step = len(signal) // len(decimated)

    # 频谱
    from scipy.fft import rfft, rfftfreq
    n = len(signal)
    mag = np.abs(rfft(signal)) / n
    freqs = rfftfreq(n, d=1 / config.SAMPLE_RATE)
    # 只保留 0~6000 Hz
    mask = freqs <= 6000
    f_mag = _decimate(mag[mask], 1500)
    f_freq = _decimate(freqs[mask], 1500)

    # CWRU 负载-转速标准对应表（.mat 内无转速变量时的兜底）
    CWRU_RPM_MAP = {0: 1797, 1: 1772, 2: 1750, 3: 1730}
    meta = {k: v for k, v in meta.items() if k != "filepath"}
    if meta.get("rpm") is None:
        meta["rpm"] = CWRU_RPM_MAP.get(meta.get("load"), None)

    return jsonify({
        "filename": filename,
        "meta": meta,
        "time": (np.arange(len(decimated)) * step / config.SAMPLE_RATE).tolist(),
        "signal": decimated.tolist(),
        "freq": f_freq.tolist(),
        "mag": f_mag.tolist(),
        "fs": config.SAMPLE_RATE,
    })


# ---------- 诊断 API ----------

@app.route("/api/diagnose", methods=["POST"])
def api_diagnose():
    data = request.get_json(force=True)
    filename = data.get("filename", "")
    try:
        signal, meta = _load_signal(filename)
        result = _diagnose_from_signal(signal, filename)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------- 健康预测 API ----------

@app.route("/api/predict", methods=["POST"])
def api_predict():
    data = request.get_json(force=True)
    filename = data.get("filename", "")
    metric = data.get("metric", "rms")
    try:
        signal, meta = _load_signal(filename)
        res = predict_health(signal, metric=metric, forecast_steps=30)

        # 将 numpy 数组转 list 返回
        return jsonify({
            "filename": filename,
            "metric": metric,
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
            "warning": res["warning"],
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400


# ---------- 知识推理 API ----------

@app.route("/api/reason", methods=["POST"])
def api_reason():
    data = request.get_json(force=True)
    fault_type = data.get("fault_type", "")
    try:
        result = reason(fault_type)
        return jsonify(result)
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/knowledge", methods=["GET"])
def api_knowledge():
    """返回知识库全部条目"""
    return jsonify(database.query_knowledge())


# ---------- 记录 API ----------

@app.route("/api/records", methods=["GET"])
def api_records():
    return jsonify({"samples": database.query_fault_samples(30),
                    "alarms": database.query_alarms(30)})


if __name__ == "__main__":
    print("=" * 50)
    print("轴承故障智能监测与诊断系统")
    print(f"数据目录: {config.DATA_DIR}")
    print(f"数据库: {database.DB_PATH}")
    print("访问: http://127.0.0.1:5000")
    print("=" * 50)
    app.run(host="127.0.0.1", port=5000, debug=True)
