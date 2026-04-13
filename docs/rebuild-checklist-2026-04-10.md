# niuniu-agent 重构清单

更新时间：2026-04-12

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
- [x] `remote_control.sh competition-start` 现在会持久化 `competition.run_id`，UI 不会再凭空生成重复 manager
- [x] Agents 列表已去掉 `worker-slot:*` 占位项，只展示真实 agent，空闲并发信息收敛到 manager 摘要
- [x] 已支持双供应商模型配置、自动故障切换，以及 Web UI 手动切换当前供应商/模型
- [x] `competition` 内部 worker/MCP 产生的非外部 `CancelledError` 不会再直接打死 supervisor 主进程
- [x] process status 已增加 PID 命令校验，脏 PID/复用 PID 不会再被误判成仍在运行
- [x] 已增加 stalled worker watchdog，running 但长期无活动的 worker 会自动取消并重排
- [x] 已增加 completed worker retirement，已完成 challenge 上的旧 worker 会被自动取消并释放槽位
- [x] 已补充 callback server 资源配置，debug/competition prompt 与 Web UI 都能直接看到可回连公网主机
- [x] 单个 worker 在单题连续运行超过 1 小时且仍有未开始 challenge 时，会保存状态/记忆、关闭实例并临时降级让位
- [x] challenge 关键过程与结果已持久化到本地 memory 表，manager / worker / Web UI 都可回看
- [x] 已增加 `niuniu-agent clear-memory --yes`，可清理本地 runtime 记忆和 debug session 数据，避免 demo 污染正式比赛

## 进行中

- [x] 把通用 skills 真正接入赛题推进策略
说明：
`skills/*/SKILL.md`、动态注册表、`load_skill`、planner、入口 prompt、trigger prompts 已接入 `debug` / `competition`，并已切成通用能力命名。

- [x] 做强 `competition` 的长期状态恢复
说明：
当前已具备 supervisor、限速退避、启动恢复、旧 run 状态清理、本地已解题完成态归一化、manager/worker run id 隔离。

- [x] 补强 Web UI 的远端实机验证与更多页面交互
说明：
dashboard、challenge detail、agent detail、online debug chat、competition start/stop/restart、worker pause/delete、manager stop/delete 已完成，且调试机已多次验证 `8081` 页面可运行。

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

- [x] 明确不采用多模型同题 swarm 作为当前主路径
说明：
当前主路径固定为“多题并发 + 单协调器 + 最多 3 个 worker”，这项架构取舍已经定稿，不再作为未完事项保留。

## 工具安装/准备清单

这一节不是“可选优化”，而是四赛道要提前准备好的基础工具面。后续实现时应优先做“存在性检查 + 缺失时降级 + 安装教程”。

### A. 基础运行与解析工具

- [x] `python3 / pip / venv`
作用：运行 agent、本地 PoC、解析接口返回、批量脚本编排。  
安装：`sudo apt-get install -y python3 python3-pip python3.12-venv`

- [x] `curl`
作用：最小 HTTP 探测、回显验证、接口快速验证。  
安装：系统通常自带；缺失时 `sudo apt-get install -y curl`

- [x] `jq`
作用：JSON 响应过滤、API 回包快速提取、flag 字段定位。  
安装：`sudo apt-get install -y jq`

- [x] `ripgrep`
作用：本地结果检索、日志过滤、导出文件快速搜索。  
安装：`sudo apt-get install -y ripgrep`

- [x] `uv`
作用：默认运行 agent、同步依赖、执行本地 Python 工具链。  
安装：优先官方安装脚本或 `python3 -m pip install --user uv`

- [x] `netcat`
作用：快速 TCP/UDP 探测、简易交互验证、端口级回显确认。  
安装：`sudo apt-get install -y netcat-openbsd`

- [x] `dnsutils`
作用：DNS 查询、域名解析、服务发现、内网名称验证。  
安装：`sudo apt-get install -y dnsutils`

### B. Web / SRC 常用工具

- [x] `ffuf`
作用：目录、文件、参数、子路径快速枚举。  
安装：`sudo apt-get install -y ffuf`

