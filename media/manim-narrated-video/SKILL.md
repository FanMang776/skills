---
name: manim-narrated-video
description: Use when making Manim+edge-tts narrated videos with subtitles.
version: 2.0.0
author: Ch Jiang (FanMang776), Hermes Agent
license: MIT
platforms: [windows]
metadata:
  hermes:
    tags: [manim, edge-tts, video, narration, subtitles, chinese]
    category: media
---

# Manim + edge-tts 旁白视频完整制作流程

从文案定稿到成片审核收工的完整流水线：Manim 卡片动画 + edge-tts 中文旁白 + 逐字硬字幕，产出 1080p60 成片。已在 Windows 实践验证（知识科普系列 5 集，累计 11 分钟成片）。

## When to Use

- 制作"口播讲解 + 卡片动画"类知识视频（方法论拆解、科普、教程）
- 已有文案或需要从素材整理文案，需要配音、字幕、渲染全流程
- Don't use for: 实拍剪辑、纯字幕组（无配音生成需求）、需要出镜真人口播的视频

## Prerequisites

- **Python 3.13 + manim 0.21+**：本机常与默认 python（3.14）共存，manim 装在特定版本——先 `python -c "import manim"` 确认，找不到就换 `C:/Python313/python.exe` 显式调用
- **edge-tts**：`pip install edge-tts`，无需 API key
- **ffmpeg/ffprobe** 在 PATH（裁剪、拼接、抽帧、音量检测全靠它）
- **字体**：中文用 Microsoft YaHei（Windows 自带），代码用 Consolas
- 无 LaTeX 也可跑：全部用 `Text()`，禁 MathTex/DecimalNumber

## 工作流总览

```
文案定稿 → 配音生成(带词级时间戳) → 字幕cue推导 → 分镜场景代码
→ 草稿渲染+帧检 → 1080p60渲染 → 裁剪拼接 → 成片验收(含字幕全量审计)
```

## Step 1 — 文案定稿

- 按"痛点钩子 → 机制拆解 → 生活化类比 → 现场演示 → 结尾预告"结构组织
- 每段一个场景；总字数按实测语速折算时长（见 Step 2 语速表），先估算再定稿
- **完稿后冻结文本**：配音、字幕、场景代码全部以这份文本为唯一事实源。后续任何文字改动都必须重新走配音→字幕→渲染

## Step 2 — 配音生成（必须同次拿词级时间戳）

```python
import asyncio, edge_tts, json

comm = edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+10%",
                            boundary="WordBoundary")   # 显式传，默认是 SentenceBoundary
async for chunk in comm.stream():
    if chunk["type"] == "audio":
        f.write(chunk["data"])                          # mp3 分段文件
    elif chunk["type"] == "WordBoundary":
        words.append({"t": chunk["offset"]/1e7,         # 100ns → 秒
                      "d": chunk["duration"]/1e7,
                      "w": chunk["text"]})              # 词文本不含标点
```

**铁律（每条都是踩过的坑）：**

- 字幕时间点**只能用 TTS 引擎报的边界时间**，禁止 silencedetect 静音段估算——句间长停顿会让估算偏早 1.5~4 秒
- 优先 WordBoundary 而非 SentenceBoundary：句中拆分字幕、长句切多条都能锚到真实发声点
- WordBoundary 的词文本不含标点：把词流与原稿做"非标点字符数"对齐，在原稿的句号/问号处断句
- `offset` 单位是 100ns；首词自带约 0.1s 引擎前置
- **同一文本重新生成会得到新的配音**——音频、词边界、字幕 cue 必须同批次，绝不能新音频配旧 cue
- 语速档实测：-8%≈3.5字/秒，+10%≈4.9字/秒，+20%≈5.3字/秒。定字数前先试听实测

## Step 3 — 字幕 cue 推导

从词流生成字幕行，规则：

1. 在原稿的句号/问号/叹号处断句（把词流按非标点字符数对齐回原稿定位）
2. 超过 ~23 个中文字的行在最近的逗号/破折号处二分拆成两条，第二条 cue = 该段首词的真实发声时间
3. 展示文本：去句尾标点，句内标点替换为空格
4. 输出 `SEG_SUBS = {场景: [(cue秒, "字幕文本"), ...]}` 数据结构

已知边界：voice 里若含中英混排数字（如"10块"），WordBoundary 会拆成"10"+"块"，字符对齐时按原稿字符数走即可。

## Step 4 — Manim 场景代码

