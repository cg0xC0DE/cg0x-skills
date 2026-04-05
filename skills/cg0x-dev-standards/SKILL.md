---
name: cg0x-dev-standards
description: >
  Defines cross-platform (Windows + macOS) development standards for Python web projects:
  tech stack, project structure, watchdog startup scripts, credential management,
  nginx/ngrok deployment, and health checks.
  Use when user starts a new web project, asks about project structure conventions,
  deployment setup, or needs init/start scripts.
  Triggers: "新建项目", "项目规范", "dev standards", "project setup", "部署", "deploy",
  "nginx", "ngrok", "健康检查", "health check", "启动脚本", "watchdog", "守护".
---

# Development Standards

## Usage

Typical prompts that should trigger this skill:

```
帮我新建一个 Web 项目，按照标准规范来
```

```
Set up a new Python + HTML project following dev standards
```

```
帮我配置 nginx 和 ngrok 部署
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| OS | Windows 10/11 or macOS (both supported) |
| Frontend | Pure HTML/JS/CSS (no frameworks) |
| Backend | Python (3.10 or 3.11) |
| Server | ngrok → nginx → Python HTTP server |
| Scripts | `.cmd` (Windows) / `.sh` (macOS) — all service scripts use watchdog loops |

## Data Storage

- Create `data/` folder in backend directory for data storage
- Use filesystem instead of database/cache
- Formats: JSON/CSV/TXT, etc.

## Backend Component Structure

Each backend **module/component** maintains its own config and credentials files:

| File | Purpose | Git |
|------|---------|-----|
| `config.py` | System-level settings: thread counts, constants, prompt templates, literals | ✅ Committed |
| `credentials.py` | Plaintext secrets: API tokens, CLI tokens, connection strings, etc. | ❌ Gitignored |
| `example_credentials.py` | Same structure as `credentials.py` but with placeholder values | ✅ Committed |

`credentials.py` is per-component because different modules talk to different services:
- LLM module → model provider API key
- Git module → Git token
- Storage module → Azure/AWS connection string
- Scraper module → Apify token

`example_credentials.py` mirrors the real file exactly, with dummy values. It serves as an open-source placeholder so new contributors know what to fill in:

```python
# example_credentials.py
class LLMCredentials:
    API_KEY: str = "sk-your-api-key-here"
    ORG_ID: str = "org-placeholder"
```

## Network Architecture

- **Frontend → Backend**: Use ngrok domain (not localhost) for API calls
- **nginx**: Separate location blocks — `/<project>/` for frontend, `/<project>-service/` for backend API

## Standard Workflow

### 1. Project Setup

- Frontend folder: short name, e.g. `link2asr`, `civitaidl`
- Backend folder: frontend name + `-service`, e.g. `link2asr-service`
- Create a `.gitignore` in project root (template below)

**Standard `.gitignore`:**
```gitignore
# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
env/
.venv/

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Credentials (never commit secrets)
credential.py
credentials.py
```

```cmd
@echo off
REM Create project directory
mkdir %USERPROFILE%\Project\PROJECT_NAME

REM Create venv (Python 3.11)
python -m venv venv

REM Activate venv
call venv\Scripts\activate.bat

REM Install dependencies
pip install -r requirements.txt
```

### 2. Project Startup Scripts

Each project keeps up to 4 scripts in its **root directory**, with platform-specific extensions. Not every project needs all four.

| Script (Windows / macOS) | Purpose | When Needed |
|--------------------------|---------|-------------|
| `init.cmd` / `init.sh` | Environment & dependency init | Projects with venv, credentials, or system-level deps |
| `start_frontend.cmd` / `start_frontend.sh` | Start frontend server (watchdog) | Always |
| `start_backend.cmd` / `start_backend.sh` | Start backend server (watchdog) | Always |
| `start_deps.cmd` / `start_deps.sh` | Start external dependencies (watchdog) | Only if project relies on external services |

> **Rule: Every `start_*.cmd` / `start_*.sh` MUST use a watchdog loop.** If the service process exits (crash, OOM, unhandled exception), the script waits a few seconds and restarts it automatically. This eliminates the need for external process managers and makes each script self-healing.

#### `init.cmd` / `init.sh` — Environment Init

Runs once (or after dependency changes). **No watchdog needed** — this is interactive.

Typical steps:

```
[0] Preflight checks
    - Required: Python 3.10+  → fail if missing
    - Optional: ffmpeg, node, ngrok, CUDA, etc. → warn if missing, prompt to continue
