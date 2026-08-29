"""
CWRU 数据加载模块
=================
负责解析 CWRU 数据文件名、读取 .mat 文件并提取指定通道的振动信号。

CWRU 文件名格式说明：
  - 正常数据：normal_{负载}_{编号}.mat       例：normal_0_97.mat
  - 故障数据：12k_Drive_End_{类型}{直径}{位置}_{负载}_{编号}.mat
      例：12k_Drive_End_IR007_0_105.mat        -> 内圈故障，直径0.007"，0 HP
          12k_Drive_End_OR007@6_0_130.mat     -> 外圈故障(@6:00)，直径0.007"，0 HP
          12k_Drive_End_B014_0_185.mat        -> 滚动体故障，直径0.014"，0 HP

.mat 文件内部变量：
  X{编号}_DE_time : 驱动端 (Drive End) 加速度信号 (N,1)
  X{编号}_FE_time : 风扇端 (Fan End) 加速度信号
  X{编号}_BA_time : 基座 (Base) 加速度信号（故障数据才有）
  X{编号}RPM      : 电机转速 (1,1)
"""
import os
import re
import numpy as np
import scipy.io

from . import config


def parse_cwru_filename(filename: str) -> dict:
    """
    解析 CWRU 数据文件名，返回元信息字典。

    返回字段：
      label      : 故障类型标签（Normal / IR / B / OR）
      label_cn   : 中文类型名
      diameter   : 故障直径（英寸字符串，如 "007"），正常数据为 None
      position   : 外圈故障位置（"6"/"3"/"12"），非外圈为 None
      load       : 负载（HP，int）
      sample_id  : 数据编号（int）
    """
    name = os.path.basename(filename)

    # 正常数据
    m = re.match(r"^normal_(\d+)_(\d+)\.mat$", name, re.IGNORECASE)
    if m:
        return {
            "label": "Normal",
            "label_cn": config.CLASS_NAMES["Normal"],
            "diameter": None,
            "position": None,
            "load": int(m.group(1)),
            "sample_id": int(m.group(2)),
        }

    # 故障数据：12k_Drive_End_(IR|B|OR)(直径)(位置?)_(负载)_(编号).mat
    m = re.match(
        r"^12k_Drive_End_(IR|B|OR)(\d{3})(?:@(\d+))?_(\d)_(\d+)\.mat$",
        name,
        re.IGNORECASE,
    )
    if m:
        label, diameter, position, load, sample_id = m.groups()
        return {
            "label": label.upper(),
            "label_cn": config.CLASS_NAMES[label.upper()],
            "diameter": diameter,
            "position": position if label.upper() == "OR" else None,
            "load": int(load),
            "sample_id": int(sample_id),
        }

    raise ValueError(f"无法识别的 CWRU 文件名: {name}")


def list_data_files(data_dir: str = None) -> list:
    """列出数据目录下所有 .mat 数据文件（按文件名排序）"""
    data_dir = data_dir or config.DATA_DIR
    if not os.path.isdir(data_dir):
        raise FileNotFoundError(f"数据目录不存在: {data_dir}")
    files = [
        os.path.join(data_dir, f)
        for f in sorted(os.listdir(data_dir))
        if f.lower().endswith(".mat")
    ]
    return files


def load_mat_file(filepath: str, channel: str = "DE") -> tuple:
    """
    加载单个 .mat 文件，返回 (信号一维数组, 元信息字典)。

    channel 支持：DE（驱动端）、FE（风扇端）、BA（基座）。
    """
    channel = channel.upper()
    data = scipy.io.loadmat(filepath)

    # 自动匹配 X{编号}_{channel}_time 变量
    pattern = re.compile(rf"^X(\d+)_{channel}_time$")
    signal_key = None
    sample_id = None
    for key in data:
        if pattern.match(key):
            signal_key = key
            sample_id = int(pattern.match(key).group(1))
            break
    if signal_key is None:
        raise ValueError(f"文件 {os.path.basename(filepath)} 中未找到 {channel}_time 变量")

    signal = np.asarray(data[signal_key]).ravel().astype(np.float64)

    # 读取转速
    rpm = None
    rpm_key = f"X{sample_id}RPM"
    if rpm_key in data:
        rpm = float(np.asarray(data[rpm_key]).ravel()[0])

    meta = parse_cwru_filename(filepath)
    meta["channel"] = channel
    meta["rpm"] = rpm
    meta["length"] = len(signal)
    meta["filepath"] = filepath
    return signal, meta


def load_dataset(data_dir: str = None, channel: str = "DE") -> list:
    """
    加载整个数据目录，返回样本列表。

    返回：[{"signal": ndarray, "meta": dict}, ...]
    """
    files = list_data_files(data_dir)
    samples = []
    for fp in files:
        signal, meta = load_mat_file(fp, channel=channel)
        samples.append({"signal": signal, "meta": meta})
    return samples


if __name__ == "__main__":
    # 简单自测
    print(f"数据目录: {config.DATA_DIR}")
    files = list_data_files()
    print(f"共发现 {len(files)} 个 .mat 文件\n")
    for fp in files[:5]:
        sig, meta = load_mat_file(fp)
        print(f"{os.path.basename(fp)}")
        print(f"  -> 类型={meta['label']}({meta['label_cn']}), "
              f"直径={meta['diameter']}, 负载={meta['load']}HP, "
              f"转速={meta['rpm']}rpm, 长度={meta['length']}点")
