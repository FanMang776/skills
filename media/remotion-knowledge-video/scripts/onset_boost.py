# -*- coding: utf-8 -*-
"""句首弱音自适应归一化（SKILL.md 第 7 节实现，固定增益方案已淘汰）

流程：细粒度 onset 检测(-42dB) → 每处实测首 0.2s RMS 独立定增益(目标 -16dB, 上限 x5)
→ 包络(10ms 攻/200ms hold/300ms 余弦回落) → 两遍迭代 → 段级 loudnorm 锁时长
→ 闭环验收(任何 onset 首 0.2s < -19dB 即 FAIL 退出)

用法: python onset_boost.py <in.mp4> <out.mp4>
"""
import subprocess, sys, os, re
import numpy as np

SR = 48000
TARGET_DB = -16.0
FAIL_DB = -19.0
MAX_GAIN = 5.0

def decode(path):
    r = subprocess.run(['ffmpeg', '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                       capture_output=True)
    return np.frombuffer(r.stdout, dtype=np.float32)

def rms_db(x):
    if len(x) == 0:
        return -120.0
    v = float(np.sqrt(np.mean(x ** 2)))
    return 20 * np.log10(v) if v > 0 else -120.0

def detect_onsets(pcm, win=0.02, step=0.01, thresh=-42.0, silent_before=0.15, adaptive=False):
    nWin, nStep = int(win * SR), int(step * SR)
    dB = np.array([rms_db(pcm[i:i + nWin]) for i in range(0, max(1, len(pcm) - nWin), nStep)])
    if adaptive:
        # 底噪自适应：响度处理后底噪被抬高，绝对阈值会失效（EP2 踩坑）
        thresh = float(np.percentile(dB, 10)) + 10.0
    onsets, last_voice_end = [], -1e9
    in_voice = False
    for i, d in enumerate(dB):
        t = i * step
        if d > thresh and not in_voice:
            if t - last_voice_end >= silent_before:
                onsets.append(t)
            in_voice = True
        elif d <= thresh and in_voice:
            in_voice = False
            last_voice_end = t
    return onsets

def apply_boost(pcm, onsets_with_gain):
    env = np.ones_like(pcm)
    a, hold, fall = int(0.01 * SR), int(0.20 * SR), int(0.30 * SR)
    for t0, g in onsets_with_gain:
        i0 = int(t0 * SR)
        i1 = min(i0 + a + hold + fall, len(pcm))
        if i0 >= len(pcm):
            continue
        seg = np.ones(i1 - i0)
        na = min(a, len(seg))
        seg[:na] = np.linspace(1.0, g, na)
        if len(seg) > na:
            nh = min(hold, len(seg) - na)
            seg[na:na + nh] = g
            nf = len(seg) - na - nh
            if nf > 0:
                seg[na + nh:] = g + (1.0 - g) * (1 - np.cos(np.linspace(0, np.pi, nf))) / 2
        env[i0:i1] = np.maximum(env[i0:i1], seg)
    return np.clip(pcm * env, -1.0, 1.0)

def plan_gains(pcm, onsets):
    plan = []
    span = int(0.51 * SR)
    for t0 in onsets:
        i0 = int(t0 * SR)
        seg = pcm[i0:i0 + int(0.2 * SR)]
        cur = rms_db(seg)
        g = min(MAX_GAIN, 10 ** ((TARGET_DB - cur) / 20))
        # 包络全窗(attack+hold+release)峰值约束：任何增益下 pcm*env 不得超 0.85，杜绝硬削波
        win = pcm[i0:min(i0 + span, len(pcm))]
        pk = float(np.abs(win).max()) if len(win) else 0.0
        if pk > 0:
            g = min(g, 0.85 / pk)
        if g > 1.05:
            plan.append((t0, g))
    return plan

def encode(pcm, path, dur_samples):
    p = subprocess.run(['ffmpeg', '-y', '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-i', '-',
                        '-af', f'loudnorm=I=-14:TP=-1.5:LRA=9,aresample={SR},apad,atrim=end_sample={dur_samples}',
                        '-ar', str(SR), '-c:a', 'pcm_s16le', path],
                       input=pcm.tobytes(), capture_output=True)
    if p.returncode != 0:
        sys.exit(f'encode failed: {p.stderr.decode(errors="replace")[-400:]}')

def verify(path, orig_dur, ref_onsets=None):
    pcm = decode(path)
    if ref_onsets is None:
        ons = detect_onsets(pcm, adaptive=True)
    else:
        ons = ref_onsets  # 响度处理不改时间轴，用源音频的真实语音 onset 位置
    worst = min((rms_db(pcm[int(t * SR):int(t * SR) + int(0.2 * SR)]) for t in ons), default=-16.0)
    return pcm, ons, worst

def main():
    src, dst = sys.argv[1], sys.argv[2]
    pcm = decode(src)
    dur_samples = len(pcm)
    print(f'decoded {dur_samples/SR:.2f}s')

    src_onsets = detect_onsets(pcm)  # 源音频真实语音 onset（绝对阈值，源上有效）
    for pass_no in (1, 2):
        ons = src_onsets
        plan = plan_gains(pcm, ons)
        print(f'pass{pass_no}: {len(ons)} onsets, {len(plan)} need boost')
        if not plan:
            break
        pcm = apply_boost(pcm, plan)

    tmp_wav = dst + '.tmp.wav'
    encode(pcm, tmp_wav, dur_samples)
    pcm2, ons2, worst = verify(tmp_wav, dur_samples / SR, ref_onsets=src_onsets)
    print(f'closed-loop: {len(ons2)} onsets, weakest onset = {worst:.1f} dB')
    if worst < FAIL_DB:
        sys.exit(f'FAIL: weakest onset {worst:.1f} dB < {FAIL_DB} dB — rerun needed')

    # mux 回视频（视频流 copy）
    p = subprocess.run(['ffmpeg', '-y', '-i', src, '-i', tmp_wav,
                        '-map', '0:v:0', '-map', '1:a:0',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart', dst],
                       capture_output=True)
    os.remove(tmp_wav)
    if p.returncode != 0:
        sys.exit(f'mux failed: {p.stderr.decode(errors="replace")[-400:]}')
    q = subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', dst],
                       capture_output=True, text=True)
    print(f'OK -> {dst}  duration={q.stdout.strip()}s')

if __name__ == '__main__':
    main()
