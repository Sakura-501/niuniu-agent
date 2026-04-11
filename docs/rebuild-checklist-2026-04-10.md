# niuniu-agent 重构清单

更新时间：2026-04-10

## 执行约束

- [x] 在完成计划文档中的所有步骤和要求之前不要主动停止，遇到问题自己解决，同时把当前这句话也写入计划文档。

## 已完成

- [x] 把项目主架构切到 `control_plane / agent_stack / runtime` 分层
- [x] 接入 `openai-agents` 相关依赖
- [x] 把 `debug` 模式改成交互式对话模式
- [x] 把中文输入解码问题修掉
- [x] 把远端控制脚本改成默认不自动 `update`
- [x] 把远端控制脚本修成可自举清理 `scripts/` 脏工作树
- [x] 把赛题快照、完成态、选题逻辑独立到 `control_plane`
- [x] 把主循环改成显式 `tool_calls -> tool result -> continue`
- [x] 调试机实测 `debug` 模式可正常进入对话
- [x] 调试机实测 `git pull` 更新路径可用
- [x] 把比赛控制面主路径统一到 `openai-agents` MCP gateway
- [x] 落地通用 skills 注册表
- [x] 落地入口 prompt + trigger prompts 基础结构
- [x] 启动时检查工具是否存在
- [x] 缺失工具时给出明确日志
- [x] 外层 `competition` 循环持续运行，不因单次异常退出
- [x] 单题失败重试策略
- [x] 连续失败退避策略
- [x] 单题完成后自动切下一题
- [x] 空闲状态自动轮询
- [x] 当前活跃赛题记录
- [x] 失败次数与恢复点
- [x] 挑战历史记录
- [x] 当前阶段性结论基础记录
- [x] 识别并删除不再作为主路径的旧模块
- [x] 清理旧测试并迁移到新架构
- [x] 调试机验证 `debug` 模式可真正交互跑通
- [x] 调试机验证 `competition` 模式可持续运行
- [x] 调试机验证异常后自动恢复
- [x] 调试机验证 `scripts/remote_control.sh competition-start`
- [x] 调试机验证 `scripts/remote_control.sh competition-restart`
- [x] 提示查看策略基础逻辑
- [x] 当前 foothold / 阶段性结论基础记录
- [x] 调试机验证已完成题不会优先重复浪费时间
- [x] 3 实例上限约束已在代码层强制执行
- [x] 正确 flag 提交且题目完成后会立即关闭实例
- [x] 完成一题后会自动继续下一题，不停留
- [x] hint 查看已加 5 分钟无进展条件约束
- [x] 当前代码对应的架构图与流程图已落地到文档
- [x] skills 模块已切到磁盘 `skills/*/SKILL.md` 目录 + `load_skill` 动态加载
- [x] 所有内置 `SKILL.md` 已收敛到标准 skill frontmatter，只保留 `name` 和 `description`
- [x] `competition` 已增加 `manager agent + 最多 3 个 worker agent` 的状态兜底骨架
- [x] 已增加 `8081` Web UI、在线 debug 页面、agent 日志/流程查看和后台热更新控制脚本
- [x] 调试机验证 `git pull` 后 `8081` Web UI 可启动并返回首页 HTML
- [x] Web UI 已补充 `hint` 状态、challenge `official/local` 数据来源说明、debug 会话恢复、debug agent stop/delete
- [x] `Start Competition` 后 Web Agents 列表会立即 seed manager 状态并共享同一 `runtime_dir`
- [x] `competition` 遇到官方 MCP `list_challenges` 限速时会退避重试，不再直接把进程打停
- [x] `competition` 已提升为 supervisor 运行模式，`run_competition_loop` 自身抛错后也会自动重建上下文继续运行
- [x] challenge 完成后会移除对应 worker 的当前状态，不再继续占据 Agents 列表
- [x] worker 已改成单次运行唯一 `worker_run_id`，agent 详情日志不再混入旧 run
- [x] worker agent 已支持 Web `pause/delete`，已完成 worker 保留在 Agents 列表用于查看本次日志
- [x] manager 也已切到单次 `competition_run_id`，不同 competition run 的日志相互隔离
- [x] Agents UI 已改成按 `manager -> workers` 的树形展示
- [x] manager 现在支持 Web `stop/delete`，删除会真正移除该次 competition run 的 manager 和 workers
- [x] `remote_control.sh update` 已切到默认执行 `uv sync`，默认运行方式改为 `uv run`

## 进行中

- [ ] 把通用 skills 真正接入赛题推进策略
说明：
目前 `skills/*/SKILL.md`、动态注册表、`load_skill`、planner、入口 prompt、trigger prompts 已落地并接入 `debug` / `competition`。
剩余工作是继续增强通用能力、更多触发覆盖和更稳的排序策略，而不是再拆成赛道专属 skill。

