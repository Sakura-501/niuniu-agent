# niuniu-agent

`niuniu-agent` 是一个面向腾讯智能渗透挑战赛主赛场的异步自主渗透 Agent。

当前版本已经不是早期的单循环脚本，而是围绕下面几层组织：

- `control_plane`
- `agent_stack`
- `runtime`
- `state / telemetry`
- `skills / prompts`
- `web console`

目标是：

- `debug` 模式能交互式对话调试
- `competition` 模式能无人值守不停机运行
- 比赛控制面、状态、错误恢复和并发调度都由代码明确控制，而不是完全交给模型即兴决定
- `8081` Web UI 能查看 manager / worker / challenge 状态并在线调试
- 长时间卡题时会自动保存记忆并临时让位给未开始题

图示文档：

- [架构图与流程图](docs/architecture-and-flow.md)

## 1. 当前架构

### 1.1 控制平面 `control_plane`

位置：

- [challenge_store.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/control_plane/challenge_store.py)
- [contest_gateway.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/control_plane/contest_gateway.py)
- [models.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/control_plane/models.py)

职责：

- 获取主赛场 challenge 列表
- 解析 challenge 状态
- 判断哪些题已完成
- 选择下一个未完成 challenge
- 输出 challenge 快照供 agent 使用

### 1.2 Agent 栈 `agent_stack`

位置：

- [agent.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/agent_stack/agent.py)
- [tool_bus.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/agent_stack/tool_bus.py)
- [prompts.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/agent_stack/prompts.py)

职责：

- 使用 OpenAI 兼容接口运行显式 tool-use loop
- 不是只靠 SDK 黑盒 `Runner.run()` 控主循环
- 语义接近：

```python
if not tool_calls:
    return
results = []
```

也就是：

- 有工具调用就继续
- 工具结果回写消息历史
- 没有工具调用才结束当前轮次

### 1.3 Runtime `runtime`

位置：

- [debug_repl.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/debug_repl.py)
- [competition_loop.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/competition_loop.py)
- [coordinator.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/coordinator.py)
- [findings_bus.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/findings_bus.py)
- [recovery.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/recovery.py)

职责：

- `debug`
  - 交互式 REPL
  - 工具进度可见
  - 最终答案会做结构化整理
- `competition`
  - 外层循环不停
  - 最多 3 个并发 challenge worker
  - 统一 coordinator 管理
  - findings bus 共享阶段性结论
  - 错误自动恢复与退避

### 1.4 状态与日志

位置：

- [state_store.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/state_store.py)
- [telemetry.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/telemetry.py)

职责：

- 已提交 flag
- 当前活跃题
- 失败次数
- 最近错误
- 最近进展时间
- 单次尝试开始时间 / 已尝试次数 / defer 冷却状态
- challenge 历史事件
- challenge 笔记（foothold / last_flag / last_error / shared_findings 等）
- challenge 持久化记忆（turn_summary / hint / error / credential_hint / deferred 等）
- 结构化事件日志
- manager / worker / debug agent 状态
- agent 事件流与工具执行日志

### 1.5 Web Console `web`

位置：

- [app.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/web/app.py)
- [service.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/web/service.py)

职责：

- 提供 `8081` Web 控制台
- 展示比赛总览、challenge 详情、agent 详情
- 在线流式调试 debug agent
- 一键启动 / 停止 / 重启 `competition`
- 展示 agent 事件流和执行过程

## 2. 两种运行模式

### 2.1 `debug`

启动：

```bash
niuniu-agent run --mode debug
```

特点：

- 中文输入可用
- 交互式
- 先显示 challenge 概览
- 工具执行时有实时进度：
  - `[tool:start]`
  - `[tool:done]`
- 最终回答尽量整理成更清晰的结构

### 2.2 `competition`

启动：

```bash
niuniu-agent run --mode competition
```

特点：

- 外层循环不会主动停止
- 自动拉题
- 自动选择未完成题
- 最多 3 个 challenge worker 并发
- 错误后自动恢复
- challenge 完成后自动切下一题
- 单题单次尝试超过 1 小时且仍有未开始题目时会自动保存状态并临时切题

