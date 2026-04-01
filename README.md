# cg0x-skills

cg0x 共享的 AI Agent 技能库，覆盖开发工作流与项目自动化。

## 安装

### 快速安装（推荐）

```
npx skills add cg0x/cg0x-skills
```

### 注册为插件市场

在 Claude Code 中运行：

```
/plugin marketplace add cg0x/cg0x-skills
```

### 手动安装单个 Skill

将目标 Skill 的 `SKILL.md` 复制到 Claude Code 的 Skill 目录：

```
# 全局安装（对所有项目生效）
~/.claude/skills/cg0x-<skill-name>/SKILL.md

# 项目级安装
your-project/.claude/skills/cg0x-<skill-name>/SKILL.md
```

也可以直接将 `SKILL.md` 内容粘贴到任意 AI 对话中作为 Prompt 使用。

---

## Available Skills

技能分为一个插件分组 **dev-tools**，包含以下技能：

### cg0x-project-launcher

合并 init-maker + dev-standards 的单一远程上线 skill。一次执行完成从环境检测到 ngrok 公网暴露的全部流程。

很多开源项目的部署流程散落在 README 的各个角落——装 Python、装 Node、建虚拟环境、填 API Key……对新手极不友好。Init-Maker 让 Agent 自动扫描项目依赖，生成完整可运行的 `init.bat`，用户双击即可完成全部初始化。
**目标用户**：有基本编程经验的 Type B 用户，通过 Remote Control Agent 远程操控家庭电脑。

**8 阶段 Pipeline**：

| Phase | 内容 |
|-------|------|
| 1 | 环境探测（OS + Required/Optional 依赖分类） |
| 2 | 项目脚手架（目录结构 + .gitignore） |
| 3 | 依赖安装（venv + pip + npm，静默自动化） |
| 4 | 凭证收集（交互式，逐字段） |
| 5 | nginx 配置（location blocks + reload） |
| 6 | 服务启动（watchdog loop + port cleanup） |
| 7 | ngrok 公网暴露 |
| 8 | 健康验证（四层 × 三路径 HTTP 200） |

**双系统支持**：所有脚本同时生成 `.cmd`（Windows）和 `.sh`（macOS）两个版本。

**设计原则**：

- **Required 依赖阻塞** — Python、git 等缺失则等待用户安装，不跳过
- **Optional 依赖警告后跳过** — ffmpeg、ngrok 等缺失显示 Impact 后继续
- **watchdog loop** — 所有 `start_*.cmd/sh` 含进程退出自动重启
- **port cleanup** — 每次启动前杀端口占用进程，防止重复启动
- **ngrok-skip-browser-warning** — 所有前端 fetch 必须带此 header

**触发示例**：

```
帮我远程上线这个项目
一键启动并发布到公网
```


### cg0x-subagent-team

管理多 Agent 开发项目中的子 Agent 团队组成、模型优先级、角色分配与工作流。

支持 **编程模式快速调度**：通过 `opus编程模式`、`kimi编程模式` 等关键词口令，让 OpenClaw 自动创建或复用指定模型的 subagent 来执行任务。

**模型优先级**：

1. `anthropic/claude-opus-4-5`（首选）
2. `kimi-coding/k2p5`（备选）
3. `google/gemini-3-pro-preview`（次备选）
4. `minimax/MiniMax-M2.1`（末选）

**角色分配**：

| 子Agent | 职责 |
|---------|------|
| **Frontend Dev** | UI 设计、前端开发、图片生成 |
| **Backend Dev** | Python 后端、业务逻辑实现 |
| **Backend Tester** | API 验证、单元测试、维护测试套件 |
| **Frontend Tester** | 无头浏览器测试、页面加载、JS 交互、状态验证 |

**编程模式示例**：

```
opus编程模式 帮我重构 backend/auth 模块
kimi编程模式 写一个爬虫脚本
按照团队规范分配子Agent角色
```

---

### cg0x-service-guardian

一个 AI Agent Skill，用于生成 **Python 本地服务健康检查脚本**（守护脚本）。

本地开发环境常常同时跑多个服务（前端、后端、反向代理、隧道等），需要定期自检。朴素的健康检查——单次探测、短超时、盲目重启——经常把瞬时慢响应**误诊**为宕机，产生大量重复进程。Service Guardian 让 Agent 生成带防误诊机制的健康检查脚本。

**核心防误诊机制**：

| 机制 | 作用 |
|------|------|
| 重试探测（≥3 次） | 避免因瞬时 GC / IO 抖动导致误判 |
| 端口占用检测 | 启动前用 `netstat`/`lsof` + bind 确认端口空闲，防止重复启动 |
| 僵尸进程清理 | 重启前自动 kill 占用端口的僵尸/孤儿进程，确保新进程能绑定端口 |
| 区分错误类型 | `ConnectionRefused`（真挂了）vs `timeout`（只是慢） |
| 外部 URL 不自动重启 | ngrok 等外部隧道受网络波动影响，只报告不重启 |
| 正常时静默退出 | 适合 Task Scheduler / cron 定时调用 |