- [ ] 做强 `competition` 的长期状态恢复
说明：
当前已具备活跃赛题、失败次数、退避恢复、挑战历史、阶段性结论、manager/worker 状态与基础 foothold 提取。
剩余工作是长期多轮恢复、更准确的自动提取与更强的 manager 调度策略。

- [ ] 补强 Web UI 的远端实机验证与更多页面交互
说明：
当前已落地 dashboard、challenge detail、agent detail、online debug chat、competition start/stop/restart，且调试机已验证 `ui-start` 可拉起 `8081` 首页。
剩余工作是调试页流式交互、更多控制项与页面细节打磨。

## 强制规则落实情况

- [x] 最多同时开启 3 个容器实例
说明：
代码层已强制：
启动 challenge 前会先看当前 running 实例数量；
如果已到上限，会先停止其它运行实例，再启动目标题。

- [x] 提交完正确 flag 且 challenge 完成后立即关闭实例
说明：
`submit_flag` 后会立刻刷新 challenge 状态；
如果已完成且实例仍在运行，会立即 `stop_challenge`。

- [x] 一旦完成一个 challenge，就继续下一个 challenge
说明：
`competition` 外层调度器会持续选择未完成 challenge；
完成后释放槽位给下一题，不会停留。

- [x] 超过 5 分钟没有思路进展或结果，才能查看 hint
说明：
当前已在策略层/笔记层接入基础约束；
下一步会继续把“5 分钟无进展”的时间判断做得更细。

## ctf-agent 借鉴点

这一部分基于 [ctf-agent](/Users/nonoge/Desktop/auto_pentest/agent-2025-Ref/ctf-agent/README.md) 的思路整理，明确哪些要借鉴，哪些不直接照搬。

### 已采纳

- [x] `coordinator + worker` 结构
说明：
不采用“3 个完全独立主循环乱跑”，而是采用一个统一 coordinator 负责调度，最多 3 个 challenge worker 并发。
实现位置：
[coordinator.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/coordinator.py)

- [x] 并发上限和平台约束一致
说明：
比赛平台最多 3 个 challenge 实例，所以 worker 并发也控制在 3。

- [x] 共享 findings bus
说明：
不同 challenge worker 的阶段性结论可以通过共享 findings bus 被统一管理。
实现位置：
[findings_bus.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/runtime/findings_bus.py)

- [x] coordinator / findings bus 已有测试覆盖
说明：
测试位置：
- [test_competition_coordinator.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/tests/test_competition_coordinator.py)
- [test_findings_bus.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/tests/test_findings_bus.py)

### 不直接照搬

- [ ] 多模型同题 swarm 赛跑
说明：
`ctf-agent` 是多模型并发打同一道题，我们当前更适合先做“多题并发 + 单协调器”。
后续如果比赛表现需要，再考虑在单题内部加 swarm。

## 工具安装/准备清单

这一节不是“可选优化”，而是四赛道要提前准备好的基础工具面。后续实现时应优先做“存在性检查 + 缺失时降级 + 安装教程”。

### A. 基础运行与解析工具

- [ ] `python3 / pip / venv`
作用：运行 agent、本地 PoC、解析接口返回、批量脚本编排。  
安装：`sudo apt-get install -y python3 python3-pip python3.12-venv`

- [ ] `curl`
作用：最小 HTTP 探测、回显验证、接口快速验证。  
安装：系统通常自带；缺失时 `sudo apt-get install -y curl`

- [ ] `jq`
作用：JSON 响应过滤、API 回包快速提取、flag 字段定位。  
安装：`sudo apt-get install -y jq`

- [ ] `ripgrep`
作用：本地结果检索、日志过滤、导出文件快速搜索。  
安装：`sudo apt-get install -y ripgrep`

### B. Web / SRC 常用工具

- [ ] `ffuf`
作用：目录、文件、参数、子路径快速枚举。  
安装：`sudo apt-get install -y ffuf`

- [ ] `nmap`
作用：端口发现、服务识别、基础探测。  
安装：`sudo apt-get install -y nmap`

- [ ] `whatweb`
作用：Web 指纹识别。  
安装：`sudo apt-get install -y whatweb`

- [ ] `sqlmap`
作用：SQL 注入验证与自动化利用。  
安装：`sudo apt-get install -y sqlmap`

### C. 漏洞 / 云安全 / AI 基础设施工具

- [ ] `nuclei`
作用：CVE 模板验证、资产批量快速检测。  
安装：按官方二进制或 `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest`

- [ ] `httpx`
作用：存活探测、标题/状态码/服务信息批量收集。  
安装：按官方二进制或 `go install github.com/projectdiscovery/httpx/cmd/httpx@latest`

