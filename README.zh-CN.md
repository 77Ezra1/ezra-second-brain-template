# ezra-second-brain-template 中文说明

> 把 Telegram / Agent 对话变成一个可追溯、可查询、可复盘的本地 Markdown 外脑。

`ezra-second-brain-template` 是一套**文件系统优先**的个人外脑模板：你随口说一句“外脑，记一下……”，系统会把原始输入、结构化笔记、待办、日报、消费、文章和主题知识沉淀到本地文件里。

它不是一个笨重的 Notion/Jira 替代品，而是一套更适合 Agent 的本地知识底座：

```text
随手说一句 → raw 原文保留 → Markdown/JSONL 结构化 → 可查询/可复盘/可迁移
```

## 为什么做这个

很多个人知识库的问题是：

- 入口太重，记录成本高；
- 数据在平台里，迁移困难；
- 记录很多，但后续查不到、用不上；
- Agent 能聊天，但没有一个稳定的长期本地记忆层。

这套系统的目标是反过来：

- **输入足够轻**：Telegram / CLI / 任意 Agent 都能写入；
- **存储足够朴素**：Markdown + JSONL，没有数据库锁定；
- **检索足够确定**：常见查询走规则路由，不全靠 LLM 猜；
- **隐私足够清楚**：你的真实数据留在本地，不随模板开源。

## 适合谁

- 想用 Telegram 当随身记录入口的人；
- 想给 Claude Code / Codex / Cursor / Hermes 配一个本地知识库的人；
- 想自动生成工作日报、明日安排、待办的人；
- 想把文章、文档、消费、想法沉淀成 Markdown 的人；
- 想二次开发一套个人外脑系统的人。

## 功能速览

| 能力 | 说明 | 示例 |
|---|---|---|
| 快速记录 | 保存 raw / inbox / daily note | `外脑：今天开项目会` |
| 本地查询 | 从 Markdown / JSONL 查记录 | `外脑？今天记录了什么` |
| 工作日报 | 生成 `今日复盘 / 明日安排` | `python scripts/work_report.py --review-day today` |
| 待办管理 | 创建、完成、取消行动项 | `外脑待办：统一素材命名规则` |
| 文章归档 | URL / 粘贴正文 / 文档入库 | `外脑存文章：https://example.com` |
| 主题沉淀 | 文章和记录沉淀到 topic page | `外脑？人设IP 方法论` |
| 消费记录 | 轻量记账与本地查询 | `外脑：今天午饭花了28元` |
| Agent 安装 | 一段命令让任意 Agent 安装 | Python one-liner / npx |

完整命令清单见：[`docs/commands.zh-CN.md`](docs/commands.zh-CN.md)

## 一键安装

### 方式 A：复制给任意 Agent

把下面这段话发给你的 Agent 工具：

```text
请帮我安装 ezra-second-brain-template：
1. 在我的用户目录下创建 second-brain 工作区；
2. 从 https://github.com/77Ezra1/ezra-second-brain-template 获取模板；
3. 不要覆盖已有私人数据；
4. 复制 config/brain.example.yaml 为 config/brain.yaml；
5. 创建 data/raw、data/inbox、data/wiki、data/daily、data/reviews 等本地数据目录；
6. 运行 python -m pytest tests -q 和 python scripts/brain_cli.py validate 验证；
7. 最后告诉我安装路径和可用命令。
如果可以运行 shell，请优先使用项目提供的安装脚本：
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
```

### 方式 B：Python 一行安装

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
```

指定安装目录：

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --target ~/second-brain
```

### 方式 C：npx / npm 风格

```bash
npx github:77Ezra1/ezra-second-brain-template --target ~/second-brain
```

> npx 方式会调用 Python 安装脚本，因此目标环境仍需要 Python 3.11+。

## 10 秒体验

```bash
cd ~/second-brain

python scripts/telegram_brain_router.py \
  --text "外脑：今天开项目会，确认内容框架" \
  --source telegram \
  --data-dir ./data

python scripts/telegram_brain_router.py \
  --text "外脑？今天记录了什么" \
  --source telegram \
  --data-dir ./data
```

生成示例日报：

```bash
HERMES_SECOND_BRAIN_ROOT=./examples/data \
python scripts/work_report.py --review-day 2026-01-01 --plan-day 2026-01-02 --no-save
```

输出类似：

```text
1/1 今日复盘
1. 开项目会确认内容框架

1/2 明日安排
1. 暂无记录
```

## 常用命令

| 你想做什么 | 直接说 |
|---|---|
| 记录事情 | `外脑：今天完成了素材复盘` |
| 查今天 | `外脑？今天记录了什么` |
| 查消费 | `外脑？这个月主要开销是什么` |
| 存文章 | `外脑存文章：https://example.com/article` |
| 加待办 | `外脑待办：统一素材命名规则` |
| 完成待办 | `外脑完成：统一素材命名规则` |
| 生成总结 | `外脑总结：今天` |
| 生成问题 | `外脑提问：最近一周` |
| 修正记录 | `外脑修正：把午饭28改成32` |

完整版本：[`docs/commands.zh-CN.md`](docs/commands.zh-CN.md)

## 目录结构

```text
config/      配置文件示例；本地复制 brain.example.yaml 为 brain.yaml
scripts/     核心 CLI、路由、文章入库、日报生成、验证脚本
templates/   Markdown 模板
tests/       测试用例
examples/    虚构示例数据
docs/        架构、隐私、命令清单
```

安装后的私人数据建议放在：

```text
data/raw/
data/inbox/
data/wiki/
data/daily/
data/reviews/
```

## 隐私说明

这个仓库是模板，不应该提交你的真实数据。

不要提交：

- Telegram 原始消息；
- 消费记录；
- 工作日报；
- 私人文章归档；
- 飞书、GitHub、Telegram Token；
- `.env`、cookie、API key；
- 身份证、银行卡、手机号等敏感信息。

## 开发验证

```bash
npm run test
npm run validate

# 或者直接：
python -m pytest tests -q
python scripts/brain_cli.py validate
```

## License

MIT