[1] Create venv (if not exist)
[2] pip install -r requirements.txt
[3] Configure credentials interactively (API keys, connection strings, etc.)
[4] Optionally start frontend + backend
```

Key patterns:
- **Windows**: Detect Python via `py -3.10` launcher first, fallback to `python`, verify version `>= 3.10`. Use `%VENV_PY% -m pip` instead of `pip.exe`.
- **macOS**: Detect via `python3.10` or `python3`, verify version. Use `$VENV_PY -m pip`.
- Separate **required** (hard fail) vs **optional** (warn + prompt) dependencies
- Write credentials to local files (never commit them)

#### `start_frontend.cmd` / `start_backend.cmd` — Service Start (Windows)

**All service scripts MUST include a watchdog loop.** Template:

```cmd
@echo off
setlocal EnableDelayedExpansion
set ROOT=%~dp0
pushd "%ROOT%"

set VENV_PY=%ROOT%<backend_dir>\venv\Scripts\python.exe
if not exist "%VENV_PY%" (
  echo venv not found. Please run init.cmd first.
  popd & exit /b 1
)

set RESTART_DELAY=5
set PORT=<PORT>

:loop
:: Port cleanup — kill any existing process on the port before starting
for /f "tokens=5" %%a in ('netstat -ano ^| findstr "LISTENING" ^| findstr ":%PORT% "') do (
    if not "%%a"=="0" (
        echo [%date% %time%] Port %PORT% occupied by PID %%a, killing ...
        taskkill /PID %%a /F >nul 2>&1
        timeout /t 1 /nobreak >nul
    )
)
echo [%date% %time%] Starting <service> on http://localhost:%PORT% ...
REM Backend:  "%VENV_PY%" app.py --port %PORT%
REM Frontend: "%VENV_PY%" -m http.server %PORT%   (or: npx serve <dir> -l %PORT%)
set "exitcode=!errorlevel!"

echo [%date% %time%] <service> exited (code: !exitcode!). Restarting in %RESTART_DELAY%s ...
timeout /t %RESTART_DELAY% /nobreak >nul
goto loop
```

#### `start_frontend.sh` / `start_backend.sh` — Service Start (macOS)

```bash
#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
VENV_PY="$ROOT/<backend_dir>/venv/bin/python"

if [ ! -f "$VENV_PY" ]; then
  echo "venv not found. Please run init.sh first."
  exit 1
fi

RESTART_DELAY=5
PORT=<PORT>

while true; do
  # Port cleanup — kill any existing process on the port before starting
  PORT_PID=$(lsof -ti :"$PORT" 2>/dev/null || true)
  if [ -n "$PORT_PID" ]; then
    echo "[$(date)] Port $PORT occupied by PID $PORT_PID, killing ..."
    kill -9 $PORT_PID 2>/dev/null || true
    sleep 1
  fi
  echo "[$(date)] Starting <service> on http://localhost:$PORT ..."
  # Backend:  "$VENV_PY" app.py --port $PORT
  # Frontend: "$VENV_PY" -m http.server $PORT
  exitcode=$?
  echo "[$(date)] <service> exited (code: $exitcode). Restarting in ${RESTART_DELAY}s ..."
  sleep "$RESTART_DELAY"
done
```

> On macOS, remember to `chmod +x start_*.sh` after creation.

Key patterns (both platforms):
- Always check venv exists before entering the loop
- **Port cleanup before every start**: Use `netstat` + `taskkill` (Windows) or `lsof` + `kill` (macOS) to kill any existing process on the port. This ensures the script can be re-run without "port already in use" errors
- Frontend can use either `python -m http.server` or `npx serve`
- Backend installs its own pip deps at startup if lightweight (e.g. `pip install requests -q`)
- Hardcode port per project to avoid conflicts
- Log timestamp on every start/restart for debugging
- `RESTART_DELAY` is configurable; default 5 seconds

#### `start_deps.cmd` / `start_deps.sh` — External Dependencies

Same watchdog pattern as above, for external services (e.g. ComfyUI, Ollama):

**Windows:**
```cmd
:loop
echo [%date% %time%] Starting <service> ...
call "<service_startup_script>"
echo [%date% %time%] Exited (code: %ERRORLEVEL%). Restarting in <N>s ...
timeout /t <N> /nobreak >nul
goto loop
```

**macOS:**
```bash
while true; do
  echo "[$(date)] Starting <service> ..."
  <service_command>
  echo "[$(date)] Exited (code: $?). Restarting in <N>s ..."
  sleep <N>
done
```

### 3. Development & Testing

```cmd
@echo off
REM Always use venv
cd /d %USERPROFILE%\Project\PROJECT_NAME
call venv\Scripts\activate.bat