## 3. 当前数据流

### 3.1 `debug` 数据流

```text
用户输入
  -> challenge_store.refresh()
  -> 生成当前 challenge snapshot
  -> 根据 description / notes / state 选择 skills
  -> 构造 entry prompt + trigger prompts
  -> agent 执行显式 tool-use loop
  -> 工具进度实时输出
  -> 最终回答输出
```

### 3.2 `competition` 数据流

```text
competition outer loop
  -> challenge_store.refresh()
  -> coordinator 选择最多 3 个未完成 challenge
  -> 为每个 challenge 启动 worker
  -> worker 读取 challenge state / history / notes / memories / shared findings
  -> 构造 prompt
  -> agent 执行显式 tool-use loop
  -> 写回 history / notes / memories / findings / telemetry
  -> 长时间卡题则 defer、停实例、让位给未开始题
  -> challenge 完成则释放 worker 槽位
  -> 继续下一轮
```

## 4. 关键比赛约束如何落实

### 4.1 最多 3 个实例

当前不只是 prompt 提示，而是代码层也在做：

- 启动 challenge 前先看当前运行中的实例数量
- 达到上限时先停其他 running challenge，再重试启动

位置：

- [tool_bus.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/agent_stack/tool_bus.py)

### 4.2 提交 flag 后立即关闭已完成实例

当前代码会：

1. 提交 flag
2. 刷新 challenge 快照
3. 如果 challenge 已完成且实例还在运行
4. 立即关闭实例

### 4.3 hint 使用限制

当前策略已经接入：

- 连续失败
- 最近 5 分钟无进展
- 已看过 hint 不再重复看

位置：

- [competition_loop.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/competition_loop.py)
- [recovery.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/recovery.py)

### 4.4 长时间卡题自动降级

当前代码会：

1. 记录每个 challenge 单次尝试的开始时间
2. 如果单个 worker 在同一题连续运行超过 1 小时
3. 且此时仍有未开始的 challenge
4. 则把当前总结、hint、error、关键线索写入本地 memory
5. 停掉该题实例并进入短暂 defer
6. 把 worker 槽位让给未开始题

这样可以避免 3 个 worker 被少量卡题长期占满。

### 4.5 本地持久化记忆与清理

当前本地会持久化：

- `history`
- `notes`
- `challenge_memories`
- `submitted_flags`
- agent 状态与事件

正式比赛前如果要清掉 debug/demo 污染，可以执行：

```bash
niuniu-agent clear-memory --runtime-dir runtime --yes
```

## 5. 为什么之前会报错

你提到过这个报错：

```text
OperationalError: no such column: last_progress_at
```

原因是：

- 调试机上旧版 `state.db` 没有 `last_progress_at` 列
- 代码升级后开始查询新列
- SQLite 旧 schema 没迁移，就直接报错

当前已经修复：

- 启动时会自动检查并迁移旧 schema
- 不需要你手工删库

## 6. 为什么之前 debug 容易退出

早期问题主要有两类：

1. 工具异常直接上抛  
现在已经改成：
- 工具异常转成 tool result
- 会话不直接退出

2. 最终输出过于原始  
现在已经改成：
- 过程和最终回答分层
- 工具进度简化输出
- 最终答复尽量结构化

## 7. 现在的策略框架

### 7.1 通用 Skills

位置：

- [registry.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/skills/registry.py)
- [planner.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/skills/planner.py)
- [tracks.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/skills/tracks.py)
- [skills/](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/skills)

特点：

- 不是按四个赛道拆成四套 skill
- 是 learn-claude-code 风格的磁盘 skill 目录
- `SKILL.md` 只保留标准 skill frontmatter：`name` 和 `description`
- 运行时只暴露轻量 catalog，需要时再通过 `load_skill` 加载全文
- 比赛画像只用于排序通用 skill，不定义赛道专属 skill

当前核心能力包括：

