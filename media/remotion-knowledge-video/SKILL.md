---
name: remotion-knowledge-video
description: Use when 把技术方法论/教程做成带动画的抖音/小红书竖屏视频：TTS 分段→Remotion 分层合成→whisper 字幕对齐→响度修复→渲染交付。全流程代码化，改稿秒重渲。
version: 1.0.0
author: cj (FanMang776)
license: MIT
platforms: [any]
requires: [node>=18, ffmpeg, python+pip(edge-tts, faster-whisper, numpy), Remotion(npx create-video)]
---

# Remotion 知识类竖屏视频管线

把一篇技术方法论做成画面丰富的竖屏视频（1080×1920@30fps）。核心经验：**画面丰富 = 四层结构叠加**（粒子/bokeh 背景 + 拟真 UI 界面 + 动效字卡 + 图表动画），拒绝单调图卡风；**声画同步 = 不估算，全用实测**（TTS 时长驱动场景、whisper 字级时间戳驱动字幕、能量曲线校准边界）。

## 管线总览

```
逐字稿(8段/带时间轴) → TTS分段(mp3+实测时长) → Remotion场景(时长驱动) 
→ 渲染 → whisper字级对齐生成字幕 → 能量曲线校准字幕边界 → 句首增强 → 交付
```

## 1. 前期：环境（Windows 实测坑）

- 系统代理是注册表 IE 代理（如 127.0.0.1:7897），env 无变量。Remotion 下载 headless Chrome 会直连 storage.googleapis.com 然后 ECONNRESET/超时。**解法：手动 curl 走代理下载 chrome-for-testing 的 zip，解压后用 `REMOTION_CHROME_EXECUTABLE=<路径>` 指向本地 chrome-headless-shell.exe**，浏览器目录留好复用，永不再下。
- TS 报 `Cannot find module './xxx'` 先查相对路径层级（compositions/ 子目录里要用 `../`），别怀疑编码。
- 渲染命令模板：
  ```bash
  REMOTION_CHROME_EXECUTABLE=<chrome路径> npx remotion render <CompId> out/xxx.mp4
  ```

## 2. 逐字稿规矩（沿用 douyin-video-production skill）

5 字/秒估时长；0-6s 钩子；痛点开场干货收尾；每段标注画面提示与可截图字幕；**比喻先行术语殿后**。分段编号 P1..Pn，TTS 与 Remotion 场景一一对应。

## 3. TTS 分段

```python
import edge_tts
cm = edge_tts.Communicate(text, "zh-CN-YunxiNeural", rate="+8%")  # voice 必须全名
await cm.save(f"{seg}.mp3")
# 立刻 ffprobe 实测每段时长 -> tts-durations.json（估算不可信）
```

**403「Invalid response status」≠ 网络问题（2026-10 起必踩）**：微软把 Edge 朗读后端从 `speech.platform.bing.com/.../readaloud/edge/v1` 迁到了 `api.msedgeservices.com/tts/cognitiveservices/websocket/v1`，所有 edge-tts 版本（含最新）一律 403，而同 IP 的 `voices/list` 仍返回 200——**别在代理、换 IP、校时上浪费时间**。修复 = 改 `edge_tts/constants.py`（机器上往往有多份安装：`python -m edge_tts` 用的和 `edge-tts` CLI 的 venv 是两份，`grep -rl speech.platform.bing.com .../site-packages/edge_tts/constants.py` 找全）：

```python
BASE_URL = "api.msedgeservices.com/tts/cognitiveservices"
WSS_URL = f"wss://{BASE_URL}/websocket/v1?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
VOICE_LIST = f"https://{BASE_URL}/voices/list?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
# CHROMIUM_FULL_VERSION 保持不动 → Sec-MS-GEC-Version 仍是 1-143.0.3650.75（新主机仍认旧 token 算法）
```

验证：带 `Ocp-Apim-Subscription-Key` + `Sec-MS-GEC` + `Sec-MS-GEC-Version=1-143.0.3650.75` + `ConnectionId` 开 WebSocket，拿到 **101** 即通（之后服务器等你发首帧配置，读超时=成功，不是失败）。注意 `pip install -U edge-tts` 会把常量改回去，升级后要重打。

**新主机限流凶**：每段之间 `sleep ≥8s`，每段包 6-8 次重试（退避 10-60s）；429 后重试成功是常态，别看到 429 就放弃整批。

- 场景帧数 = `ceil((tts时长 + 0.6s呼吸) * 30)`，写进 theme.ts 统一管理。
- mp3 放 Remotion 项目 `public/`，场景内 `<Audio src={staticFile('pN.mp3')} />`。

## 4. 视觉体系（画面丰富的底线）

深色科技风主题色（#0d1117 系 + 荧光绿强调），**每个场景至少两层叠加**。可复用组件（项目 `src/components/Rich.tsx`）：

| 组件 | 用途 | 关键参数 |
|---|---|---|
| `GlassPanel` | 玻璃拟态面板（backdrop blur+高光边+投影） | 一切 UI 卡片的基底 |
| `DisplayTitle` | 大标题 clipPath 揭示 | **inset 上下留 -20%/20% 余量，否则裁字** |
| `AccentChip` | 强调词色块衬底（马克笔感） | 代替一切发光 textShadow |
| `AmbientGlow` | 环境光斑（极淡径向渐变+慢呼吸） | opacity ≤0.14 |
| `ShineSweep` | 面板扫光 | 幅度克制（opacity 0.45） |
| `FlyIn` | easeOutCubic 飞入 | distance ≤90，弹簧要收敛 |
| `UserBubble` | 右对齐用户气泡+头像 | 拟真聊天必备 |

**反模式（PPT 艺术字三件套，用户一票否决）**：彩色 textShadow 发光、残影叠层、镜像倒影。强调用色块和变色，不用发光。

