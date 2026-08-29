"""
健康趋势预测模块
================
基于历史振动信号构建健康指标时序，预测设备健康退化趋势并实现早期预警。

实现方案（对应方案设计 2.4）：
  - 健康指标序列：在振动信号上沿时间滑动计算健康指标（RMS / 峭度等），
    模拟设备随运行时间缓慢磨损、振动增强的退化过程；
  - 趋势预测：滑动窗口 + 线性回归外推（可选二次多项式），预测未来健康指标；
  - 早期预警：当预测值越过预警阈值时输出告警。

说明：CWRU 为稳态故障数据集（非退化数据），本模块以振动能量级
（RMS）随时间的演变近似健康退化过程，用于演示趋势预测与预警逻辑；
实际工程中可替换为真实退化监测数据。
"""
import numpy as np
from scipy import signal as scipy_signal

from . import config


# ---------- 健康指标计算 ----------

def _metric_rms(x: np.ndarray) -> float:
    """均方根（振动能量指标），值越大退化越严重"""
    return float(np.sqrt(np.mean(x ** 2)))


def _metric_kurtosis(x: np.ndarray) -> float:
    """峭度（冲击特征指标），正常约 3，故障时显著增大"""
    if x.std() == 0:
        return 0.0
    return float(np.mean((x - x.mean()) ** 4) / (x.std() ** 4))


METRICS = {
    "rms": _metric_rms,
    "kurtosis": _metric_kurtosis,
}


def build_health_series(signal: np.ndarray, window: int = None,
                        stride: int = None, metric: str = "rms") -> np.ndarray:
    """
    沿信号滑动窗口构建健康指标时序。

    参数：
      signal : 一维振动信号
      window : 窗口长度
      stride : 滑动步长
      metric : "rms" / "kurtosis"

    返回：
      健康指标一维序列
    """
    if metric not in METRICS:
        raise ValueError(f"不支持的指标: {metric}，可选 {list(METRICS)}")
    window = window or config.WINDOW_LENGTH
    stride = stride or config.WINDOW_STRIDE
    func = METRICS[metric]

    n = len(signal)
    n_windows = (n - window) // stride + 1
    values = []
    for i in range(n_windows):
        seg = signal[i * stride : i * stride + window]
        values.append(func(seg))
    return np.array(values)


# ---------- 趋势预测 ----------

def trend_predict(series: np.ndarray, forecast_steps: int = 20,
                  degree: int = 1) -> tuple:
    """
    基于最小二乘多项式回归拟合趋势并外推预测。

    参数：
      series         : 历史健康指标序列
      forecast_steps : 外推预测的未来步数
      degree         : 多项式阶数（1=线性，2=二次）

    返回：
      (x_history, y_history, x_forecast, y_forecast, coef)
        coef : 拟合多项式系数（高次在前）
    """
    series = np.asarray(series, dtype=np.float64)
    n = len(series)
    x_hist = np.arange(n, dtype=np.float64)
    # 最小二乘多项式拟合
    coef = np.polyfit(x_hist, series, degree)

    x_fc = np.arange(n, n + forecast_steps, dtype=np.float64)
    y_hist = np.polyval(coef, x_hist)
    y_fc = np.polyval(coef, x_fc)
    return x_hist, series, x_fc, y_fc, coef


def health_score(metric_value: float, baseline: float,
                 threshold: float) -> float:
    """
    将健康指标映射为健康度百分制（0~100）。

    公式：health = 100 * (1 - (value - baseline) / (threshold - baseline))
    并裁剪到 [0, 100]。
      - value <= baseline  : 健康度 100（设备正常）
      - value >= threshold : 健康度 0（达到预警/失效线）
    """
    if threshold <= baseline:
        raise ValueError("预警阈值必须大于基准值")
    score = 100.0 * (1.0 - (metric_value - baseline) / (threshold - baseline))
    return float(np.clip(score, 0.0, 100.0))


def predict_health(signal: np.ndarray, metric: str = "rms",
                   forecast_steps: int = 20, threshold_percentile: float = 90.0,
                   window: int = None, stride: int = None) -> dict:
    """
    完整的健康趋势预测与预警流程。

    参数：
      signal               : 一维振动信号
      metric               : 健康指标（"rms"/"kurtosis"）
      forecast_steps       : 外推步数
      threshold_percentile : 预警阈值设为历史指标的分位数（如 90%）
      window/stride        : 滑动窗口参数

    返回：
      dict，包含健康序列、预测结果、健康度、是否预警等
    """
    series = build_health_series(signal, window=window, stride=stride, metric=metric)

    # 预警阈值：历史序列的 90 分位（代表当前最差工况）
    threshold = float(np.percentile(series, threshold_percentile))
    baseline = float(np.min(series))

    x_hist, y_hist, x_fc, y_fc, coef = trend_predict(series, forecast_steps)

    # 当前健康度与预测末端健康度
    current_score = health_score(series[-1], baseline, threshold)
    forecast_end = y_fc[-1]
    forecast_score = health_score(forecast_end, baseline, threshold)

    # 预警判断：预测末端越过阈值 或 趋势上升过快
    warn = forecast_end >= threshold
    trend_slope = float(coef[0])  # 一阶系数（线性时即斜率）

    return {
        "metric": metric,
        "series": series,
        "x_history": x_hist,
        "y_history": y_hist,
        "x_forecast": x_fc,
        "y_forecast": y_fc,
        "baseline": baseline,
        "threshold": threshold,
        "current_value": float(series[-1]),
        "forecast_value": forecast_end,
        "current_health": current_score,
        "forecast_health": forecast_score,
        "trend_slope": trend_slope,
        "warning": bool(warn),
        "coef": coef,
    }


if __name__ == "__main__":
    from .data_loader import load_mat_file, list_data_files

    # 用一段内圈故障信号演示
    files = list_data_files()
    sig, meta = load_mat_file([f for f in files if "IR021" in f][0])
    print(f"信号: {meta['label']} 故障, 长度={len(sig)}")

    res = predict_health(sig, metric="rms", forecast_steps=30)
    print(f"\n健康指标: {res['metric']}")
    print(f"历史长度: {len(res['series'])} 个窗口")
    print(f"基准值={res['baseline']:.4f}, 预警阈值={res['threshold']:.4f}")
    print(f"当前值={res['current_value']:.4f}, 预测末端={res['forecast_value']:.4f}")
    print(f"当前健康度={res['current_health']:.1f}, 预测末端健康度={res['forecast_health']:.1f}")
    print(f"趋势斜率={res['trend_slope']:.6f}, 是否预警={'是' if res['warning'] else '否'}")
