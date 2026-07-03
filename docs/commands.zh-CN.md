# 外脑命令清单

这份清单把 `ezra-second-brain-template` 里最常用的聊天命令和本地 CLI 命令集中放在一起，方便复制给 Telegram、Hermes 或任意 Agent 工具。

## Telegram / Agent 入口命令

> 默认入口脚本：`scripts/telegram_brain_router.py`  
> 推荐测试时都加：`--data-dir ./data`，避免污染真实资料。

| 场景 | 命令格式 | 示例 | 结果 |
|---|---|---|---|
| 快速记录 | `外脑：<内容>` | `外脑：今天开项目会，确认内容框架和下周安排` | 写入 raw / inbox / daily note，并按内容分类 |
| 自然语言记录 | `外脑，记一下<内容>` | `外脑，记一下今天跟团队复盘了素材产出问题` | Agent 可转为 capture 流程 |
| 查询外脑 | `外脑？<问题>` | `外脑？今天记录了什么` | 从本地 Markdown / JSONL 查询并返回来源 |
| 查询消费 | `外脑？这个月主要开销是什么` | `外脑？这个月总消费多少` | 汇总本月消费记录 |
| 查询主题 | `外脑？<主题>` | `外脑？人设IP 方法论` | 优先查询 `wiki/topics/` 主题页 |
| 记录文章 URL | `外脑存文章：<URL>` | `外脑存文章：https://example.com/article` | 抓取/归档文章，生成结构化笔记 |
| 文档 / OCR 入库 | `外脑存文章OCR：<路径或URL>` | `外脑存文章OCR：C:/docs/report.pdf` | 尝试抽取文档文本和图片 OCR |
| 生成总结 | `外脑总结：<范围>` | `外脑总结：今天` | 生成 daily / weekly / monthly review |
| 生成问题 | `外脑提问：<范围>` | `外脑提问：最近一周` | 基于记录生成反思问题 |
| 修正记录 | `外脑修正：<说明>` | `外脑修正：把午饭28改成午饭32` | 尝试修正近期记录 |
| 新增待办 | `外脑待办：<事项>` | `外脑待办：统一素材命名规则` | 写入 `wiki/actions/open.md` |
| 完成待办 | `外脑完成：<事项>` | `外脑完成：统一素材命名规则` | 从 open 移到 completed |
| 取消待办 | `外脑取消：<事项>` | `外脑取消：旧版素材整理方案` | 从 open 移到 cancelled |
| 记录日报复盘 | `外脑：今日复盘...` | `外脑：今日复盘，跟进KOC投放，整理竞品数据` | 可进入工作日报源数据 |
| 记录明日安排 | `外脑：明日安排...` | `外脑：明日安排，根据KOC数据调整随心推` | 写入 `daily/work_report.jsonl` 和安排记录 |

## Router 命令示例

```bash
python scripts/telegram_brain_router.py --text "外脑：今天开项目会，确认内容框架" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑？今天记录了什么" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑待办：统一素材命名规则" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑完成：统一素材命名规则" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑存文章：https://example.com/article" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑总结：今天" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑提问：最近一周" --source telegram --data-dir ./data
python scripts/telegram_brain_router.py --text "外脑修正：把午饭28改成午饭32" --source telegram --data-dir ./data
```

## 本地 CLI 命令

| 命令 | 示例 | 说明 |
|---|---|---|
| `capture` | `python scripts/brain_cli.py capture --text "今天午饭花了28元" --source telegram` | 直接捕获一条记录 |
| `query` | `python scripts/brain_cli.py query --text "这个月主要开销是什么"` | 查询本地外脑 |
| `article` | `python scripts/brain_cli.py article --url "https://example.com" --title "Example"` | 手动创建文章笔记 |
| `article --payload-json` | `python scripts/brain_cli.py article --url "https://example.com" --payload-json payload.json` | 用结构化 payload 入库文章 |
| `summary` | `python scripts/brain_cli.py summary --scope today` | 生成总结 |
| `questions` | `python scripts/brain_cli.py questions --scope "最近一周"` | 生成反思问题 |
| `correction` | `python scripts/brain_cli.py correction --text "把午饭28改成32"` | 修正记录 |
| `paths` | `python scripts/brain_cli.py paths --type daily --date 2026-01-01` | 查看某类记录路径 |
| `validate` | `python scripts/brain_cli.py validate` | 校验目录结构 |
| `rebuild-index` | `python scripts/brain_cli.py rebuild-index` | 重建索引 |

## 日报命令

```bash
# 用示例数据生成日报
HERMES_SECOND_BRAIN_ROOT=./examples/data \
python scripts/work_report.py --review-day 2026-01-01 --plan-day 2026-01-02 --no-save

# 用当前数据生成今天日报
python scripts/work_report.py --review-day today --plan-day tomorrow

# 生成指定日期日报
python scripts/work_report.py --review-day 2026-01-01 --plan-day 2026-01-02
```

## 飞书 / Lark CLI 增强命令

如果想连接飞书云文档、多维表格和可视化看板，可以安装 `lark-cli`：

```bash
npm install -g @larksuite/cli
npx -y skills add https://open.feishu.cn --skill -y
lark-cli --version
```

绑定和授权：

```bash
lark-cli config bind --source hermes --identity user-default
LARK_CLI_SUPPRESS_NOTICE=1 lark-cli auth login --recommend --no-wait --json
LARK_CLI_SUPPRESS_NOTICE=1 lark-cli auth status --json --verify
```

多维表格同步配置写在本地 `config/brain.yaml`，不要提交到公开仓库：

```yaml
lark_expense_sync:
  enabled: true
  base_token: "你的多维表格 base token"
  table_id: "你的 table id"
  identity: user
```

完整说明见：[`docs/feishu-lark-cli.zh-CN.md`](feishu-lark-cli.zh-CN.md)

## 安装命令

```bash
# Python 一行安装
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())"

# 指定安装目录
python -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --target ~/second-brain

# npx / Node 风格
npx github:77Ezra1/ezra-second-brain-template --target ~/second-brain
```

## 给任意 Agent 的安装提示词

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