- `web-surface-mapping`
- `service-enumeration`
- `known-vulnerability-mapping`
- `web-vulnerability-testing`
- `api-workflow-testing`
- `cloud-asset-assessment`
- `lateral-movement-planning`
- `privilege-path-analysis`
- `directory-identity-enumeration`
- `evidence-capture`

### 7.2 比赛画像

已定义：

- `track1`: SRC / 主流 Web 漏洞
- `track2`: CVE / 云安全 / AI 基础设施
- `track3`: 多步攻击 / 横向移动 / 权限维持
- `track4`: 域渗透 / 企业内网

当前还在继续补强的是：

- 比赛画像下的通用 skill 排序
- 更强的阶段切换和触发覆盖

## 8. 调试机使用

### 8.1 更新

```bash
cd ~/niuniu-agent
git pull --ff-only origin main
uv sync
```

### 8.2 交互调试

```bash
uv run niuniu-agent run --mode debug
```

### 8.3 无人值守

```bash
uv run niuniu-agent run --mode competition
```

### 8.4 控制脚本

```bash
bash scripts/remote_control.sh debug
bash scripts/remote_control.sh competition-start
bash scripts/remote_control.sh ui-start
bash scripts/remote_control.sh competition-status
bash scripts/remote_control.sh ui-status
bash scripts/remote_control.sh competition-stop
bash scripts/remote_control.sh competition-restart
bash scripts/remote_control.sh ui-stop
bash scripts/remote_control.sh ui-restart
```

### 8.5 Web UI

启动后默认访问：

```text
http://<host>:8081
```

当前页面包括：

- dashboard：比赛总览、process 状态、agent 状态、最近执行流
- model routing：当前供应商、自动故障切换状态、手动切换供应商/模型
- debug：在线对话调试 agent，流式显示模型和工具事件
- challenge detail：单题 history / notes / agent events
- agent detail：单个 manager / worker / debug agent 的状态与事件

## 9. 环境变量

最少需要：

- `NIUNIU_AGENT_MODEL`
- `NIUNIU_AGENT_MODEL_BASE_URL`
- `NIUNIU_AGENT_MODEL_API_KEY`
- `NIUNIU_AGENT_MODEL_PROVIDER_ID`
- `NIUNIU_AGENT_MODEL_PROVIDER_NAME`
- `NIUNIU_AGENT_CONTEST_HOST`
- `NIUNIU_AGENT_CONTEST_TOKEN`
- `NIUNIU_AGENT_WEB_HOST`
- `NIUNIU_AGENT_WEB_PORT`

可选的备用供应商：

- `NIUNIU_AGENT_FALLBACK_MODEL_PROVIDER_ID`
- `NIUNIU_AGENT_FALLBACK_MODEL_PROVIDER_NAME`
- `NIUNIU_AGENT_FALLBACK_MODEL`
- `NIUNIU_AGENT_FALLBACK_MODEL_BASE_URL`
- `NIUNIU_AGENT_FALLBACK_MODEL_API_KEY`
- `NIUNIU_AGENT_MODEL_FAILOVER_ENABLED`

可选的回连资源：

- `NIUNIU_AGENT_CALLBACK_PUBLIC_IP`
- `NIUNIU_AGENT_CALLBACK_USERNAME`
- `NIUNIU_AGENT_CALLBACK_PASSWORD`
- `NIUNIU_AGENT_CALLBACK_USAGE`

当前主赛场：

```bash
NIUNIU_AGENT_CONTEST_HOST=https://challenge.zc.tencent.com
```

零界域名记录为：

```bash
https://challenge.zc.tencent.com:8443
```

当前主路径仍只接主赛场。

## 10. 当前验证结果

目前已经验证过：

- 本地测试通过
- `debug` 可交互
- 中文输入可用
- `competition` 可持续运行
- 错误可自动恢复
- 实例数量限制已在代码层执行
- flag 成功提交后本地状态会同步更新

## 11. 当前仍在继续做的事

- 四赛道能力进一步补强
- 长时间运行后的状态恢复
- 更完整的高阶工具降级
- 更强的结果整理和调试体验
