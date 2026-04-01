# cg0x-project-launcher Design

## Overview

合并 `cg0x-init-maker` + `cg0x-dev-standards` 为单一skill `cg0x-project-launcher`。

**Target user**: Type B（有基本编程经验，能看懂README并跟着操作，不懂技术细节）

**Core use case**: Remote control agent帮用户在家庭电脑上从零搭建项目并通过ngrok公网暴露、发布链接。

**独立保留**: `cg0x-service-guardian`（按需调用）、`cg0x-subagent-team`（与主路径正交）

**No subcommand syntax** (`:` 分隔) — Pipeline本身是线性的，用户说一句话，机器执行到底。

---

## Target Architecture

```
skills/
└── cg0x-project-launcher/
    └── SKILL.md
```

---

## Pipeline (8 Phases)

### Phase 1 — 环境探测

- 检测 OS（Windows / macOS），自动选择脚本后缀
- 检测 Python 版本（>= 3.10）、node、npm、git、ngrok
- **Required vs Optional 分类**：
  - Required（Python、git、pip）：缺失则阻塞，提供 winget/homebrew 安装命令，重试验证
  - Optional（node、ffmpeg、ngrok）：缺失则警告，说明 Impact 后允许跳过
- 所有警告必须包含 **Impact 说明**（如"无法提取音频"、"移动端无法访问"）

### Phase 2 — 项目脚手架生成

- 根据项目类型生成目录结构：
  - `frontend/` — 静态HTML+JS+CSS
  - `backend-service/` — Python后端
- 生成标准 `.gitignore`（venv、\_\_pycache\_\_、credentials.py、.DS_Store等）
- 所有脚本双系统版本：Windows `.cmd` + macOS `.sh`

### Phase 3 — 依赖安装（静默自动化）

- 创建 venv（如不存在）
- `pip install -r requirements.txt`
- `npm install`（如 node_modules 不存在）
- **Phase 2 的脚本生成依赖此阶段结果**

### Phase 4 — 凭证收集（交互式）

- 扫描 `example_credentials.py` 等模板文件，逐字段收集
- 每字段：**用途说明** + **缺失影响** + 用户输入提示
- 全部收集完成后一次性写入 `credentials.py`（不提前rename）
- 凭证文件 **Gitignored**，不提交

### Phase 5 — nginx 配置

- 生成 nginx `location` 块：
  - `/project-name/` → 前端静态文件
  - `/project-name-service/` → 后端API
- 执行 `nginx -s reload`
- 写入 `nginx.conf`（如需要新建）

### Phase 6 — 启动服务

- **先启动 backend** → 再启动 frontend
- 每个 `start_*.cmd` / `start_*.sh` 包含：
  - **watchdog loop**：进程退出后自动重启（RESTART_DELAY=5s）
  - **port cleanup**：启动前杀占用端口的进程（netstat+lsof）
- stderr/stdout → DEVNULL（防止 zombie handle）

### Phase 7 — ngrok 公网暴露

- 启动 `ngrok http BACKEND_PORT`
- 获取 public URL
- **所有前端 fetch() 调用必须带 header**：`'ngrok-skip-browser-warning': 'true'`

### Phase 8 — 健康验证

四层 × 三路径验证，每条必须 HTTP 200：

| 层级 | 范围 |
|------|------|
| ngrok 全局 | device-wide tunnel |
| nginx 全局 | proxy layer |
| 项目前端 | 3路径（ngrok / nginx / localhost） |
| 项目后端 | 3路径（ngrok / nginx / localhost） |

**Auto-recovery 顺序**：ngrok → nginx → backend → frontend

---

## Generated Scripts 规范

### start_backend.cmd / start_backend.sh

```cmd
@echo off
setlocal EnableDelayedExpansion
set ROOT=%~dp0
set VENV_PY=%ROOT%backend-service\venv\Scripts\python.exe
set PORT=8080
set RESTART_DELAY=5

:loop
REM --- port cleanup ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORT% "') do (
    if not "%%a"=="0" taskkill /PID %%a /F >nul 2>&1
    timeout /t 1 /nobreak >nul
)
echo Starting backend on http://localhost:%PORT% ...
"%VENV_PY%" -m http.server %PORT%
echo Exited (code: !errorlevel!). Restarting in %RESTART_DELAY%s ...
timeout /t %RESTART_DELAY% /nobreak >nul
goto loop
```

### start_frontend.cmd / start_frontend.sh

同上结构，换 `python -m http.server FRONTEND_PORT` 或 `npx serve`。

### init.cmd / init.sh

一次性交互脚本（**无 watchdog**），三阶段：环境检测 → 依赖安装 → 凭证收集。

---

## Critical Rules（从原skill继承）

| 规则 | 来源 |
|------|------|
| 所有 `echo` 字符串必须用双引号包裹 | init-maker |
| 使用 `REM` 而非 `::` 做注释 | init-maker |
| Windows 脚本用 CRLF，macOS 用 LF | init-maker |
| `goto` 替代复杂 `if/else` 嵌套 | init-maker |
| 多行文件写入用 `>` + `>>`，不用 `(...) > file` | init-maker |
| `ngrok-skip-browser-warning` header 所有 fetch 必须带 | dev-standards |
| `127.0.0.1` 而非 `localhost`（DNS开销） | service-guardian |
| venv 必须单独创建，每个项目隔离 | dev-standards |

---

## service-guardian 关系

- **不合并** — guardian是 Phase 8 之后可选的长期守护步骤
- Phase 8 结束后提示：`如需后台守护进程，运行 /cg0x-service-guardian`

---

## subagent-team 关系

- **正交** — 多Agent团队管理不在这条Pipeline上
- 如用户提到"多人协作"，单独触发 `/cg0x-subagent-team`

---

## Skill 文件结构

```
skills/cg0x-project-launcher/SKILL.md  (~400-450行)
```

SKILL.md body 包含：
1. YAML front matter（name + description + triggers）
2. 8 Phase 执行流程
3. 生成脚本模板（start_*.cmd/sh）
4. 双系统语法对照表
5. Critical Rules 清单
6. service-guardian / subagent-team 引用说明

---

## 合并后的 skill 数量变化

| Before | After |
|--------|-------|
| cg0x-init-maker | cg0x-project-launcher（合并init+dev-std） |
| cg0x-dev-standards | （内容合并进project-launcher） |
| cg0x-service-guardian | 保持不变 |
| cg0x-subagent-team | 保持不变 |

**总 skill 数**：4 → 3（net -1）
