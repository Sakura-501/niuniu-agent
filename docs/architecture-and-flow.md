# niuniu-agent 架构图与流程图

本文档只描述当前仓库已经落地的真实实现，不画“未来设想图”。

对应代码入口：

- `CLI`：[src/niuniu_agent/cli.py](../src/niuniu_agent/cli.py)
- `control_plane`：[src/niuniu_agent/control_plane](../src/niuniu_agent/control_plane)
- `agent_stack`：[src/niuniu_agent/agent_stack](../src/niuniu_agent/agent_stack)
- `runtime`：[src/niuniu_agent/runtime](../src/niuniu_agent/runtime)
- `state`：[src/niuniu_agent/state_store.py](../src/niuniu_agent/state_store.py)
- `skills`：[src/niuniu_agent/skills](../src/niuniu_agent/skills)

## 1. 架构图

```mermaid
flowchart LR
    user([User / Operator])
    cli["CLI<br/>cli.py"]
    settings["AgentSettings<br/>config.py"]
    logger["EventLogger<br/>events.jsonl"]
    state["StateStore<br/>state.db"]
    toolbox["LocalToolbox<br/>http / shell / python"]
    skills["SkillRegistry<br/>planner / tracks"]
    web["Web Console<br/>FastAPI :8081"]
    gateway["ContestGateway<br/>MCP streamable HTTP"]
    mcp["Contest MCP<br/>challenge.zc.tencent.com"]
    store["ChallengeStore<br/>snapshot / candidate / summary"]
    ctx["RuntimeContext"]

    subgraph runtime["Runtime Layer"]
        debug["debug_repl.py<br/>interactive repl"]
        formatter["answer_formatter.py<br/>final answer shaping"]
        competition["competition_loop.py<br/>outer loop"]
        coordinator["coordinator.py<br/>max 3 workers"]
        manager["manager.py<br/>manager agent"]
        findings["findings_bus.py<br/>shared findings"]
        recovery["recovery.py<br/>hint gate / note extract"]
    end

    subgraph agent["Agent Stack"]
        prompts["prompts.py<br/>entry + trigger prompts"]
        pentest["AsyncPentestAgent<br/>explicit tool-use loop"]
        toolbus["ToolBus<br/>OpenAI function tools"]
    end

    user --> cli
    cli --> settings
    cli --> logger
    cli --> state
    cli --> toolbox
    cli --> skills
    cli --> gateway
    cli --> web
    gateway <--> mcp
    cli --> store
    gateway --> store
    state --> store

    settings --> ctx
    logger --> ctx
    state --> ctx
    toolbox --> ctx
    skills --> ctx
    gateway --> ctx
    store --> ctx

    ctx --> debug
    ctx --> competition
    ctx --> web

    debug --> prompts
    debug --> pentest
    debug --> formatter

    competition --> prompts
    competition --> coordinator
    competition --> manager
    competition --> findings
    competition --> recovery
    competition --> pentest

    prompts --> pentest
    pentest --> toolbus
    toolbus --> gateway
    toolbus --> toolbox
    toolbus --> state
    toolbus --> logger

    gateway --> store
    pentest --> state
    pentest --> logger
    web --> state
    web --> gateway
    findings --> state
    recovery --> state
```

## 2. Debug 模式流程图

```mermaid
flowchart TD
    start([start debug])
    init["run_debug_repl()<br/>create AsyncOpenAI client"]
    first_snapshot["challenge_store.refresh()<br/>print challenge summary"]
    input["read user input"]
    exitq{"exit / quit ?"}
    refresh["refresh snapshot<br/>select active challenge"]
    load["load runtime_state + notes<br/>infer track + plan skills"]
    build["build entry prompt<br/>+ trigger prompts"]
    run["agent.execute_stream()"]
    toolq{"tool_calls ?"}
    dispatch["ToolBus.dispatch()"]
    official["official contest tools<br/>start / stop / submit / hint"]
    local["local tools<br/>http / shell / python"]
    append["append tool result to history<br/>continue model loop"]
    formatq{"need formatted answer ?"}
    format["answer_formatter.stream_formatted_answer()"]
    raw["print raw model answer"]
    done["print final answer"]

    start --> init --> first_snapshot --> input
    input --> exitq
    exitq -- yes --> end([leave repl])
    exitq -- no --> refresh --> load --> build --> run
    run --> toolq
    toolq -- yes --> dispatch
    dispatch --> official
    dispatch --> local
    official --> append
    local --> append
    append --> run
    toolq -- no --> formatq
    formatq -- yes --> format --> done --> input
    formatq -- no --> raw --> input
```

## 3. Competition 模式流程图

```mermaid
flowchart TD
    start([start competition])
    init["create AsyncOpenAI client<br/>findings_bus + coordinator(3)"]
    outer["outer loop"]
    snapshot["challenge_store.refresh()"]
    openq{"unfinished challenges ?"}
    idle["log idle<br/>sleep"]
    schedule["coordinator.schedule()<br/>max 3 workers"]
    worker["worker(challenge_code)"]
    target["refresh target challenge"]
    completeq{"target missing or completed ?"}
    success["record_challenge_success()<br/>release worker"]
    runtime["mark active<br/>load runtime_state / notes"]
    hintq{"failure >= 3 and<br/>no progress >= 5 min ?"}
    hint["view_hint()<br/>persist hint event"]
    share["read shared findings"]
    prompt["build entry prompt<br/>+ recovery / flag / exploit triggers"]
    agent["agent.execute()"]
    toolq{"tool_calls ?"}
    dispatch["ToolBus.dispatch()"]
    official["contest gateway"]
    local["local toolbox"]
    loopback["append tool result to history<br/>continue agent loop"]
    persist["persist history / notes / findings / telemetry"]
    progressq{"output or tool events ?"}
    mark["mark_progress()"]
    pause["sleep 1s"]
    err["record failure + last_error<br/>history + telemetry"]
    backoff["sleep backoff<br/>let outer loop reschedule"]

    start --> init --> outer --> snapshot --> openq
    openq -- no --> idle --> outer
    openq -- yes --> schedule --> outer

    schedule --> worker
    worker --> target --> completeq
    completeq -- yes --> success
    completeq -- no --> runtime --> hintq
    hintq -- yes --> hint --> share
    hintq -- no --> share
    share --> prompt --> agent
    agent --> toolq
    toolq -- yes --> dispatch
    dispatch --> official
    dispatch --> local
    official --> loopback --> agent
    local --> loopback
    toolq -- no --> persist --> progressq
    progressq -- yes --> mark --> pause --> target
    progressq -- no --> pause --> target
    worker -. exception .-> err --> backoff --> outer
```

## 4. 读图说明

- `debug` 是单会话交互链路，重点是“显式 tool-use loop + 工具进度可见 + 最终答案整理”。
- `competition` 是外层不停机调度链路，重点是“outer loop + coordinator + 最多 3 个 worker + findings bus + 恢复/退避”。
- `web` 现在是单独的控制面入口，读取 challenge snapshot、agent status、agent events，并可在线调试 debug agent。
- 比赛约束不是只写在 prompt 里，`ToolBus` 和 `recovery` 已经把实例上限、flag 提交后停实例、hint 5 分钟门槛等规则落实到代码路径里。
