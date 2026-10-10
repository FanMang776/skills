# remotion-knowledge-video

把技术方法论/教程做成画面丰富的抖音/小红书竖屏视频（1080×1920@30fps）。全流程代码化：改稿秒重渲。

## 解决的问题

- 图卡式视频画面单调 → 四层结构（bokeh 背景/拟真 UI/动效字卡/图表动画），组件即插即用
- 声画不同步 → 字幕时间轴不估算，whisper 字级时间戳 + 成片能量曲线双重校准
- TTS 句首弱音听不清 → 逐句首能量检测 + 精确增益包络（压缩器 attack 太慢救不了弱起）
- 手工剪辑不可迭代 → 全部代码化，改一句话重渲一段再拼接

## 文件结构

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 完整管线文档：环境坑/TTS/视觉体系/字幕对齐/布局禁建区/QA 清单 |
| `templates/Rich.tsx` | 视觉组件库：GlassPanel/DisplayTitle/AccentChip/AmbientGlow/ShineSweep/FlyIn/UserBubble |
| `templates/Background.tsx` | 三层景深 bokeh 背景（确定性伪随机） |
| `templates/Overlays.tsx` | 底部字幕卡 + 右上角署名角标 |
| `templates/Subtitles.tsx` | 逐句字幕组件（读 subtitles.json 时间轴） |
| `templates/theme.ts` | 主题色 + TTS 时长驱动的场景帧数管理 |
| `scripts/gen_tts.py` | edge-tts 分段生成 + ffprobe 实测时长 |
| `scripts/gen_subs_v3.py` | whisper 字级对齐原始文案生成字幕（含繁简/错字映射） |
| `scripts/boost_onsets.py` | 句首能量检测 + 增益包络 |

## 核心流程

1. **逐字稿**：8 段左右、带画面提示，钩子前置
2. **TTS**：edge-tts（zh-CN-YunxiNeural +8%）分段 → ffprobe 实测时长 → 场景帧数 = (时长+0.6s)×30
3. **Remotion 合成**：四层结构场景，`<Audio>` + `<Sequence>` 按实测时长驱动
4. **渲染**：`REMOTION_CHROME_EXECUTABLE` 指向本地 chrome-headless-shell（浏览器已缓存则免下载）
5. **字幕**：whisper 字级时间戳 + 原始文案贪心匹配（繁简/错字映射）→ 成片能量曲线二次校准
6. **音频修复**：句首能量检测 → numpy 增益包络（+8~10dB/0.45s）→ loudnorm
7. **QA**：抽帧 vision 查叠压/裁切/中文渲染；字幕边界无倒流；句首 RMS ≥ -20dB

细节和坑位全在 [SKILL.md](media/remotion-knowledge-video/SKILL.md)。

## 实战坑位摘要

- 字幕时间轴**绝不用字符数比例估算**——TTS 语速不均必然漂移
- PPT 艺术字三件套（彩色发光/残影/倒影）是反模式，强调用色块
- DisplayTitle 的 clipPath 要留上下余量，否则裁字
- 底部 88~218px 是字幕禁建区，场景金句卡 bottom ≥ 400
- 压缩器（speechnorm/compand）救不了 TTS 弱起，必须逐句首包络
- 替换中段后拼接，必须 ffprobe 验证总时长（踩过丢开头 58s 的坑）