**脚本四层架构**：

- **配置层** — `SERVICES` + `START_SCRIPTS` 字典，统一管理服务定义和启动命令
- **探测层** — TCP 端口探测、本地 HTTP 探测、外部 URL 探测，带重试包装
- **守卫层** — `is_port_in_use()` 端口占用检测 + `kill_port_process()` 僵尸进程清理 + `start_service()` 安全启动
- **主循环** — 重试检查 → 诊断 → 守卫 → 修复 → 二次验证

**设计原则**：

- **零外部依赖** — 纯 Python 标准库，无需 pip install
- **静默正常** — 所有服务正常时无任何输出，exit 0
- **结构化配置** — 单一 `SERVICES` 字典是检查和重启的唯一数据源
- **跨平台可适配** — Windows 默认（`DETACHED_PROCESS`），注释说明 Linux 适配方式

```
# 触发示例
帮我写一个守护脚本，定时检查本地服务是否正常
我的自检脚本老是误报服务挂了，帮我修一下
```

---

### cg0x-agent-memory

一个 AI Agent Skill，为 OpenClaw 的简陋记忆系统打补丁，建立三层记忆体系。

OpenClaw 默认把整个 session JSONL 喂给 LLM，session 无限增长（700KB = ~500K tokens/次心跳）。内置 `safeguard` 压缩会重置 session 但**不保留摘要**，上下文全部丢失。本 Skill 解决这个问题。

**三层记忆架构**：

| 层级 | 载体 | 说明 |
|------|------|------|
| 短期 | Session JSONL | OpenClaw 管理，超过 100KB 自动压缩 |
| 中期 | `MEMORY.md` | 子弹列表摘要，每条：`时间·场景·人物·事件·起因·结果·情绪影响`，最多 50 条 |
| 长期 | `memory/archive/YYYY-MM.md` | FIFO 归档，按需查询 |

**包含工具**：

- `tools/compact_session.py` — 通用压缩工具，支持 Anthropic / OpenAI 兼容 API，可作为库调用或 CLI 独立运行
- `tools/query_deep_memory.py` — 归档记忆关键词搜索工具

**核心机制**：

- 检测到 session JSONL > 100KB 时触发压缩
- 调用 LLM（推荐最便宜的 haiku/gpt-4o-mini）生成摘要子弹列表
- 旧 session 重命名为 `.reset.<timestamp>`，新 session 保留最后 10 行保证对话连续性
- MEMORY.md 超过 50 条时，最旧的条目 FIFO 归档到月度文件

```
# 触发示例
帮我建立记忆系统
session 太长了，帮我压缩一下
你忘记了上次我们说的事情
把这个记下来
查一下以前关于项目截止日期的记录
```

---

### cg0x-mq-event

一个 AI Agent Skill，指导如何将项目中的异常事件推送到本地 cmd-patrol 消息队列（MQ）。

当自动化流水线遇到**无法自动处理的问题**（元数据解析失败、模型缺失、验证错误等），应通过 MQ 上报事件，由人工在 cmd-patrol 面板中查看和处理。

**核心机制**：

| 机制 | 说明 |
|------|------|
| 端点发现 | 环境变量 `CMD_PATROL_URL`，默认 `http://127.0.0.1:5050` |
| 消息状态 | `new` → `ack` → `done`，只有人工确认才会终结 |
| 零依赖 | 提供纯 stdlib 的 Python helper，复制即用 |
| 最佳努力 | 推送失败不会影响主进程运行 |

**适用场景**：

- 跳过的任务（解析失败、格式不支持）
- 需要手工获取的资源（模型下载、API Key）
- 超出自动化能力的验证错误
- 任何静默失败会导致数据丢失的情况

```
# 触发示例
帮我在错误处理里加上事件推送到 MQ
把跳过的任务报告给 patrol
```

---

## 项目结构

```
cg0x-skills/
├── .claude-plugin/
│   └── marketplace.json
├── skills/
│   ├── cg0x-project-launcher/
│   │   └── SKILL.md
│   ├── cg0x-subagent-team/
│   │   └── SKILL.md
│   ├── cg0x-service-guardian/
│   │   └── SKILL.md
│   ├── cg0x-mq-event/
│   │   └── SKILL.md
│   └── cg0x-agent-memory/
│       ├── SKILL.md
│       └── tools/
│           ├── compact_session.py
│           └── query_deep_memory.py
├── CLAUDE.md
├── README.md
└── .gitignore
```

## License

Apache-2.0