REM Run development server (debug mode)
python -m http.server PORT
REM Use backend venv to start frontend too, to avoid missing Python errors from system default
REM OR for Flask/FastAPI:
REM python app.py
```

### 4. Deployment Steps

**A. Start Backend Server:**
```cmd
cd /d %USERPROFILE%\Project\PROJECT_NAME
call venv\Scripts\activate.bat
python -m http.server BACKEND_PORT
```

**B. Update nginx Config:**
Edit nginx.conf to add location blocks.

**C. Add location blocks:**
```nginx
server {
    listen 80;
    server_name localhost;

    # Frontend (static files via proxy to Python http.server)
    location /PROJECT_NAME/ {
        rewrite ^/PROJECT_NAME/(.*)$ /$1 break;
        proxy_pass http://localhost:FRONTEND_PORT/;
    }

    # Backend API proxy
    location /PROJECT_NAME-service/ {
        rewrite ^/PROJECT_NAME-service/(.*) /$1 break;
        proxy_pass http://127.0.0.1:BACKEND_PORT/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

**D. Reload nginx:**
```cmd
nginx -s reload
```

**E. Verify ngrok tunnel:**
```cmd
ngrok http 8080
curl localhost:4040/api/tunnels
```

**F. Access URLs:**
- Frontend (local): http://localhost/PROJECT_NAME/
- Frontend (public): https://YOUR-NGROK-URL.ngrok-free.dev/PROJECT_NAME/
- Backend API (local): http://localhost/PROJECT_NAME-service/
- Backend API (public): https://YOUR-NGROK-URL.ngrok-free.dev/PROJECT_NAME-service/

**G. Frontend API configuration:**
```javascript
// Use ngrok domain for backend API calls
// Suffix follows nginx location: /<project>-service/
const API_BASE = 'https://YOUR-NGROK-URL.ngrok-free.dev/PROJECT_NAME-service';

// IMPORTANT: Every fetch() call MUST include the ngrok-skip-browser-warning header
// to bypass ngrok's free-tier interstitial page. Without it, API requests return HTML
// instead of JSON and the frontend shows "网络错误".
fetch(`${API_BASE}/endpoint`, {
  method: 'GET',   // or 'POST'
  headers: {
    'ngrok-skip-browser-warning': 'true',
    // ... other headers
  },
});
```

**H. Deployment Verification:**
```cmd
REM 1. Check nginx is running
curl -I http://localhost/PROJECT_NAME/

REM 2. Verify all routes return 200
REM    - Frontend page
REM    - Backend API endpoints
REM    - All configured location paths
REM    If any route returns non-200, deployment fails
```

**I. Health Check Script:**
Run `node healthcheck.js` to verify all services. Checks **4 parts**:

| Part | Scope | What it Checks |
|------|-------|----------------|
| **1. ngrok** | Global (device-wide) | Tunnel is alive, HTTP 200 |
| **2. nginx** | Global (device-wide) | Proxy is running, HTTP 200 |
| **3. Project Frontend** | Per-project, 3 paths | ngrok domain / nginx / localhost |
| **4. Project Backend** | Per-project, 3 paths | ngrok domain / nginx / localhost |

For each project's frontend and backend, validate through all 3 access paths:

| Access Path | Example URL |
|-------------|-------------|
| ngrok domain | `https://NGROK_URL/PROJECT_NAME/` (frontend) / `https://NGROK_URL/PROJECT_NAME-service/` (backend) |
| nginx proxy | `http://localhost/PROJECT_NAME/` (frontend) / `http://localhost/PROJECT_NAME-service/` (backend) |
| localhost direct | `http://localhost:PORT/` |

**Validation Criteria:**
- HTTP 200 status code
- Content keywords match (e.g., frontend returns "ProjectName", backend returns `{"status":"ok"}`)
- Port connectivity check

**Auto-Recovery Sequence:**
1. ngrok tunnel
2. nginx (proxy layer)
3. Project backend service
4. Project frontend service

**Example Output:**
```
=== Health Check ===
✅ ngrok: 正常
✅ nginx: 正常
--- project: demoProject ---
✅ frontend (ngrok):    正常
✅ frontend (nginx):    正常
✅ frontend (localhost): 正常
✅ backend (ngrok):     正常
✅ backend (nginx):     正常
✅ backend (localhost):  正常
✅ 所有链路验证通过！
```


## Key Rules

- ✅ Each Python project gets its own venv (3.10 or 3.11)
- ✅ Always use venv for pip, python, debugging
- ✅ **Every `start_*` script MUST have a watchdog loop** — no fire-and-forget
- ✅ **Every `start_*` script MUST port-cleanup before starting** — kill existing occupant so re-run never fails
- ✅ Provide both `.cmd` (Windows) and `.sh` (macOS) versions of all scripts
- ✅ Start backend first, then update nginx
- ✅ nginx proxy_pass to 127.0.0.1:BACKEND_PORT
- ✅ ngrok tunnel (8080 → public) remains active
- ✅ Frontend calls backend via ngrok domain
- ✅ **Every frontend `fetch()` call MUST include `'ngrok-skip-browser-warning': 'true'` header** — ngrok free-tier returns an interstitial HTML page without it, causing JSON parse failures
- ✅ All routes must return 200 for delivery
