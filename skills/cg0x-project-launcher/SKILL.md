---
name: cg0x-project-launcher
description: >
  Remote-first project launch skill.
  Detects environment, scaffolds project, installs deps, collects credentials,
  configures nginx, starts services with watchdog, exposes via ngrok, and verifies
  all three access paths (localhost / nginx / ngrok) return HTTP 200.
  Use when user says "帮我远程上线这个项目" or "一键启动并发布".
  Triggers: "远程上线", "一键启动", "发布到公网", "ngrok", "帮我搭建项目",
  "从零开始项目", "launch project remotely", "deploy with ngrok".
---

# cg0x-project-launcher — Remote Project Launcher

## 8-Phase Pipeline

```
Phase 1: 环境探测（OS + Required/Optional deps）
Phase 2: 项目脚手架（目录结构 + .gitignore）
Phase 3: 依赖安装（venv + pip + npm，静默）
Phase 4: 凭证收集（交互式，逐字段）
Phase 5: nginx 配置（location blocks + reload）
Phase 6: 启动服务（watchdog + port cleanup）
Phase 7: ngrok 公网暴露
Phase 8: 健康验证（四层 × 三路径 200）
```

---

## Phase 1 — 环境探测

### OS检测

```bat
REM Windows
if defined OS (set OS_TYPE=Windows) else if exist /bin/uname (set OS_TYPE=macOS)
```

```bash
# macOS
[ "$(uname)" = "Darwin" ] && OS_TYPE="macOS"
```

### Required vs Optional 分类

| 依赖 | 检测命令（Win） | 检测命令（macOS） | Required |
|------|----------------|-----------------|---------|
| Python | `python --version` | `python3 --version` | Yes |
| pip | `pip --version` | `pip3 --version` | Yes |
| git | `git --version` | `git --version` | Yes |
| node | `node --version` | `node --version` | Optional |
| npm | `npm --version` | `npm --version` | Optional |
| ngrok | `ngrok version` | `ngrok version` | Optional |
| ffmpeg | `ffmpeg -version` | `ffmpeg -version` | Optional |

### Impact 规则（每条缺失信息必须包含）

```
[MISSING] <tool> is not detected.
         Impact: <what breaks without it>

[WARN] <tool> is not detected.
       Impact: <what feature degrades or is unavailable>
       Option to skip (optional deps only).
```

### Required Deps — 阻塞式重试循环

```bat
:CHECK_PYTHON
python --version >nul 2>&1
if not errorlevel 1 goto PYTHON_OK

echo [MISSING] Python is not detected.
echo          Impact: The backend cannot run at all.
set /p ANS="Install via winget? (Y/N): "
if /i "!ANS!"=="Y" (
    winget install Python.Python.3.12 --accept-source-agreements --accept-package-agreements
)
if /i "!ANS!" neq "Y" (
    echo Please install Python manually and ensure it is in PATH.
    set /p _="Press ENTER to re-check..."
)
goto CHECK_PYTHON
:PYTHON_OK
```

### Optional Deps — 警告后跳过

```bat
:CHECK_FFMPEG
where ffmpeg >nul 2>&1
if not errorlevel 1 goto FFMPEG_OK

echo [WARN] ffmpeg is not detected.
echo        Impact: Cannot extract audio. Video transcription will FAIL.
choice /m "Install via winget"
if errorlevel 2 goto FFMPEG_SKIP
winget install Gyan.FFmpeg --accept-source-agreements --accept-package-agreements
:FFMPEG_SKIP
echo        Skipped — this is optional.
:FFMPEG_OK
```

### macOS 对照

```bash
# winget → brew
BREW_AVAILABLE=0
command -v brew &>/dev/null && BREW_AVAILABLE=1

check_python() {
  if command -v python3 &>/dev/null; then return 0; fi
  echo "[MISSING] Python not detected."
  echo "Impact: Backend cannot run."
  if [ "$BREW_AVAILABLE" -eq 1 ]; then
    read -p "Install via Homebrew? (Y/N): " ans
    [[ "$ans" =~ ^[Yy]$ ]] && brew install python@3.12
  fi
  read -p "After installing, press ENTER to re-check..."
  check_python
}
```

---

## Phase 2 — 项目脚手架

### 标准目录结构

```
PROJECT_NAME/
├── frontend/              # HTML + JS + CSS
├── backend-service/        # Python backend
│   └── venv/              # Python virtual environment
├── data/                  # JSON/CSV/TXT storage
└── .gitignore
```

### .gitignore 模板

