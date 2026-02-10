---
name: cg0x-subagent-team
description: >
  Manages subagent team composition, model priority, role assignment, and workflow
  for multi-agent development projects. Use when user needs to coordinate subagents,
  assign dev/test roles, or define team workflow.
  Triggers: "子Agent", "subagent", "团队管理", "team management", "角色分配",
  "role assignment", "模型优先级", "model priority", "opus编程模式",
  "kimi编程模式", "xx编程模式".
---

# Subagent Team Management

## Usage

Typical prompts that should trigger this skill:

```
按照团队规范分配子Agent角色
```

```
Set up subagent team for this project
```

```
opus编程模式 帮我重构这个模块
```

```
kimi编程模式 写一个爬虫
```

## Model Priority (for new subagents)

1. **anthropic/claude-opus-4-5** (preferred)
2. **kimi-coding/k2p5** (fallback)
3. **google/gemini-3-pro-preview** (next fallback)
4. **minimax/MiniMax-M2.1** (last resort)

## Role Assignment

| Subagent | Responsibilities |
|----------|-----------------|
| **Frontend Dev** | UI design, frontend development, image generation |
| **Backend Dev** | Python backend, business logic implementation |
| **Backend Tester** | API verification, unit tests, maintain test suite |
| **Frontend Tester** | Headless browser testing, page load, JS clicks, state verification |

## Deliverables (Tester Required)

Tester subagent must provide:

1. **Test project code** - All test cases
2. **Test report** - Results (pass/fail, screenshots)
3. **Public access URL** - Actual ngrok domain
4. **Feature path清单** - All accessible routes and endpoints

All must pass before delivery.

## Workflow

```
1. Task Assignment → Must pair with tester
   - Backend dev → Backend Tester
   - Frontend dev → Frontend Tester
2. Development → Dev implements features
3. Testing → Tester validates independently (all must pass)
4. Bug Fix → Respective dev fixes issues
5. Management → I coordinate subagents, responsible to user
```

## Programming Mode Quick Dispatch（编程模式）

A shortcut convention for OpenClaw to quickly route tasks to model-specific subagents.

### How It Works

The user says a keyword in the format **"<model>编程模式"** followed by the task description. OpenClaw recognizes the keyword and dispatches accordingly:

```
<model>编程模式 <task description>
```

### Dispatch Rules

1. **Parse the keyword** — Extract the model name from the pattern `<model>编程模式`.
2. **Check for existing subagent** — If a subagent based on the specified model is **already running**, route the task to that subagent directly.
3. **Create if not exists** — If no subagent based on the specified model exists yet, **create a new subagent** with the specified model, then assign the task.
4. **Execute** — The subagent begins working on the task description that follows the keyword.

### Preconfigured Modes

| Keyword | Model | Notes |
|---------|-------|-------|
| **opus编程模式** | `anthropic/claude-opus-4-5` | Strongest reasoning, preferred for complex tasks |
| **kimi编程模式** | `kimi-coding/k2p5` | Fast iteration, good for general coding |

> New modes can be added by defining additional `<model>编程模式 → model mapping` entries above.
> The model identifier must match what OpenClaw accepts in its subagent creation API.

### Examples

```
opus编程模式 帮我重构 backend/auth 模块，拆分成 JWT 和 OAuth 两个子模块
```
→ OpenClaw checks: claude-opus-4-5 subagent running? **No** → Creates one → Assigns the refactoring task.

```
opus编程模式 继续，把单元测试也补上
```
→ OpenClaw checks: claude-opus-4-5 subagent running? **Yes** → Routes directly to the existing subagent.

```
kimi编程模式 写一个从 Civitai 批量下载模型的 Python 脚本
```
→ OpenClaw checks: k2p5 subagent running? **No** → Creates one → Assigns the scripting task.