- [x] `feroxbuster`
作用：高并发目录与文件枚举，适合大型 Web 面。  
安装：`cargo install feroxbuster`

- [x] `gobuster`
作用：目录、虚拟主机、DNS 目标枚举备用路径。  
安装：`sudo apt-get install -y gobuster`

- [x] `nikto`
作用：Web 基础配置、危险文件、低门槛问题快速扫面。  
安装：`sudo apt-get install -y nikto`

- [x] `nmap`
作用：端口发现、服务识别、基础探测。  
安装：`sudo apt-get install -y nmap`

- [x] `rustscan`
作用：高速端口发现，适合作为 `nmap` 前置探测器。  
安装：优先官方 release 二进制或 `cargo install rustscan`

- [x] `masscan`
作用：高速端口探测、内网大范围资产发现。  
安装：`sudo apt-get install -y masscan`

- [x] `whatweb`
作用：Web 指纹识别。  
安装：`sudo apt-get install -y whatweb`

- [x] `sqlmap`
作用：SQL 注入验证与自动化利用。  
安装：`sudo apt-get install -y sqlmap`

### C. 漏洞 / 云安全 / AI 基础设施工具

- [x] `nuclei`
作用：CVE 模板验证、资产批量快速检测。  
安装：按官方二进制或 `go install github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest`

- [x] `fscan`
作用：常见服务、漏洞和内网资产的快速综合扫描。  
安装：官方 release 二进制，当前通过 `scripts/fetch_portable_tools.py` 获取

- [x] `cloudfox`
作用：云环境资产、身份和权限快速态势感知。  
安装：官方 release 二进制，当前通过 `scripts/fetch_portable_tools.py` 获取

- [x] `httpx`
作用：存活探测、标题/状态码/服务信息批量收集。  
安装：按官方二进制或 `go install github.com/projectdiscovery/httpx/cmd/httpx@latest`

- [x] `openssl`
作用：证书、TLS、基础密码学和编码处理。  
安装：系统通常自带；缺失时 `sudo apt-get install -y openssl`

- [x] `redis-cli`
作用：Redis / key-value 服务交互验证。  
安装：`sudo apt-get install -y redis-tools`

- [x] `mysql-client`
作用：MySQL 服务连通性与数据库交互验证。  
安装：`sudo apt-get install -y mysql-client`

- [x] `postgresql-client`
作用：PostgreSQL 服务连通性与数据库交互验证。  
安装：`sudo apt-get install -y postgresql-client`

- [x] `socat`
作用：端口转发、半交互 relay、轻量隧道与回连辅助。  
安装：`sudo apt-get install -y socat`

- [x] `proxychains4`
作用：多跳代理转发、内网横向阶段链路复用。  
安装：`sudo apt-get install -y proxychains4`

- [x] `frp` (`frpc` / `frps`)
作用：反向代理、端口暴露、回连与稳定隧道。  
安装：官方 release 二进制，当前通过 `scripts/fetch_portable_tools.py` 获取

- [x] `stowaway`
作用：多级隧道和横向网络转发。  
安装：官方 release 二进制，当前通过 `scripts/fetch_portable_tools.py` 获取

- [x] `AJPy` / `phpggc` / `grafanaExp` / `redis-rogue-server` / `rogue_mysql_server`
作用：Tomcat AJP / Ghostcat、PHP 反序列化 gadget 生成、Grafana `CVE-2021-43798` 文件读、Redis rogue replication/module load、rogue MySQL 握手链路。  
安装：当前已把高价值上游脚本/二进制作为仓库内便携资产落地到 `tools/portable/web/*`、`tools/portable/service/*`，通过 `tools/bin/ajpy-tomcat`、`tools/bin/phpggc`、`tools/bin/grafana-exp`、`tools/bin/redis-rogue-server`、`tools/bin/rogue-mysql-server` 直接调用。

### D. 内网 / 域渗透 / 横向基础工具

- [x] `smbclient`
作用：SMB 枚举与文件访问。  
安装：`sudo apt-get install -y smbclient`

