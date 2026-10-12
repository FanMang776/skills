# short-video-production

不露脸把技术内容做成知识类短视频：口播稿 → edge-tts 配音 → 图卡/程序化画面 → ffmpeg/Remotion 合成。Windows 环境，路径约定 `G:\HermesWorkspce`。

## 文件结构

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 完整流程：逐字稿规范 → 配音 → 图卡 → 成片 → 交付清单 |

## 核心流程

1. **口播稿**：按「钩子→痛点→招式→收尾」分段写，每段标时长预算（实测 ~4.6 字/秒）；定位是「分享」不是「教学」。逐字稿必须给用户过目后再配音。
2. **配音**：edge-tts（默认 `zh-CN-YunxiNeural +8%`），先给用户多个音色样音挑选。
3. **画面**：静态图卡只是中间稿（读 PPT 感）；正式成片走代码生成管线（Remotion / Manim），场景时长由旁白实测时长推导。
4. **合成**：场景逐个渲染 → ffmpeg concat → 铺配音 → 烧字幕。

## 头号坑：edge-tts 403「Invalid response status」

微软已于 2026-10 把 Edge 朗读后端从 `speech.platform.bing.com/.../readaloud/edge/v1` 迁到 `api.msedgeservices.com/tts/cognitiveservices/websocket/v1`。**所有 edge-tts 版本（含最新）都会 403，且 `voices/list` 同 IP 仍返回 200**——403 不是你的网络/IP/时钟问题，别在代理和校时上浪费时间。

修复：改 `edge_tts/constants.py`（注意机器上可能有多个安装：`python -m edge_tts` 用的和 `edge-tts` CLI 的 venv 是两份）：

```python
BASE_URL = "api.msedgeservices.com/tts/cognitiveservices"
WSS_URL = f"wss://{BASE_URL}/websocket/v1?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
VOICE_LIST = f"https://{BASE_URL}/voices/list?Ocp-Apim-Subscription-Key={TRUSTED_CLIENT_TOKEN}"
# CHROMIUM_FULL_VERSION 保持不变，Sec-MS-GEC-Version 仍是 1-143.0.3650.75（新主机仍认旧 token 算法）
```

验证方式：带 `Ocp-Apim-Subscription-Key` + `Sec-MS-GEC` + `Sec-MS-GEC-Version=1-143.0.3650.75` + `ConnectionId` 打开 WebSocket，拿到 **101** 即通（之后服务器等你发首帧配置，读超时是正常的，不是失败）。

新主机限流很凶：**每段之间隔 ~10s**，每段包 6-8 次重试（退避 10-60s）；429 后重试成功是常态。

其余坑（TTS 读音规范、逐字稿写法、字幕对齐）见 `SKILL.md`。
