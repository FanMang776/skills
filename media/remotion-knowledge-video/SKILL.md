---
name: remotion-knowledge-video
description: Use when 把技术方法论/教程做成带动画的16:9横屏讲解视频：TTS 分段→Remotion 分层合成→whisper 字幕对齐→响度修复→渲染交付。全流程代码化，改稿秒重渲。支持两套视觉体系：玻璃拟态科技风 / 马赛克像素小人风。
version: 1.2.0
author: cj (FanMang776)
license: MIT
platforms: [any]
requires: [node>=18, ffmpeg, python+pip(edge-tts, faster-whisper, numpy), Remotion(npx create-video)]
---

# Remotion 知识类横屏视频管线

把一篇技术方法论做成画面丰富的横屏视频（1920×1080@30fps，16:9；抖音/小红书横屏、B 站通用）。核心经验：**画面丰富 = 四层结构叠加**（粒子/bokeh 背景 + 拟真 UI 界面 + 动效字卡 + 图表动画），拒绝单调图卡风；**声画同步 = 不估算，全用实测**（TTS 时长驱动场景、whisper 字级时间戳驱动字幕、能量曲线校准边界）。

**横屏专项（2026-10 实测）**：①核心元素四周留 ~5% 安全区（横屏视频在竖屏平台会小窗播放，构图居中才不难看）；②横向示意图（流水线、对比图）是横屏主场戏，放得开是横屏最大红利；③字幕带收窄到底部 60~150px（无竖屏平台 UI 预留）。

## 管线总览

```
逐字稿(8段/带时间轴) → TTS分段(mp3+实测时长) → Remotion场景(时长驱动) 
→ 渲染 → whisper字级对齐生成字幕 → 能量曲线校准字幕边界 → 句首增强 → 交付
```

## 1. 前期：环境（Windows 实测坑）

- 系统代理是注册表 IE 代理（如 127.0.0.1:7897），env 无变量。Remotion 下载 headless Chrome 会直连 storage.googleapis.com 然后 ECONNRESET/超时。**解法：手动 curl 走代理下载 chrome-for-testing 的 zip，解压后渲染时指给 Remotion**，浏览器目录留好复用，永不再下。**坑（2026-10 实测，Remotion 4.0.537）：`REMOTION_CHROME_EXECUTABLE` 环境变量已不生效，它照样去下自己的 120MB headless-shell 然后 ECONNRESET——必须用 CLI 参数 `--browser-executable="<chrome路径>"`**（`remotion.config.ts` 里 `Config.setBrowserExecutable()` 也可以）。
- TS 报 `Cannot find module './xxx'` 先查相对路径层级（compositions/ 子目录里要用 `../`），别怀疑编码。
- 渲染命令模板：
  ```bash
  npx remotion render <CompId> out/xxx.mp4 --browser-executable="<chrome路径>"
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

### 3b. 火山豆包 TTS 路线（2026-10 实测，EP2 验证）

edge-tts 之外的合规选项：火山引擎「语音合成 2.0」（新版控制台 API Key 单头鉴权，音色即剪映/抖音同款家族，如 刘飞2.0=`zh_male_liufei_uranus_bigtts`）。参考实现 `scripts/gen_tts_volc.py` + `scripts/gen_subs_volc.py`。

- **接口**：POST `https://openspeech.bytedance.com/api/v3/tts/unidirectional`，headers 三件套 `X-Api-Key` / `X-Api-Resource-Id: seed-tts-2.0` / `X-Api-Request-Id`；响应是 NDJSON 行流，`code=0` 带 `data`(b64音频)，`20000000`=结束。
- **字幕时间戳（三个坑全踩过）**：①`enable_subtitle: true` 必须放 **`req_params.audio_params` 里面**（放顶层无效）；②官方文档说返回 `TTSSubtitle` 事件——那是 WebSocket 接口的，**HTTP 单向流式实际在 `sentence` 字段**里（`sentence.words[]` 含 `word/startTime/endTime`，**单位是秒**不是 1e7 纳秒）；③**时间戳系统性偏早**：每段 mp3 有 0.6~0.8s 静音头但词表从 t=0 开始，且长段（>20s）有累积漂移。
- **字幕生成走专用脚本不走 rebuild**：volc 的 `sentence.words` 本身是原文顺序，直接顺序映射即可，不需要 edge-tts 那套 SequenceMatcher 模糊对齐；逐段用「词表首词 t vs 细粒度 PCM 能量 onset（20ms 窗）」实测整体偏移，每行再吸附 ±0.6s 内最近发声点，最后**行首 0.3s 能量闭环**（< -32dB 整行后移 0.3s）。silencedetect(-35dB) 会漏短停顿导致 QA 大量误报，**验收判据要用直接 PCM 能量**（行首 0.3s < -32dB 算早挂）。
- **语速**：刘飞 2.0 默认语速明显快于 edge-tts Yunxi+8%（同样文稿短约 30%），要控时长用 `audio_params.speech_rate`（-50~100）。
- 限流远比 edge-tts 宽松，段间隔 2s 足够；费用约 5 元/万字符，新用户送 2 万字符。

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