```gitignore
__pycache__/
*.py[cod]
*$py.class
venv/
env/
.venv/
.vscode/
.idea/
*.swp
.DS_Store
credentials.py
```

### 双系统生成规则

所有脚本必须同时生成 Windows `.cmd` 和 macOS `.sh` 两个版本。

---

## Phase 3 — 依赖安装（静默自动化）

```bat
REM --- venv ---
if exist "backend-service\venv" goto VENV_EXISTS
echo [INFO] Creating venv...
python -m venv backend-service\venv
:VENV_EXISTS

call backend-service\venv\Scripts\activate.bat
pip install -r backend-service\requirements.txt
```

```bash
# macOS
if [ ! -d backend-service/venv ]; then
  python3 -m venv backend-service/venv
fi
source backend-service/venv/bin/activate
pip install -r backend-service/requirements.txt
```

---

## Phase 4 — 凭证收集（交互式）

### 扫描凭证字段

扫描 `example_credentials.py`、`example_credentials.json` 等文件，逐字段收集。

### 每字段三要素

```
[1/N] FIELD_NAME
  用途: <module> uses this for <feature>
  缺失影响: <what breaks if empty>
  > Enter value:
```

### 写入规范

- 全部字段收集完才写入文件（不用提前 rename）
- Windows: 顺序 `echo >` + `echo >>`，不用 `(...) > file`

```bat
echo [INFO] Writing credentials.py...
echo API_KEY = '!API_KEY!' > backend-service\credentials.py
echo SECRET_KEY = '!SECRET_KEY!' >> backend-service\credentials.py
```

---

## Phase 5 — nginx 配置

### 生成 location 块

```nginx
server {
    listen 80;
    server_name localhost;

    location /PROJECT_NAME/ {
        rewrite ^/PROJECT_NAME/(.*)$ /$1 break;
        proxy_pass http://localhost:FRONTEND_PORT/;
    }

    location /PROJECT_NAME-service/ {
        rewrite ^/PROJECT_NAME-service/(.*)$ /$1 break;
        proxy_pass http://127.0.0.1:BACKEND_PORT/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 部署步骤

1. 追加 location 块到 `nginx.conf`
2. 执行 `nginx -s reload`

---

## Phase 6 — 启动服务（watchdog + port cleanup）

### start_backend.cmd 模板

```bat
@echo off
setlocal EnableDelayedExpansion
set ROOT=%~dp0
set VENV_PY=%ROOT%backend-service\venv\Scripts\python.exe
set PORT=8080
set RESTART_DELAY=5

:loop
REM --- port cleanup ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORT% "') do (
    if not "%%a"=="0" (
        echo [%date% %time%] Port %PORT% occupied by PID %%a, killing...
        taskkill /PID %%a /F >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
)
echo [%date% %time%] Starting backend on http://localhost:%PORT%...
"%VENV_PY%" -m http.server %PORT%
set "exitcode=!errorlevel!"
echo [%date% %time%] Backend exited (code: !exitcode!). Restarting in %RESTART_DELAY%s...
timeout /t %RESTART_DELAY% /nobreak >nul
goto loop
```

### start_backend.sh 模板

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PY="$ROOT/backend-service/venv/bin/python"
PORT=8080
RESTART_DELAY=5

while true; do
  PORT_PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
  if [ -n "$PORT_PID" ]; then
    echo "[$(date)] Port $PORT occupied by PID $PORT_PID, killing..."
    kill -9 $PORT_PID 2>/dev/null || true
    sleep 1
  fi
  echo "[$(date)] Starting backend on http://localhost:$PORT..."
  "$VENV_PY" -m http.server $PORT
  echo "[$(date)] Backend exited. Restarting in ${RESTART_DELAY}s..."
  sleep "$RESTART_DELAY"
done
```

### start_frontend.cmd 模板

```bat
@echo off
setlocal EnableDelayedExpansion
set ROOT=%~dp0
set VENV_PY=%ROOT%backend-service\venv\Scripts\python.exe
set PORT=3000
set RESTART_DELAY=5

:loop
REM --- port cleanup ---
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORT% "') do (
    if not "%%a"=="0" (
        echo [%date% %time%] Port %PORT% occupied by PID %%a, killing...
        taskkill /PID %%a /F >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
)
echo [%date% %time%] Starting frontend on http://localhost:%PORT%...
"%VENV_PY%" -m http.server %PORT%
set "exitcode=!errorlevel!"
echo [%date% %time%] Frontend exited (code: !exitcode!). Restarting in %RESTART_DELAY%s...
timeout /t %RESTART_DELAY% /nobreak >nul
goto loop
```

