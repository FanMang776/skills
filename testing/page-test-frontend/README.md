# page-test-frontend：Playwright 前端页面测试

让 agent 用 Playwright + 系统 Edge 无头浏览器直接驱动**已部署/运行中的前端**做功能测试：导航、点击、填表、上传、截图留证、抓 API 证据，最后产出可归档的测试报告。

## 它解决什么问题

让 AI 写 Playwright 脚本测页面，最常见的死法不是语法错，而是**等不对、点不到、看不见**：

- `networkidle` 在有轮询（告警、消息、心跳）的页面上**永不收敛**，脚本永远超时
- 组件库的下拉/弹窗/遮罩有自己的一套 DOM 结构，按直觉写的选择器全被 input 拦截 pointer events
- toast 约 3 秒消失，动作做完再截图，证据已经没了
- 元素明明在 DOM 里却"点不动"——其实只是躲在未激活的 tab pane 里（`display:none`），不是 bug
- 必选项没选时主按钮是 disabled 态，硬 click 就是干等超时

这些坑每一条都真实踩过，skill 把它们固化成一张「场景 → 正确做法」规则表，agent 照做即稳。

## 使用

1. 把本目录复制到 agent 技能目录（如 `~/.hermes/skills/`），或按对应平台的技能加载机制配置
2. 对 agent 说「用 Playwright 测一下 http://xxx 的 XX 页面」即可；SKILL.md 提供可直接改写复用的骨架脚本和防呆规则，不需要从零搭环境
3. 完整内容见 [SKILL.md](SKILL.md)

## 内容速览

- **骨架脚本**：`channel: 'msedge'` 免下载浏览器、viewport、API 响应监听，复制即用
- **登录鉴权先行**：storageState 复用会话 / localStorage 注 token，管理后台第一步不再卡壳
- **先探测再套选择器**：不同组件库类名完全不同，先看清 DOM 再写选择器
- **必守规则表**：等待策略、侧边栏导航、组件库下拉（Element Plus / Ant Design 对照）、弹窗定位与关闭、toast 抓取时机、隐藏 tab pane、disabled 按钮防呆
- **测试纪律**：占资源/改共享状态的操作（触发训练、支付、发消息）未经用户确认不执行；测试数据加统一前缀并留清理清单；失败报告五要素——复现步骤、期望、实际、API 证据、严重程度
- **Common Mistakes**：直达路由与导航渲染不一致、隐藏 overlay 残留不算 bug、超时先怀疑元素未渲染

## 适用与不适用

- **适用**：管理后台 / 中后台 SPA（Vue、React 均可，含 Element Plus、Ant Design 等组件库）的功能测试、回归验证、截图留证
- **不适用**：单元测试与组件测试（Vitest/Jest 的活）、视觉回归像素对比（未含 pixel diff 方案）

## 来源

提炼自 asr-platform 项目的前端测试实战，每条规则都有真实踩坑记录背书；通用化时补充了 Ant Design 对照与登录鉴权指引。
