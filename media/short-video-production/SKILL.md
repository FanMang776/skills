---
name: short-video-production
description: Use when making a short explainer video (口播稿→TTS→图卡→成片).
---

# Short Video Production (TTS + 程序化成片)

Making a knowledge-style short video from technical content without a real presenter. Pipeline: 口播稿 → edge-tts 配音 → 图卡/Manim 场景 → ffmpeg 合成. User is on Windows; paths under G:\HermesWorkspce.

## Standing user preferences

- **定位是「分享/介绍」，不是「教学」**: always attribute the original author up front (「作者是 X，就是那个…」); frame pain points as 「他的观点是」; end with 「这套方法对我启发很大，分享给你」 + source/link guidance (「链接放评论区」). Never frame as 「我教你」.
- **不录真人**: voice is TTS. User chose edge-tts `zh-CN-YunxiNeural` (活泼男声) at `--rate=+8%`; compare-sample voices before committing but this is the accepted default.
- **逐字稿必须给用户过目** before generating the final voiceover, and again after any wording change. Present it segmented by video section (钩子/痛点/招式/收尾) so the user can approve per-block.
- 中文交流；执行阶段直接做，不逐步确认。

## Procedure

### 1. 口播稿 (script)

Write the verbatim script segmented by section, each section with a time budget (~4.6 字/秒 measured on a real render; use ~5 字/秒 for estimates). For a 90-120s video: 3s hook → pain points → 3-4 招式 blocks ~15s each → 总结+关注引导.

