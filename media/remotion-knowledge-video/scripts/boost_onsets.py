# -*- coding: utf-8 -*-
"""句首增强 v2：在每个发声起始点后 0.45s 内应用增益包络（+8dB 快速爬升后回落）。
用 ffmpeg 的 volume+adelay 双路混合法逐段处理。

原理：把音频拆成「每个句首区间的 boosted 版」太复杂。
改用 axfilter 不存在……最终方案：对整段音频应用多次「局部增益」，
用 volume=enable='between(t,a,b)' 多链叠加是不行的（enable 只能开关固定增益）。

真正可行：Python 读 PCM，自己加包络，写回。用 numpy + subprocess 管道。
"""
import subprocess, json, os, numpy as np, wave, io

BASE = os.path.dirname(os.path.abspath(__file__))
onsets = json.load(open(os.path.join(BASE, 'speech-onsets.json')))

def process(seg):
    src = os.path.join(BASE, f'{seg}.mp3')
    # 解码为 44.1k 单声道 float32 raw
    r = subprocess.run(['ffmpeg','-i',src,'-f','f32le','-ac','1','-ar','44100','-'],
                       capture_output=True)
    pcm = np.frombuffer(r.stdout, dtype=np.float32)
    sr = 44100

    # 每个句首 t0: 在 [t0, t0+0.45s] 应用增益包络 1.0→2.5(≈+8dB)→1.0
    env = np.ones_like(pcm)
    for t0 in onsets[seg]:
        i0 = int(t0 * sr)
        i1 = min(int((t0 + 0.45) * sr), len(pcm))
        n = i1 - i0
        if n <= 0:
            continue
        # 包络：0-80ms 线性升到峰值 2.5，80-450ms 余弦回落到 1.0
        rise = int(0.08 * sr)
        peak = 2.5
        if n <= rise:
            env[i0:i1] = np.maximum(env[i0:i1], np.linspace(1.0, peak, n))
        else:
            env[i0:i0+rise] = np.maximum(env[i0:i0+rise], np.linspace(1.0, peak, rise))
            fall_t = np.linspace(0, np.pi, n - rise)
            env[i0+rise:i1] = np.maximum(env[i0+rise:i1], 1.0 + (peak - 1.0) * (1 + np.cos(fall_t)) / 2)

    boosted = np.clip(pcm * env, -1.0, 1.0)

    # 写回 wav -> mp3（带 loudnorm 收尾）
    wav_path = os.path.join(BASE, f'{seg}-env.wav')
    # 用 ffmpeg raw 输入写 wav
    p = subprocess.run(['ffmpeg','-y','-f','f32le','-ac','1','-ar',str(sr),'-i','-',
                        '-c:a','pcm_s16le', wav_path],
                       input=boosted.tobytes(), capture_output=True)
    out = os.path.join(BASE, f'{seg}-strong.mp3')
    r2 = subprocess.run(['ffmpeg','-y','-i',wav_path,
                         '-af','loudnorm=I=-14:TP=-1.5:LRA=9','-b:a','192k', out],
                        capture_output=True, text=True)
    os.remove(wav_path)
    if r2.returncode != 0:
        print(seg, 'FAIL', r2.stderr[-200:])
        return False
    d = subprocess.run(['ffprobe','-v','error','-show_entries','format=duration',
                        '-of','default=nw=1:nk=1', out], capture_output=True, text=True)
    print(seg, 'ok', d.stdout.strip())
    return True

for seg in ['p1','p2','p3','p4','p5','p6','p7','p8']:
    process(seg)
print('ALL DONE')
