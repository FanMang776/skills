# windows-file-lock

定位 Windows 上「文件/文件夹正在使用、操作无法完成、被另一程序打开」弹窗背后的占用进程,并安全解除。

## 解决的问题

删除 / 重命名 / 移动文件或文件夹时被系统拒绝,报「文件(夹)正在使用」「file/folder in use」「being used by another process」——本质是有进程持有目标子树内的句柄。本 skill 一条龙完成:**找出凶手 PID → 判定是否真阻塞 → 温和解除(或经同意后强杀)**。

## 文件结构

| 文件 | 用途 |
|---|---|
| `SKILL.md` | 完整排查流程 + 实战坑位笔记 |
| `scripts/find_cwd.ps1` | 扫描各进程 PEB,找出工作目录(CWD)停在目标树里的进程(备选线索) |
| `scripts/rm_scan.ps1` | 用 Restart Manager API 查打开目标内数据文件的进程(备选) |

## 排查顺序

1. **首选**:Sysinternals `handle64`(自动从 `download.sysinternals.com` 下载),一步命中持有句柄的进程。
2. `find_cwd.ps1`:handle64 不可得时,按 CWD 缩小嫌疑面。
3. `rm_scan.ps1`:查被打开的数据文件。注意已知局限——查不到纯目录句柄,RM 返回空 ≠ 没人占用。

## 核心判定规则

> 删除/重命名文件夹 X 被阻止 ⟺ 有进程持有 **X 子树内部**的句柄。
> 只持有 X **父目录**句柄(如资源管理器停在父目录)不构成阻塞,别误判。

## 已知坑(实战验证)

- Git Bash 内联 `powershell -Command "...$var..."` 的 `$var` 会被 bash 吞 → 一律写 `.ps1` 用 `-File` 执行。
- Windows PowerShell 5.1 把 UTF-8 无 BOM 的 .ps1 当 GBK → 脚本保持纯 ASCII。
- 中文路径在控制台回显为 `??`,只影响显示不影响 handle64 匹配;传参用英文子串 `-NameFilter` 兜底。

详见 `SKILL.md`,内含真实案例(CodeBuddy 持有 `.git` 目录句柄)与自研句柄遍历的内存偏移备忘。
