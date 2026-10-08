---
name: html-explainer-pages
description: Use when 需要把一个概念、调研结论或流程做成可视化讲解页——用户说"看字看不明白""做个动画/图解/可视化讲一下"，或要把 API/源码调研结果变成可滚动的单文件 HTML 动画页面时
version: 0.1.0
author: cj (FanMang776)
license: MIT
platforms: [any]
---

# HTML Explainer Pages

单文件、零依赖、滚动叙事的讲解页。核心原则：**内容分屏，每屏只讲一件事，滚动触发一次性 reveal**。
视觉设计（配色/字体/布局气质）交给 `anthropic-skills:frontend-design`，本 skill 只管三件事：
叙事结构、骨架模式、验证流水线——验证流水线是提速的大头。

## When to Use

- 把文字结论转成动画/图解讲给用户（API 调研、架构讲解、流程演示）
- 教学场景：一个概念配一屏 + 一个可交互载体（YAML 高亮 / 映射动画 / 步骤链 / 时间线）
- Not for: 数据报表（用 dataviz skill）、需要构建步骤的正式前端项目（用 web-standards skill）

## Procedure

1. **分屏大纲先行。** 把材料拆成 5–7 屏写下来再动手：每屏 = 一句导语 + 一个可视化载体。
   载体就四种选一：逐行代码/YAML（配侧栏 hover 联动）、左右映射动画、步骤时间线、可切换 Tab。
   花一次大胆在 Hero（图谱生长或首屏主动画），其余全克制。
2. **单文件骨架。** 一个 `.html`，内嵌全部 CSS/JS，零外部请求（离线可开、双击即用）。
   动效统一走一个模式：元素默认隐藏，IntersectionObserver 加 `.on` 类触发 CSS transition，
   触发后 `unobserve`（只演一次）；所有动效包 `@media (prefers-reduced-motion: reduce)` 强制关断。
   中文用系统字体栈，别引 webfont。
3. **文案用真实数据。** 抓来的真实字段名、真实 API 返回当例子，不用 Lorem ipsum 式占位——
   真实感本身就是讲解力。
4. **预览验证流水线**（Windows + Claude 浏览器面板实证过的坑，照做免踩）：
   - 外网 URL 不能 attach 预览，必须本地起服务：`.claude/launch.json` 写
     `python -m http.server <port> --directory .`，`preview_start` 后 `location.href` 导航到文件
   - 逐节验证：`preview_eval` 里 `window.scrollTo({top: el.offsetTop, behavior:'instant'})` → 截图
   - **截图空白/超时 ≠ 页面坏了**。先 DOM 断言（`elementFromPoint`、`textContent`、样式计算值），
     内容在就是预览窗合成器卡了：`window.scrollBy({top:±10})` 抖一下再截，通常就好
   - 动画类内容验证用 `preview_eval` + Promise 等待终态（如步骤链全部 `.lit`、hint 文案变化）
   - 收尾必做：`preview_stop` + 删掉临时 `launch.json`
5. **交互控件全部点一遍**（Tab 切换、按钮触发），交互后的状态变化用 DOM 断言而不是肉眼。

## Common Mistakes

| 坑 | 后果与对策 |
|---|---|
| CSS 变量/类名手滑打错字（如 `#5E7astronomy8C`） | 变量失效静默降级；写完 grep 一遍 `var(--` 与定义对账 |
| JS 动态生成的行也带 `.ln` 隐藏类 | 父级 `.on` 时机对不上就永远隐形；动态内容要么父容器先 `.on`，要么直接可见 |
| Hero 里 absolute 定位的元素忘了父级 `position:relative` | 定位飞出屏幕；容器一律显式 `position:relative` |
| 把预览窗渲染卡顿当页面 bug 反复改代码 | 先 DOM 断言再动手改；改代码是最后手段 |
| reveal 选择器漏写新加的区块 | 选择器集中定义一处（如 `.yaml-reveal` 类标记），不散落 |

## Example

[example-ontos-explainer.html](example-ontos-explainer.html) —— Ontos 本体建模机制讲解页（真实产出），
含全部四种载体：hover 联动 YAML、四类原语 Tab、列映射动画、审批步骤链、版本时间线、Hero SVG 图谱生长。
新页面以此为底稿换内容，比从零写快一半以上。
