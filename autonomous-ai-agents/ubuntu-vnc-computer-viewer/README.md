# ubuntu-vnc-computer-viewer

把局域网里一台 Ubuntu 实体机的**物理桌面**接入 Hermes Desktop 的 Computer 面板（插件：[hunterbohm/hermes-computer-viewer](https://github.com/hunterbohm/hermes-computer-viewer)），实现在聊天侧边栏里查看、操作远程 Ubuntu 桌面，或让 Agent 代管。

## 解决什么问题

插件本身只认 WebSocket/noVNC 协议，**不能直连裸 VNC 端口**——网上大多数教程教你在远端装完 x11vnc 后直接填 `IP:5900`，永远连不上。本 skill 固化了完整可用的三段链路：

```
Hermes Desktop 插件 ──HTTP/WS──▶ websockify (:6080, noVNC 网页根目录)
                    ──TCP──────▶ x11vnc (:5900) ──▶ X display（常常是 :1 而非 :0）
```

全程**无需 sudo**：websockify 装在用户 venv，x11vnc 以登录用户身份运行，适配只有 SSH 公钥、没有 sudo 密码的服务器。

## 文件结构

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 完整流程：插件安装 → x11vnc 启动 → websockify 桥接 → 验证 → 插件填表口径，附实战坑位清单 |

## 核心流程（速览）

1. **装插件**（Windows 宿主机）：`plugin.js` 放入 `~/.hermes/desktop-plugins/computer-viewer/`，Ctrl+K → Reload desktop plugins
2. **远端起 x11vnc**：先用 `ls /tmp/.X11-unix/` 和 `ps wwwaux | grep Xorg` 找到**真实显示号和 `-auth` 授权文件路径**（现代 GDM/Ubuntu 常是 `:1` + `/run/user/1000/gdm/Xauthority`），再带 `-rfbauth` 启动
3. **websockify 桥接**：`venv --without-pip` + get-pip.py 装进 `~/.vnc/wsenv`，noVNC 网页目录 scp 过去，`--web` 指向它监听 6080
4. **验证**：宿主机 `curl http://IP:6080/vnc.html` 返回 200 再动 UI
5. **插件里填**：地址填 **`http://IP:6080/vnc.html`**（不是 `IP:5900`），密码为 `x11vnc -storepasswd` 设置的密码

## 实战坑位（详情见 SKILL.md）

- SSH 会话里的 `$DISPLAY`（如 `localhost:10.0`）是 X11 转发，抓的是错误目标；`-auth guess` 在 SSH 下也会失败
- Wayland 会话对 x11vnc 完全不可见，必须是 "Ubuntu on Xorg" 会话
- 普通桌面会话的 `~/.Xauthority` 往往是猜错的位置，以 Xorg 进程命令行里的 `-auth` 参数为准
- 打包版 Hermes Desktop 没有调试端口，插件 UI 只能用户手点（VNC 密码本就应用户自己输）
- 插件添加计算机界面的 OS 选择只有 Mac/Windows，没有 Linux 选项——那只是教程文字，选哪个都不影响连接

## 安装

把本文件夹复制到 `~/.hermes/skills/autonomous-ai-agents/ubuntu-vnc-computer-viewer/`（Windows 为 `C:\Users\<user>\AppData\Local\hermes\skills\...`）。

## 待办

- x11vnc 与 websockify 目前为手动拉起，重启失效；systemd 开机自启单元是下一个迭代项

## 环境备注（原版含机器特情坑）

本仓库为此 skill 的**原版**，含本机环境特有信息（如 Windows 侧 curl 必须 `--ssl-no-revoke`、宿主机实际路径 `C:\Users\cj\AppData\Local\hermes\...`）。去环境化通用版见内网仓库 `knowledge_base/skiils`。