- [ ] `openssl`
作用：证书、TLS、基础密码学和编码处理。  
安装：系统通常自带；缺失时 `sudo apt-get install -y openssl`

### D. 内网 / 域渗透 / 横向基础工具

- [ ] `smbclient`
作用：SMB 枚举与文件访问。  
安装：`sudo apt-get install -y smbclient`

- [ ] `ldap-utils`
作用：LDAP / AD 基础查询。  
安装：`sudo apt-get install -y ldap-utils`

- [ ] `impacket` 系列
作用：域环境、Kerberos、SMB、横向基础操作。  
安装：优先 `python -m pip install impacket`

### E. 工具接入实现要求

- [x] 启动时检查工具是否存在
- [x] 缺失工具时给出明确日志
- [x] 缺失工具时自动退回到 Python / curl 替代路径
- [x] 在 `debug` 模式中支持显式查看工具可用性
说明：
工具清单代码位置：
[tools_inventory.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/tools_inventory.py)
启动检查与日志位置：
[cli.py](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/src/niuniu_agent/cli.py)

## 通用 Skills 设计表

这里的 `skills` 不是“四赛道四套完全独立逻辑”，而是严格按 skill 规范编写的可复用能力模块。比赛画像只负责排序和组合这些通用能力。

### 1. `web-surface-mapping`

作用：识别 Web 入口、路由、静态资源、目录、接口、常见参数。  
关键词触发：`web`、`portal`、`site`、`http`、`login`、`admin`、`dashboard`  
典型使用时机：题目刚接管、需要先摸清攻击面时。  
输出期望：入口列表、关键路径、参数点、技术栈指纹。

### 2. `service-enumeration`

作用：识别端口、协议、运行服务、版本信息。  
关键词触发：`service`、`port`、`tcp`、`udp`、`ssh`、`redis`、`mysql`、`fastapi`  
典型使用时机：非纯 Web 题、需要先识别服务栈时。  
输出期望：端口表、服务类型、可疑高价值服务。

### 3. `known-vulnerability-mapping`

作用：根据指纹、版本、响应头、组件特征映射潜在 CVE。  
关键词触发：`cve`、`version`、`apache`、`nginx`、`fastapi`、`spring`、`grafana`  
典型使用时机：第二赛区、识别到已知组件时。  
输出期望：候选漏洞列表、优先验证顺序。

### 4. `web-vulnerability-testing`

作用：验证主流 Web 漏洞，包括注入、越权、文件、模板、反序列化等。  
关键词触发：`sqli`、`xss`、`upload`、`ssti`、`idor`、`auth bypass`、`template`  
典型使用时机：第一赛区、第二赛区的 Web 面验证。  
输出期望：可复现请求、利用链、flag/敏感信息证据。

### 5. `api-workflow-testing`

作用：针对 JSON/API 接口的认证、鉴权、结构化利用。  
关键词触发：`api`、`json`、`token`、`jwt`、`graphql`、`rest`  
典型使用时机：接口型题目或前后端分离应用。  
输出期望：关键接口、鉴权缺陷、利用步骤。

### 6. `cloud-asset-assessment`

作用：识别云元数据、对象存储、AI 服务接口、模型推理服务入口。  
关键词触发：`cloud`、`bucket`、`metadata`、`llm`、`model`、`inference`、`ai`  
典型使用时机：第二赛区云安全 / AI 基础设施题。  
输出期望：高风险资产、可疑服务、云配置缺陷。

### 7. `lateral-movement-planning`

作用：多步攻击推进、横向移动、下一跳规划。  
关键词触发：`pivot`、`lateral`、`next hop`、`internal`、`foothold`  
典型使用时机：第三赛区或第四赛区中拿到初始 foothold 后。  
输出期望：当前 foothold、下一跳、凭据/通道复用机会。

### 8. `privilege-path-analysis`

作用：提权检查、凭据收集、权限维持、环境信息归档。  
关键词触发：`privesc`、`sudo`、`capability`、`credential`、`persistence`  
典型使用时机：第三赛区、第四赛区、已拿到 shell 或低权限时。  
输出期望：提权路径、可复用凭据、长期控制策略。

### 9. `directory-identity-enumeration`

作用：域信息收集、主机角色识别、AD 基础枚举。  
关键词触发：`domain`、`ad`、`ldap`、`kerberos`、`dc`、`smb`  
典型使用时机：第四赛区企业内网/域环境。  
输出期望：域结构、关键主机、可打点位。

### 10. `evidence-capture`

作用：flag 提交、结果确认、失败恢复、重复提交去重。  
关键词触发：`flag`、`submit`、`recovery`、`retry`  
典型使用时机：任意赛区，发现候选 flag 后。  
输出期望：提交结果、是否得分、是否继续尝试。

## Skills 使用教程

