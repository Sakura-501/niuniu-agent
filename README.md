# niuniu-agent

`niuniu-agent` 是一个面向腾讯智能渗透挑战赛主赛场的基础版自主渗透 Agent。

当前版本的目标不是一次性做完全部赛道策略，而是先把最核心的无人值守骨架跑通：

- 只接入主赛场
- 只使用官方 MCP
- 支持 `debug` / `competition` 两种运行模式
- 支持四赛道策略路由骨架
- 支持结构化日志和本地状态持久化

后续如果要做 UI、任务控制面板、日志可视化，直接在这个基础上扩展即可。

## 1. 当前能力

当前版本已经实现：

- 官方主赛场 MCP 接入
- 赛题列表获取、实例启动、Flag 提交、提示查看、实例停止
- Agent 主控循环
- 四赛道策略注册表
- 本地执行工具箱
  - HTTP 请求
  - Shell 命令执行
  - Python 片段执行
- 运行日志落盘
- 已提交 Flag 去重

当前版本暂未实现：

- Web UI 控制台
- 真正有针对性的四赛道深度策略
- 后台守护和自动自启动脚本

## 2. 目录说明

核心目录如下：

- `src/niuniu_agent/config.py`
  - 配置加载
- `src/niuniu_agent/contest_mcp.py`
  - 官方 MCP 适配层
- `src/niuniu_agent/controller.py`
  - Agent 主控逻辑
- `src/niuniu_agent/strategies/`
  - 四赛道策略骨架
- `src/niuniu_agent/tooling.py`
  - 本地工具执行层
- `src/niuniu_agent/llm.py`
  - 基于 OpenAI 兼容接口的工具调用循环
- `runtime/events.jsonl`
  - 结构化事件日志
- `runtime/state.db`
  - 本地状态数据库

## 3. 环境变量

把 `.env.example` 复制为 `.env` 后，至少需要填写以下变量：

- `NIUNIU_AGENT_MODEL`
- `NIUNIU_AGENT_MODEL_BASE_URL`
- `NIUNIU_AGENT_MODEL_API_KEY`
- `NIUNIU_AGENT_CONTEST_HOST`
- `NIUNIU_AGENT_CONTEST_TOKEN`

示例：

```bash
cp .env.example .env
```

`.env` 内容示例：

```bash
NIUNIU_AGENT_MODE=debug
NIUNIU_AGENT_MODEL=ep-jsc7o0kw
NIUNIU_AGENT_MODEL_BASE_URL=https://tokenhub.tencentmaas.com/v1
NIUNIU_AGENT_MODEL_API_KEY=replace-me
NIUNIU_AGENT_CONTEST_HOST=10.0.0.44:8000
NIUNIU_AGENT_CONTEST_TOKEN=replace-me
NIUNIU_AGENT_POLL_INTERVAL_SECONDS=15
```

## 4. 本地启动教程

### 4.1 使用 `uv`

如果本地安装了 `uv`，推荐直接这样启动：

```bash
uv sync
cp .env.example .env
```

加载环境变量：

```bash
set -a
source .env
set +a
```

执行一次调试模式：

```bash
uv run niuniu-agent run --mode debug --once
```

指定赛题执行一次：

```bash
uv run niuniu-agent run --mode debug --once --challenge-code <challenge_code>
```

以无人值守循环方式运行：

```bash
uv run niuniu-agent run --mode competition
```

### 4.2 不使用 `uv`

如果机器没有 `uv`，可以用标准 Python 虚拟环境：

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

然后同样加载环境变量并启动：

```bash
set -a
source .env
set +a
niuniu-agent run --mode debug --once
```

## 5. 两种运行模式

### 5.1 `debug` 模式

适合调试期使用。

特点：

- 启动后进入交互式对话
- Agent 会自动刷新赛题列表
- 对话中能知道哪些题已完成、哪些题仍未完成
- 对话中可以通过 MCP 工具自动启动赛题、停题、看提示、提交 Flag
- 适合联调、排障、观察策略行为