### 风格 B：马赛克像素小人风（2026-10 Docker 视频验证通过）

整支视频的视觉语言换成低分辨率像素画：**所有场景画在 480×270 逻辑网格上，`transform: scale(4)` 放大到 1920×1080**（`PixelStage` 组件，见 `templates/Pixel.tsx`，直接拷进项目）。与风格 A 的差异全在约束上：

- **时钟**：`useTick()` = `Math.floor(frame/2.5)`，12fps 阶跃——像素动画宁可卡顿，越顺滑越没像素味。弹性缓动/easeOut 一律不用，入场用 `scale(pop)` 三阶跃或直接出现
- **限色板**：深海军蓝底 `#0d1420` + Docker 蓝 `#2496ed` + 荧光青 `#3ddc97`，全部颜色进 theme 常量，禁止临时取色
- **组件库**（templates/Pixel.tsx 全套）：`R`(像素矩形)、`Guy`(小人:walk 4 帧摆臂/idle 呼吸+眨眼/talk 张嘴/point)、`Whale`(吉祥物:双层集装箱+翘尾+喷水泡泡)、`Crate`、`Terminal`(打字机逐行)、`TitleCard`、`PopText`(节拍字卡)、`CheckRow`(✓/✗ 清单行)、`GridBg`(像素网格+渐晕)。角色动作靠 2-4 帧循环+位移，不画中间帧
- **字体**：等宽英文用 `Consolas, "Microsoft YaHei", monospace` + fontWeight 900；中文仍用思源黑体
- **反模式**：模糊光斑（像素世界里光晕=穿帮，背景渐晕用 radial-gradient 一层即可）、抗锯齿动效、真实照片素材、Math.random（用 prand）
- **字幕**：沿用第 5 节管线不变，样式改直角方块底（无圆角），字幕带禁建区规则不变

**致命陷阱——R 组件的相对定位**：`R` 是 `position:absolute`，相对**最近的 positioned 祖先**而不是舞台。场景顶层直接用没问题；一旦嵌进 positioned div（卡片、字卡），坐标就变成相对该 div——踩过两次（P2 卡片顶栏飞到屏幕中央、P5 盾牌漂移）。规则：**嵌进 positioned 容器里的 R，坐标从容器左上角算**。

## 4b. 节拍驱动场景（风格无关，必做）

**画面必须按口播逐句推进，每句台词对应一段专属画面动作**——静态构图摆好元素等标签弹出，用户会打回（原话：「画面内容单调，不够丰富，只展示了一小部分动作，没有和讲解内容对应」）。丰富不是元素多，是动作跟着说话走。

做法：字幕定稿后（第 5 节产出 `subtitles.json`），把每句台词的全局时间换算成场景局部帧，写进 `src/beats.ts` 常量表；场景里每个 beat 安排一个可视化响应——元素入场、状态翻转、清单逐项打叉、演示推进、角色换动作。最小示例：

