"""
最简 PPG 心率估计 baseline
=========================
只做最朴素的事：带通滤波 + 滑动窗口 + FFT 找峰。
跳过 NLMS / Wiener / Phase Vocoder。

数据来源: PPG-DaLiA 的 SX_E4.zip
  - BVP.csv : PPG 原始波形 @ 64 Hz
  - HR.csv  : Empatica 自带的 HR 估计 @ 1 Hz (作 sanity check 参考，非 gold standard)
  - 不碰 1.4 GB 的 SX.pkl

输出: HR 估计 vs Empatica HR 参考 + 图
"""
from pathlib import Path
import zipfile
import io
import numpy as np
from scipy.signal import butter, filtfilt
import matplotlib.pyplot as plt

# Windows 下让 matplotlib 能显示中文
plt.rcParams["font.sans-serif"] = ["Microsoft YaHei", "SimHei", "DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False

# ---------- 配置 ----------
SUBJECT = "S1"
DATA_ROOT = Path(__file__).parent / "PPG_FieldStudy"

WIN_SEC = 8                # 窗口长度
STEP_SEC = 2               # 滑动步长
F_LOW, F_HIGH = 0.5, 4.0   # HR 30-240 BPM 对应 0.5-4 Hz
FFT_N = 4096               # FFT 长度 (补零提升频率分辨率)


def read_e4_csv(zf: zipfile.ZipFile, name: str):
    """读取 Empatica E4 的 CSV。
    格式: 第 1 行 = 起始时间戳 (UNIX), 第 2 行 = 采样率, 第 3 行起 = 数据
    返回: (data ndarray, fs, start_ts)
    """
    with zf.open(name) as f:
        raw = io.TextIOWrapper(f, encoding="utf-8").read().strip().split("\n")
    start_ts = float(raw[0].split(",")[0])
    fs = float(raw[1].split(",")[0])
    arr = np.array([list(map(float, line.split(","))) for line in raw[2:]],
                   dtype=np.float32)
    if arr.shape[1] == 1:
        arr = arr.ravel()
    return arr, fs, start_ts


def load_subject(subject: str):
    """从 E4 zip 直接读 BVP + HR 参考。"""
    zip_path = DATA_ROOT / subject / f"{subject}_E4.zip"
    print(f"  读取 {zip_path.name} ...")
    with zipfile.ZipFile(zip_path) as zf:
        bvp, fs_bvp, _ = read_e4_csv(zf, "BVP.csv")
        hr_ref, fs_hr, _ = read_e4_csv(zf, "HR.csv")
    print(f"    BVP : {len(bvp)} 样本 @ {fs_bvp} Hz ≈ {len(bvp)/fs_bvp/60:.1f} 分钟")
    print(f"    HR  : {len(hr_ref)} 样本 @ {fs_hr} Hz (Empatica 参考)")
    return bvp, int(fs_bvp), hr_ref, fs_hr


def bandpass(x, fs, lo, hi, order=4):
    """Butterworth 4 阶带通，0 相位失真 (filtfilt 双向滤波)。"""
    b, a = butter(order, [lo, hi], btype="band", fs=fs)
    return filtfilt(b, a, x)


def estimate_hr(window, fs):
    """对一个窗口做 FFT，在 0.5-4 Hz 内找最大峰，返回 BPM。"""
    w = window * np.hanning(len(window))
    spec = np.abs(np.fft.rfft(w, n=FFT_N)) ** 2
    freqs = np.fft.rfftfreq(FFT_N, d=1 / fs)
    mask = (freqs >= F_LOW) & (freqs <= F_HIGH)
    peak_freq = freqs[mask][np.argmax(spec[mask])]
    return peak_freq * 60.0  # Hz -> BPM


def run(subject: str):
    print(f"=== 被试 {subject} ===")
    bvp, fs, hr_ref, fs_hr = load_subject(subject)

    # STEP 2: 带通滤波
    print("[STEP 2] 带通滤波 0.5-4 Hz ...")
    filtered = bandpass(bvp, fs, F_LOW, F_HIGH)

    # STEP 3 + 5: 滑动窗口 + FFT
    print("[STEP 3+5] 滑动窗口 + FFT 找峰 ...")
    win = WIN_SEC * fs       # 512
    step = STEP_SEC * fs     # 128
    n_win = (len(filtered) - win) // step + 1
    hr_pred = np.array([
        estimate_hr(filtered[i * step : i * step + win], fs)
        for i in range(n_win)
    ])
    # 每个估计对应窗口中心相对开始的秒数
    t_pred = np.arange(n_win) * STEP_SEC + WIN_SEC / 2

    # 把 Empatica HR 重采样到同样的时间轴 (它从约 10s 开始, 1 Hz)
    t_ref = np.arange(len(hr_ref)) / fs_hr + 10.0
    hr_ref_aligned = np.interp(t_pred, t_ref, hr_ref,
                               left=np.nan, right=np.nan)

    # 评估 (排除 nan)
    valid = ~np.isnan(hr_ref_aligned)
    err = hr_pred[valid] - hr_ref_aligned[valid]
    mae = np.mean(np.abs(err))
    rmse = np.sqrt(np.mean(err ** 2))

    print(f"\n=== 结果 (vs Empatica 参考) ===")
    print(f"  窗口数            : {n_win}")
    print(f"  MAE               : {mae:6.2f} BPM")
    print(f"  RMSE              : {rmse:6.2f} BPM")
    print(f"  最大绝对误差      : {np.max(np.abs(err)):6.2f} BPM")
    print(f"  误差 < 5  BPM 占比 : {(np.abs(err) < 5).mean() * 100:5.1f} %")
    print(f"  误差 < 10 BPM 占比 : {(np.abs(err) < 10).mean() * 100:5.1f} %")

    # 画图
    t_min = t_pred / 60.0
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), sharex=True)

    axes[0].plot(t_min, hr_ref_aligned, "k-",
                 label="Empatica 参考", linewidth=1.5)
    axes[0].plot(t_min, hr_pred, "r-",
                 label="我们的 FFT 估计", linewidth=1.0, alpha=0.85)
    axes[0].set_ylabel("心率 (BPM)")
    axes[0].set_title(f"{subject} — 简单 FFT 基线 (vs Empatica, MAE = {mae:.2f} BPM)")
    axes[0].legend()
    axes[0].grid(alpha=0.3)

    axes[1].plot(t_min[valid], err, "b-", linewidth=0.8)
    axes[1].axhline(0, color="k", linewidth=0.5)
    axes[1].fill_between(t_min, -5, 5, alpha=0.15, color="green", label="±5 BPM")
    axes[1].set_xlabel("时间 (分钟)")
    axes[1].set_ylabel("误差 (BPM)")
    axes[1].legend()
    axes[1].grid(alpha=0.3)

    plt.tight_layout()
    out = Path(__file__).parent / f"hr_simple_{subject}.png"
    plt.savefig(out, dpi=110)
    print(f"\n  图已保存: {out.name}")
    plt.show()


if __name__ == "__main__":
    run(SUBJECT)
