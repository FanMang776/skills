# -*- coding: utf-8 -*-
"""edge-tts 词级时间戳字幕生成（SKILL.md 5a 节参考实现）

含两个踩实修复：
1. 字幕行与词表用「归一化后 SequenceMatcher 模糊单调对齐」，
   不用字符数精确消耗——KIP-1150 / S3 / Aiven 这类 token 书写长度≠发音长度
   （连字符不发音、英文按字母读），精确计数一处错位后面全歪。
2. 对齐结果必须把「W 字符流位置」反查成「词序号」再取时间——
   中文单字词让两者恰好重合，多字词/数字/英文一累积就劈。

用法：
  python gen_subs_edgetts.py           # 合成 TTS + 生成字幕（词表落盘 words-<seg>.json）
  python gen_subs_edgetts.py rebuild   # 用存档词表重建字幕（改切分/对齐不重合成）

依赖: edge-tts(403 补丁见 SKILL.md 3 节), ffmpeg/ffprobe
产出: subtitles.json + words-<seg>.json + 各段 mp3
"""
import asyncio
import bisect
import json
import math
import os
import re
import subprocess
import sys
import time
from difflib import SequenceMatcher

import edge_tts

# ---------- 配置：换成你的稿子 ----------
VOICE = "zh-CN-YunxiNeural"
RATE = "+8%"
FPS = 30
BREATH = 0.6  # 每段收尾呼吸(秒)
SEGMENTS = [
    # ("p1", "第一段旁白文本……"),
]
# ----------------------------------------

BASE = os.path.dirname(os.path.abspath(__file__))
PUNCT = set("，。？！；：、—…·,.?!;:()（）\"'“”‘’ \t")


def speech_chunks(text):
    """把文本切成字幕行：按标点切句，聚合到每行不超过 ~20 个语音字符。"""
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


def align_lines_to_words(lines, words):
    """模糊单调对齐（修复版，见模块 docstring 的两个坑）。"""
    norm = lambda s: "".join(ch.lower() for ch in s if ch.isalnum())
    S = ""
    line_ranges = []
    for ln in lines:
        n = norm(ln)
        line_ranges.append((len(S), len(S) + len(n)))
        S += n
    wn = [norm(w["w"]) for w in words]
    W = "".join(wn)
    word_start_pos = []  # 每个词在 W 字符流里的起始位置
    p = 0
    for s_ in wn:
        word_start_pos.append(p)
        p += len(s_)
    sm = SequenceMatcher(None, S, W, autojunk=False)
    anchors = []  # (S 位置, W 位置)
    for i1, j1, n in sm.get_matching_blocks():
        if n == 0:
            continue
        for k in range(n):
            anchors.append((i1 + k, j1 + k))
    if not anchors:
        # 完全对不上（不该发生）：退化为按语音字符比例均分
        total_t = words[-1]["t"] + words[-1]["d"] if words else 0.0
        total_n = len(S) or 1
        acc = 0.0
        out = []
        for (s0, s1), ln in zip(line_ranges, lines):
            out.append([acc, total_t * s1 / total_n, ln])
            acc = total_t * s1 / total_n
        return out
    a_s = [a[0] for a in anchors]

    def map_pos(i):
        idx = bisect.bisect_left(a_s, i)
        if idx < len(anchors) and anchors[idx][0] == i:
            return anchors[idx][1]
        if idx == 0:
            return anchors[0][1]
        if idx >= len(anchors):
            return anchors[-1][1]
        s_a, w_a = anchors[idx - 1]
        s_b, w_b = anchors[idx]
        frac = (i - s_a) / (s_b - s_a)
        return w_a + (w_b - w_a) * frac

    out = []
    for (s0, s1), ln in zip(line_ranges, lines):
        w_start = map_pos(s0)
        w_end = map_pos(s1)

        def widx(wp):  # W 字符位置 -> 词序号（多字词会让两者错开，必须反查）
            return max(0, min(len(words) - 1, bisect.bisect_right(word_start_pos, wp) - 1))

        i0 = widx(w_start)
        i_last = max(i0, widx(max(w_start, w_end - 1e-6)))
        start = words[i0]["t"]
        end = words[i_last]["t"] + words[i_last]["d"]
        out.append([start, end, ln])
    return out


