# macOS 安装指南

这份指南面向 macOS 用户，把 `ezra-second-brain-template` 安装成本地文件系统优先的外脑工作区。

## 前置条件

- macOS 12+ 推荐。
- Python 3.11+ 推荐。
- 可选：Node.js 18+，用于 `npx` 安装方式和 Playwright/网页抓取能力。

检查：

```bash
python3 --version
node --version   # 可选
```

## 一行安装

```bash
curl -fsSL https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-macos.sh | bash
```

默认安装到：

```text
~/second-brain
```

指定目录：

```bash
curl -fsSL https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-macos.sh | bash -s -- --target ~/second-brain
```

如果目录已经存在且你确认只补齐模板文件：

```bash
curl -fsSL https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-macos.sh | bash -s -- --target ~/second-brain --force
```

## Python fallback

```bash
python3 -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --platform macos --target ~/second-brain
```

## 安装后验证

```bash
cd ~/second-brain
python3 scripts/brain_cli.py validate
python3 scripts/telegram_brain_router.py --text "外脑：今天安装了本地外脑" --source cli --data-dir ./data
python3 scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source cli --data-dir ./data
```

预期：

- `validate` 输出 `Second Brain validation OK`。
- capture 会写入 `data/raw/`、`data/inbox/`、`data/wiki/`。
- query 能查回刚写入的记录并显示来源。

## 可选虚拟环境

```bash
cd ~/second-brain
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip pytest
python -m pytest tests -q
```

## 常用命令

```bash
python3 scripts/telegram_brain_router.py --text "外脑：今天完成了素材复盘" --source cli --data-dir ./data
python3 scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source cli --data-dir ./data
python3 scripts/telegram_brain_router.py --text "外脑待办：统一素材命名规则" --source cli --data-dir ./data
python3 scripts/work_report.py --review-day today --plan-day tomorrow
```

## 数据位置

安装器会生成：

```text
~/second-brain/config/brain.yaml
~/second-brain/data/raw/
~/second-brain/data/inbox/
~/second-brain/data/wiki/
~/second-brain/data/daily/
~/second-brain/data/reviews/
```

`config/brain.yaml` 中的 `root` 会指向你的本地 `data` 目录，`platform` 会写成 `macos`。

## 隐私提醒

真实记录在本地 `data/` 里。不要把 `data/`、`.env`、token、cookie 或个人记录提交到公开仓库。
