# Windows 安装指南

这份指南面向 Windows 用户，把 `ezra-second-brain-template` 安装成本地文件系统优先的外脑工作区。推荐使用 PowerShell。

## 前置条件

- Windows 10/11。
- Python 3.11+ 推荐。安装时勾选 “Add python.exe to PATH”，或使用 Windows Python Launcher `py`。
- 可选：Node.js 18+，用于 `npx` 安装方式和 Playwright/网页抓取能力。

检查：

```powershell
py -3 --version
node --version   # 可选
```

如果 `py -3` 不可用，尝试：

```powershell
python --version
```

## 一行安装

在 PowerShell 里运行：

```powershell
irm https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-windows.ps1 | iex
```

默认安装到：

```text
%USERPROFILE%\second-brain
```

指定目录：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-windows.ps1))) -Target "$HOME\second-brain"
```

如果目录已经存在且你确认只补齐模板文件：

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-windows.ps1))) -Target "$HOME\second-brain" -Force
```

## Python fallback

```powershell
py -3 -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --platform windows --target "$HOME\second-brain"
```

如果没有 `py`，用：

```powershell
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --platform windows --target "$HOME\second-brain"
```

## 安装后验证

```powershell
cd $HOME\second-brain
py -3 scripts\brain_cli.py validate
py -3 scripts\telegram_brain_router.py --text "外脑：今天安装了本地外脑" --source cli --data-dir .\data
py -3 scripts\telegram_brain_router.py --text "外脑？今天记录了什么" --source cli --data-dir .\data
```

预期：

- `validate` 输出 `Second Brain validation OK`。
- capture 会写入 `data\raw\`、`data\inbox\`、`data\wiki\`。
- query 能查回刚写入的记录并显示来源。

## 可选虚拟环境

```powershell
cd $HOME\second-brain
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip pytest
python -m pytest tests -q
```

如果 PowerShell 阻止激活脚本，可以仅在当前进程放宽策略：

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

## 常用命令

```powershell
py -3 scripts\telegram_brain_router.py --text "外脑：今天完成了素材复盘" --source cli --data-dir .\data
py -3 scripts\telegram_brain_router.py --text "外脑？今天记录了什么" --source cli --data-dir .\data
py -3 scripts\telegram_brain_router.py --text "外脑待办：统一素材命名规则" --source cli --data-dir .\data
py -3 scripts\work_report.py --review-day today --plan-day tomorrow
```

## 数据位置

安装器会生成：

```text
%USERPROFILE%\second-brain\config\brain.yaml
%USERPROFILE%\second-brain\data\raw\
%USERPROFILE%\second-brain\data\inbox\
%USERPROFILE%\second-brain\data\wiki\
%USERPROFILE%\second-brain\data\daily\
%USERPROFILE%\second-brain\data\reviews\
```

`config/brain.yaml` 中的 `root` 会指向你的本地 `data` 目录，`platform` 会写成 `windows`。配置里会使用 Python 可读的 `/` 路径格式，脚本在 Windows 上可正常识别。

## 隐私提醒

真实记录在本地 `data\` 里。不要把 `data\`、`.env`、token、cookie 或个人记录提交到公开仓库。
