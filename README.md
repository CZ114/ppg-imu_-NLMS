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

- **数据集**：`D:/Imperial/individual/learn/PPG_FieldStudy/`（15 受试者，~2.5h 各）
- **ESP32 项目**：`D:/Imperial/individual/audioAndsensor/integrated_esp32/`
- **算法参考综述**：`C:/Users/陈哲/Desktop/ppg_imu_algorithms.html`

## 当前阶段

**Phase A — 方案设计**：本目录初始化，记录验证流程，未开始编码。