- [x] `ldap-utils`
作用：LDAP / AD 基础查询。  
安装：`sudo apt-get install -y ldap-utils`

- [x] `impacket` 系列
作用：域环境、Kerberos、SMB、横向基础操作。  
安装：优先 `python -m pip install impacket`

- [x] `netexec`
作用：域环境认证、横向与服务探测的一体化执行。  
安装：`python3 -m pip install --user netexec`

- [x] `bloodhound-python`
作用：域关系收集、权限路径图分析。  
安装：`python3 -m pip install --user bloodhound-python`

- [x] `mimikatz` 备份资产
作用：Windows 环境凭据提取和认证材料利用。  
安装：Windows-only 资产，当前通过 `scripts/fetch_portable_tools.py` 备份官方 release 包供后续投放

- [x] `kerbrute`
作用：Kerberos 用户枚举与口令验证。  
安装：`go install github.com/ropnop/kerbrute@latest`

- [x] `PetitPotam` / `DFSCoerce` / `PassTheCert`
作用：强制认证、Schannel/LDAP 证书认证、AD 证书链路补充。  
安装：当前已把上游脚本作为仓库内便携资产落地到 `tools/portable/domain/linux_amd64/*`，通过 `tools/bin/petitpotam`、`tools/bin/dfscoerce`、`tools/bin/passthecert` wrapper 在调试机直接调用。

- [x] `noPac`
作用：`CVE-2021-42278` / `CVE-2021-42287` 域提权链扫描与利用。  
安装：当前已把上游 Python 脚本作为仓库内便携资产落地到 `tools/portable/domain/linux_amd64/nopac`，通过 `tools/bin/nopac`、`tools/bin/nopac-scanner` wrapper 在调试机直接调用。

- [x] `Powermad` / `PrivescCheck` / `Certify.exe` / `MS14-068.exe` 备份资产
作用：Windows 主机上的 MAQ/ADIDNS、Windows 本地提权检查、AD CS 枚举，以及旧版 Kerberos 利用链兜底。  
安装：当前已把资产落地到 `tools/portable/windows_assets/*`，并提供 `tools/bin/*-asset` wrapper 输出投放路径；对应使用教程已补到 `skills/tool-windows-ad-stage-assets`。

- [x] `Rubeus` / `SharpHound` / `SweetPotato` / `SeBackupPrivilege` 备份资产
作用：Windows Kerberos 操作、Windows 侧 BloodHound 采集、本地提权、`SeBackupPrivilege` 复制受保护文件。  
安装：当前已把资产落地到 `tools/portable/windows_assets/*`，并提供 `rubeus-asset`、`sharphound-asset`、`sweetpotato-asset`、`sebackupprivilege-asset` wrapper 输出投放路径。

- [x] `hydra`
作用：多协议口令爆破。  
安装：`sudo apt-get install -y hydra`

- [x] `john`
作用：密码哈希破解。  
安装：`sudo apt-get install -y john`

- [x] `hashcat`
作用：GPU/CPU 密码哈希破解。  
安装：`sudo apt-get install -y hashcat`

### F. 权限提升 / 后渗透工具

- [x] `linpeas`
作用：Linux 权限提升线索收集。  
安装：官方 release 二进制，当前通过 `scripts/fetch_portable_tools.py` 获取

- [x] `pspy`
作用：无 root 的 Linux 进程/计划任务观察。  
安装：官方 release 二进制，当前通过 `scripts/fetch_portable_tools.py` 获取

- [x] `metasploit-framework`
作用：多协议 payload、session 管理和 exploit 框架。  
安装：调试机当前通过 `snap install metasploit-framework --classic` 完成

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
安装自动化脚本：
[install_toolchain.sh](/Users/nonoge/Desktop/auto_pentest/niuniu-agent/scripts/install_toolchain.sh)

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

### 11. `port-scan-operations`

作用：在 `rustscan / nmap / masscan` 之间做有边界的端口与服务探测。  
输出期望：端口表、服务指纹、进一步验证建议。

### 12. `web-content-discovery`

