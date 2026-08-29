"""
Web API 端到端测试脚本
=======================
测试后端全部 API 接口：
  GET  /api/health
  GET  /api/datasets
  GET  /api/signal/<filename>
  POST /api/diagnose
  POST /api/predict
  POST /api/reason
  GET  /api/knowledge
  GET  /api/records

用法：先启动 python web/app.py，再运行本脚本
"""
import json
import urllib.request

BASE = "http://127.0.0.1:5000/api"


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=30) as r:
        return json.loads(r.read().decode())


def post(path, payload):
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(payload).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


passed = 0
failed = 0


def check(name, cond, detail=""):
    global passed, failed
    if cond:
        passed += 1
        print(f"  [PASS] {name} {detail}")
    else:
        failed += 1
        print(f"  [FAIL] {name} {detail}")


def main():
    print("===== 1. 健康检查 =====")
    h = get("/health")
    check("health", h["status"] == "ok", f"model_loaded={h['model_loaded']}")

    print("\n===== 2. 数据集列表 =====")
    ds = get("/datasets")
    check("datasets", len(ds) >= 10, f"共 {len(ds)} 个文件")
    filename = ds[0]["filename"]
    print(f"  选取测试文件: {filename} ({ds[0]['label_cn']})")

    print("\n===== 3. 信号数据 =====")
    sig = get(f"/signal/{urllib.parse.quote(filename)}")
    check("signal", len(sig["time"]) > 0 and len(sig["signal"]) > 0,
          f"波形 {len(sig['signal'])} 点, 频谱 {len(sig['freq'])} 点")
    check("signal meta", sig["meta"]["label"] == ds[0]["label"])

    print("\n===== 4. 故障诊断 =====")
    diag = post("/diagnose", {"filename": filename})
    check("diagnose", "fault_type" in diag,
          f"结果={diag.get('fault_name')}, 置信度={diag.get('confidence')}")
    check("diagnose advice", "advice" in diag and len(diag["advice"]) > 0)

    print("\n===== 5. 健康预测 =====")
    pred = post("/predict", {"filename": filename, "metric": "rms"})
    check("predict", len(pred["y_history"]) > 0 and len(pred["y_forecast"]) > 0,
          f"历史 {len(pred['y_history'])} 点, 预测 {len(pred['y_forecast'])} 点")
    check("predict health", 0 <= pred["forecast_health"] <= 100,
          f"健康度 {pred['current_health']}->{pred['forecast_health']}, 预警={pred['warning']}")

    print("\n===== 6. 知识推理 =====")
    rsn = post("/reason", {"fault_type": diag["fault_type"]})
    check("reason", rsn["fault_name"] and rsn["severity"],
          f"{rsn['fault_name']}({rsn['severity']})")

    print("\n===== 7. 知识库与记录 =====")
    kb = get("/knowledge")
    check("knowledge", len(kb) == 4, f"{len(kb)} 条知识")
    rec = get("/records")
    check("records", len(rec["samples"]) >= 1, f"{len(rec['samples'])} 条诊断记录")
    check("alarms", isinstance(rec["alarms"], list))

    print(f"\n结果: {passed} 通过, {failed} 失败")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    import urllib.parse
    exit(main())