**架构（防同步漂移的关键设计）：**

- 每场景一段配音 mp3；`SegScene` 基类提供：
  - `audio_for(name)`：**add_sound 挂载配音 + 返回时长**（两件事必须绑在一起——只取时长忘挂音轨 = 无声视频，见 Pitfalls）
  - `subs_until(subs, t_target, state)`：字幕数据驱动推进。场景代码只写动画节拍点（`subs_until(subs, 12.1, st)`），字幕在节拍内按 cue 自动切换。**禁止手工排 `wait_sub(subs[i])` 索引序列**——cue 增删后索引必然错位
  - `finish(dur)`：结尾 `wait_to(dur + 0.25)` 补齐帧数取整损耗
- `SUB_DELAY = 0.3`（字幕统一延后量，仅抵消淡入）：锚点本身是准的，不需要补偿性加大
- **动画节拍给字幕让路**：场景排完后逐 cue 检查"该时刻前的动画累计时长 ≤ cue+SUB_DELAY"，超了就压前面动画的 run_time
- 场景内不要用裸 `wait_to(常量)` 锚定节拍；cue 改了常量会静默失效

**视觉与渲染约束：**

- `config.background_color = "#F5F6F8"` 显式设白底（Manim 默认黑底，深色标题会隐形）
- 中文 `font="Microsoft YaHei"`；**禁用 emoji**（YaHei 无字形，渲染成十六进制方块）
- `subtitle()` 内置超宽缩放：文本宽超 13.4 单位自动等比缩到框内
- 卡片组件化：`mini_card` / `big_card`（标题+注释行）/ `tag`（左上角徽章），新场景先复用再新造

## Step 5 — 草稿渲染 + 帧检

```
python -m manim -ql script.py <全部场景>
```

- 每场景抽 2 帧（35%、75% 处）视觉检查：文字重叠、越界、字幕完整、卡片布局
- 逐 cue 推演时间轴：任一 cue 前的动画累计时长超拍，压 run_time 修复
- 全部通过才进正式渲染

## Step 6 — 1080p60 正式渲染 + 裁剪拼接

```
python -m manim -qh --fps 60 script.py <全部场景>
# 每场景裁齐到音频时长（视频比音频长零点几秒是帧取整）：
ffmpeg -i S1.mp4 -t <音频时长> -c:v copy -c:a aac -shortest trimmed/S1.mp4
# 拼接：
ffmpeg -f concat -safe 0 -i concat.txt -c copy final.mp4
```

- 裁剪后逐场景验证 `stream=codec_type` 含 video+audio 双流
- concat 前确认每段流 start_time=0

## Step 7 — 成片验收（收工标准）

1. **音轨**：`volumedetect` 看峰值（正常 -5dB 左右）；最终产物必须含 audio 流
2. **字幕全量审计**（必须做，抽样会漏）：
   - 按每场景音频时长累计算出各场景在成片中的起始时间
   - 对每条字幕：在 `场景起始 + cue + 1.2s` 处抽帧（+0.45s 会撞上淡入中间态）
   - 视觉读出帧内字幕文字，与该 cue 的预期文本比对——**全绿才算收工**
   - 若某帧显示上一条字幕：先在 cue+2.5s 复核排除切换延迟，确认真拖后才修
3. **规格**：1080p60、音视频双流、时长 = 各段音频之和

## Pitfalls

- **静音段估算字幕时间**：偏早 1.5~4 秒（EP3 连环返工根因）。永远用引擎边界时间
- **只取时长不挂音轨**：`seg()` 和 `add_sound` 必须封装成一个 `audio_for()`，拆开就会忘
- **手工字幕索引**：cue 列表一变，`subs[3]` 到 `subs[9]` 的手工序列全错且无声
- **emoji**：渲染成十六进制方块，卡片文案用纯文字
- **默认 python 没有 manim**：多版本共存机器上先确认解释器路径
- **新音频配旧 cue**：重新生成配音后必须重算全部 cue
- **压缩改写字幕**：观众听到字幕里没有的词就是"缺文字"，字幕逐字对应口播

## Verification

- [ ] 每场景 mp4 含 video+audio 双流，`.wav` 中间产物存在
- [ ] 成片含 audio 流，volumedetect 峰值 -5dB 左右
- [ ] 全部字幕行（不是抽样）通过 cue+1.2s 抽帧比对
- [ ] 成片时长 = 各段配音时长之和（±0.5s）
- [ ] 草稿帧检记录在案：无文字重叠/越界/乱码方块