作用：在 `ffuf / gobuster / feroxbuster` 之间做路径、文件、vhost 和隐藏内容发现。  
输出期望：高价值路径、过滤条件、递归建议。

### 13. `cve-template-scanning`

作用：基于 `nuclei / fscan / httpx / whatweb` 做已知漏洞模板验证。  
输出期望：可疑模板命中、人工复核点、下一步利用线索。

### 14. `cloud-security-enumeration`

作用：面向云身份、对象存储、元数据和 AI 基础设施的攻击面枚举。  
输出期望：云资产边界、身份线索、可验证风险面。

### 15. `tunnel-and-pivot-operations`

作用：使用 `frp / stowaway / socat / proxychains4` 规划回连、转发和横向代理。  
输出期望：最小可行隧道方案、监听与清理步骤。

### 16. `persistence-operations`

作用：在确有必要时保持低噪声持久化与回连能力。  
输出期望：保留通道、清理方式、继续利用条件。

### 17. `domain-operations`

作用：围绕 `impacket / netexec / bloodhound / kerbrute / mimikatz` 的域渗透流程。  
输出期望：域关系图、最短权限路径、可复用凭据。

### 18. `linux-privilege-escalation`

作用：围绕 `linpeas / pspy / sudo / capability` 的 Linux 提权流程。  
输出期望：高确定性提权路径、证据、清理方案。

### 19. `resource-aware-execution`

作用：限制重型扫描和批量工具的 CPU / 内存 / 并发开销，防止机器卡死。  
输出期望：合理的并发、限速、超时和回收策略。

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

- [x] 第一赛区通用能力：SRC / Web 众测侦察能力
- [x] 第一赛区通用能力：主流 Web 漏洞快速验证能力
- [x] 第二赛区通用能力：CVE 指纹识别与版本映射
- [x] 第二赛区通用能力：云安全 / AI 基础设施攻击面识别
- [x] 第三赛区通用能力：多步攻击路径规划
- [x] 第三赛区通用能力：权限维持与阶段状态记录
- [x] 第四赛区通用能力：域渗透基础资产识别
- [x] 第四赛区通用能力：内网横向与权限路径分析

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
- [x] 长时间运行后的状态恢复
- [x] challenge 长期记忆表（关键过程 / 结果 / 线索 / flag / hint / error）
- [x] manager / worker prompt 已回灌本地记忆，不会每次从零开始
- [x] 已提供一键清理本地记忆能力，正式比赛前可清空 demo 污染

### 九、长时间卡题调度策略

- [x] 单个 worker 在单题连续运行超过 1 小时且存在未开始题目时，不再无限占坑
- [x] 触发降级前会先把当前过程摘要、错误、hint、关键结论落库
- [x] 触发降级时会停止对应 challenge 实例，释放平台实例槽位
- [x] challenge 会进入短暂 defer 状态，等待后续空闲 worker 再回捞
- [x] Web/UI 已能显示 `deferred` 调度状态

### 七、调试与验证

- [x] 调试机验证 `competition` 模式可持续运行
- [x] 调试机验证异常后自动恢复
- [x] 调试机验证已完成题不会重复浪费时间
- [x] 调试机验证 flag 提交后状态更新正确
说明：
代码层已完成：
- 成功提交 flag 会写入本地状态
- 会写入历史事件
- 会记录 `last_flag`
- 如果 challenge 完成且实例仍在运行，会立即关闭实例
调试机上已观察到 `last_flag` / `submitted_flags` / `history` 同步落库。
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

- [x] 当前架构虽然已经能交互，但四赛道能力模块还不够完整
- [x] `competition` 模式的长期恢复还不够强
- [x] 当前虽然已有自动降级，但部分高阶工具还只是轻量降级，不是完整替代

## 调试机实测补充（2026-04-12）

- [x] 调试机实测 `feroxbuster` 已可用
- [x] 调试机实测 `gobuster / socat / proxychains4` 已安装并可调用
- [x] 调试机实测工具清单中的四赛道基础工具已全部存在
- [x] 调试机实测 `rustscan / cloudfox / frpc / frps / stowaway / fscan / linpeas / pspy / msfconsole` 已安装并可调用
