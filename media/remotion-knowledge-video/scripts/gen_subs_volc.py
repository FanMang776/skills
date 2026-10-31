# -*- coding: utf-8 -*-
"""volc 词表 → 字幕（专用版，替代 rebuild 的模糊对齐路线）

volc sentence.words 就是原文顺序（含标点），直接顺序映射；
每段整体偏移用「词表首词 t vs silencedetect 首个发声点」实测校正，
再逐条吸附到 ±0.3s 内最近的发声点。
"""
import bisect, json, math, os, re, subprocess, sys

FPS = 30
BREATH = 0.6
PUNCT = set("，。？！；：、—…·,.?!;:()（）\"'“”‘’ \t")

# 与 gen_tts_volc.py 保持一致
SEGS = [
    ("p1", 6.024), ("p2", 12.048), ("p3", 25.896), ("p4", 19.464),
    ("p5", 25.656), ("p6", 17.856), ("p7", 20.616), ("p8", 13.632),
]

def speech_chunks(text):
    pieces = re.split(r"([，。？！；：、—…]|\.{3})", text)
    lines, buf = [], ""
    for piece in pieces:
        if not piece:
            continue
        if PUNCT.issuperset(piece):
            if buf:
                lines.append(buf)
                buf = ""
            continue
        if buf and len(buf) + len(piece) > 20:
            lines.append(buf)
            buf = piece
        else:
            buf += piece
    if buf:
        lines.append(buf)
    return lines

def onsets(mp3):
    p = subprocess.run(["ffmpeg", "-i", mp3, "-af", "silencedetect=noise=-35dB:d=0.08", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(m.group(1)) for m in re.finditer(r"silence_end: ([\d.]+)", p.stderr)]

def probe(mp3):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                       capture_output=True, text=True)
    return float(p.stdout.strip())

def norm(s):
    return "".join(ch for ch in s if not PUNCT.issuperset(ch))

def fine_onsets(mp3, thresh_db=-40.0, win=0.02, step=0.01):
    """细粒度能量 onset：直接对 PCM，抓弱起音（silencedetect 会漏）"""
    import numpy as np
    r = subprocess.run(["ffmpeg", "-i", mp3, "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                       capture_output=True)
    pcm = np.frombuffer(r.stdout, dtype=np.float32)
    sr = 16000
    n = len(pcm) - int(win * sr)
    dB = np.full(n // int(step * sr) + 1, -120.0)
    for i in range(len(dB)):
        seg = pcm[i * int(step * sr): i * int(step * sr) + int(win * sr)]
        v = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0
        dB[i] = 20 * np.log10(v) if v > 0 else -120
    onsets, in_voice, last_end = [], False, -1e9
    for i, d in enumerate(dB):
        t = i * step
        if d > thresh_db and not in_voice:
            if t - last_end >= 0.1:
                onsets.append(t)
            in_voice = True
        elif d <= thresh_db and in_voice:
            in_voice = False
            last_end = t
    return onsets

def build_segment(seg_id, text):
    words = json.load(open(f"public/words-{seg_id}.json", encoding="utf-8"))
    mp3 = f"public/{seg_id}.mp3"
    fons = fine_onsets(mp3)
    # 实测整体偏移：词表首词 t vs 首个发声点
    first_t = words[0]["t"] if words else 0.0
    shift = (fons[0] - first_t) if fons else -first_t
    # 顺序映射：行内字符（去标点）依次消耗词表
    lines = speech_chunks(text)
    out = []
    wi = 0
    for ln in lines:
        need = norm(ln)
        got = []
        while wi < len(words) and len("".join(norm(g["w"]) for g in got)) < len(need):
            got.append(words[wi])
            wi += 1
        if not got:
            continue
        start = got[0]["t"] + shift
        end = got[-1]["t"] + shift + got[-1]["d"]
        # 细粒度吸附 ±0.6s 内最近发声点（校正长句累积漂移）
        if fons:
            cand = min(fons, key=lambda o: abs(o - start))
            if abs(cand - start) <= 0.6:
                start = cand
        out.append([max(0.0, start), end, ln])
    return out

def main():
    import numpy as np
    result, acc_frames = [], 0
    # 全片 PCM，用于行首能量闭环验收
    pcm_cache = {}
    def pcm_of(seg_id):
        if seg_id not in pcm_cache:
            r = subprocess.run(["ffmpeg", "-i", f"public/{seg_id}.mp3", "-f", "f32le", "-ac", "1", "-ar", "16000", "-"],
                               capture_output=True)
            pcm_cache[seg_id] = np.frombuffer(r.stdout, dtype=np.float32)
        return pcm_cache[seg_id]
    def rms_db_local(seg_id, t0, dur, sr=16000):
        pcm = pcm_of(seg_id)
        seg = pcm[int(t0 * sr):int((t0 + dur) * sr)]
        v = float(np.sqrt(np.mean(seg ** 2))) if len(seg) else 0
        return 20 * np.log10(v) if v > 0 else -120

    seg_text = dict(zip(["p1","p2","p3","p4","p5","p6","p7","p8"], json.load(open("segments.json", encoding="utf-8"))))
    for seg_id, dur in SEGS:
        text = seg_text[seg_id]
        subs = build_segment(seg_id, text)
        # 闭环：行首 0.3s 无声 → 整行后移 0.3s（不动行尾对齐）
        fixed = []
        for s, e, txt in subs:
            if rms_db_local(seg_id, s, 0.3) < -32 and rms_db_local(seg_id, s + 0.3, 0.3) >= -32:
                s += 0.3
            fixed.append([s, e, txt])
        subs = fixed
        offset = acc_frames / FPS
        for s, e, txt in subs:
            result.append({"start": round(offset + s, 3), "end": round(offset + e, 3), "text": txt})
        acc_frames += math.ceil((dur + BREATH) * FPS)
        bad = sum(1 for s, e, _ in subs if e - s < 0.4)
        print(f"[{seg_id}] {len(subs)} subs, 短行: {bad}")
    json.dump(result, open("src/subtitles.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成 {len(result)} 条，片尾 {acc_frames / FPS:.2f}s")

if __name__ == "__main__":
    main()