Series continuation (EP2+): read the previous episode's script md and scene files FIRST — open by picking up the hook the previous ending planted, reuse its voice/定位/palette, and end pointing at the next episode's topic: name the concept but do NOT explain its mechanism (that is the next episode's content). Confirm series direction with the user before writing (which 招式 next, 机制拆解 vs 演示 mix), then write straight through without per-section check-ins.

TTS-writing rules (these cost a regeneration each if violated):
- Avoid mid-sentence English words where a Chinese phrase works naturally — the TTS engine switches pronunciation style and inserts a pause (reads "AI" as two halting English letters). Prefer 提示词/拷问会话/思考消耗 over prompt/Grilling/token when the audience is broad; keep an English term only if programmers genuinely say it that way, and flag those spots to the user for a listen-check.
- Do NOT substitute homophone characters to fake a pronunciation (writing 爱 for "AI") — ask the user first; this substitution was explicitly rejected. If the letter reading is unacceptable, the real fix is a different engine (火山/MiniMax/OpenAI TTS), not respelling.
- Proper nouns in Latin script ("Matt Pocock") trigger the same style switch; give the user a heads-up to listen to that spot.

Script-legibility rules for the user's review pass (they read the md line by line as spoken text):
- No meta/hype framing in the hook (「问得最多的」「评论区炸了」) unless it is true — the user edits such claims out. Prefer plain continuation phrasing (「接下来一条条拆，先拆最重要的第一招」).
- Define a mechanism in plain language FIRST, drop the coined term LAST (「前面不欠答案、现在就能答的那批问题——这批问题叫边界」), never term-first then a dense definition.
- Examples must be everyday and neutral (搬家选城市), not career/sensitive dilemmas (要不要辞职) — the latter derails the comment section.

### 2. 配音 (edge-tts)

Prefer the built-in `text_to_speech` tool; when it fails with "No audio was received" (it does, intermittently), fall through to the local CLI — same engine, more control:

```bash
python -m edge_tts --voice zh-CN-YunxiNeural --rate=+8% \
  --file script.txt --write-media out.mp3
# voices: zh-CN-YunxiNeural (活泼男声), zh-CN-XiaoxiaoNeural (温润女声),
#         zh-CN-YunyangNeural (新闻男声); en-US-AndrewMultilingualNeural reads
#         Chinese very naturally and handles English names natively, slight foreign accent
```

- Check duration with `ffprobe -v quiet -show_entries format=duration -of csv=p=0 out.mp3`. 90s script ≈ 100-120s at +8%; trim the script if over budget.

**edge-tts 403 「Invalid response status」——微软后端迁移，必须改常量（2026-10 起）**: Microsoft migrated Edge Read Aloud from `speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1` to `api.msedgeservices.com/tts/cognitiveservices/websocket/v1`. All edge-tts versions (incl. 7.2.8) 403 on the old host from every region, while `voices/list` still returns 200 — so a 403 here is NOT your network/IP/version, do not waste time on proxies or clock skew. Fix = edit `edge_tts/constants.py` in EVERY install (the `python -m edge_tts` one and the `edge-tts` CLI venv; `pip install -U` overwrites it):

```python
BASE_URL = "api.msedgeservices.com/tts/cognitiveservices"
WSS_URL = f"wss://{BASE_URL}/websocket/v1?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
VOICE_LIST = f"https://{BASE_URL}/voices/list?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
# keep CHROMIUM_FULL_VERSION unchanged -> Sec-MS-GEC-Version stays "1-143.0.3650.75" (the legacy
# token value is still accepted on the new host; the v2 token algorithm is unknown/unreleased)
```

`grep -rl 'speech.platform.bing.com' .../site-packages/edge_tts/constants.py` finds the installs; back up with `.orig-bak`. To verify a handshake without a full synthesis, open the WS with `Ocp-Apim-Subscription-Key` + `Sec-MS-GEC` (`DRM.generate_sec_ms_gec()`) + `Sec-MS-GEC-Version=1-143.0.3650.75` + `ConnectionId` and expect **101** (the server then idles waiting for your first config frame, so a read timeout is success, not failure).

**429 on the new host**: it rate-limits aggressively — one segment per ~10s, and wrap each segment in a retry loop (6-8 attempts, backoff 10-60s). A 429 then a success on retry is normal; only fail the run after the attempts are exhausted.

- For voice choice, generate ONE short sample line per candidate voice (same text), send all as MEDIA, let the user pick. zh-CN voices on edge-tts: Xiaoxiao/Xiaoyi (女), Yunxi/Yunjian/Yunyang/Yunxia (男), liaoning-Xiaobei, shaanxi-Xiaoni.
- Working files: `epN-final-vK.txt` (TTS input) and `epN-final-yunxi-vK.mp3`; when approved, copy to `epN-FINAL.mp3` and move trials to `archive/`.

### 3. 图卡 (static cards, optional intermediate step)

720×1280 HTML (9:16), dark GitHub style, one card per script section, wording VERBATIM from the approved script (cards and voiceover must not drift). Deliver in chat via `::preview{file="cards.html"}`. Static cards alone read as "念 PPT" — for anything beyond a draft, go to step 4.

### 4. 成片 (programmatic video — user's preferred direction)

User chose a code-generated pipeline (Manim scenes → ffmpeg) over HTML screen-recording, modeled on the 三体-style pipeline: 画面是代码生成的，可复现，改一个场景只重渲那一个.

- Environment: `pip install manim` (0.21.0 works), ffmpeg full build present. Full Manim craft rules live in the `manim-video` skill — load it before writing scenes.
- Chinese text in Manim: `Text(..., font="Microsoft YaHei")`, never LaTeX/MathTex for Chinese.
- Scene durations are derived from the voiceover, not chosen: split `epN-FINAL.mp3` at silence gaps (`ffmpeg silencedetect`), map each segment to a Scene, render scenes to match. 消灭长静音.
- Style: carry the card palette (#0d1117 background, blue/violet accents) into Manim — user's videos should not look like a 3B1B math lecture unless asked.
- Compose: render scenes at `-ql` for iteration, `-qh` only for final; `ffmpeg -f concat` the clips, mux the voiceover, burn an srt generated from the segmented script, output 1080x1920.
- De-risk: build ONE scene (the hook, ~15s) end-to-end including audio mux as a 样片 for user approval before rendering the rest.

### 5. 交付清单

A finished episode leaves behind: `epN-FINAL.mp3`, TTS input txt, segmented 逐字稿 md, cards.html, final mp4. Name trial renders with `-draft`/version suffixes so the FINAL name is unambiguous.