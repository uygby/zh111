# 工业设备轴承故障智能监测与诊断系统

> 制造智能技术课程设计 · 智造24-2-25 张昊

基于振动信号实现轴承故障智能诊断的 B/S 架构 Web 系统。系统面向设备运维工业场景，实现轴承故障识别（正常、内圈故障、外圈故障、滚动体故障）、健康趋势预测与早期预警、故障知识推理与运维建议输出，并通过 Web 界面完成数据展示、诊断与可视化一体化演示。

## 📹 演示视频

点击下方视频在线播放（3 分钟系统完整演示，带字幕）：

[▶ 演示视频.mp4](./演示视频/演示视频.mp4)

> 字幕源文件：[演示视频字幕.srt](./演示视频/演示视频字幕.srt)

## 项目文档

| 文档 | 说明 |
| --- | --- |
| [课程设计报告.docx](./工业设备轴承故障智能监测与诊断系统_课程设计报告.docx) | 完整课程设计报告（含 AI 使用披露章节） |
| [需求规格说明书.md](./需求规格说明书.md) | 功能/非功能需求、系统架构、验收标准 |
| [过程档案.md](./过程档案.md) | Vibe Coding 过程记录、AI 出错案例与纠正 |
| [选题说明.md](./选题说明.md) | 选题背景、意义、完成目标与涉及的技术方向 |
| [学习笔记.md](./学习笔记.md) | Vibe Coding / AI 编程工具 / Git 原理学习笔记 |
| [docs/阶段三算法模块报告.md](./docs/阶段三算法模块报告.md) | 阶段三算法模块开发与实验结果 |
| [docs/阶段五系统测试报告.md](./docs/阶段五系统测试报告.md) | 阶段五系统联调与功能测试 |
| [docs/阶段六系统设计报告.md](./docs/阶段六系统设计报告.md) | 阶段六 Web 系统设计实现 |
| [docs/系统使用说明.md](./docs/系统使用说明.md) | 系统部署与操作指南 |
| [docs/答辩准备.md](./docs/答辩准备.md) | 答辩演示流程与问答准备 |
| [bearing_system.py](./bearing_system.py) | 单文件整合版（全部功能合一） |
| [启动系统.bat](./启动系统.bat) | 一键启动脚本 |

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
| 阶段二 | 8/29–8/31 | 数据集下载、数据预处理与特征提取模块开发（已完成） |
| 阶段三 | 9/1–9/5 | 故障分类、时序预测、知识推理算法模块开发与模型训练（已完成） |
| 阶段四 | 9/6–9/12 | Web 系统前后端开发与集成（已完成） |
| 阶段五 | 9/13–9/15 | 系统联调、功能测试与界面完善（已完成） |
| 阶段六 | 9/16–9/20 | 文档整理、答辩准备（已完成） |

## 项目结构

```
zh111/
├── README.md                 # 项目说明与数据来源
├── requirements.txt          # Python 依赖
├── 选题说明.md / 方案设计.md / 学习笔记.md
├── data/
│   ├── cwru/                 # CWRU 原始 .mat 数据（不入库，脚本可复现下载）
│   └── processed/            # 特征矩阵（features.csv / feature_matrix.npz）
├── src/                      # 核心源码模块
│   ├── config.py             # 全局配置（采样率、窗口参数、类别定义）
│   ├── data_loader.py        # CWRU 数据加载与文件名解析
│   ├── preprocessing.py      # 滤波、去趋势、滑动窗口切片、标准化
│   ├── feature_extraction.py # 时域/频域特征提取（20 维）
│   ├── classifier.py         # 故障分类（KNN/SVM/随机森林）
│   ├── health_prediction.py  # 健康趋势预测与预警
│   └── knowledge_base.py     # 故障知识库与规则推理
├── scripts/
│   ├── download_cwru.py      # CWRU 数据集下载脚本
│   ├── download_cwru_fast.py # 并发下载（高效版）
│   ├── build_features.py     # 数据准备：原始数据 -> 特征矩阵
│   ├── train_classifier.py   # 模型训练评估
│   └── verify_*.py           # 验证脚本
├── models/                   # 训练好的模型与评估报告
├── web/                      # Web 系统（阶段四）
│   ├── app.py                # Flask 后端主应用（REST API + 页面托管）
│   ├── database.py           # SQLite 数据库模块（四张表 + 知识库）
│   ├── templates/index.html  # 前端页面
│   └── static/               # 样式 / 前端逻辑 / 本地化 ECharts
├── scripts/
│   ├── test_api.py           # Web API 端到端测试脚本
│   └── ...                   # 数据下载/特征/训练/验证脚本
└── docs/                     # 技术报告（阶段三/五/六 + 使用说明 + 答辩准备）
```

