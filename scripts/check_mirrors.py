"""查看 hmmhxh/CWRU 完整文件列表"""
import urllib.request
import json

url = "https://api.github.com/repos/hmmhxh/CWRU/contents/"
req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
resp = urllib.request.urlopen(req, timeout=20)
items = json.loads(resp.read().decode())

names = [it["name"] for it in items]
print(f"共 {len(names)} 个文件")
print("\n--- Normal 相关 ---")
for n in names:
    if "Normal" in n or "normal" in n:
        print(" ", n)
print("\n--- 全部文件名（每行5个） ---")
for i in range(0, len(names), 5):
    print("  " + "  ".join(names[i : i + 5]))
