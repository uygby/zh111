"""
数据预处理模块
==============
包含振动信号的滤波、滑动窗口切片、标准化等操作，
为后续特征提取与模型训练准备数据。

主要函数：
  bandpass_filter   : Butterworth 带通滤波（可选，用于去除噪声与趋势项）
  detrend_signal    : 去趋势（去除均值漂移）
  sliding_window    : 滑动窗口切片，将长序列切成固定长度的样本
  zscore_normalize  : z-score 标准化（按样本或按整段信号）
  preprocess_signal : 完整预处理流程（滤波 -> 去趋势 -> 切片 -> 标准化）
"""
import numpy as np
from scipy import signal as scipy_signal

from . import config


def bandpass_filter(x: np.ndarray, fs: int = None,
                    lowcut: float = None, highcut: float = None,
                    order: int = 4) -> np.ndarray:
    """
    Butterworth 带通滤波。

    参数：
      x       : 一维振动信号
      fs      : 采样率 (Hz)
      lowcut  : 低通截止频率 (Hz)，None 表示不加下限
      highcut : 高通截止频率 (Hz)，None 表示不加上限
      order   : 滤波器阶数

    说明：CWRU 轴承故障特征主要集中在中低频段（几百 Hz 至数千 Hz）。
    典型带通范围如 500~5000 Hz 可滤除工频干扰与高频噪声。
    若 lowcut/highcut 均为 None，则返回原信号。
    """
    if lowcut is None and highcut is None:
        return x.copy()
    fs = fs or config.SAMPLE_RATE
    nyq = 0.5 * fs

    if lowcut is not None and highcut is not None:
        btype, freqs = "bandpass", [lowcut, highcut]
    elif lowcut is not None:
        btype, freqs = "highpass", [lowcut]
    else:
        btype, freqs = "lowpass", [highcut]

    # 截止频率需在 Nyquist 以内
    freqs = [min(f, nyq * 0.99) for f in freqs]
    if freqs[0] <= 0:
        return x.copy()

    b, a = scipy_signal.butter(order, freqs, btype=btype, fs=fs)
    # 使用 filtfilt 零相位滤波，避免相位偏移
    return scipy_signal.filtfilt(b, a, x)


def detrend_signal(x: np.ndarray) -> np.ndarray:
    """去除线性趋势（消除传感器零漂与缓慢漂移的影响）"""
    return scipy_signal.detrend(x, type="linear")


def sliding_window(x: np.ndarray, window_length: int = None,
                   stride: int = None) -> np.ndarray:
    """
    滑动窗口切片。

    将一维信号切分为形状为 (n_windows, window_length) 的二维数组。

    参数：
      x              : 一维振动信号
      window_length  : 窗口长度（点数）
      stride         : 滑动步长（点数）

    返回：
      (n_windows, window_length) 数组
    """
    window_length = window_length or config.WINDOW_LENGTH
    stride = stride or config.WINDOW_STRIDE
    n = len(x)
    if n < window_length:
        raise ValueError(
            f"信号长度 {n} 小于窗口长度 {window_length}，无法切片"
        )
    # 计算窗口个数（丢弃末尾不足一个窗口的部分）
    n_windows = (n - window_length) // stride + 1
    idx = np.arange(window_length)[None, :] + stride * np.arange(n_windows)[:, None]
    return x[idx]


def zscore_normalize(x: np.ndarray) -> np.ndarray:
    """
    z-score 标准化： (x - mean) / std

    对二维数组按每个样本（行）标准化；对一维数组按整段标准化。
    """
    x = np.asarray(x, dtype=np.float64)
    if x.ndim == 1:
        std = x.std()
        if std == 0:
            return np.zeros_like(x)
        return (x - x.mean()) / std
    elif x.ndim == 2:
        means = x.mean(axis=1, keepdims=True)
        stds = x.std(axis=1, keepdims=True)
        stds[stds == 0] = 1.0  # 避免除零
        return (x - means) / stds
    else:
        raise ValueError("仅支持一维或二维数组")


def minmax_normalize(x: np.ndarray) -> np.ndarray:
    """Min-Max 标准化到 [0, 1]，对一维数组按整段标准化"""
    x = np.asarray(x, dtype=np.float64)
    xmin, xmax = x.min(), x.max()
    if xmax == xmin:
        return np.zeros_like(x)
    return (x - xmin) / (xmax - xmin)


def preprocess_signal(x: np.ndarray, fs: int = None,
                      lowcut: float = None, highcut: float = None,
                      window_length: int = None, stride: int = None,
                      normalize: str = "zscore") -> np.ndarray:
    """
    完整预处理流程：滤波 -> 去趋势 -> 切片 -> 标准化。

    参数：
      x              : 一维振动信号
      fs             : 采样率
      lowcut/highcut : 带通滤波截止频率（None 表示不滤波）
      window_length  : 切片窗口长度
      stride         : 滑动步长
      normalize      : "zscore" / "minmax" / None（不标准化）

    返回：
      (n_windows, window_length) 预处理后的样本数组
    """
    y = x
    if lowcut is not None or highcut is not None:
        y = bandpass_filter(y, fs=fs, lowcut=lowcut, highcut=highcut)
    y = detrend_signal(y)
    windows = sliding_window(y, window_length=window_length, stride=stride)

    if normalize == "zscore":
        windows = zscore_normalize(windows)
    elif normalize == "minmax":
        # 逐样本 Min-Max 标准化
        mins = windows.min(axis=1, keepdims=True)
        maxs = windows.max(axis=1, keepdims=True)
        ranges = maxs - mins
        ranges[ranges == 0] = 1.0
        windows = (windows - mins) / ranges
    return windows


if __name__ == "__main__":
    # 简单自测
    from .data_loader import load_mat_file, list_data_files

    files = list_data_files()
    sig, meta = load_mat_file(files[0])
    print(f"原始信号: 长度={len(sig)}, 标准差={sig.std():.4f}")

    # 测试滑动窗口
    win = sliding_window(sig, window_length=1024, stride=512)
    print(f"滑动窗口切片: {win.shape}")

    # 测试完整预处理
    processed = preprocess_signal(
        sig, fs=config.SAMPLE_RATE,
        lowcut=500, highcut=5000,
        window_length=1024, stride=512,
        normalize="zscore",
    )
    print(f"预处理后: {processed.shape}, 每样本均值≈{processed.mean():.4f}, "
          f"标准差≈{processed.std(axis=1).mean():.4f}")