```ts
// src/beats.ts —— P4 场景从全局帧 2477 起,该句「现在合上盖」在全局 104.58s
export const B4 = { close: 660 };  // (104.58 - 2477/30) * 30 = 660 局部帧
// 场景里:  {frame > B4.close && <合盖动画/>}
```

抽帧 QA 增加一问：**「这一秒口播说了什么，画面是否在演」**——答不上来就是死帧，按死帧补 beat，而不是加装饰。

## 5. 字幕（踩坑最多的环节）

**绝对不要用「字符数比例」估算字幕时间轴**——TTS 语速不均（标点停顿、数字变读法），必然漂移声画不同步。

### 5a. 首选方案：edge-tts WordBoundary 词级时间戳（一次到位，免匹配免校准）

edge-tts 合成时引擎会流式吐出 `WordBoundary` 事件——**每个词在音频里的精确时间由引擎自己报出**，字幕时间轴按构造对齐，whisper 匹配、能量校准全部不需要：

```python
cm = edge_tts.Communicate(text, voice, rate='+8%', boundary='WordBoundary')  # 显式传，默认是句级
words, audio = [], bytearray()
async for chunk in cm.stream():
    if chunk['type'] == 'audio':
        audio += chunk['data']              # 自己拼 mp3（save() 和 stream 不能并用）
    elif chunk['type'] == 'WordBoundary':
        words.append({'t': chunk['offset']/1e7, 'd': chunk['duration']/1e7, 'w': chunk['text']})
```

- 句子时间 = 句内首词起点 / 末词终点；行边界与词表做**归一化模糊单调对齐**（见下），不要做「顺序字符对应」
- **对齐的两个坑（2026-10 实测）**：①「按字符数精确消耗词表」必炸——KIP-1150、S3、Aiven 这类 token 书写长度≠发音长度（连字符不发音、英文按字母读），一处错位后面全歪，P7 尾部六行被挤成 0.45s。修复 = 字幕行文本与词表各自归一化（lowercase+只留字母数字）后 SequenceMatcher 模糊单调对齐。②对齐结果不能把「W 字符流位置」直接当「词序号」取时间——中文单字词让两者恰好重合，多字词/数字/英文一累积就劈，必须用 bisect 反查每个词在字符流里的起始位置。参考实现：`scripts/gen_subs_edgetts.py`（词表落盘 `words-<seg>.json`，改切分/对齐可 `rebuild` 模式免重合成）
- 长句切分：>9s **或 >40 字**在逗号处切，**切点边界用真实词时间**，别按字数比例（切出 15字+64字 的畸形分布）
- **唯一已知坑：WordBoundary 比实际音频早 ~0.25s**（引擎时间轴 vs 流播放时间轴）。修正：silencedetect 取该段首个发声起点，全局平移后每条再吸附 ±0.3s 内最近的发声点
- 字幕组件用**单行自适应字号**（fontSize = clamp(20, 52, 可用宽/字数)），永不折行——长句折行会把字幕条顶进场景元素

### 5b. 兜底方案：whisper 模糊匹配（拿不到 WordBoundary 时才用）

1. faster-whisper `word_timestamps=True` 转写；**匹配用模糊算法，别逐字贪心**：whisper 中文同音错字极多（孵化→幅画、JNI→GNI、JIT→Jet），逐字贪心零命中并级联失败（一句错字毒死后面 5 句）。把**整句**与 **whisper 段**做归一化 bigram 重叠打分，单调指针取最优；中文数字归一化（十二→12）+ 只保留汉字/字母/数字
2. 3-5% 句子匹配不上属正常，用前后句区间按字数插值兜底；**链式时间轴**（终点 = 下一句起点，最后一句到音频尾-0.2s）——否则段尾几秒没字幕
3. **起点吸附到真实发声边界必做**：whisper 时间戳系统性偏早（段首可早 1s+）。silencedetect=noise=-35dB:d=0.15 取发声点，每条 start 吸附 ±0.9s 内最近者；每段第一条无条件吸附首个发声点

