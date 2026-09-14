---
name: windows-file-lock
description: 定位 Windows 上"文件/文件夹正在使用、操作无法完成、被另一程序打开/占用"弹窗背后的进程。Use whenever the user reports a file or folder that cannot be deleted, renamed, or moved ("文件(夹)正在使用", "file/folder in use", "being used by another process", 删除/重命名失败), shows a screenshot of such a dialog, or asks which process is locking/occupying a path — even if they just say "删不掉" or paste an error image without more words.
---

# Windows 文件占用排查

目标：找出持有目标路径子树内句柄的进程（PID），并安全解除。

## 核心判定规则

删除/重命名文件夹 X 被阻止 ⟺ 有进程持有 **X 子树内部**的文件或目录句柄。
只有 X **父目录**的句柄（如资源管理器窗口停在父目录）**不构成阻塞**——别把无辜者误判为凶手。

## 快速路径：Sysinternals handle64（首选，通常一步命中）

已安装则直接用；未安装则下载（`download.sysinternals.com` 的可达性远好于 `live.sysinternals.com`）：

```bash
curl -sL --max-time 45 "https://download.sysinternals.com/files/Handle.zip" -o /tmp/handle.zip \
  && unzip -o /tmp/handle.zip handle64.exe -d /tmp
```

查询时用**不含中文的路径前缀子串**（控制台会把中文回显成 `??`，但匹配不受影响）：

```bash
/tmp/handle64.exe -accepteula -nobanner "ClaudeWorkspace\\test\\harness"
```

输出解读（真实案例）：

```
explorer.exe       pid: 16680  type: File   447C: E:\ClaudeWorkspace\test            ← 父目录句柄，无害
CodeBuddy CN.exe   pid: 19836  type: File    5A0: E:\ClaudeWorkspace\test            ← 父目录句柄
CodeBuddy CN.exe   pid: 19836  type: File    590: E:\...\test\harness终端\.git        ← 真凶：树内目录句柄
```

无需管理员权限即可查询同用户会话的进程。

## 备选一：谁的工作目录(CWD)停在目标树里

handle64 拿不到或想缩小嫌疑面时用 `scripts/find_cwd.ps1`（读各进程 PEB 的 CurrentDirectory）：

```bash
powershell -NoProfile -ExecutionPolicy Bypass \
  -File ~/.agents/skills/windows-file-lock/scripts/find_cwd.ps1 -PathPrefix 'E:\ClaudeWorkspace\test'
```

注意局限：CWD 在**父目录**≠阻塞子文件夹删除，仅作嫌疑排序线索。真实案例中 CWD 扫描把矛头指向 CodeBuddy 实例，与 handle64 结论互相印证。

## 备选二：Restart Manager 查打开的数据文件

`scripts/rm_scan.ps1` 用安装器同款 API 报告哪些进程打开了目标内被采样的文件：

```bash
powershell -NoProfile -ExecutionPolicy Bypass \
  -File ~/.agents/skills/windows-file-lock/scripts/rm_scan.ps1 -Parent 'E:\ClaudeWorkspace\test' -NameFilter 'harness'
```

已知局限（本次实测踩过）：它查不到**纯目录句柄和 CWD 占用**——案例中扫了 170 个文件全部为空，最后靠 handle64 命中的是 `.git` 目录句柄。RM 返回空 ≠ 没人占用。

## PowerShell 三大坑（本机验证过，防绕弯路）

1. Git Bash 里 `powershell -Command "...$var..."` 的 `$var` 会被 bash 吞掉 → 一律写成 `.ps1` 文件用 `-File` 执行。
2. Windows PowerShell 5.1 把 UTF-8 无 BOM 的 .ps1 当 GBK 解析 → 脚本里的中文注释能直接炸出语法错误 → 自写脚本保持纯 ASCII；中文路径参数在命令行传参也可能乱码 → 支持 `-NameFilter` 英文子串兜底发现。
3. 输出中文乱码：脚本开头加 `[Console]::OutputEncoding = [System.Text.Encoding]::UTF8`，输出里 `??` 只影响显示不影响匹配。

## 结案处置

报告给用户：PID / 进程名 / 可执行路径 / 启动时间 / 具体占用的句柄，例如：

> 占用者是 CodeBuddy CN.exe (PID 19836)，今天 09:50 启动，持有 `...\harness终端\.git` 目录句柄。

- 先建议温和解除：在对应应用里关闭该项目/窗口（IDE、AI 编程工具如 CodeBuddy/VS Code/Cursor、node dev server、停在目录里的终端都是常见元凶）。用户点对话框"重试"验证。
- 需要强杀时（可能丢失应用未保存状态，必须先征得用户同意）：`taskkill /PID <pid> /F`。

## 附：自研句柄遍历偏移备忘（handle64 彻底不可得时）

- `NtQuerySystemInformation(64=SystemExtendedHandleInformation)`：缓冲区头 16 字节 = NumberOfHandles + Reserved，条目数组从 **+16** 开始；x64 每条 40 字节：Object@0, PID@8, Handle@16, GrantedAccess@24, ObjectTypeIndex@**30**（不是 34）。
- 读 CWD（x64）：PEB->ProcessParameters@PEB+0x20；`CurrentDirectory.DosPath` 的 Length@PP+**0x38**、Buffer 指针@PP+**0x40**（0x40 是缓冲区指针字段本身，UNICODE_STRING 起点是 0x38）。
- `NtQueryObject(ObjectNameInformation)` 对某些管道句柄会**永久挂起**：跳过 GrantedAccess==0x0012019F / 0x001A019F / 无 READ_CONTROL(0x20000) 位者；全表扫描限定白名单 PID + 300s 超时兜底。
