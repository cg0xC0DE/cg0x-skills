---
name: cg0x-dev-standards
description: >
  Defines development standards for Python web projects: tech stack, project structure,
  startup scripts, credential management, nginx/ngrok deployment, and health checks.
  Use when user starts a new web project, asks about project structure conventions,
  deployment setup, or needs init/start scripts.
  Triggers: "新建项目", "项目规范", "dev standards", "project setup", "部署", "deploy",
  "nginx", "ngrok", "健康检查", "health check".
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
| Frontend | Pure HTML/JS/CSS (no frameworks) |
| Backend | Python (3.10 or 3.11) |
| Server | ngrok → nginx → Python HTTP server |

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
- **nginx**: Separate location blocks for frontend and backend with rewrite routing

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

Each project keeps up to 4 `.cmd` scripts in its **root directory**. Not every project needs all four.

| Script | Purpose | When Needed |
|--------|---------|-------------|
| `init.cmd` | Environment & dependency init | Projects with venv, credentials, or system-level deps |
| `start_frontend.cmd` | Start frontend server | Always |
| `start_backend.cmd` | Start backend server | Always |
| `start_deps.cmd` | Start external dependencies | Only if project relies on external services |

#### `init.cmd` — Environment Init

Runs once (or after dependency changes). Typical steps:

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
- Detect Python via `py -3.10` launcher first, fallback to `python`, verify version `>= 3.10`
- Separate **required** (hard fail) vs **optional** (warn + prompt) dependencies
- Use `%VENV_PY% -m pip` instead of `pip.exe` to avoid stale launcher paths
- Write credentials to local files (never commit them)

#### `start_frontend.cmd` / `start_backend.cmd` — Service Start

Common boilerplate:

```cmd
@echo off
setlocal
set ROOT=%~dp0
pushd "%ROOT%"

set VENV_PY=%ROOT%<backend_dir>\venv\Scripts\python.exe
if not exist "%VENV_PY%" (
  echo venv not found. Please run init.cmd first.
  popd & exit /b 1
)

echo Starting <service> on http://localhost:<PORT> ...
REM Backend:  "%VENV_PY%" app.py --port <PORT>
REM Frontend: "%VENV_PY%" -m http.server <PORT>   (or: npx serve <dir> -l <PORT>)

popd
endlocal
```

Key patterns:
- Always check venv exists before starting
- Frontend can use either `python -m http.server` (via backend venv) or `npx serve`
- Backend installs its own pip deps at startup if lightweight (e.g. `pip install requests -q`)
- Hardcode port per project to avoid conflicts

#### `start_deps.cmd` — External Dependencies

For projects that depend on external services (e.g. ComfyUI, Ollama). Typical pattern is a **watchdog loop** that auto-restarts on crash:

```cmd
:loop
echo Starting <service> ...
call "<service_startup_script>"
echo Exited (code: %ERRORLEVEL%). Restarting in <N>s ...
timeout /t <N> /nobreak >nul
goto loop
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
    listen 8080;
    server_name localhost;

    # Frontend (static files)
    location /PROJECT_NAME/ {
        root /path/to/PROJECT_NAME;
        index index.html;
    }

    # Backend API proxy
    location /PROJECT_NAME/api/ {
        rewrite ^/PROJECT_NAME/api/(.*) /$1 break;
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
- Local: http://localhost:8080/PROJECT_NAME/
- Public: https://YOUR-NGROK-URL.ngrok-free.dev/PROJECT_NAME/

**G. Frontend API configuration:**
```javascript
// Use ngrok domain for backend API calls
const API_BASE = 'https://YOUR-NGROK-URL.ngrok-free.dev/PROJECT_NAME/api';
```

**H. Deployment Verification:**
```cmd
REM 1. Check nginx is running
curl -I http://localhost:8080/PROJECT_NAME/

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
| ngrok domain | `https://NGROK_URL/PROJECT_NAME/` |
| nginx proxy | `http://localhost:8080/PROJECT_NAME/` |
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
- ✅ Start backend first, then update nginx
- ✅ nginx proxy_pass to 127.0.0.1:BACKEND_PORT
- ✅ ngrok tunnel (8080 → public) remains active
- ✅ Frontend calls backend via ngrok domain
- ✅ All routes must return 200 for delivery
