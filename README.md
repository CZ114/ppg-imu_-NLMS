# PPG-HR 算法验证工作目录

本目录用于在 **PPG-DaLiA (PPG_FieldStudy)** 公开数据集上离线验证 PPG + IMU 心率估计算法（NLMS / Wiener / Phase Vocoder），为 ESP32-S3 嵌入式实现做前期算法验证。

## 目录结构（规划）

```
ppg_hr_validation/
├── README.md                ← 本文件，工作目录总览
├── validation_plan.md       ← 完整测试方案（先读这个）
├── dataset_notes.md         ← PPG-DaLiA 数据集字段速查
├── data/                    ← 数据集软链接或副本（不入版本控制）
├── src/                     ← Python 实现
│   ├── io_utils.py          ← 数据加载
│   ├── algorithms.py        ← NLMS / Wiener / Phase Vocoder
│   ├── baselines.py         ← B0 / B1 基线
│   ├── eval.py              ← 评估指标 (MAE/RMSE/Bland-Altman)
│   └── run_loso.py          ← LOSO 主实验脚本
├── notebooks/               ← 调试 / 可视化 Jupyter
├── results/                 ← 实验输出 (csv, png)
└── docs/                    ← 算法笔记、推导
```

## 相关资源

- **数据集**：PPG-DaLiA / PPG_FieldStudy（公开数据集，15 受试者，~2.5h/人）；获取方式见 `dataset_notes.md`
- **ESP32 项目**：本仓库算法将移植到独立的 ESP32-S3 固件工程
- **算法参考综述**：本地综述文档（PPG/IMU 去伪影方法对比）

> 本机绝对路径（数据集、固件工程、综述文件）记录在 `validation_plan.md` §〇，**不入版本控制**。

## 当前阶段

**Phase A — 方案设计**：本目录初始化，记录验证流程，未开始编码。
