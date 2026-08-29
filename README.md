# 工业设备轴承故障智能监测与诊断系统

> 制造智能技术课程设计 · 智造24-2-25 张昊

基于振动信号实现轴承故障智能诊断的 B/S 架构 Web 系统。系统面向设备运维工业场景，实现轴承故障识别（正常、内圈故障、外圈故障、滚动体故障）、健康趋势预测与早期预警、故障知识推理与运维建议输出，并通过 Web 界面完成数据展示、诊断与可视化一体化演示。

## 项目文档

| 文档 | 说明 |
| --- | --- |
| [选题说明.md](./选题说明.md) | 选题背景、意义、完成目标与涉及的技术方向 |
| [方案设计.md](./方案设计.md) | 功能需求分析、方案论证、技术栈、技术路线与计划安排 |
| [学习笔记.md](./学习笔记.md) | Vibe Coding / AI 编程工具 / Git 原理学习笔记 |

## 数据来源说明

本项目使用公开的工业数据集，数据来源及引用链接如下：

### 凯斯西储大学（CWRU）轴承数据中心数据集

- **数据集名称**：Case Western Reserve University (CWRU) Bearing Data Center
- **官方主页**：https://engineering.case.edu/bearingdatacenter
- **数据集说明**：该数据集为旋转机械轴承故障诊断领域最常用的公开基准数据集。实验采用 2 hp Reliance Electric 电机，通过电火花加工（EDM）在内圈、滚动体、外圈分别注入 0.007 英寸至 0.040 英寸的不同故障，并在 0~3 马力负载（电机转速 1797~1720 RPM）下采集电机轴承附近及远端位置的振动加速度信号，包含正常、内圈故障、外圈故障、滚动体故障等多种工况数据。
- **用途**：用于故障分类模型训练与测试、振动信号特征提取验证、健康趋势预测研究。

### 数据使用规范

1. **公开数据集**：在使用公开数据集时，需在本 README 中注明来源与引用链接（如上）。
2. **自建数据集**：如后续自建数据集，须先将数据集开源发布到 [Hugging Face](https://huggingface.co) 或 [ModelScope](https://modelscope.cn) 等开源平台，取得可访问的引用链接后，再在本文档中补充引用链接，确保数据可追溯、可复现。
3. **数据安全**：私有敏感数据不建议用于课程设计，避免泄露风险。所有数据均须符合学术规范与开源许可要求。

## 技术栈

| 层次 | 技术选型 |
| --- | --- |
| 前端 | HTML / CSS / JavaScript + Bootstrap + ECharts |
| 后端 | Python + Flask / FastAPI |
| 算法 | scikit-learn、NumPy、Pandas、SciPy |
| 数据库 | SQLite |
| 版本管理 | Git + GitHub |

## 开发计划

| 阶段 | 时间 | 任务内容 |
| --- | --- | --- |
| 阶段一 | 8/27–8/28 | 选题与方案规划（已完成） |
| 阶段二 | 8/29–8/31 | 数据集下载、数据预处理与特征提取模块开发 |
| 阶段三 | 9/1–9/5 | 故障分类、时序预测、知识推理算法模块开发与模型训练 |
| 阶段四 | 9/6–9/12 | Web 系统前后端开发与集成 |
| 阶段五 | 9/13–9/15 | 系统联调、功能测试与界面完善 |
| 阶段六 | 9/16–9/20 | 文档整理、答辩准备 |

## 参考引用

- Smith W A, Randall R B. Rolling element bearing diagnostics using the Case Western Reserve University data: A benchmark study[J]. Mechanical Systems and Signal Processing, 2015, 64-65: 100-131.
- Case Western Reserve University. Bearing Data Center[EB/OL]. https://engineering.case.edu/bearingdatacenter
