# NLMS PPG-HR 算法验证方案

> 目标：在 PPG-DaLiA 数据集上离线验证「NLMS + Wiener + Phase Vocoder」pipeline 的有效性，为 ESP32-S3 嵌入式实现提供算法基线和参数。

---

## 〇、本地路径（不入库）

以下资源**只存在于本地工作站**，已在 `.gitignore` 中排除，不上传 GitHub：

| 用途 | 本机绝对路径 |
|---|---|
| PPG-DaLiA 数据集（15 受试者，~2.5h/人） | `D:/Imperial/individual/learn/PPG_FieldStudy/` |
| ESP32-S3 固件工程（移植目标） | `D:/Imperial/individual/audioAndsensor/integrated_esp32/` |
| 算法综述（PPG/IMU 去伪影方法对比） | `C:/Users/陈哲/Desktop/ppg_imu_algorithms.html` |

> 在其他机器上复现时需自行准备这三项资源并在脚本里更新路径。数据集获取见 `dataset_notes.md`。

---

## 一、研究问题

回答以下三个问题：

1. **Q1（有效性）**：用 IMU 做 NLMS 自适应去伪影，是否能显著降低 PPG HR 估计误差？
2. **Q2（适用范围）**：在哪些活动（走路、爬楼、骑车 vs 静坐、办公）上有效？哪些反而变差？
3. **Q3（参数）**：最优的滤波器阶数 $L$、步长 $\mu$、参考信号选择（X / Y / Z / $|\mathbf{a}|$ / 多通道）是什么？

---

## 二、评估对象（三个等级的算法）

| 编号 | 算法 | 描述 | 预期 MAE (BPM) |
|---|---|---|---|
| **B0** | Naive | BVP → 带通 → FFT → 最大峰 | 12–20 |
| **B1** | ACC 频谱掩模 | B0 + ACC 主频附近 bin 置零 | 7–10 |
| **B2** | **NLMS + B0** | NLMS(BVP, \|ACC\|) → 带通 → FFT | **≤ 5（目标）** |
| B3 | NLMS + Wiener | B2 + 频谱减法 | ≤ 4 |
| B4 | NLMS + Wiener + 历史跟踪 | B3 + 在 ±10 BPM 邻域找峰 | ≤ 3 |
| B5 | B4 + Phase Vocoder | B4 + 亚 bin 精化 | ≤ 2.5 |

> **核心验证 = B0 vs B1 vs B2**。B3-B5 是可选的"加料"实验，证明 NLMS 兼容其他改进。
>
> 论文 SOTA 在 PPG-DaLiA 上 MAE 约 7–8 BPM（CNN 类方法），传统方法 9–12。这个数据集**比 IEEE SP Cup 的跑步数据集难得多**，因为包含开车、午餐等低运动场景，运动伪影规律性差。

---

## 三、Pipeline 总览

```
[SX.pkl] ──┬── BVP (64 Hz)
           ├── wrist/ACC (32 Hz) ── 上采样到 64 Hz ── 取模长 |a|=√(ax²+ay²+az²)
           ├── label (HR ground truth, 每 2s 一个)
           └── activity (用于分活动评估)
                │
                ▼
       ┌──────────────────────┐
       │  STEP 1: NLMS        │   d = BVP, x = |a|
       │  滤波器阶 L, 步长 μ  │   输出 e[n] = 去伪影 PPG
       └──────────────────────┘
                │
                ▼
       ┌──────────────────────┐
       │  STEP 2: 带通 0.5-4Hz │   Butterworth 4 阶, filtfilt
       └──────────────────────┘
                │
                ▼
       ┌──────────────────────┐
       │  STEP 3: 8s 窗 + FFT │   N=1024 (zero-pad), Hann 窗
       │  滑窗 2s             │
       └──────────────────────┘
                │
                ▼
       ┌──────────────────────┐
       │  STEP 4: 峰值挑选    │   在 [0.5, 4] Hz 找最大谱峰
       └──────────────────────┘
                │
                ▼
        预测 HR (BPM) → 与 label 比较
```

---

## 四、评估协议（必须按这个，才能跟论文对比）

### 4.1 窗口
- 长度 8 秒、滑动 2 秒（数据集 label 就是按此切分）

### 4.2 训练/测试划分：**Leave-One-Subject-Out (LOSO)**
- 总共 15 折：每次用 14 人调参，第 15 人测试
- 报告 15 个被试各自的 MAE，再取均值 ± 标准差
- 对于 NLMS 这种**无监督**算法，"调参"只是 grid search 最优 $\mu, L$ — 仍要 LOSO 避免对单人过拟合

### 4.3 评估指标

| 指标 | 公式 | 用途 |
|---|---|---|
| **MAE** | $\frac{1}{N}\sum |\hat{HR} - HR|$ | 主指标 |
| RMSE | $\sqrt{\frac{1}{N}\sum (\hat{HR} - HR)^2}$ | 惩罚大误差 |
| Pearson $r$ | $\mathrm{corr}(\hat{HR}, HR)$ | 趋势一致性 |
| Bland-Altman 95% LoA | $\bar{d} \pm 1.96\sigma_d$ | 临床标准 |

