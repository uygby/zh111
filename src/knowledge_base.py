"""
故障知识库与规则推理模块
========================
建立「故障类型 - 成因 - 特征表现 - 处理建议」知识库，
基于规则匹配（If-Then）自动输出运维建议。

适用对象：滚动轴承常见故障（基于 CWRU 数据集 4 类状态）。
"""
import numpy as np

# ---------- 故障知识库 ----------
# 每类故障记录：成因、特征表现、处理建议、检查要点
KNOWLEDGE_BASE = {
    "Normal": {
        "name": "正常",
        "cause": "轴承处于正常运行状态，振动能量与冲击特征处于正常水平。",
        "features": "峭度接近 3，RMS 较低，频谱无明显故障特征频率分量。",
        "advice": "设备运行正常，按计划开展定期巡检与润滑维护即可，无需停机处理。",
        "checks": ["保持润滑周期", "定期监测振动趋势"],
    },
    "IR": {
        "name": "内圈故障",
        "cause": "内圈滚道出现点蚀、剥落或疲劳裂纹（常见于装配过紧、润滑不良、"
                 "异物进入或长期过载），内圈随轴旋转使故障冲击周期性作用。",
        "features": "振动信号存在周期性冲击，峭度与峰值因子显著升高，"
                    "频谱出现内圈故障特征频率 BPFI 及其谐波（带转速边带）。",
        "advice": "建议安排停机检修，检查内圈滚道表面；如故障处于早期可密切监控，"
                  "发展为中度/重度时更换轴承。检查装配过盈量、润滑状态与轴承载荷。",
        "checks": ["检查内圈滚道剥落/点蚀", "核查装配过盈与润滑", "更换轴承（重度时）"],
    },
    "B": {
        "name": "滚动体故障",
        "cause": "滚动体表面出现点蚀、剥落或裂纹（常见于润滑失效、疲劳、"
                 "异物压痕），滚动体自转使故障点周期性进入/离开承载区。",
        "features": "冲击特征明显且随工况波动，峭度显著增大；"
                    "频谱出现滚动体故障特征频率 BSF 及其谐波，"
                    "故障特征频率常带保持架转频调制。",
        "advice": "建议安排停机检查滚动体表面；滚动体故障发展较快，易引发保持架损坏，"
                  "应尽早更换轴承。同时排查润滑与异物来源。",
        "checks": ["检查滚动体点蚀/剥落", "排查润滑失效与异物", "尽早更换轴承"],
    },
    "OR": {
        "name": "外圈故障",
        "cause": "外圈滚道出现点蚀、剥落（常见于外圈承载区受力集中、"
                 "安装不正或腐蚀），外圈固定于轴承座，故障冲击位置相对固定。",
        "features": "周期性冲击稳定，峭度升高；频谱出现外圈故障特征频率 BPFO"
                    "及其谐波，故障冲击位置与承载区相对关系（6:00/3:00/12:00）"
                    "影响调制特征。",
        "advice": "建议安排检修，检查外圈滚道与轴承座配合面；"
                  "外圈故障易造成轴承座磨损，应检查座孔配合与对中情况，"
                  "中度以上建议更换轴承。",
        "checks": ["检查外圈滚道剥落", "检查轴承座配合与对中", "更换轴承（中度以上）"],
    },
}

# 严重程度分级
SEVERITY_LEVELS = ["轻度", "中度", "重度"]


def get_fault_info(fault_type: str) -> dict:
    """获取故障类型的基础知识条目"""
    if fault_type not in KNOWLEDGE_BASE:
        raise ValueError(
            f"未知故障类型: {fault_type}，可选 {list(KNOWLEDGE_BASE)}"
        )
    return KNOWLEDGE_BASE[fault_type]


def severity_from_features(features: dict) -> str:
    """
    基于振动特征判断故障严重程度（规则推理）。

    规则（阈值依据轴承诊断经验设定）：
      - 峭度 kurtosis：
          < 4.5 且 RMS 处于正常区间  -> 轻度
          >= 8                        -> 重度
      - 综合：峭度越高、RMS 越大则越严重

    参数：
      features : 特征字典（含 kurtosis、rms 等）

    返回：
      "轻度" / "中度" / "重度"
    """
    if features is None:
        return "轻度"
    kurtosis = features.get("kurtosis", 3.0)
    rms = features.get("rms", 0.0)

    if kurtosis >= 8.0:
        return "重度"
    if kurtosis >= 5.0:
        return "中度"
    # 峭度接近正常但 RMS 偏高，也视为中度
    if kurtosis >= 4.0 and rms > 0.3:
        return "中度"
    return "轻度"


def reason(fault_type: str, features: dict = None) -> dict:
    """
    故障推理主入口：输入诊断的故障类型（及可选特征），
    输出结构化运维建议。

    返回：
      dict，包含故障信息、严重程度、处理建议、检查清单
    """
    info = get_fault_info(fault_type)
    severity = severity_from_features(features) if features else "轻度"

    advice = info["advice"]
    # 按严重程度补充处置优先级
    if severity == "重度":
        priority = "紧急：建议立即停机并更换轴承，防止故障扩大造成设备损坏。"
    elif severity == "中度":
        priority = "较急：建议近期安排检修，加强监测频次。"
    else:
        priority = "常规：纳入例行检修计划，持续监测趋势。"
    advice = priority + "\n" + advice

    return {
        "fault_type": fault_type,
        "fault_name": info["name"],
        "cause": info["cause"],
        "features_desc": info["features"],
        "severity": severity,
        "advice": advice,
        "checks": info["checks"],
    }


if __name__ == "__main__":
    # 自测：演示 4 类故障的推理输出
    from .feature_extraction import extract_features
    from .data_loader import load_mat_file, list_data_files
    from .preprocessing import sliding_window

    files = list_data_files()
    print("=" * 55)
    print("故障知识推理演示")
    print("=" * 55)
    for label in ["Normal", "IR", "B", "OR"]:
        # 从文件名匹配对应样本
        for fp in files:
            if label == "Normal" and "normal" in fp:
                break
            elif label != "Normal" and f"12k_Drive_End_{label}007" in fp:
                break
        sig, _ = load_mat_file(fp)
        win = sliding_window(sig, 1024, 512)[5]
        feats = extract_features(win, as_dict=True)

        result = reason(label, feats)
        print(f"\n----- {label} ({result['fault_name']}) -----")
        print(f"严重程度: {result['severity']}")
        print(f"成因: {result['cause'][:40]}...")
        print(f"建议: {result['advice'][:60]}...")
        print(f"检查清单: {result['checks']}")