**字体**：微软雅黑默认渲染显廉价。下载思源黑体（SourceHanSansSC Heavy/Bold/Normal）放 `public/fonts/`，@font-face 注册后 `fontFamily: 'SourceHan'`。中文渲染后必须抽帧验证无豆腐块。

**背景**：`Background.tsx` 三层景深 bokeh 光斑（确定性伪随机 prand，禁 Math.random）+ 细网格 + 渐晕。

## 5. 字幕（踩坑最多的环节）

**绝对不要用「字符数比例」估算字幕时间轴**——TTS 语速不均（标点停顿、数字变读法），必然漂移声画不同步。正确做法：

1. faster-whisper 对每段 mp3 做 `word_timestamps=True` 转写
2. **匹配用模糊算法，别逐字贪心**：whisper 中文转写同音错字极多（孵化→幅画、JNI→GNI、JIT→Jet、向量化→箱量化），逐字贪心匹配会零命中并级联失败（实测一句错字毒死后面 5 句）。正确做法：把**每个整句**与 **whisper 段**做归一化后二元组（bigram）重叠打分，单调指针前进取最优；中文数字归一化（十二→12）+ 只保留汉字/字母/数字参与比较。仍有 3-5% 句子匹配不上属正常，用前后句区间按字数插值兜底
3. **链式时间轴**：句子起点来自匹配段（同段多句按字数比例分布），**终点 = 下一句起点**（最后一句到音频尾-0.2s）——否则句尾取 whisper 段结尾会提前结束，段尾几秒没字幕
4. 长句切分：>9s **或 >40 字**（字多时长短也会溢出）在逗号处切分；**切点按理想字数位置就近选取**——别拿字符距离和秒数比较（切出 15字+64字 的畸形分布），切完按字数比例分配时间
5. 每句 start 再用能量曲线校准（0.25s 窗口，在 [start-0.5, start+1.5] 找首个 >-35dB 窗口），偏差 >0.15s 修正

字幕组件：底部 bottom:88，半透明深色底板（圆角+边框），白粗体+WebkitTextStroke 描边，长句自动缩字号。

## 6. 布局防叠压（用户三次反馈的教训）

- **字幕区是禁建区**：bottom 88~218px 高度带内不放任何场景元素。所有底部金句卡 bottom ≥ 400（字幕在下方 150px 带 + 平台 UI 预留）。
- 署名角标放**右上角**（top:60, right:28），不与字幕抢底部。
- **每轮渲染后抽帧 vision QA**：`ffmpeg -ss <t> -i out.mp4 -frames:v 1` → vision_analyze 问「有无叠压/裁切/穿帮」。中段、结尾段、字幕最长的段必查。
- 场景元素总高超出 → 压缩卡片 padding 和 gap，不要让内容伸进字幕带。

## 7. 句首弱音（用户两次反馈的教训）

TTS（edge-tts）句首起音是气声，**speechnorm/compand 这类压缩器 attack 太慢救不了 100-200ms 的弱起**。正确做法：

1. silencedetect 找全片所有「静音→发声」跳变点（noise=-38dB:d=0.12）
2. numpy 逐样本：每个跳变点后 0.45s 应用增益包络（60-80ms 线性升到 +8~10dB，余弦回落），**只在实测 RMS < -20dB 的弱起点应用**
3. 全片 loudnorm=I=-14:TP=-1.5 收尾
4. 验证：抽句首 0.25s 测 RMS，弱起位置应从 -25~-40dB 抬到 -16~-18dB

**注意区分弱起和标点停顿**：句中 0.5s 的 -240dB 静音是逗号，不是弱起，别给停顿加增益。

## 8. 渲染后 QA 清单

- [ ] 时长 = 各场景帧数总和 ÷ 30
- [ ] 抽帧（中段/结尾段/字幕最长段）vision 查叠压、裁切、穿帮、中文渲染
- [ ] 字幕逐句：能量曲线校准后无倒流、无 >8.5s 长挂
- [ ] 句首响度抽测 ≥ -20dB
- [ ] 片尾按需裁剪（如「关注我」段在渲染前就从逐字稿删掉，别渲染后再剪）

**样片先行（用户明确的流程要求）**：0.5x 草稿渲完后，**不要直接进全量渲染或逐场景细修**——先用 ffmpeg 剪 1-2 段 ~20s 代表性样片（开场钩子一段 + 一个中段代表场景）给用户看：

```bash
ffmpeg -ss <t> -t 20 -i draft.mp4 -c:v libx264 -crf 26 -preset fast \
  -c:a aac -b:a 96k -movflags +faststart preview-xxx.mp4
```

用户点头确认「声音/字幕/画面节奏」方向对了，再继续修叠压、上 1080p 全量。方向性问题（语速、音色、字幕大小、动效密度）在样片阶段改最便宜——全量渲完再改等于重渲全片。

## 9. 迭代纪律

用户反馈的每一处问题：先定位根因（抽帧/测能量），修在**组件层或管线层**（一处修全片生效），不要打补丁。每轮修改只重渲受影响场景段（`--frames=start-end`），ffmpeg concat 拼回，省钱省时——**但拼接后必须 ffprobe 验证总时长 = 各段之和**，且要确认拼接顺序没把前段切掉（踩过：替换中段时把开头 58s 丢了）。

## 10. 抖音发布

文案公式：痛点反问 → 「不是你笨，是 AI 替你干活」反转 → 方法精髓一句（反常识点，如「不报答案，只问你错在哪」）→ 思想出处署名（视频里有角标，口径要一致）→ 开源工具钩子 → 「完整版 x 分钟」完播钩子。话题标签：#AI #学习方法 #效率工具 #开源。封面用撞色大字帧。
