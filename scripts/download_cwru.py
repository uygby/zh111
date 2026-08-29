"""
CWRU 轴承数据集下载脚本
========================
从 GitHub 镜像仓库 hmmhxh/CWRU 下载凯斯西储大学（CWRU）12k 驱动端轴承数据。

数据来源：
  官方：Case Western Reserve University Bearing Data Center
       https://engineering.case.edu/bearingdatacenter
  镜像：https://github.com/hmmhxh/CWRU (master 分支)

下载清单：12k 驱动端、0 HP 负载（约 1797 RPM）、正常 + 3 类故障 × 3 种故障直径
共 10 个 .mat 文件。

用法：
  python scripts/download_cwru.py [--all]
  --all 时下载 12k 驱动端全部文件（含 0~3 HP 负载）
"""
import os
import sys
import time
import urllib.request

BASE_URL = "https://raw.githubusercontent.com/hmmhxh/CWRU/master/"
DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data", "cwru")

# 阶段二演示集：0 HP 负载，正常 + 内圈/滚动体/外圈(6:00) × 007/014/021
DEFAULT_FILES = [
    # 正常状态
    "normal_0_97.mat",
    # 内圈故障
    "12k_Drive_End_IR007_0_105.mat",
    "12k_Drive_End_IR014_0_169.mat",
    "12k_Drive_End_IR021_0_209.mat",
    # 滚动体故障
    "12k_Drive_End_B007_0_118.mat",
    "12k_Drive_End_B014_0_185.mat",
    "12k_Drive_End_B021_0_222.mat",
    # 外圈故障（负载区中心 @6:00）
    "12k_Drive_End_OR007@6_0_130.mat",
    "12k_Drive_End_OR014@6_0_197.mat",
    "12k_Drive_End_OR021@6_0_234.mat",
]

# 12k 驱动端全部文件（供 --all 使用）
ALL_FILES = [
    "normal_0_97.mat",
    "normal_1_98.mat",
    "normal_2_99.mat",
    "normal_3_100.mat",
    "12k_Drive_End_B007_0_118.mat", "12k_Drive_End_B007_1_119.mat",
    "12k_Drive_End_B007_2_120.mat", "12k_Drive_End_B007_3_121.mat",
    "12k_Drive_End_B014_0_185.mat", "12k_Drive_End_B014_1_186.mat",
    "12k_Drive_End_B014_2_187.mat", "12k_Drive_End_B014_3_188.mat",
    "12k_Drive_End_B021_0_222.mat", "12k_Drive_End_B021_1_223.mat",
    "12k_Drive_End_B021_2_224.mat", "12k_Drive_End_B021_3_225.mat",
    "12k_Drive_End_B028_0_3005.mat", "12k_Drive_End_B028_1_3006.mat",
    "12k_Drive_End_B028_2_3007.mat", "12k_Drive_End_B028_3_3008.mat",
    "12k_Drive_End_IR007_0_105.mat", "12k_Drive_End_IR007_1_106.mat",
    "12k_Drive_End_IR007_2_107.mat", "12k_Drive_End_IR007_3_108.mat",
    "12k_Drive_End_IR014_0_169.mat", "12k_Drive_End_IR014_1_170.mat",
    "12k_Drive_End_IR014_2_171.mat", "12k_Drive_End_IR014_3_172.mat",
    "12k_Drive_End_IR021_0_209.mat", "12k_Drive_End_IR021_1_210.mat",
    "12k_Drive_End_IR021_2_211.mat", "12k_Drive_End_IR021_3_212.mat",
    "12k_Drive_End_IR028_0_3001.mat", "12k_Drive_End_IR028_1_3002.mat",
    "12k_Drive_End_IR028_2_3003.mat", "12k_Drive_End_IR028_3_3004.mat",
    "12k_Drive_End_OR007@6_0_130.mat", "12k_Drive_End_OR007@6_1_131.mat",
    "12k_Drive_End_OR007@6_2_132.mat", "12k_Drive_End_OR007@6_3_133.mat",
    "12k_Drive_End_OR007@3_0_144.mat", "12k_Drive_End_OR007@3_1_145.mat",
    "12k_Drive_End_OR007@3_2_146.mat", "12k_Drive_End_OR007@3_3_147.mat",
    "12k_Drive_End_OR007@12_0_156.mat", "12k_Drive_End_OR007@12_1_158.mat",
    "12k_Drive_End_OR007@12_2_159.mat", "12k_Drive_End_OR007@12_3_160.mat",
    "12k_Drive_End_OR014@6_0_197.mat", "12k_Drive_End_OR014@6_1_198.mat",
    "12k_Drive_End_OR014@6_2_199.mat", "12k_Drive_End_OR014@6_3_200.mat",
    "12k_Drive_End_OR021@6_0_234.mat", "12k_Drive_End_OR021@6_1_235.mat",
    "12k_Drive_End_OR021@6_2_236.mat", "12k_Drive_End_OR021@6_3_237.mat",
    "12k_Drive_End_OR021@3_0_246.mat", "12k_Drive_End_OR021@3_1_247.mat",
    "12k_Drive_End_OR021@3_2_248.mat", "12k_Drive_End_OR021@3_3_249.mat",
    "12k_Drive_End_OR021@12_0_258.mat", "12k_Drive_End_OR021@12_1_259.mat",
    "12k_Drive_End_OR021@12_2_260.mat", "12k_Drive_End_OR021@12_3_261.mat",
]

MAX_RETRY = 3
TIMEOUT = 90


def download(url: str, dest: str) -> bool:
    """下载单个文件，带重试；已存在且非空的文件跳过"""
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        print(f"[跳过] {os.path.basename(dest)} 已存在")
        return True
    if os.path.exists(dest):  # 删除损坏的 0 字节文件
        os.remove(dest)
    for attempt in range(1, MAX_RETRY + 1):
        print(f"[下载] {os.path.basename(dest)} (第 {attempt}/{MAX_RETRY} 次) ...")
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            size = os.path.getsize(dest)
            if size > 0:
                print(f"  -> 完成 {size / 1024:.1f} KB")
                return True
            else:
                os.remove(dest)
                raise RuntimeError("下载结果为空文件")
        except Exception as e:
            print(f"  -> 失败: {type(e).__name__}: {str(e)[:150]}")
            if os.path.exists(dest):
                try:
                    os.remove(dest)
                except OSError:
                    pass
            time.sleep(2)
    return False


def main():
    use_all = "--all" in sys.argv
    files = ALL_FILES if use_all else DEFAULT_FILES
    os.makedirs(DATA_DIR, exist_ok=True)
    ok, fail = 0, 0
    for f in files:
        url = BASE_URL + f
        dest = os.path.join(DATA_DIR, f)
        if download(url, dest):
            ok += 1
        else:
            fail += 1
    print(f"\n完成：成功 {ok} 个，失败 {fail} 个")
    print(f"数据目录：{os.path.abspath(DATA_DIR)}")


if __name__ == "__main__":
    main()
