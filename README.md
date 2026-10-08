# FanMang776 Skills

Hermes Agent 技能集合。每个 `media/`、`research/`、`windows/` 等分类目录下的子文件夹是一个独立技能，核心是 `SKILL.md`。

## 技能列表

### media

| 技能 | 说明 |
|---|---|
| [manim-narrated-video](media/manim-narrated-video/SKILL.md) | Manim + edge-tts 旁白视频完整制作流程：文案 → 配音（词级时间戳）→ 字幕对齐 → 草稿帧检 → 1080p60 渲染 → 字幕全量审计收工。含同步防漂移架构与全部踩坑记录 |
| [douyin-video-transcript](media/douyin-video-transcript/SKILL.md) | 抖音视频元数据 + 口播文案提取（Playwright msedge headless + faster-whisper 本地转写） |

### research

| 技能 | 说明 |
|---|---|
| [three-question-domain-ramp](research/three-question-domain-ramp/SKILL.md) | 三问法速通陌生领域：共识五框架 + 分歧争议图 + AI 出题演练循环，agent 只做出题人判卷人，含防幻觉/防代答纪律与双模板 |

### windows

| 技能 | 说明 |
|---|---|
| windows-file-lock | 删除/重命名被占用的 Windows 文件（句柄扫描 + 安全 rm 脚本） |

### teaching

| 技能 | 说明 |
|---|---|
| [html-explainer-pages](teaching/html-explainer-pages/SKILL.md) | 把概念/调研结论做成单文件零依赖的滚动叙事 HTML 动画讲解页：分屏大纲 → reveal 骨架 → 浏览器预览验证流水线（截图卡顿≠页面坏的判定法），附真实产出示例 |

### autonomous-ai-agents

| 技能 | 说明 |
|---|---|
| ubuntu-vnc-computer-viewer | 通过 x11vnc + websockify 把局域网 Ubuntu 桌面接入 Hermes Computer viewer |

## 安装

把对应技能目录复制到 `~/.hermes/skills/` 下，或按 Hermes 的技能加载机制配置路径。

## 说明

- 技能均为实践验证后的沉淀，SKILL.md 内含完整的踩坑记录（Pitfalls）和收工验收清单（Verification）
- 平台兼容性以各技能 frontmatter 的 `platforms` 字段为准

## License

[MIT](LICENSE) © 2026 Lane (FanMang776)
