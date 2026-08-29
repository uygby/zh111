"""
特征提取模块
============
从振动信号片段中提取时域特征与频域特征，用于故障分类与健康趋势预测。

时域特征（12 个）：均值、绝对均值、标准差、方差、均方根(RMS)、峰峰值、
                  峰值、峭度、偏度、波形因子、峰值因子、脉冲因子、裕度因子

频域特征（8 个）：频谱幅值均值、频谱幅值标准差、频谱质心、频谱均方根、
                  主频幅值、主频位置、频谱峰度、频谱偏度

说明：
  - 峭度/峰值因子对轴承故障冲击敏感，是轴承诊断最常用的指标；
  - 频域特征通过 FFT 提取，能反映故障特征频率分量。
"""
import numpy as np
from scipy import signal as scipy_signal

from . import config

# 特征名列表（保持顺序一致，便于构造特征矩阵）
TIME_FEATURES = [
    "mean", "abs_mean", "std", "variance", "rms", "peak_to_peak",
    "peak", "kurtosis", "skewness", "crest_factor",
    "impulse_factor", "margin_factor",
]

FREQ_FEATURES = [
    "spec_mean", "spec_std", "spec_centroid", "spec_rms",
    "spec_peak_amp", "spec_peak_freq", "spec_kurtosis", "spec_skewness",
]

ALL_FEATURES = TIME_FEATURES + FREQ_FEATURES


def time_domain_features(x: np.ndarray) -> dict:
    """
    计算时域特征，返回字典。

    参数：
      x : 一维振动信号片段（窗口）
    """
    x = np.asarray(x, dtype=np.float64)
    n = len(x)
    abs_x = np.abs(x)

    mean = x.mean()
    abs_mean = abs_x.mean()
    std = x.std()
    variance = x.var()
    rms = np.sqrt(np.mean(x ** 2))
    peak_to_peak = x.max() - x.min()
    peak = np.max(abs_x)

    # 四阶/三阶中心矩统计量
    if std > 0:
        kurtosis = np.mean((x - mean) ** 4) / (std ** 4)          # 峭度
        skewness = np.mean((x - mean) ** 3) / (std ** 3)          # 偏度
        crest_factor = peak / rms                                 # 峰值因子
        impulse_factor = peak / abs_mean if abs_mean > 0 else 0.0 # 脉冲因子
        margin_factor = peak / (np.mean(np.sqrt(abs_x)) ** 2) if abs_mean > 0 else 0.0  # 裕度因子
    else:
        kurtosis = skewness = crest_factor = impulse_factor = margin_factor = 0.0

    return {
        "mean": mean,
        "abs_mean": abs_mean,
        "std": std,
        "variance": variance,
        "rms": rms,
        "peak_to_peak": peak_to_peak,
        "peak": peak,
        "kurtosis": kurtosis,
        "skewness": skewness,
        "crest_factor": crest_factor,
        "impulse_factor": impulse_factor,
        "margin_factor": margin_factor,
    }


def frequency_domain_features(x: np.ndarray, fs: int = None) -> dict:
    """
    计算频域特征，返回字典。

    参数：
      x  : 一维振动信号片段（窗口）
      fs : 采样率 (Hz)
    """
    x = np.asarray(x, dtype=np.float64)
    fs = fs or config.SAMPLE_RATE
    n = len(x)

    # FFT 单边幅度谱
    fft_vals = np.fft.rfft(x)
    mag = np.abs(fft_vals) / n
    freqs = np.fft.rfftfreq(n, d=1.0 / fs)

    # 去掉直流分量（0 Hz）
    mag = mag[1:]
    freqs = freqs[1:]
    if len(mag) == 0:
        return {f: 0.0 for f in FREQ_FEATURES}

    spec_mean = mag.mean()
    spec_std = mag.std()
    spec_rms = np.sqrt(np.mean(mag ** 2))

    # 频谱质心：加权平均频率
    if mag.sum() > 0:
        spec_centroid = np.sum(freqs * mag) / mag.sum()
    else:
        spec_centroid = 0.0

    # 主频幅值与位置
    peak_idx = np.argmax(mag)
    spec_peak_amp = mag[peak_idx]
    spec_peak_freq = freqs[peak_idx]

    # 频谱峰度/偏度（基于幅度分布）
    if spec_std > 0:
        spec_kurtosis = np.mean((mag - spec_mean) ** 4) / (spec_std ** 4)
        spec_skewness = np.mean((mag - spec_mean) ** 3) / (spec_std ** 3)
    else:
        spec_kurtosis = spec_skewness = 0.0

    return {
        "spec_mean": spec_mean,
        "spec_std": spec_std,
        "spec_centroid": spec_centroid,
        "spec_rms": spec_rms,
        "spec_peak_amp": spec_peak_amp,
        "spec_peak_freq": spec_peak_freq,
        "spec_kurtosis": spec_kurtosis,
        "spec_skewness": spec_skewness,
    }


def extract_features(x: np.ndarray, fs: int = None,
                     as_dict: bool = False):
    """
    提取全部特征（时域 + 频域）。

    参数：
      x       : 一维振动信号片段，或 (n, window_length) 的二维样本数组
      fs      : 采样率
      as_dict : True 返回 dict（单样本时）；False 返回特征矩阵

    返回：
      - 一维输入且 as_dict=True  ：特征字典
      - 一维输入且 as_dict=False ：特征数组 (n_features,)
      - 二维输入                 ：特征矩阵 (n_samples, n_features)
    """
    x = np.asarray(x, dtype=np.float64)
    fs = fs or config.SAMPLE_RATE

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

    else:
        raise ValueError("仅支持一维或二维数组")


def feature_names() -> list:
    """返回特征名列表（与特征矩阵列顺序一致）"""
    return list(ALL_FEATURES)


if __name__ == "__main__":
    # 简单自测：对正常与内圈故障信号各取一个窗口，对比特征差异
    from .data_loader import load_mat_file, list_data_files
    from .preprocessing import sliding_window

    files = list_data_files()
    print(f"特征总数: {len(ALL_FEATURES)}")

    # 正常信号
    sig_n, meta_n = load_mat_file([f for f in files if "normal" in f][0])
    win_n = sliding_window(sig_n, window_length=1024, stride=512)[0]

    # 内圈故障信号
    sig_f, meta_f = load_mat_file([f for f in files if "IR007" in f][0])
    win_f = sliding_window(sig_f, window_length=1024, stride=512)[0]

    fn = feature_names()
    feats_n = extract_features(win_n, as_dict=True)
    feats_f = extract_features(win_f, as_dict=True)

    print("\n特征对比（正常 vs 内圈故障）：")
    print(f"{'特征':<16}{'正常':>12}{'内圈故障':>14}")
    for name in fn:
        print(f"{name:<16}{feats_n[name]:>12.4f}{feats_f[name]:>14.4f}")