### 4.4 分活动报告（**关键**）
按 `activity` ID 分别算 MAE：

| Activity | 期望 NLMS 收益 |
|---|---|
| 1 (sitting) | 几乎无收益，**不应变差**（验证不过抑制） |
| 2 (stairs), 7 (walking) | **大收益**（强周期性运动伪影） |
| 4 (cycling) | 中等收益 |
| 3, 5, 6, 8 | 小到中收益 |

---

## 五、实验设计（按顺序执行）

### Exp 1：Sanity Check — 单被试可视化
- 取 S7 的爬楼段（参考 readme Figure 1）
- 画 4 张图叠在一起：
  1. 原始 BVP
  2. \|ACC\|
  3. NLMS 输出 `e[n]`
  4. 三者的功率谱（标出真值 HR）
- **目的**：肉眼确认 NLMS 把 ACC 主频从 PPG 谱里减掉了

### Exp 2：参数扫描（在 S1, S5, S10 三人上）
- $\mu \in \{0.05, 0.1, 0.2, 0.3, 0.5, 1.0\}$
- $L \in \{8, 16, 32, 64, 128\}$
- 参考信号 $\in$ {ax, ay, az, \|a\|, 三通道并联 NLMS}
- 报告：MAE 热图 + 最优组合

### Exp 3：主实验 — LOSO on 15 subjects
- 用 Exp 2 选出的最优 $(\mu, L, \text{ref})$
- 对 B0 / B1 / B2 三个算法各跑一遍 15 人 LOSO
- 输出：
  - 总 MAE 表格（3 算法 × 15 被试 + 均值）
  - 分活动 MAE 表格（3 算法 × 8 活动）
  - Bland-Altman 图（B0 vs B2）
  - 每被试 MAE 箱线图

### Exp 4（可选）：扩展实验
- B3/B4/B5 渐进加料，看每一步带来多少改进
- 跨数据集：在 IEEE SP Cup 2015 跑步数据上验证不过拟合
- 受试者亚组分析（按肤色 / 性别 / 运动频率）

---

## 六、需要重点检查的工程问题

1. **采样率对齐**：BVP @64 Hz，ACC @32 Hz，必须把 ACC 上采样到 64 Hz（`scipy.signal.resample_poly(acc, 2, 1)`），不能直接 NLMS

2. **NLMS 收敛**：前几个样本 $\mathbf{w}$ 还没收敛，输出有瞬态，每个窗口的**前 ~1 秒（64 样本）数据要丢弃**或预先把 NLMS 跑过 warm-up 段

3. **静止时不过抑制**：当 `activity==1` (sitting) 时 IMU 能量极低，NLMS 不应该破坏 PPG。如果 MAE 反而升高，加 motion gate：
   ```
   if RMS(|a|窗) < threshold:  跳过 NLMS, 直接用原 BVP
   ```

4. **窗口边界效应**：FFT 之前加 Hann 窗，避免谱泄漏

5. **零填充（zero-padding）**：8s × 64Hz = 512 样本 → zero-pad 到 N=1024 让 FFT bin 间隔从 2 BPM 缩到 1 BPM（这是**免费**的精度提升）

6. **HR 真值的范围**：典型 [40, 200] BPM = [0.67, 3.33] Hz；带通用 [0.5, 4] Hz 保留余量

7. **复现性**：固定 numpy 随机种子；记录 scipy / numpy 版本

---

## 七、产出物

实验完成后这个目录应该包含：

- `results/per_subject_mae.csv` — 15 行 × 3 算法
- `results/per_activity_mae.csv` — 8 行 × 3 算法
- `results/bland_altman_B0_vs_B2.png`
- `results/param_sweep_heatmap.png`
- `results/exp1_sanity_check.png`
- `docs/findings.md` — 一页结论，回答 Q1/Q2/Q3

最终决定：**是否把 NLMS 移植到 ESP32-S3**，以及用什么参数。

---

## 八、风险和限制

| 风险 | 缓解 |
|---|---|
| PPG-DaLiA 用的是 Empatica E4，跟你的硬件不同 | 算法对硬件不敏感，但绝对 MAE 可能差异大；关注**相对改进**而非绝对值 |
| 单纯 NLMS 在 DaLiA 上历史表现一般 | 这就是验证目的；如果 B2 没显著优于 B0，需要直接上 B3/B4 |
| S6 数据不完整 | LOSO 时正常包含，但单独标注 |
| Empatica 的 BVP 已经做过厂家预处理 | 算法验证不影响；但移植到 ESP32 + MAX30102 时要注意自己做去直流 |

---

## 九、参考文献

详见本地综述 `ppg_imu_algorithms.html`（路径见第 〇 节），核心三篇：

- Reiss et al. (2019) *Deep PPG / PPG-DaLiA*. Sensors 19(14).
- Temko (2017) *WFPV*. IEEE TBME 64(9).
- Han & Kim (2012) *LMS for PPG artifacts*. CBM 42(4).
- Haykin (2014) *Adaptive Filter Theory*, Ch.6.
