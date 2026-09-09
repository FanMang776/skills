---
name: douyin-video-transcript
description: Use when a Douyin link needs its transcript extracted
version: 1.0.0
author: Hermes Agent (curator)
platforms: [windows]
metadata:
  hermes:
    tags: [douyin, video, transcript, stt, ingestion]
    category: media
---

# Douyin 视频文案/转写提取

从抖音分享链接拿到视频元数据（标题/文案/作者/数据）和口播全文（本地 STT）。在 Windows 无 Chrome 机器上验证过（2026-09-07）。

## 前置检查

- `playwright` 已装（venv：`uv pip install --python <venv>/python.exe playwright`，首次还需 `python -m playwright install msedge`）
- `faster_whisper` 可 import；`ffmpeg` 在 PATH 或已知绝对路径（本机：`F:/Software/ffmpeg/ffmpeg-8.1.2-full_build/bin/ffmpeg.exe`）
- **无 Chrome 时不要用 browser_exec/browser-harness**：它会尝试系统方式打开 `chrome://inspect` 触发授权流程，而 chrome:// 协议关联坏了会弹 Windows「没有应用可打开此链接」死循环。直接用 Playwright `channel="msedge"`。

## 流程

### 1. 解析短链拿视频 ID

```bash
curl -sL -o /dev/null -w "%{url_effective}\n" "https://v.douyin.com/XXXXXX/" -A "Mozilla/5.0 (iPhone)"
# 重定向 URL 里的 /video/<ID>/ 即视频 ID
```

### 2. Playwright(headless Edge) 打开视频页，拦截 aweme detail XHR

XHR `aweme/v1/web/aweme/detail/` 的响应 JSON 里有全部元数据，比解析 DOM 稳：

```python
from playwright.async_api import async_playwright
captured = []
async def on_resp(resp):
    if "aweme" in resp.url and "detail" in resp.url.lower():
        captured.append(await resp.text())
# launch(channel="msedge", headless=True, args=["--disable-blink-features=AutomationControlled"])
# context: zh-CN locale + Edge UA；goto www.douyin.com/video/<ID>，wait_for_timeout(10000)
```

从 `aweme_detail` 取：`desc`（标题+话题标签，即全部文案）、`author.nickname`、`create_time`（unix 秒）、`duration`（ms）、`statistics`（digg/comment/share/collect_count）、`video.play_addr.url_list[0]`（无水印播放地址）。

**没有字幕轨**（`cla_info`/`seo_info` 为空）——要口播全文必须自己下载视频跑 STT。

备选：iesdouyin.com 分享页 SSR 数据里没有视频内容（只有 UA/query 等页面配置），不用试；www.douyin.com 对裸 curl 只回一个 JS-vm 壳页，也拿不到 RENDER_DATA。

### 3. 下载视频 + 抽音轨

```bash
curl -sL <play_url> -o dy_video.mp4 --max-time 120 -H "Referer: https://www.douyin.com/" -A "Mozilla/5.0"
ffmpeg -y -i dy_video.mp4 -vn -ar 16000 -ac 1 -b:a 48k dy_audio.wav
```

### 4. faster-whisper 转写 —— 必须后台 terminal 跑

**坑**：execute_code 300s 超时会杀 kernel；CPU 上 small 模型转 4:45 音频 300s 跑不完直接超时。
正确姿势：写脚本文件 → `terminal(background=true, notify=true)` 跑，`sleep`/轮询等结果文件。

```python
# dy_stt.py
from faster_whisper import WhisperModel
model = WhisperModel("base", device="cpu", compute_type="int8")
segments, info = model.transcribe("dy_audio.wav", language="zh", vad_filter=True, beam_size=1)
# base+int8+beam_size=1：4:45 音频约 14s 出 152 段（首次含模型下载 ~6min，之后秒级到分钟级）
```

带时间轴输出 `[m:ss] text`，便于整理成带章节的文稿。

### 5. 整理进 wiki（Karpathy LLM wiki 约定）

- 转写是**听写稿**：base 模型中文错字不少（"纯过日子"→"纯锅日子"、homophone 大量混用）。整理时逐句修正明显同音错字，删口语冗余，保留时间轴分节；在文稿头部注明「听写整理+错字修正」。
- **源页必须同时存原始转写稿**：用户要求「转写存原文，再摄入」——整理版（Full Text）之外，追加一节 `## 原始转写稿（faster-whisper base，未修饰）`，带时间轴原样放入，两版并置。这是 sources/ 不可编辑原则下的溯源要求：修饰稿是解读，原始听写稿才是原文。
- 源页 frontmatter：`source_format: video-transcript`、`sha256`（对转写正文算，惯例同其他 raw 源）、`source_url` 写短链+视频 ID+账号+发布日期+时长。
- 视频统计数据（赞/评/转/藏）注明「截至摄入日」，是溯源锚点的一部分。
- 与库主题无关的视频明说「作为情绪/社会样本存档」，找同类型既有源页互链，别硬扯关联。

## 已验证的坑（2026-09-09 二轮摄入）

- **execute_code 里绝不用 hermes read_file 的返回值写文件**：read_file 返回带 `N|N|` 行号前缀的内容，整段写回会污染文件；且它有去重缓存（`status: unchanged, content_returned: False`，dict 里没有 content 键）。vault 文件操作一律 `open()` 原生读写。
- 大批量 frontmatter 编辑后**必须 `git diff` 逐文件核对**，确认 diff 只含预期行；误改的无关文件用 `git checkout -- <file>` 还原。
- 央视网这类稿子专有名词错字有规律：「生疼」=昇腾/CloudMatrix、「大摩行」=大语言模型、「項量/舉證」=向量/矩阵、「平景」=瓶颈、「機會/積貴/機貴」=机柜、「服氣」=服务器、「零曲/领取」=灵衢。整理时在 Full Text 头部注明修正对照。
- 摄入收尾要跑 vault 本地的 `.claude/skills/maintaining-llm-wiki/scripts/patch_index_queries.py`（queries/ 不被插件索引的补丁），见 obsidian-llm-wiki-plugin skill。

## 相关

- 摄入后收尾（断链扫描/git/Regenerate index）见 note-taking/obsidian-llm-wiki-plugin skill。
- 微信公众号文章抓取不需要浏览器：curl 直接拿 HTML，解析 `#js_content`、`var msg_title`、`var createTime`、`id="js_name"`（web_extract 对 mp.weixin.qq.com 会误报 private network 拦截）。
