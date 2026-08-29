"""
CWRU 数据集并发下载脚本（高效版）
=================================
使用多线程并发下载，大幅提升下载速度。

用法：
  python scripts/download_cwru_fast.py [--workers 8]
"""
import os
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed

BASE_URL = "https://raw.githubusercontent.com/hmmhxh/CWRU/master/"
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "cwru")

# 12k 驱动端 + 正常数据全部文件
FILES = [
    "normal_0_97.mat", "normal_1_98.mat", "normal_2_99.mat", "normal_3_100.mat",
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

TIMEOUT = 60
MAX_RETRY = 2
LOCK = None  # 打印锁（单线程足够）


def download_one(filename: str) -> bool:
    dest = os.path.join(DATA_DIR, filename)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return True  # 已存在，跳过
    if os.path.exists(dest):
        try:
            os.remove(dest)
        except OSError:
            pass
    url = BASE_URL + filename
    for attempt in range(1, MAX_RETRY + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp, open(dest, "wb") as f:
                f.write(resp.read())
            if os.path.getsize(dest) > 0:
                print(f"[OK] {filename} ({os.path.getsize(dest)//1024} KB)")
                return True
            os.remove(dest)
        except Exception as e:
            print(f"[!] {filename} 第{attempt}次失败: {type(e).__name__}")
            time.sleep(1)
    return False


def main():
    workers = 8
    if "--workers" in sys.argv:
        idx = sys.argv.index("--workers")
        workers = int(sys.argv[idx + 1])

    os.makedirs(DATA_DIR, exist_ok=True)
    # 过滤已下载完成文件
    todo = [f for f in FILES if not (os.path.exists(os.path.join(DATA_DIR, f)) and os.path.getsize(os.path.join(DATA_DIR, f)) > 0)]
    done = len(FILES) - len(todo)
    print(f"共 {len(FILES)} 个文件，已完成 {done} 个，待下载 {len(todo)} 个（{workers} 线程并发）")

    ok, fail = 0, 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(download_one, f): f for f in todo}
        for fut in as_completed(futures):
            if fut.result():
                ok += 1
            else:
                fail += 1
                print(f"[FAIL] {futures[fut]}")

    print(f"\n完成：成功 {ok}，失败 {fail}，耗时 {time.time()-t0:.0f} 秒")
    if fail:
        print("失败文件清单已保留，可再次运行本脚本重试")


if __name__ == "__main__":
    main()
