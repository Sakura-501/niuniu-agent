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

## 进行中

- [ ] 把四赛道的通用 skills 真正接入赛题推进策略
说明：
目前 skills 注册表和入口/trigger prompts 已落地，
但还需要把四赛道的能力模块进一步绑定到更细的推进阶段和恢复策略里。

- [ ] 做强 `competition` 的长期状态恢复
说明：
当前已具备活跃赛题、失败次数、退避恢复，但还缺长期 foothold / 阶段性结论恢复。

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

这里的 `skills` 不是“四赛道四套完全独立逻辑”，而是可复用能力模块。赛道只负责组合这些能力。

### 1. `recon_web`

作用：识别 Web 入口、路由、静态资源、目录、接口、常见参数。  
关键词触发：`web`、`portal`、`site`、`http`、`login`、`admin`、`dashboard`  
典型使用时机：题目刚接管、需要先摸清攻击面时。  
输出期望：入口列表、关键路径、参数点、技术栈指纹。

### 2. `recon_service`

作用：识别端口、协议、运行服务、版本信息。  
关键词触发：`service`、`port`、`tcp`、`udp`、`ssh`、`redis`、`mysql`、`fastapi`  
典型使用时机：非纯 Web 题、需要先识别服务栈时。  
输出期望：端口表、服务类型、可疑高价值服务。

### 3. `cve_mapping`

作用：根据指纹、版本、响应头、组件特征映射潜在 CVE。  
关键词触发：`cve`、`version`、`apache`、`nginx`、`fastapi`、`spring`、`grafana`  
典型使用时机：第二赛区、识别到已知组件时。  
输出期望：候选漏洞列表、优先验证顺序。

### 4. `exploit_web`

作用：验证主流 Web 漏洞，包括注入、越权、文件、模板、反序列化等。  
关键词触发：`sqli`、`xss`、`upload`、`ssti`、`idor`、`auth bypass`、`template`  
典型使用时机：第一赛区、第二赛区的 Web 面验证。  
输出期望：可复现请求、利用链、flag/敏感信息证据。

### 5. `exploit_api`

作用：针对 JSON/API 接口的认证、鉴权、结构化利用。  
关键词触发：`api`、`json`、`token`、`jwt`、`graphql`、`rest`  
典型使用时机：接口型题目或前后端分离应用。  
输出期望：关键接口、鉴权缺陷、利用步骤。

### 6. `cloud_ai_surface`

作用：识别云元数据、对象存储、AI 服务接口、模型推理服务入口。  
关键词触发：`cloud`、`bucket`、`metadata`、`llm`、`model`、`inference`、`ai`  
典型使用时机：第二赛区云安全 / AI 基础设施题。  
输出期望：高风险资产、可疑服务、云配置缺陷。

### 7. `pivot_lateral`

作用：多步攻击推进、横向移动、下一跳规划。  
关键词触发：`pivot`、`lateral`、`next hop`、`internal`、`foothold`  
典型使用时机：第三赛区或第四赛区中拿到初始 foothold 后。  
输出期望：当前 foothold、下一跳、凭据/通道复用机会。

### 8. `privesc_maintain`

作用：提权检查、凭据收集、权限维持、环境信息归档。  
关键词触发：`privesc`、`sudo`、`capability`、`credential`、`persistence`  
典型使用时机：第三赛区、第四赛区、已拿到 shell 或低权限时。  
输出期望：提权路径、可复用凭据、长期控制策略。

### 9. `domain_enum`

作用：域信息收集、主机角色识别、AD 基础枚举。  
关键词触发：`domain`、`ad`、`ldap`、`kerberos`、`dc`、`smb`  
典型使用时机：第四赛区企业内网/域环境。  
输出期望：域结构、关键主机、可打点位。

### 10. `flag_submit_recovery`

作用：flag 提交、结果确认、失败恢复、重复提交去重。  
关键词触发：`flag`、`submit`、`recovery`、`retry`  
典型使用时机：任意赛区，发现候选 flag 后。  
输出期望：提交结果、是否得分、是否继续尝试。

## Skills 使用教程

### 使用原则

- [x] 赛道不要直接绑定单个 skill，而是绑定 skill 组合
- [x] 优先从 `recon_*` 开始，再进入 `exploit_*`
- [x] 拿到 foothold 后再触发 `pivot_lateral` / `privesc_maintain`
- [x] 任何疑似 flag 都交给 `flag_submit_recovery`

### 典型组合

- 第一赛区：`recon_web + exploit_web + exploit_api + flag_submit_recovery`
- 第二赛区：`recon_service + cve_mapping + cloud_ai_surface + exploit_web + flag_submit_recovery`
- 第三赛区：`recon_service + pivot_lateral + privesc_maintain + flag_submit_recovery`
- 第四赛区：`recon_service + domain_enum + pivot_lateral + privesc_maintain + flag_submit_recovery`

### 技能触发方式

- [x] 入口 prompt 根据题目描述先做第一轮技能选择
- [x] 侦察结束 trigger prompt 重新评估下一技能
- [x] 利用失败 trigger prompt 切换技能或回退到侦察
- [ ] 拿到 foothold trigger prompt 自动切换到横向/提权技能

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
- [ ] `competition` 后台运行日志与状态增强

### 五、提示策略

- [ ] 明确什么情况下自动看提示
- [ ] 防止重复查看同一题提示
- [ ] 把提示查看记入本地状态
- [ ] 看提示后的 prompt 续跑逻辑

### 六、状态持久化

- [x] 当前活跃赛题记录
- [x] 挑战历史记录
- [x] 失败次数与恢复点
- [ ] 当前 foothold / 阶段性结论记录
- [ ] 长时间运行后的状态恢复

### 七、调试与验证

- [ ] 调试机验证 `competition` 模式可持续运行
- [ ] 调试机验证异常后自动恢复
- [ ] 调试机验证已完成题不会重复浪费时间
- [ ] 调试机验证 flag 提交后状态更新正确
- [ ] 调试机验证 `scripts/remote_control.sh competition-start`
- [ ] 调试机验证 `scripts/remote_control.sh competition-restart`

### 八、清理旧实现

- [x] 识别并删除已经不再作为主路径的旧模块
- [x] 清理旧的 controller/debug_chat/llm 兼容残留
- [x] 清理旧测试或将其迁移到新架构
- [x] 让 README 只描述新架构，不再混用旧术语

## 当前我建议的优先级

1. 调试机完整跑通 `competition`
2. 把四赛道通用 skills 真正接到推进阶段
3. 记录 foothold / 权限维持等更细粒度笔记
4. 长时间运行后的状态恢复
5. `competition` 后台日志与控制脚本联调

## 当前最关键的风险

- [ ] 当前架构虽然已经能交互，但四赛道能力模块还不够完整
- [ ] `competition` 模式的长期恢复还不够强
- [ ] 当前虽然已有自动降级，但部分高阶工具还只是轻量降级，不是完整替代