字幕组件：底部 bottom:88，半透明深色底板（圆角+边框），白粗体+WebkitTextStroke 描边，长句自动缩字号。

## 6. 布局防叠压（用户三次反馈的教训）

- **字幕区是禁建区**：横屏 bottom 60~150px 高度带内不放任何场景元素。金句卡、对照表等底部元素 bottom ≥ 180（字幕带 + 呼吸空间）。
- 署名角标放**右上角**（top:54, right:64），不与字幕抢底部。
- **每轮渲染后抽帧 vision QA**：`ffmpeg -ss <t> -i out.mp4 -frames:v 1` → vision_analyze 问「有无叠压/裁切/穿帮」。中段、结尾段、字幕最长的段必查。
- 场景元素总高超出 → 压缩卡片 padding 和 gap，不要让内容伸进字幕带。
- 横屏安全区：核心信息四周留 ~5%（约 96px），封面/前 3 秒尤其如此——竖屏平台小窗播放时四边会被裁。

## 7. 句首弱音（用户多次反馈，固定增益方案已淘汰）

神经 TTS 首音节是气声且**响度不可控**（Microsoft 官方答复：无参数保证 onset 响度一致，只能合成后外部测量+处理）。固定 +8dB 包络是错的——特弱起点（-35dB 起）根本不够，且 -38dB 阈值的 silencedetect 会晚抓弱起音。正确做法：**自适应 onset 归一化 + 闭环验收**：

1. 细粒度能量 onset：20ms 窗/10ms 步，阈值 -42dB（比 silencedetect 早抓到弱起），从 ≥150ms 静音后进入发声算一处
2. 每处实测首 0.2s RMS，**独立定增益**拉到目标 -16dB（增益 = 10^((目标-实测)/20)，上限 ×5=+14dB）
3. 包络：10ms 快攻、hold 200ms、300ms 余弦回落到 1.0
4. **两遍迭代**：处理完复测，仍低于目标的再来一轮
5. 段级 loudnorm=I=-14:TP=-1.5:LRA=9 统一响度（apad+atrim 锁死时长不变）。**坑：loudnorm 会把输出重采样到 192kHz**，atrim 的样本数是按 44.1kHz 算的，必须写成 `loudnorm=...,aresample=44100,apad,atrim=end_sample=N`（并加 `-ar 44100`）——顺序不对会把 8.8s 裁成 2.0s
6. **闭环验收**：对输出重新解码，逐 onset 复测首 0.2s RMS——任何一处 < -19dB 直接 FAIL 退出重跑。实测效果：224 处 onset 最弱 -16.6dB（修复前最弱 -39dB），零残留

**注意区分弱起和标点停顿**：句中 0.5s 的深静音是逗号，不是弱起，别给停顿加增益。

**闭环验收的阈值陷阱（EP2 实测）**：volc 合成的音频底噪比 edge-tts 高，loudnorm 拉响度后底噪越过 -42dB 绝对检测线，闭环检测出的「onset」会从 50 个掉到 8 个（全是噪声波动），必然假 FAIL。修复：`onset_boost.py` 已改为**用源音频的真实 onset 位置清单**去输出音频上测响度（响度处理不改时间轴），不用输出音频重新检测 onset。

## 8. 渲染后 QA 清单

**字幕对齐必须机器全量验收，不要让用户反复试看**（用户明确要求）：渲完后用能量曲线逐行测量——每条字幕 (a) 开头 0.3s 必须有语音（早挂检测）(b) 行内语音覆盖率（自然语音词间停顿 25-40%，≥2.5s 的行低于 45% 才算异常）(c) 与最近发声边界的误差。三项全绿（早挂 0、FAIL 0）才交付，不达标自己修完再渲。

- [ ] 时长 = 各场景帧数总和 ÷ 30
- [ ] 抽帧（中段/结尾段/字幕最长段）vision 查叠压、裁切、穿帮、中文渲染
- [ ] 节拍抽检（4b）：随机 3 个时间点，对照字幕问「画面是否在演这一句」，死帧补 beat
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