### start_frontend.sh 模板

```bash
#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PY="$ROOT/backend-service/venv/bin/python"
PORT=3000
RESTART_DELAY=5

while true; do
  PORT_PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
  if [ -n "$PORT_PID" ]; then
    echo "[$(date)] Port $PORT occupied by PID $PORT_PID, killing..."
    kill -9 $PORT_PID 2>/dev/null || true
    sleep 1
  fi
  echo "[$(date)] Starting frontend on http://localhost:$PORT..."
  "$VENV_PY" -m http.server $PORT
  echo "[$(date)] Frontend exited. Restarting in ${RESTART_DELAY}s..."
  sleep "$RESTART_DELAY"
done
```

---

## Phase 7 — ngrok 公网暴露

### 启动 ngrok

```bat
start ngrok http %BACKEND_PORT%
```

### 获取 tunnel URL

```bat
curl localhost:4040/api/tunnels
```

### 前端 fetch 规范

所有 `fetch()` 必须带：

```javascript
fetch(`${API_BASE}/endpoint`, {
  method: 'GET',
  headers: {
    'ngrok-skip-browser-warning': 'true',
  },
})
```

---

## Phase 8 — 健康验证

### 四层 × 三路径验证

| 层级 | 验证内容 |
|------|---------|
| ngrok | tunnel alive, HTTP 200 |
| nginx | proxy alive, HTTP 200 |
| frontend | localhost / nginx / ngrok 均 200 |
| backend | localhost / nginx / ngrok 均 200 |

### 验证通过输出

```
=== Health Check ===
✅ ngrok: 正常
✅ nginx: 正常
--- project: demoProject ---
✅ frontend (ngrok):     正常
✅ frontend (nginx):     正常
✅ frontend (localhost):  正常
✅ backend (ngrok):      正常
✅ backend (nginx):      正常
✅ backend (localhost):   正常
✅ 所有链路验证通过！
Public URL: https://xxxx.ngrok-free.dev/
```

### 验证失败处理

列出挂掉的链路 + 修复建议，不自动尝试修复。

### Anti-Misdiagnosis Checklist

生成健康检查脚本时，必须包含以下防误诊机制：

| # | 机制 | 防止的问题 |
|---|------|----------|
| 1 | 重试循环（≥ 3 次） | GC暂停/瞬时超时误报 |
| 2 | Port timeout ≥ 5s | 慢响应误报 |
| 3 | HTTP timeout ≥ 8s | 后端冷启动误报 |
| 4 | 启动前 `is_port_in_use()` 检查 | 重复进程启动 |
| 5 | 启动前 `kill_port_process()` 清理僵尸进程 | 僵尸进程占端口导致新进程绑定失败 |
| 6 | 外部 URL 不触发自动重启 | 网络抖动触发误重启 |
| 7 | 区分 `ConnectionRefused`（进程死了）vs `timeout`（进程忙） | 重启正在工作的服务 |
| 8 | `127.0.0.1` 而非 `localhost` | DNS 解析增加探测延迟 |

---

## Critical Rules

| 规则 |
|------|
| `echo` 字符串必须用双引号包裹 |
| `REM` 而非 `::` 做注释（`chcp 65001` 下多字节字符会破坏解析） |
| Windows 脚本用 CRLF，macOS 用 LF |
| 多行文件写入用 `> ` + `>>`，不用 `(...) > file` |
| Required deps 缺失必须阻塞 + 重试循环 |
| 每条缺失信息必须包含 Impact 说明 |
| Optional deps 缺失警告后允许跳过 |
| `goto` 替代复杂 `if/else` 嵌套 |
| `ngrok-skip-browser-warning` 所有 fetch 必须带 |
| `127.0.0.1` 而非 `localhost`（DNS延迟） |
| venv 每个项目独立创建 |
| port cleanup 每次启动前执行 |
| watchdog loop 所有 start_* 脚本必须包含 |

---

## 双系统语法对照表

| 功能 | Windows | macOS |
|------|---------|-------|
| 变量检测 | `if defined VAR` | `if [ -n "$VAR" ]` |
| 文件存在 | `if exist "path"` | `if [ -f "path" ]` |
| 目录存在 | `if exist "path"` | `if [ -d "path" ]` |
| 循环 | `:label` + `goto` | `while true; do` + `done` |
| 端口占用检测 | `netstat -ano \| findstr` | `lsof -ti :PORT` |
| 杀进程 | `taskkill /F /PID` | `kill -9` |
| sleep | `timeout /t N` | `sleep N` |
| 函数定义 | `goto :EOF` 返回 | `return` |