### 使用原则

- [x] 赛道不要直接绑定单个 skill，而是绑定 skill 组合
- [x] 优先从映射/枚举类 skill 开始，再进入测试/利用类 skill
- [x] 拿到 foothold 后再触发 `lateral-movement-planning` / `privilege-path-analysis`
- [x] 任何疑似 flag 或关键证据都交给 `evidence-capture`

### 典型组合

- Web/SRC 倾向：`web-surface-mapping + web-vulnerability-testing + api-workflow-testing + evidence-capture`
- 漏洞/云/AI 倾向：`service-enumeration + known-vulnerability-mapping + cloud-asset-assessment + evidence-capture`
- 横向/提权 倾向：`service-enumeration + lateral-movement-planning + privilege-path-analysis + evidence-capture`
- 身份/目录 倾向：`service-enumeration + directory-identity-enumeration + lateral-movement-planning + privilege-path-analysis + evidence-capture`

### 技能触发方式

- [x] 入口 prompt 根据题目描述先做第一轮技能选择
- [x] 侦察结束 trigger prompt 重新评估下一技能
- [x] 利用失败 trigger prompt 切换技能或回退到侦察
- [x] 拿到 foothold trigger prompt 自动切换到横向/提权技能

## 未完成

### 一、四赛道能力层

- [ ] 第一赛区通用能力：SRC / Web 众测侦察能力
- [ ] 第一赛区通用能力：主流 Web 漏洞快速验证能力
- [ ] 第二赛区通用能力：CVE 指纹识别与版本映射
- [ ] 第二赛区通用能力：云安全 / AI 基础设施攻击面识别
- [ ] 第三赛区通用能力：多步攻击路径规划
- [ ] 第三赛区通用能力：权限维持与阶段状态记录
- [ ] 第四赛区通用能力：域渗透基础资产识别
- [ ] 第四赛区通用能力：内网横向与权限路径分析

### 二、skills 体系

- [x] 设计并落地通用 skills 注册表
- [x] 用“能力模块”替代“赛道专属硬编码技能”
- [x] 实现赛道到技能组合的路由策略
- [x] 为每个 skill 增加可复用的描述、触发条件、输入输出约束

### 三、prompt 体系

- [x] 入口系统 prompt
- [x] 赛题接管 trigger prompt
- [x] 侦察完成 trigger prompt
- [x] 利用前 trigger prompt
- [x] 错误恢复 trigger prompt
- [x] 提示查看 trigger prompt
- [x] flag 提交前 trigger prompt

### 四、competition 不停机模式

- [x] 外层循环持续运行，不会因为单次异常退出
- [x] 单题失败重试策略
- [x] 连续失败退避策略
- [x] 单题完成后自动切下一题
- [x] 空闲状态自动轮询
- [x] `competition` 后台运行日志与状态增强

### 五、提示策略

- [x] 明确什么情况下自动看提示
- [x] 防止重复查看同一题提示
- [x] 把提示查看记入本地状态
- [x] 看提示后的 prompt 续跑逻辑

### 六、状态持久化

- [x] 当前活跃赛题记录
- [x] 挑战历史记录
- [x] 失败次数与恢复点
- [x] 当前 foothold / 阶段性结论记录
- [ ] 长时间运行后的状态恢复

### 七、调试与验证

- [x] 调试机验证 `competition` 模式可持续运行
- [x] 调试机验证异常后自动恢复
- [x] 调试机验证已完成题不会重复浪费时间
- [ ] 调试机验证 flag 提交后状态更新正确
说明：
代码层已完成：
- 成功提交 flag 会写入本地状态
- 会写入历史事件
- 会记录 `last_flag`
- 如果 challenge 完成且实例仍在运行，会立即关闭实例
下一步是调试机实测。
- [x] 调试机验证 `scripts/remote_control.sh competition-start`
- [x] 调试机验证 `scripts/remote_control.sh competition-restart`

### 八、清理旧实现

- [x] 识别并删除已经不再作为主路径的旧模块
- [x] 清理旧的 controller/debug_chat/llm 兼容残留
- [x] 清理旧测试或将其迁移到新架构
- [x] 让 README 只描述新架构，不再混用旧术语

## 当前我建议的优先级

1. 调试机验证 flag 提交后状态更新正确
2. 长时间运行后的状态恢复
3. 第二赛区 / 第三赛区 / 第四赛区能力继续补强
4. 第一赛区主流 Web 漏洞验证能力增强
5. 更完整的高阶工具自动降级

## 当前最关键的风险

- [ ] 当前架构虽然已经能交互，但四赛道能力模块还不够完整
- [ ] `competition` 模式的长期恢复还不够强
- [ ] 当前虽然已有自动降级，但部分高阶工具还只是轻量降级，不是完整替代
