# ubuntu-vnc-computer-viewer

让 Hermes Desktop 的 Computer 面板连上局域网里任意一台 Ubuntu 电脑的**真实桌面**——在聊天侧边栏里实时查看、鼠标键盘直接操作，或让 AI 替你操作，全程旁观。同事拿到本 skill 即可从零复刻，无需 sudo 权限。

## 成品效果

```
Hermes Desktop 侧边栏 ──┐
                        ├─ Computer 面板里出现 Ubuntu 桌面画面
   ws://IP:6080/websockify ──▶ websockify (Ubuntu :6080) ──▶ x11vnc (:5900) ──▶ 物理桌面 (:1)
```

- 局域网内任意 Ubuntu 实体机/带桌面的虚拟机均可
- 全程用户态安装（venv），**不需要 sudo**
- Hermes AI 可同时通过 SSH 操作同一台机器，人在面板里实时监工

## 前置条件

| 项 | 要求 |
|---|---|
| Windows 主机 | 装有 Hermes Desktop（打包版即可） |
| Ubuntu 目标机 | 桌面会话为 **Xorg**（Wayland 不行）；SSH 可登录（推荐公钥） |
| 网络 | 两机互通，Ubuntu 的 5900/6080 端口未被防火墙拦 |

## 五步流程（详细命令见 SKILL.md）

### ① 装 Hermes 插件（Windows）

下载 [hermes-computer-viewer](https://github.com/hunterbohm/hermes-computer-viewer) 的 `plugin.js`，放到：

```
C:\Users\<用户名>\AppData\Local\hermes\desktop-plugins\computer-viewer\plugin.js
```

Hermes 里按 **Ctrl+K → Reload desktop plugins**，侧栏出现 Computer 面板即成功。

### ② Ubuntu 上起 x11vnc

```bash
# 首次：设 VNC 密码（记住它，最后要用）
x11vnc -storepasswd

# 找真实显示号和授权文件（不要假设 :0！）
ls /tmp/.X11-unix/                    # 看到 X1 → 显示号是 :1
ps wwwaux | grep Xorg | grep -v grep  # 抄下 -auth 后面的路径

# 启动（把 :1 和 auth 路径换成上一步查到的）
nohup x11vnc -display :1 -auth /run/user/1000/gdm/Xauthority \
  -forever -loop -noxdamage -repeat \
  -rfbauth ~/.vnc/passwd -rfbport 5900 -shared \
  >~/.vnc/x11vnc.log 2>&1 &

# 验证：日志出现 "The VNC desktop is" 和 "PORT=5900"
tail ~/.vnc/x11vnc.log
```

> **Wayland 会话连不上/黑屏**：注销 → 登录界面右下角齿轮 → 选 "Ubuntu on Xorg" 重新登录。

### ③ Ubuntu 上装 websockify 桥（免 sudo）

插件只认 WebSocket，**不能直连 5900**，必须搭这个桥：

```bash
# 装 websockify 到用户 venv（--without-pip 路径，避开 pip 自举卡死）
python3 -m venv --without-pip ~/.vnc/wsenv
curl -sS https://bootstrap.pypa.io/get-pip.py -o ~/.vnc/get-pip.py
~/.vnc/wsenv/bin/python ~/.vnc/get-pip.py -q
~/.vnc/wsenv/bin/python -m pip install -q websockify
```

noVNC 网页目录（可选，仅浏览器直访时需要；插件本身用不到）：在本机下载 [noVNC release tarball](https://github.com/novnc/noVNC/releases)，`scp -r` 解压目录到 Ubuntu 的 `~/.vnc/noVNC`。

```bash
# 启动桥（如果拷了 noVNC 目录，浏览器访问 :6080 也能出登录页）
nohup ~/.vnc/wsenv/bin/websockify --web=$HOME/.vnc/noVNC \
  0.0.0.0:6080 localhost:5900 >~/.vnc/websockify.log 2>&1 &

# 验证：监听 6080 即可
ss -tln | grep 6080
```

### ④ Windows 侧验证

```powershell
# 返回 200 就绪（没拷 noVNC 目录时此步会 404，只要 6080 通了即可）
curl http://<Ubuntu IP>:6080/vnc.html
```

### ⑤ Hermes 面板里添加计算机

Ctrl+J → Computer 面板 → 设置/添加：

| 字段 | 填什么 |
|---|---|
| Where | **Local** |
| Name | 随意，如 `Ubuntu-119` |
| OS 选择 | Mac/Windows 随意（没有 Linux 选项，不影响） |
| **Computer address** | **`ws://<Ubuntu IP>:6080/websockify`** ⚠️ 不是 http 地址！ |

点连接 → 弹密码框 → 输第②步设的密码。

> ⚠️ **最大坑**：填 `http://IP:6080/vnc.html` 在打包版桌面端里会被**静默拦截**（黑屏、点连接无反应、无任何报错）——必须用 `ws://` 地址。
> 若连接后**黑屏但蓝点亮**：链路已通，点右上角 ↗ 全屏按钮即出画面。

## 使用场景

- **手动远控**：面板 ↗ 全屏，鼠标键盘直接操作，等同坐到那台机器前
- **AI 代操作**：让 Hermes 通过 SSH 在该机干活（装软件、查状态、搬文件），面板里实时观看
- **图形界面自动化**：配合 computer-use 让 AI 在桌面上点按钮开窗口

## 常见故障速查

| 症状 | 原因 → 处理 |
|---|---|
| 点连接毫无反应 | 地址填了 http://（iframe 被打包版拦截）→ 改 `ws://IP:6080/websockify` |
| 密码框弹不出/连不上 | websockify 僵尸进程堆积 → `pkill -f websockify` 后重启一个，确认 `pgrep -fc websockify` 为 1 |
| 连上但黑屏（蓝点亮） | 非安全上下文渲染问题 → 点 ↗ 全屏 |
| 密码总报错 | 输错或中文输入法干扰；重置：Ubuntu 上重跑 `x11vnc -storepasswd` 并重启 x11vnc |
| Ubuntu 重启后连不上 | x11vnc/websockify 未自启 → 按第②③步重拉（或配 systemd，见 SKILL.md 待办） |
| SSH 里跑 x11vnc 报 XOpenDisplay failed | SSH 的 `$DISPLAY` 是 X11 转发假象 → 按第②步显式指定 `-display :1 -auth <真实路径>` |

## 文件结构

| 文件 | 内容 |
|---|---|
| `SKILL.md` | 完整技术流程 + 全部实战坑位（LevelDB 配置位置、免 sudo venv、显示号探测等） |
| `README.md` | 本文件——给同事的快速上手指南 |

## 待办

- x11vnc 与 websockify 开机自启（systemd user 服务）
- 如需公网/跨网段使用：websockify 加 `--cert` 自签证书走 wss，或套 SSH 隧道（局域网内明文可接受）
