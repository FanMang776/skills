---
name: page-test-frontend
description: Use when 需要用 Playwright 驱动已部署/运行中的前端页面做功能测试、交互操作、截图留证或出测试报告时；也适用于驱动任何 Vue/React 管理后台（含 Element Plus 等组件库）的任何场景，包括「页面点不动」「toast 抓不到」「弹窗挡操作」「networkidle 超时」这类问题
---

# 前端页面测试（Playwright 通用）

## Overview

用 Playwright + 系统 Edge 无头浏览器驱动已部署的前端做功能测试：导航、点击、填表、上传、截图、抓 API。核心原则：**驱动脚本直接改写复用骨架，不要从零搭；所有等待都做防呆，不信任「页面加载完」这个假设。**

## 环境搭建

```bash
mkdir page-test && cd page-test
pnpm init && pnpm add playwright   # 也可 npm i playwright
```

```js
// 骨架：保存为 *.cjs（package.json 是 type:module 时，.js 会报 require 未定义）
const { chromium } = require('playwright');
const BASE = process.env.BASE_URL || 'http://localhost:8080';
const browser = await chromium.launch({ channel: 'msedge', headless: true }); // 用系统 Edge，免下载浏览器
const page = await browser.newPage({ viewport: { width: 1600, height: 900 } });
// 抓 API 请求做证据
page.on('response', r => { if (r.url().includes('/api/')) console.log(`${r.request().method()} ${r.url()} -> ${r.status()}`); });
await page.goto(BASE + '/#/dashboard', { waitUntil: 'load' });  // 路由形式按项目改：hash(#/) 或 history(/)；不要用 networkidle，见下
await page.waitForTimeout(2000);                                // 组件库渲染 + 数据请求的固定缓冲
```

截图输出到 `shots/`，测试报告建议按 `docs/testing/YYYY-MM-DD-<主题>.md` 或项目自己的测试文档约定存放。

**登录鉴权先行**：管理后台几乎都有登录墙，这是测试脚本第一步。两种做法：① 走 UI 登录一次后 `storageState` 复用会话（`browser.newContext({ storageState: 'auth.json' })`）；② 简单场景直接 `page.evaluate` 往 localStorage 注 token 后刷新。

**先探测再套选择器**：新页面先 `preview_snapshot` / 截图 / 输出部分 HTML 看清 DOM 结构和组件库，再写选择器；不同组件库（Element Plus、Ant Design、Naive UI…）类名完全不同，下表的组件库示例要按目标库替换。

## 必守规则（每条都踩过坑）

| 场景 | 正确做法 |
|------|---------|
| 等待页面 | `waitUntil: 'load'` + 固定 `waitForTimeout(2000+)`。**networkidle 永不收敛**——只要页面有任何轮询（告警、消息、心跳 websocket），idle 事件永远不来 |
| 侧边栏导航 | 不一定是 `<a>` 标签（组件库菜单常用 div + click 事件），用 `page.getByText('菜单名').first().click()`，不要解析 href |
| 组件库下拉 | 点弹层容器内的触发元素，选项在 body 挂载的下拉面板里。以 Element Plus 为例：点 `.el-select__wrapper`，选项在 `.el-select-dropdown__item`；Ant Design 则点 `.ant-select-selector`，选项在 `.ant-select-dropdown .ant-select-item`。共同点：直接点 placeholder 文本会被 input 拦截 pointer events |
| 弹窗定位 | 用弹窗容器限定范围——Element Plus 用 `page.locator('.el-overlay-dialog')`，Ant Design 用 `.ant-modal`（配 `.ant-modal-wrap`）。别用全局选择器——会匹配到遮罩后面的元素 |
| 关弹窗 | 部分组件库点「取消」后弹窗仍留在 DOM（隐藏 overlay），挡住后续点击。先 `page.keyboard.press('Escape')` 再断言已关 |
| 新建成功后的连带弹窗 | 创建/保存成功后常有「保存密钥」「复制链接」等二次弹窗，**不点掉它会挡住一切后续点击**——每类弹窗列进测试脚本注释 |
| toast/校验信息 | `[class*="message" i]` 抓文本；Element Plus 的 el-message 约 3 秒消失（Ant Design 的 `.ant-message` 类似），操作后 800ms 内抓，具体时长按目标库实测 |
| 表格校验 | `tbody tr` 过滤文本后取 `td` 的 `allTextContents()`，不要逐格 locator |
| 元素"消失" | 先查是否在未激活的 tab 面板里（`display:none`）。DOM 里有但 `isDisabled()`/可见等待失败 = 隐藏 pane，不是 bug，先切 tab |
| 按钮防呆 | 必选项未选时主按钮常是 `disabled` 态，直接 click 会超时——先 `isDisabled()` 断言门禁，别硬点 |

## 测试纪律

- 测试数据命名带统一前缀（如 `页面测试-`），报告里注明待清理；系统无删除入口的要在报告里列出清理清单
- **未经用户确认不要实际执行**：任何占资源/改共享状态的操作（触发训练/部署、发布/回滚、支付、发消息、删数据）
- 可以放心做：表单校验（空提交、非法输入）、创建/编辑/复制、搜索、弹窗回显——只读或可清理的操作
- 每个关键步骤截图；失败必须给：复现步骤、期望、实际、API 证据、严重程度
- 写操作字段命名与后端约定保持一致（如 snake_case / camelCase），从页面上下文 `fetch` 发起时尤其注意，命名不符会报「必填字段缺失」
- 页面上下文 `fetch('/api/...')` 必须在 `goto` 之后执行（about:blank 会报 Failed to parse URL）；这是绕过 UI 阻断、验证后端能力的合规手段，报告里注明「非 UI 路径」
- 前端源码可直接从 Vite dev server 拉排障（仅 dev 模式、且路径按项目实际目录改）：如 Vue 项目 `fetch('/src/views/xxx.vue')` 看禁用条件/文案，不用猜

## Common Mistakes

- 直接 `goto` 到模块路由后列表为空不一定是 bug——先从首页点导航过去对比（部分应用直达路由与导航渲染不一致）
- 断言弹窗关闭用视觉/截图证据，DOM 里残留的隐藏 overlay 不算 bug
- `getByRole('button', { name })` 匹配含 emoji 的按钮文案没问题（子串匹配）；超时先怀疑元素根本没渲染，而不是选择器写错