推荐命令：

```bash
niuniu-agent run --mode debug
```

### 5.2 `competition` 模式

适合切到正式答题模式后使用。

特点：

- 长时间循环运行
- 自动拉题
- 自动选题
- 自动启动实例和停止实例
- 适合无人值守

推荐命令：

```bash
niuniu-agent run --mode competition
```

## 6. 调试机部署教程

如果调试机可以直接访问公共 GitHub 仓库，推荐按下面流程部署。

### 6.1 首次部署

```bash
git clone https://github.com/Sakura-501/niuniu-agent.git
cd niuniu-agent
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
cp .env.example .env
```

然后编辑 `.env`，填入比赛主赛场的：

- `NIUNIU_AGENT_CONTEST_HOST`
- `NIUNIU_AGENT_CONTEST_TOKEN`
- 模型网关地址和模型 API Key

### 6.2 更新代码

```bash
cd ~/niuniu-agent
git pull --ff-only origin main
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

### 6.3 调试模式验证

```bash
cd ~/niuniu-agent
. .venv/bin/activate
set -a
source .env
set +a
niuniu-agent run --mode debug --once
```

### 6.4 正式答题前建议

官方规则是：

- 调试阶段可以 SSH
- 答题阶段切换后 SSH 会断开
- Agent 必须在切换前就已经启动

因此推荐流程是：

1. 在调试模式下完成部署和联调
2. 在调试机上先启动 `competition` 模式
3. 确认日志正常滚动
4. 再去官方平台切换到答题模式

## 7. 日志与状态文件

运行过程中最重要的两个文件：

- `runtime/events.jsonl`
- `runtime/state.db`

### 7.1 `events.jsonl`

这是后续 UI 最直接的数据源，当前已经会记录类似事件：

- `agent.started`
- `challenge.selected`
- `challenge.started`
- `challenge.completed`
- `flag.submitted`

查看方法：

```bash
tail -f runtime/events.jsonl
```

### 7.2 `state.db`

这里会保存：

- 已提交过的 Flag
- 去重状态

这样可以避免重复提交已经提交成功的 Flag。

## 8. 测试命令

本地或调试机都可以直接运行：

### 8.1 全量测试

```bash
python -m pytest -v
```

如果使用 `uv`：

```bash
uv run pytest -v
```

### 8.2 只测某一项

```bash
python -m pytest tests/test_controller.py -v
```

## 9. 已验证的内容

当前仓库已经验证过：

- 本地全量测试通过
- 调试机全量测试通过
- 调试机可以匿名 `git clone` 公共仓库
- 调试机可以通过官方 MCP 成功获取赛题列表
- 调试机可以真实执行一次 `niuniu-agent run --mode debug --once`
- 运行后 `runtime/events.jsonl` 能看到完整执行事件

## 10. 常见问题

### 10.1 调试机没有 `uv`

直接用 `venv + pip` 即可，不依赖 `uv`。

### 10.2 调试机没有 `pip` 或 `venv`

Ubuntu 上安装：

```bash
sudo apt-get update
sudo apt-get install -y python3-pip python3.12-venv
```

### 10.3 `niuniu-agent run` 报命令错误

请先更新到最新版本：

```bash
git pull --ff-only origin main
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

### 10.4 如何判断 Agent 是否真的在跑

最简单的方法就是看：

```bash
tail -f runtime/events.jsonl
```

如果持续出现：

- `agent.started`
- `challenge.selected`
- `challenge.started`

说明主控链路已经在执行。

## 11. 下一步建议

当前基础版已经适合继续往下做两类工作：

1. 加 UI
   - 日志展示
   - 启停控制
   - 模式切换
2. 强化赛道策略
   - 按四赛道补提示词
   - 增加更强的本地工具
   - 增加更细的选题和重试策略
