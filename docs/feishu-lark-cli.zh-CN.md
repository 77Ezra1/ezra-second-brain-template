# 飞书 / Lark CLI 集成指南

`ezra-second-brain-template` 默认是本地文件系统外脑；如果你希望把外脑连接到飞书云文档、飞书多维表格，并用 Base 做消费/数据可视化，可以额外安装 `lark-cli`。

> 这一步是可选增强，不影响本地 Markdown 外脑使用。

## 能带来什么

| 能力 | 说明 |
|---|---|
| 飞书云文档 | 读取、创建、整理飞书文档 / 云空间内容 |
| 多维表格 Base | 把消费、日报、项目数据同步到多维表格 |
| 可视化图表 | 基于 Base 字段创建统计视图、分类看板、趋势图 |
| Agent 自动化 | 让 Agent 能把本地外脑内容同步到飞书协作空间 |

## 安装 lark-cli

需要 Node.js / npm。

```bash
npm install -g @larksuite/cli
npx -y skills add https://open.feishu.cn --skill -y
lark-cli --version
```

如果网络较慢，可以配置代理后重试：

```bash
export HTTP_PROXY=http://127.0.0.1:7897
export HTTPS_PROXY=http://127.0.0.1:7897
export ALL_PROXY=socks5://127.0.0.1:7897
```

## 绑定 Hermes / Agent 环境

如果你的 Agent 环境已经有飞书应用凭证，可以绑定：

```bash
lark-cli config bind --source hermes --identity user-default
```

如果提示缺少 `FEISHU_APP_ID` / `FEISHU_APP_SECRET`，需要先在本机环境或 `.env` 中配置：

```env
FEISHU_APP_ID=你的飞书应用 App ID
FEISHU_APP_SECRET=你的飞书应用 App Secret
```

> 不要把 App Secret 提交到 GitHub，也不要写进公开仓库。

## 用户授权

启动授权：

```bash
LARK_CLI_SUPPRESS_NOTICE=1 lark-cli auth login --recommend --no-wait --json
```

按照输出里的链接或二维码完成授权后，再验证：

```bash
LARK_CLI_SUPPRESS_NOTICE=1 lark-cli auth status --json --verify
```

看到 `verified: true` 基本说明授权成功。

## 推荐飞书权限范围

如果你想让外脑同时支持云文档、多维表格、日历、妙记等能力，可以在飞书开放平台给应用添加这些能力/权限：

```text
docs drive sheets base calendar minutes task im contact wiki
```

只做多维表格可视化，重点是：

```text
base sheets drive docs
```

## 多维表格配置

本模板默认关闭飞书同步。你可以在本地 `config/brain.yaml` 中启用：

```yaml
lark_expense_sync:
  enabled: true
  base_token: "你的多维表格 base token"
  table_id: "你的 table id"
  identity: user
```

启用后，消费记录等数据可以同步到飞书 Base，再在飞书里配置：

- 按分类统计支出；
- 按月份看趋势；
- 按二级分类拆分；
- 做个人消费看板；
- 做日报 / 项目数据看板。

## 给 Agent 的安装提示词

```text
请帮我给 ezra-second-brain-template 安装飞书/Lark CLI 增强：
1. 检查 node/npm 是否可用；
2. 安装 @larksuite/cli；
3. 执行 npx -y skills add https://open.feishu.cn --skill -y；
4. 绑定到当前 Agent/Hermes 环境；
5. 引导我完成飞书用户授权；
6. 运行 lark-cli auth status --json --verify 验证；
7. 不要把 FEISHU_APP_SECRET、base_token、table_id 写入公开仓库。
```

## 隐私提醒

- `FEISHU_APP_SECRET` 是敏感凭证，不要发到公开 issue、README 或 git commit。
- `base_token` / `table_id` 虽然不是传统密码，但也可能暴露你的飞书数据结构，建议只放本地配置。
- GitHub 开源仓库只应该保留 `config/brain.example.yaml`，不要提交真实 `config/brain.yaml`。
