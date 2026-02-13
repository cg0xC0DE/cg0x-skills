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

### cg0x-init-maker

一个 AI Agent Skill，用于为开源项目自动生成 **Windows 一键初始化脚本** (`init.bat`)。

很多开源项目的部署流程散落在 README 的各个角落——装 Python、装 Node、建虚拟环境、填 API Key……对新手极不友好。Init-Maker 让 Agent 自动扫描项目依赖，生成完整可运行的 `init.bat`，用户双击即可完成全部初始化。

**适用项目类型**：

| 层 | 技术栈 |
|----|--------|
| 前端 | 纯 HTML + JS + CSS（通过 npm 管理依赖） |
| 后端 | Python |

> 其他架构的项目可以参考本 Skill 的结构进行改造。

**生成的脚本包含三个阶段**：

- **阶段一：环境检查** — 逐项检测系统工具（Python、Node.js、npm 等）。支持 `winget` 自动安装缺失工具，或提示手动安装后按回车重新检测。
- **阶段二：自动安装** — 全自动创建 venv、安装 `requirements.txt`、执行 `npm install` 等。已完成步骤自动跳过（幂等）。
- **阶段三：凭据配置** — 自动识别 `example_credentials.*` 模板文件，逐字段引导用户输入 API Key 等敏感信息，完成后生成正式凭据文件。

**设计原则**：

- **幂等性** — 脚本可重复运行，不会重复创建或覆盖已有内容
- **不退出，只阻塞** — 环境缺失时等待用户安装，而非直接报错退出
- **逐项交互** — 凭据逐字段录入，降低用户出错概率
- **零外部依赖** — 纯 Windows Batch，不依赖 PowerShell、WSL 或第三方工具
- **动态适配** — Agent 会根据项目实际文件（而非硬编码）生成脚本内容

**自定义与扩展**：

- **增加检测项** — 在 Phase 1 的检查表中添加新工具（如 Docker、Java）
- **修改安装步骤** — 在 Phase 2 中增减自动化操作
- **适配其他凭据格式** — Phase 3 支持 `.py`、`.json`、`.env` 等任意格式
- **迁移到其他平台** — 将 `.bat` 语法替换为 `.sh` 即可适配 Linux/macOS

**输出示例**：

```
============================================================
  Phase 1: Environment Check
============================================================
[OK] Python detected.
[OK] Node.js detected.
[OK] npm detected.

============================================================
  Phase 2: Automated Installation
============================================================
[INFO] Creating Python virtual environment...
[SKIP] node_modules already exists.
[INFO] Installing Python dependencies...
[OK] All dependencies installed.

============================================================
  Phase 3: Credential Configuration
============================================================
[INFO] Configuring credentials from example_credentials.py ...
  Enter your API_KEY: ********
  Enter your SECRET: ********
[OK] credentials.py created.

============================================================
  Initialization complete! You can now start the project.
============================================================
```

```
# 触发示例
请为本项目生成一个 Windows init.bat 初始化脚本
```

---

### cg0x-dev-standards

一份面向 AI Agent 的技能描述文件，用于快速初始化可部署的 Web 原型应用。

Agent 加载本 Skill 后，即可按照统一规范自动完成项目脚手架搭建、前后端服务配置、密钥管理、网络部署及健康检查，无需反复对齐上下文。

**技术栈**：

| 层级 | 技术 |
|------|------|
| 前端 | 纯 HTML / JS / CSS（不使用框架） |
| 后端 | Python 3.10+ |
| 网络 | ngrok → nginx → Python HTTP Server |

**项目结构约定**：

```
workplace/
├── myproject/                  # 前端（短命名）
│   ├── index.html
│   └── ...
├── myproject-service/          # 后端（前端名 + -service）
│   ├── venv/
│   ├── app.py
│   ├── requirements.txt
│   ├── data/                   # 数据存储（JSON/CSV/TXT）
│   └── some_module/
│       ├── config.py           # 系统配置（常量、线程数、话术等）
│       ├── credentials.py      # 密钥（gitignore，不提交）
│       └── example_credentials.py  # 密钥占位示例（提交）
├── .gitignore
├── init.cmd                    # 环境初始化
├── start_frontend.cmd          # 启动前端
├── start_backend.cmd           # 启动后端
└── start_deps.cmd              # 启动外部依赖（可选）
```

**启动脚本**（每个项目根目录最多 4 个 `.cmd`）：

| 脚本 | 用途 | 何时需要 |
|------|------|----------|
| `init.cmd` | 检查环境、创建 venv、安装依赖、配置密钥 | 首次运行或依赖变更后 |
| `start_frontend.cmd` | 启动前端服务 | 始终需要 |
| `start_backend.cmd` | 启动后端服务 | 始终需要 |
| `start_deps.cmd` | 启动外部依赖（如 ComfyUI） | 仅依赖外部服务时 |

**后端组件规范**：

| 文件 | 内容 | 是否提交 |
|------|------|----------|
| `config.py` | 线程数、常量、提示词模板、字面量等系统配置 | ✅ 是 |
| `credentials.py` | API Token、CLI Token、连接字符串等明文密钥 | ❌ 否（gitignore） |
| `example_credentials.py` | 与 `credentials.py` 结构一致，值为占位符 | ✅ 是 |

**网络架构**：

```
用户 → ngrok（公网隧道）→ nginx（反向代理，8080）→ 前端/后端
```

**部署流程**：启动后端 → 配置 nginx → 确认 ngrok → 验证路由 200

**健康检查**（`node healthcheck.js`）：

| 检查项 | 范围 | 说明 |
|--------|------|------|
| ngrok | 全局 | 隧道是否存活 |
| nginx | 全局 | 代理是否运行 |
| 项目前端 | 每个项目 × 3 条路径 | ngrok / nginx / localhost |
| 项目后端 | 每个项目 × 3 条路径 | ngrok / nginx / localhost |

检查失败时自动按顺序恢复：ngrok → nginx → 后端 → 前端。

```
# 触发示例
帮我新建一个 Web 项目，按照标准规范来
```

---

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

## 项目结构

```
cg0x-skills/
├── .claude-plugin/
│   └── marketplace.json
├── skills/
│   ├── cg0x-init-maker/
│   │   └── SKILL.md
│   ├── cg0x-dev-standards/
│   │   └── SKILL.md
│   ├── cg0x-subagent-team/
│   │   └── SKILL.md
│   └── cg0x-service-guardian/
│       └── SKILL.md
├── CLAUDE.md
├── README.md
└── .gitignore
```

## License

Apache-2.0
