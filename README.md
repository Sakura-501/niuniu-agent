# niuniu-agent

`niuniu-agent` 是一个面向腾讯智能渗透挑战赛主赛场的异步自主渗透 Agent。

这次版本不是在旧实现上继续打补丁，而是按 `learn-claude-code` 的主线思路重构：

- `agent loop`
- `tool control plane`
- `memory / state`
- `autonomous runtime`
- `MCP integration`

同时底层执行改成了 `openai-agents`，模型调用使用 `OpenAIChatCompletionsModel`，适配比赛环境常见的 OpenAI 兼容网关。

当前主循环已经收敛成更接近 `learn-claude-code` / `base_agent` 的显式形态：

- 模型有工具调用就继续
- 工具结果写回消息历史
- 模型没有工具调用才结束当前回合

## 1. 当前架构

重构后的代码按下面几层组织：

- `src/niuniu_agent/control_plane/`
  - 赛题快照、完成态、选题和确定性控制逻辑
- `src/niuniu_agent/agent_stack/`
  - `openai-agents` 的 model、tool bus、manager agent、track specialists
- `src/niuniu_agent/runtime/`
  - `debug` 交互式 REPL
  - `competition` 不停机自主循环
- `src/niuniu_agent/state_store.py`
  - 本地状态和已提交 flag 记忆
- `src/niuniu_agent/contest_mcp.py`
  - 官方主赛场 MCP 客户端

## 2. 两种运行模式

### 2.1 `debug`

这是交互式对话模式，不是“一次跑完就退出”的脚本模式。

特点：

- 持久对话会话
- 启动后自动刷新当前赛题状态
- 模型可直接调用官方 MCP 工具
- 模型也可调用本地 HTTP / shell / Python 工具
- 支持中文输入
- 会输出工具轨迹，便于排查 agent 在做什么

启动方式：

```bash
niuniu-agent run --mode debug
```

### 2.2 `competition`

这是无人值守模式。

特点：

- 外层循环不会主动停止
- 遇到错误会记录日志并自动重试
- 空闲时会继续轮询赛题
- 适合比赛阶段提前启动后持续运行

启动方式：

```bash
niuniu-agent run --mode competition
```

## 3. 控制平面与 agent 分工

为了避免“模型既负责推理又负责维护全局状态”这种混乱结构，这次重构明确分层：

### 控制平面

由 Python 代码负责：

- 获取赛题列表
- 解析官方返回
- 判断哪些赛题已完成
- 维护本地 flag 去重状态
- 给 agent 构造当前挑战快照

### Agent 层

由 `openai-agents` 负责：

- manager agent 统一调度
- specialist agents 负责不同赛道侧重点
- 工具调用与 handoff
- 持久会话驱动的交互调试

这和 `learn-claude-code` 的核心思想是一致的：

> 模型负责思考，代码负责工作环境和状态控制。

## 4. 使用的 OpenAI Agents 方式

当前实现使用：

- `Agent`
- `Runner`
- `SQLiteSession`
- `function_tool`
- `MCPServerStreamableHttp`
- `OpenAIChatCompletionsModel`

这样做的目的：

- 支持异步 agent loop
- 支持 persistent session
- 支持 MCP tools + 本地 tools 混合
- 支持 OpenAI 兼容网关，而不强依赖 Responses API

## 5. 环境变量

复制 `.env.example` 到 `.env`：

```bash
cp .env.example .env
```

至少需要配置：

- `NIUNIU_AGENT_MODEL`
- `NIUNIU_AGENT_MODEL_BASE_URL`
- `NIUNIU_AGENT_MODEL_API_KEY`
- `NIUNIU_AGENT_CONTEST_HOST`
- `NIUNIU_AGENT_CONTEST_TOKEN`

当前推荐示例：

```bash
NIUNIU_AGENT_MODE=debug
NIUNIU_AGENT_MODEL=ep-jsc7o0kw
NIUNIU_AGENT_MODEL_BASE_URL=https://tokenhub.tencentmaas.com/v1
NIUNIU_AGENT_MODEL_API_KEY=replace-me
NIUNIU_AGENT_CONTEST_HOST=10.0.0.44:8000
NIUNIU_AGENT_CONTEST_TOKEN=replace-me
NIUNIU_AGENT_POLL_INTERVAL_SECONDS=15
```

## 6. 本地启动

### 6.1 用 `uv`

```bash
uv sync
cp .env.example .env
set -a
source .env
set +a
uv run niuniu-agent run --mode debug
```

无人值守模式：

```bash
uv run niuniu-agent run --mode competition
```

### 6.2 不用 `uv`

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
set -a
source .env
set +a
niuniu-agent run --mode debug
```

## 7. 调试机用法

### 7.1 更新

如果调试机到 GitHub 网络正常：

```bash
cd ~/niuniu-agent
git pull --ff-only origin main
. .venv/bin/activate
python -m pip install -e '.[dev]'
```

### 7.2 一键控制脚本

脚本路径：

```bash
scripts/remote_control.sh
```

支持命令：

- `update`
- `debug`
- `debug-update`
- `competition-start`
- `competition-restart`
- `competition-stop`
- `competition-status`
- `logs`

当前语义：

- `debug`
  - 不自动更新
  - 直接启动交互式调试
- `debug-update`
  - 先更新，再进入调试
- `competition-start`
  - 不自动更新
  - 直接启动无人值守模式
- `competition-restart`
  - 先更新，再启动无人值守模式

示例：

```bash
bash scripts/remote_control.sh debug
```

```bash
bash scripts/remote_control.sh competition-start
```

```bash
bash scripts/remote_control.sh competition-status
```

## 8. 日志和状态

关键运行文件：

- `runtime/events.jsonl`
- `runtime/state.db`
- `runtime/sessions.sqlite3`
- `runtime/competition.log`
- `runtime/competition.pid`

说明：

- `events.jsonl`
  - 结构化事件日志
- `state.db`
  - 本地提交状态
- `sessions.sqlite3`
  - `debug` / `competition` 的持久会话

## 9. 测试

本地执行：

```bash
uv run pytest -v
```

或：

```bash
python -m pytest -v
```

## 10. 当前验证结果

当前版本已经验证：

- 本地测试通过
- 调试机可进入交互式 `debug`
- 调试机中文输入不再报 `UnicodeDecodeError`
- 调试机 `debug` 不会默认先 `update`
- 调试机控制脚本可执行

## 11. 下一步

这次重构已经把运行骨架切到 `learn-claude-code` 风格和 `openai-agents` 异步 runtime 上。

接下来最值得继续增强的是：

1. 赛道专用 specialist prompt 和 handoff 策略
2. `competition` 模式的持续恢复与更细粒度重试
3. 提示查看策略
4. Web UI / 日志可视化 / 运行控制面板