def synth(seg_id, text):
    async def run():
        cm = edge_tts.Communicate(text, VOICE, rate=RATE, boundary="WordBoundary")
        audio, words = bytearray(), []
        async for chunk in cm.stream():
            if chunk["type"] == "audio":
                audio += chunk["data"]
            elif chunk["type"] == "WordBoundary":
                words.append({"t": chunk["offset"] / 1e7, "d": chunk["duration"] / 1e7, "w": chunk["text"]})
        path = f"{seg_id}.mp3"
        open(path, "wb").write(bytes(audio))
        json.dump(words, open(f"words-{seg_id}.json", "w", encoding="utf-8"), ensure_ascii=False)
        return path, words

    return asyncio.run(run())


def onsets(mp3):
    p = subprocess.run(["ffmpeg", "-i", mp3, "-af", "silencedetect=noise=-42dB:d=0.08", "-f", "null", "-"],
                       capture_output=True, text=True)
    return [float(m.group(1)) for m in re.finditer(r"silence_end: ([\d.]+)", p.stderr)]


def probe(mp3):
    p = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", mp3],
                       capture_output=True, text=True)
    return float(p.stdout.strip())


def build_segment_subs(seg_id, text, words, mp3):
    """词表 -> 字幕行时间：平移修正 + 模糊对齐 + 发声点吸附。"""
    ons = onsets(mp3)
    shift = (ons[0] - words[0]["t"]) if ons else 0.0
    shifted = [{**w, "t": w["t"] + shift} for w in words]
    subs = align_lines_to_words(speech_chunks(text), shifted)
    snapped = []
    for s, e, txt in subs:
        if ons:
            cand = min(ons, key=lambda o: abs(o - s))
            if abs(cand - s) <= 0.3:
                s = cand
        snapped.append([max(0.0, s), e, txt])
    return snapped


def main(rebuild=False):
    out, scene_start_frames = [], 0
    for seg_id, text in SEGMENTS:
        mp3 = f"{seg_id}.mp3"
        if rebuild:
            words = json.load(open(f"words-{seg_id}.json", encoding="utf-8"))
            assert os.path.exists(mp3), f"{mp3} 不存在，rebuild 需要先跑过一次完整合成"
        else:
            for attempt in range(8):
                try:
                    mp3, words = synth(seg_id, text)
                    if not words:
                        raise RuntimeError("no WordBoundary events")
                    break
                except Exception as e:
                    wait = min(10 + attempt * 10, 60)
                    print(f"[{seg_id}] attempt {attempt + 1} failed: {e}; retry in {wait}s", flush=True)
                    time.sleep(wait)
            else:
                sys.exit(f"[{seg_id}] TTS failed after retries")
            time.sleep(8)  # 新主机限流保护

        snapped = build_segment_subs(seg_id, text, words, mp3)
        offset = scene_start_frames / FPS
        for s, e, txt in snapped:
            out.append({"start": round(offset + s, 3), "end": round(offset + e, 3), "text": txt})
        scene_start_frames += math.ceil((probe(mp3) + BREATH) * FPS)

        bad = [s for s in snapped if s[1] - s[0] < 0.4]
        print(f"[{seg_id}] {len(snapped)} subs, 短行(<0.4s): {len(bad)}")
        json.dump(out, open("subtitles.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"完成：{len(out)} 条字幕，片尾 {scene_start_frames / FPS:.2f}s")


if __name__ == "__main__":
    main(rebuild=len(sys.argv) > 1 and sys.argv[1] == "rebuild")
