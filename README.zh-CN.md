# ezra-second-brain-template 中文说明

一个**文件系统优先**的个人外脑模板，适合接入 Telegram、Hermes 或其他 Agent 工具使用。

它把日常输入保存为本地 Markdown / JSONL 文件，再通过确定性脚本完成：记录、查询、日报、待办、文章归档、消费记录和知识主题沉淀。

> 核心理念：**原始输入不丢失，结构化知识可追溯，私人数据默认留在本地。**

## 适合谁

- 想用 Telegram / 聊天入口随手记录信息的人；
- 想搭一个本地 Markdown 外脑的人；
- 想让 Agent 帮自己维护日报、待办、文章笔记、消费记录的人；
- 想开源/二次开发一套轻量个人知识库系统的人。

## 功能

- **低摩擦记录**：支持 `外脑：...`、`外脑？...`、`外脑待办：...` 等自然命令。
- **文件系统优先**：Markdown / JSONL 是主数据源，不依赖数据库。
- **日报生成**：支持 `今日复盘 / 明日安排` 格式的工作日报。
- **待办管理**：支持创建、完成、取消轻量行动项。
- **文章归档**：支持 URL、粘贴全文、本地文档入库。
- **主题沉淀**：文章和记录可以沉淀到 `wiki/topics/`。
- **隐私优先**：模板仓库只包含虚构示例数据，不包含真实私人数据。

## 一键安装方式

### 方式 A：给任意 Agent 的安装指令

把下面这段话复制给你的 Agent 工具，例如 Hermes、Claude Code、Codex、Cursor Agent 等：

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

适合绝大多数 Agent / 终端环境：

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"
```

指定安装目录：

```bash
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --target ~/second-brain
```

### 方式 C：npx / npm 方式

如果你的环境有 Node.js：

```bash
npx github:77Ezra1/ezra-second-brain-template --target ~/second-brain
```

> 注意：这个方式依赖 npm 能从 GitHub 安装包；最通用的方式仍然是上面的 Python 一行安装。

## 本地使用

安装后进入目录：

```bash
cd ~/second-brain
```

记录一条内容：

```bash
python scripts/telegram_brain_router.py --text "外脑：今天开项目会，确认内容框架" --source telegram --data-dir ./data
```

查询今天记录：

```bash
python scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source telegram --data-dir ./data
```

添加待办：

```bash
python scripts/telegram_brain_router.py --text "外脑待办：整理素材命名规则" --source telegram --data-dir ./data
```

生成示例日报：

```bash
HERMES_SECOND_BRAIN_ROOT=./examples/data python scripts/work_report.py --review-day 2026-01-01 --plan-day 2026-01-02 --no-save
```

## 目录结构

```text
config/      配置文件示例；本地复制 brain.example.yaml 为 brain.yaml
scripts/     核心 CLI、路由、文章入库、日报生成、验证脚本
templates/   Markdown 模板
tests/       测试用例
examples/    虚构示例数据
docs/        架构、隐私、安装说明
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
- 任何身份证、银行卡、手机号等敏感信息。

## 开发验证

```bash
python -m pytest tests -q
python scripts/brain_cli.py validate
```

## License

MIT
