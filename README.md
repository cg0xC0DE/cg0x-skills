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

### cg0x-cc-dual-launcher

多 Provider Claude Code 启动器。提供 Windows / macOS 双平台脚本，一键切换 Origin（Anthropic）、Switch（第三方 API）、Ollama（本地模型）三种配置启动 Claude Code。

**包含内容**：

- 平台脚本（`.bat` / `.sh`）：每种 profile 一个启动脚本
- 共享 profile 模板（`.json.template`）：环境变量 + 插件配置
- 插件同步脚本：跨 profile 双向合并 `enabledPlugins` 等共享设置
- Windows 右键菜单 `.reg` 模板 / macOS Quick Action

```
# 触发示例
帮我配置多 provider 的 Claude Code 启动环境
```

---

### cg0x-deathcraft

通过"死亡穿越"（Death-Transmigration）技法，自动生成角色人格文件。

默认生成单文件 `PERSONA.md`（通用格式），加 `--dual` 参数可生成 `SOUL.md + IDENTITY.md` 双文件（OpenClaw 格式）。

用户输入任意历史人物、文学角色或虚构角色名，skill 自动：识别角色 → 推断前世结局与关键人生阶段 → LLM 生成死亡穿越叙事 → 写入工作区。无需已知角色表，每次都是全新角色处理。

```
/deathcraft 虞姬                        → PERSONA.md
/deathcraft 林晚星: 22岁都市女程序员     → PERSONA.md（带描述）
/deathcraft 贾诩 --dual                 → SOUL.md + IDENTITY.md
```

---

### cg0x-frame-analysis

Frame Method（反路径锁定多框架分析法）。适用于探索期问题，默认不急着下结论，先展开多条理解路径，再决定要不要收敛。

支持三种模式：

- `/cg0x-frame-analysis on` — 开启 always-on，自动判断是否需要激活
- `/cg0x-frame-analysis off` — 关闭自动判断
- `/cg0x-frame-analysis <问题>` — 单次激活

```
/cg0x-frame-analysis on
/cg0x-frame-analysis 这个架构方案怎么选？
```

---

### cg0x-project-launcher

远程项目一键上线 skill。一次执行完成从环境检测到 ngrok 公网暴露的全部流程。

**目标用户**：通过 AI Agent 远程操控电脑部署项目的开发者。

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
| 8 | 健康验证（四层 × 三路径 HTTP 200 + 防误诊机制） |

**双系统支持**：所有脚本同时生成 `.cmd`（Windows）和 `.sh`（macOS）两个版本。

```
帮我远程上线这个项目
一键启动并发布到公网
```

---

## 项目结构

```
cg0x-skills/
├── .claude-plugin/
│   └── marketplace.json
├── skills/
│   ├── cg0x-cc-dual-launcher/
│   │   ├── SKILL.md
│   │   └── scripts/
│   │       ├── windows/
│   │       ├── macos/
│   │       └── profiles/
│   ├── cg0x-deathcraft/
│   │   └── SKILL.md
│   ├── cg0x-frame-analysis/
│   │   └── SKILL.md
│   └── cg0x-project-launcher/
│       └── SKILL.md
├── CLAUDE.md
├── README.md
└── .gitignore
```

## License

Apache-2.0