## 阶段二进展（8/29 起）

已完成：

1. **环境搭建**：Python 3.13 + numpy / pandas / scipy / scikit-learn / matplotlib
2. **数据集下载**：CWRU 12k 驱动端数据 20 个文件（正常 + 内圈/滚动体/外圈故障，0~3 HP 工况），`python scripts/download_cwru.py` 可复现
3. **数据预处理模块**（src/preprocessing.py）：Butterworth 带通滤波、去趋势、滑动窗口切片（1024 点/512 步长）、z-score 标准化
4. **特征提取模块**（src/feature_extraction.py）：20 维特征 = 12 时域 + 8 频域
5. **特征数据集**：6389 样本 × 20 特征，已保存至 data/processed/

### 特征提取说明

| 类型 | 特征 |
| --- | --- |
| 时域（12） | 均值、绝对均值、标准差、方差、RMS、峰峰值、峰值、峭度、偏度、峰值因子、脉冲因子、裕度因子 |
| 频域（8） | 频谱幅值均值/标准差、频谱质心、频谱RMS、主频幅值/位置、频谱峭度/偏度 |

> 峭度、峰值因子、频谱质心等对轴承故障冲击敏感，是诊断的关键指标。

## 阶段三进展

已完成三个算法模块（详见 [docs/阶段三算法模块报告.md](./docs/阶段三算法模块报告.md)）：

1. **故障分类模块**（src/classifier.py）：KNN / SVM / 随机森林，随机森林最优（5 折交叉验证 0.891）
2. **健康趋势预测模块**（src/health_prediction.py）：滑动窗口 + 多项式回归趋势外推 + 健康度/预警
3. **知识推理模块**（src/knowledge_base.py）：故障知识库 + 规则推理 + 严重度分级 + 运维建议

> **实验结论（数据泄漏）**：随机划分准确率 0.997，但按文件分组评估（防泄漏）为 0.633，
> 说明滑动窗口重叠导致信息泄漏、随机划分虚高；课程实验应采用按设备/文件分组评估。

## 阶段四~六进展（Web 系统）

已完成（详见 [docs/阶段六系统设计报告.md](./docs/阶段六系统设计报告.md)）：

1. **Web 后端**（web/app.py）：Flask + Flask-CORS，8 个 REST API（健康检查、数据集、信号/频谱、故障诊断、健康预测、知识推理、知识库、记录查询）
2. **SQLite 数据库**（web/database.py）：四张表（sensor_data / fault_sample / fault_knowledge / alarm_record），知识库 4 条填充，诊断/告警自动持久化
3. **前端页面**（web/templates/index.html + static/）：ECharts 波形图/频谱图/健康趋势图三图联动，故障诊断结果 + 知识推理运维建议，诊断/告警记录实时展示
4. **联调测试**（scripts/test_api.py）：**12/12 接口用例通过**；浏览器端四类数据全流程验证通过（详见 [docs/阶段五系统测试报告.md](./docs/阶段五系统测试报告.md)）
5. **界面完善**：ECharts 本地化（免 CDN）、CWRU 负载-转速映射兜底等

### 快速启动

```powershell
pip install -r requirements.txt   # 安装依赖
python web/app.py                 # 启动服务
# 浏览器访问 http://127.0.0.1:5000
```

详细操作见 [docs/系统使用说明.md](./docs/系统使用说明.md)。

## 参考引用

- Smith W A, Randall R B. Rolling element bearing diagnostics using the Case Western Reserve University data: A benchmark study[J]. Mechanical Systems and Signal Processing, 2015, 64-65: 100-131.
- Case Western Reserve University. Bearing Data Center[EB/OL]. https://engineering.case.edu/bearingdatacenter
