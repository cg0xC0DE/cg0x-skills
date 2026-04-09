<div align="center">

# ⚡ cg0x-skills

**AI Agent 技能库 — 开发工作流 · 项目自动化 · 角色炼成**

[![Skills](https://img.shields.io/badge/skills-4-blue?style=flat-square)](./skills)
[![License](https://img.shields.io/badge/license-Apache_2.0-green?style=flat-square)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-Claude_Code-blueviolet?style=flat-square)](#)

*可安装到任意 AI Agent 的即插即用技能包*

</div>

---

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

<table>
<tr><td>

### 🔀 cc-dual-launcher

**多 Provider Claude Code 启动器**

Windows / macOS 双平台，一键切换 Origin · Switch · Ollama 三种 LLM 配置。跨 profile 自动同步插件和市场设置。

```
帮我配置多 provider 的 Claude Code 启动环境
```

<details><summary>包含内容</summary>

- 平台脚本（`.bat` / `.sh`）：每种 profile 一个启动脚本
- 共享 profile 模板（`.json.template`）：环境变量 + 插件配置
- 插件同步脚本：跨 profile 双向合并共享设置
- Windows 右键菜单 `.reg` / macOS Quick Action

</details>

</td></tr>
<tr><td>

### 💀 deathcraft

**死亡穿越 · 人格炼成**

输入角色名 → 自动执行死亡穿越叙事 → 生成完整人格文件。支持单文件 `PERSONA.md`（默认）和双文件 `SOUL.md + IDENTITY.md`（OpenClaw）。

```
/deathcraft 虞姬                        → PERSONA.md
/deathcraft 林晚星: 22岁都市女程序员     → PERSONA.md（带描述）
/deathcraft 贾诩 --dual                 → SOUL.md + IDENTITY.md
```

</td></tr>
<tr><td>

### 🔍 frame-analysis

**反路径锁定 · 多框架分析法**

适用于探索期问题——先展开多条理解路径，再决定要不要收敛。支持 always-on / off / 单次三种模式。

```
/cg0x-frame-analysis on                 → 常驻自动判断
/cg0x-frame-analysis 这个架构方案怎么选？  → 单次激活
```

</td></tr>
<tr><td>

### 🚀 project-launcher

**远程项目一键上线**

8 阶段 Pipeline：环境探测 → 脚手架 → 依赖安装 → 凭证收集 → nginx → watchdog 启动 → ngrok 公网 → 健康验证。双系统（Windows / macOS）全自动。

```
帮我远程上线这个项目
一键启动并发布到公网
```

<details><summary>8 阶段详情</summary>

| Phase | 内容 |
|:-----:|------|
| 1 | 环境探测（OS + Required/Optional 依赖分类） |
| 2 | 项目脚手架（目录结构 + .gitignore） |
| 3 | 依赖安装（venv + pip + npm，静默自动化） |
| 4 | 凭证收集（交互式，逐字段） |
| 5 | nginx 配置（location blocks + reload） |
| 6 | 服务启动（watchdog loop + port cleanup） |
| 7 | ngrok 公网暴露 |
| 8 | 健康验证（四层 × 三路径 HTTP 200 + 防误诊） |

</details>

</td></tr>
</table>

---

## 项目结构

```
cg0x-skills/
├── .claude-plugin/
│   └── marketplace.json
├── skills/
│   ├── cg0x-cc-dual-launcher/    # 🔀 多 Provider 启动器
│   ├── cg0x-deathcraft/          # 💀 死亡穿越人格生成
│   ├── cg0x-frame-analysis/      # 🔍 多框架分析法
│   └── cg0x-project-launcher/    # 🚀 远程项目上线
├── CLAUDE.md
├── README.md
└── .gitignore
```

## License

Apache-2.0
