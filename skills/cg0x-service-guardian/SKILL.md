---
name: cg0x-service-guardian
description: >
  Generates cross-platform (Windows + macOS) Python healthcheck scripts for local service
  fleets with retry-based diagnosis, port-in-use guard against duplicate launches, and
  silent-on-success output. Use when user needs a daemon/watchdog script to monitor and
  auto-recover local services, or when existing healthcheck scripts cause false positives
  and duplicate processes.
  Triggers: "健康检查", "守护脚本", "服务监控", "healthcheck", "watchdog", "service guardian",
  "自检脚本", "服务挂了", "重复启动", "duplicate process".
---

# Service Guardian — Local Service Healthcheck Generator

## Usage

Typical prompts that should trigger this skill:

```
帮我写一个守护脚本，定时检查本地服务是否正常
```

```
Generate a healthcheck script for my local services
```

```
我的自检脚本老是误报服务挂了，帮我修一下
```

## Purpose

Many local dev environments run multiple services (frontend, backend, reverse proxy, tunnel, etc.) that need periodic liveness checks. A naive healthcheck — single attempt, short timeout, blind restart — frequently **misdiagnoses** transient slowness as downtime, spawning duplicate processes.

This skill produces a **robust Python healthcheck script** that:

1. Retries before declaring failure
2. Verifies the port is truly unoccupied before launching a new process
3. Stays silent when everything is healthy (suitable for cron / Task Scheduler)
4. Provides clear diagnostics when something is actually wrong

## Scope & Applicability

Target environment:

| Aspect | Expectation |
|--------|-------------|
| OS | Windows 10/11 and macOS (both fully supported) |
| Language | Python 3.10+ (stdlib only, no pip dependencies) |
| Services | Any combination of TCP-port and HTTP-endpoint services |
| Scheduler | Windows Task Scheduler / macOS launchd / cron / manual invocation |

> **Cross-platform rule**: The script is pure Python stdlib and runs on both platforms. The only OS-specific parts are `is_port_in_use()` (netstat vs lsof) and `start_service()` (process creation flags). The script **must auto-detect the OS** via `sys.platform` and branch accordingly.

---

## Script Architecture

The generated script has **four layers**, executed top-to-bottom:

```
┌─────────────────────────────────┐
│  1. Configuration Tables        │  ← SERVICES, START_SCRIPTS, tunables
├─────────────────────────────────┤
│  2. Probe Functions             │  ← check_port, check_http, check_url
├─────────────────────────────────┤
│  3. Guard Functions             │  ← is_port_in_use, start_service
├─────────────────────────────────┤
│  4. Main Loop                   │  ← retry → diagnose → guard → fix → verify
└─────────────────────────────────┘
```

---

## Layer 1 — Configuration Tables

### Global Tunables

Define these at the top of the script so they are easy to adjust:

| Constant | Purpose | Recommended Default |
|----------|---------|---------------------|
| `RETRY_COUNT` | Times to retry a failed check before declaring failure | 3 |
| `RETRY_INTERVAL` | Seconds between retries | 2 |
| `PORT_TIMEOUT` | Seconds for TCP connect timeout | 5 |
| `HTTP_TIMEOUT` | Seconds for HTTP request timeout | 8 |

> **Why these defaults matter**: The most common misdiagnosis cause is a timeout that is too short (e.g., 2 seconds) combined with zero retries. A service under momentary GC pressure or disk I/O will fail a 2-second single-shot check but respond fine 3 seconds later.

### SERVICES Dictionary

Each entry describes **one service** to monitor:

```python
SERVICES = {
    'service_key': {
        'port': 8080,              # TCP port (required for port-type; optional for http-type)
        'type': 'port' | 'http',   # Probe strategy
        'name': 'Human Name',      # Display name for logs
        'host': '127.0.0.1',       # Default: 127.0.0.1 (for http type)
        'path': '/health',         # HTTP path to probe (for http type)
        'url': 'https://...',      # Full URL for external endpoints (for http type)
        'auto_restart': True,      # Set False to skip auto-restart (e.g., external tunnels)
    },
}
```

#### Design rules

- **Every service with a port** must declare `port`, even if `type` is `http`. The port is used by the guard layer to prevent duplicate launches.
- **External URLs** (ngrok, Cloudflare Tunnel, etc.) should set `auto_restart: False`. Network jitter and rate-limiting make external URL checks unreliable for triggering restarts.
- **Use `127.0.0.1`** instead of `localhost` to avoid DNS resolution adding latency to probes.

### START_SCRIPTS Dictionary

Each entry describes **how to launch** a service:

```python
START_SCRIPTS = {
    'service_key': {
        'cmd': ['python', '-m', 'http.server', '8080'],   # Command list
        'cwd': 'C:\\path\\to\\workdir',                    # Optional working directory
    },
}
```

#### Design rules

- Use a `dict` with `cmd` and optional `cwd`, not a bare list. This avoids a sprawling `if/elif` chain in the start function.
- For PowerShell-wrapped commands, concatenate `cd` and the actual command into a single `-Command` string rather than passing them as separate list items (which breaks argument parsing).

---

## Layer 2 — Probe Functions

### `check_port(port, timeout)`

TCP connect probe. Returns `bool`.

**Requirements:**
- Use `socket.AF_INET` + `socket.SOCK_STREAM`
- Connect to `127.0.0.1` (not `localhost`)
- Wrap in `try/except OSError` to handle edge cases (e.g., network stack not ready)
- Always close the socket in all code paths

### `check_http(host, port, path, timeout)`

Local HTTP GET probe. Returns `(ok: bool, detail: str)`.

**Requirements:**
- Use `http.client.HTTPConnection` (not `urllib`) — it gives explicit control over host:port
- **Distinguish error types** in except blocks:

| Exception | Meaning | Should Restart? |
|-----------|---------|-----------------|
| `ConnectionRefusedError` | Process not listening | Yes |
| `socket.timeout` | Process is slow / overloaded | Usually no |
| Other `Exception` | Unknown | Maybe |

> This distinction is critical. The old script used bare `except:` and treated all failures identically — a timeout on a busy service would trigger a redundant restart.

### `check_url(url, timeout)`

External URL probe (for tunnels, CDNs, etc.). Returns `(ok: bool, detail)`.

**Requirements:**
- Use `urllib.request` with a `User-Agent` header (some services block default Python UA)
- This is inherently unreliable for **restart decisions** — only use for reporting

### `check_service_with_retry(key, cfg, retries, interval)`

Wrapper that calls the appropriate probe up to `retries` times.

**Requirements:**
- Return success on **first passing attempt** (short-circuit)
- Sleep `interval` seconds between attempts
- Return the detail from the **last failed attempt** for diagnostics

---

## Layer 3 — Guard Functions

### `is_port_in_use(port)`

Determines whether a process is already bound to the port. This is the **key anti-duplication mechanism**.

**Strategy (two-tier, platform-aware):**

**Windows:**
1. **Primary: `netstat`** — Parse `netstat -ano -p TCP` output; look for the port in `LISTENING` state.
2. **Fallback: bind test** — Attempt `socket.bind(('127.0.0.1', port))`. If it raises `OSError`, the port is occupied.

**macOS:**
1. **Primary: `lsof`** — Run `lsof -iTCP:<port> -sTCP:LISTEN -t` which returns the PID if the port is in use (exit code 0) or nothing (exit code 1).
2. **Fallback: bind test** — Same as Windows.

**Reference implementation:**
```python
import sys, subprocess, socket

def is_port_in_use(port):
    try:
        if sys.platform == 'win32':
            out = subprocess.check_output(
                ['netstat', '-ano', '-p', 'TCP'],
                stderr=subprocess.DEVNULL, text=True, timeout=10)
            for line in out.splitlines():
                if f':{port} ' in line and 'LISTENING' in line:
                    return True
        else:  # macOS / Linux
            result = subprocess.run(
                ['lsof', '-iTCP:' + str(port), '-sTCP:LISTEN', '-t'],
                capture_output=True, text=True, timeout=10)
            if result.returncode == 0 and result.stdout.strip():
                return True
    except Exception:
        pass
    # Fallback: bind test (cross-platform)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(('127.0.0.1', port))
        s.close()
        return False
    except OSError:
        return True
```

> **Why not just use `check_port`?** Because `check_port` does a TCP *connect*. A service might be bound to a port but temporarily not accepting connections (e.g., during startup or GC). `netstat`/`lsof`/bind detects the OS-level port reservation regardless of application-layer responsiveness.

### `kill_port_process(port)`

Finds and terminates **all** processes (including zombie / orphan processes) that occupy a given port. This is the **critical cleanup step** before restarting a service — without it, the new process will fail to bind and the port stays deadlocked by a defunct process.

**Strategy (platform-aware):**

**Windows:**
1. Parse `netstat -ano -p TCP` to find all PIDs listening on the target port.
2. For each PID, call `taskkill /F /PID <pid>` to force-terminate.
3. After killing, sleep briefly (0.5s) and verify with `is_port_in_use()` to confirm the port is freed.

**macOS / Linux:**
1. Run `lsof -iTCP:<port> -sTCP:LISTEN -t` to get all PIDs.
2. For each PID, send `SIGTERM` first (`os.kill(pid, signal.SIGTERM)`), wait up to 3 seconds.
3. If the process is still alive, escalate to `SIGKILL` (`os.kill(pid, signal.SIGKILL)`).
4. After killing, verify with `is_port_in_use()`.

**Reference implementation:**
```python
import sys, subprocess, os, signal, time

def kill_port_process(port):
    """Kill all processes occupying the given port. Returns True if port is freed."""
    pids = set()
    try:
        if sys.platform == 'win32':
            out = subprocess.check_output(
                ['netstat', '-ano', '-p', 'TCP'],
                stderr=subprocess.DEVNULL, text=True, timeout=10)
            for line in out.splitlines():
                if f':{port} ' in line and 'LISTENING' in line:
                    parts = line.split()
                    if parts:
                        try:
                            pids.add(int(parts[-1]))
                        except ValueError:
                            pass
        else:  # macOS / Linux
            result = subprocess.run(
                ['lsof', '-iTCP:' + str(port), '-sTCP:LISTEN', '-t'],
                capture_output=True, text=True, timeout=10)
            if result.returncode == 0:
                for line in result.stdout.strip().splitlines():
                    try:
                        pids.add(int(line.strip()))
                    except ValueError:
                        pass
    except Exception:
        pass

    if not pids:
        return True  # No process found; port should be free

    for pid in pids:
        try:
            if sys.platform == 'win32':
                subprocess.run(
                    ['taskkill', '/F', '/PID', str(pid)],
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
            else:
                os.kill(pid, signal.SIGTERM)
                # Wait up to 3 seconds for graceful shutdown
                for _ in range(6):
                    time.sleep(0.5)
                    try:
                        os.kill(pid, 0)  # Check if still alive
                    except OSError:
                        break
                else:
                    # Still alive — escalate to SIGKILL
                    os.kill(pid, signal.SIGKILL)
        except (OSError, subprocess.SubprocessError):
            pass  # Process may have already exited

    time.sleep(0.5)  # Brief settle time for OS to release the port
    return not is_port_in_use(port)
```

**Design rules:**
- **Always force-kill on Windows** (`taskkill /F`). Windows has no graceful-signal equivalent for arbitrary processes.
- **Graceful-then-force on macOS/Linux** (`SIGTERM` → wait → `SIGKILL`). This gives the process a chance to clean up (flush buffers, release locks) before escalating.
- **Collect all PIDs first**, then kill. A single port can be held by multiple processes (e.g., parent + forked workers).
- **Verify after killing** — the port might still be in `TIME_WAIT` state briefly. The verification confirms the port is truly freed before proceeding.

### `start_service(key)`

Launches a service after ensuring the port is free. If a dead/zombie process occupies the port, it is killed first.

**Flow:**

```
1. Look up port from SERVICES[key]
2. if port and is_port_in_use(port):
       print "Port occupied, attempting to kill existing process..."
       freed = kill_port_process(port)
       if not freed:
           print FAIL message ("Could not free port") → return False
       print "Port freed successfully"
3. Popen(cmd, cwd=cwd, shell=True, creationflags=DETACHED_PROCESS,
         stdout=DEVNULL, stderr=DEVNULL)
4. return True
```

**Requirements:**
- Always redirect stdout/stderr to `DEVNULL` for the child process to avoid zombie pipe handles
- **Auto-detect OS** for process creation:

```python
import sys, subprocess

def start_service(key):
    script = START_SCRIPTS[key]
    cmd = script['cmd']
    cwd = script.get('cwd')
    port = SERVICES[key].get('port')

    # Guard: kill zombie/orphan process occupying the port, then verify
    if port and is_port_in_use(port):
        print(f"  Port {port} is occupied, killing existing process...")
        freed = kill_port_process(port)
        if not freed:
            print(f"  FAIL: Could not free port {port}")
            return False
        print(f"  Port {port} freed successfully")

    kwargs = dict(cwd=cwd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    if sys.platform == 'win32':
        kwargs['creationflags'] = subprocess.DETACHED_PROCESS
    else:  # macOS / Linux
        kwargs['start_new_session'] = True

    subprocess.Popen(cmd, **kwargs)
    return True
```

---

## Layer 4 — Main Loop

### Flow

```
1. For each service in SERVICES:
       check_service_with_retry(...)
       if OK → silent (no output)
       if FAIL → append to issues list, print failure detail

2. If no issues → exit 0 (completely silent)

3. For each issue:
       if auto_restart is False → print SKIP, continue
       start_service(key)  ← guard will kill zombie/orphan processes then launch
       sleep 3 seconds (give the new process time to bind)

4. Re-verify all originally-failed services (with retry)

5. Print summary:
       all recovered → exit 0
       still failing → list them, exit 1
```

### Exit codes

| Code | Meaning |
|------|---------|
| 0 | All services healthy (or all recovered after restart) |
| 1 | At least one service still failing after attempted recovery |

> Exit codes matter when the script is called from Task Scheduler or a wrapper — code 1 can trigger alerts.

---

## Anti-Misdiagnosis Checklist

Before generating the script, verify these safeguards are all present:

| # | Safeguard | What It Prevents |
|---|-----------|------------------|
| 1 | Retry loop (≥ 3 attempts) | Transient timeout / GC pause false positives |
| 2 | Port timeout ≥ 5 seconds | Slow-response false positives |
| 3 | HTTP timeout ≥ 8 seconds | Backend cold-start false positives |
| 4 | `is_port_in_use()` before `Popen` | Duplicate process launches |
| 4a | `kill_port_process()` before `Popen` when port is occupied | Zombie/orphan processes blocking restart |
| 5 | `auto_restart: False` for external URLs | Network-jitter-triggered restarts |
| 6 | Distinguish `ConnectionRefusedError` vs `timeout` | Restarting busy-but-alive services |
| 7 | `127.0.0.1` instead of `localhost` | DNS resolution adding probe latency |
| 8 | `stdout/stderr=DEVNULL` on child | Zombie pipe handles keeping processes alive |

---

## Pre-Generation Checklist

Before writing the script, inspect the target environment:

1. **Which services need monitoring?** — List each with its port, type (TCP / HTTP), and health endpoint path.
2. **Which services have start scripts?** — Collect the command line, working directory, and any environment variables.
3. **Are there external endpoints (ngrok, tunnels)?** — Mark them `auto_restart: False`.
4. **What OS?** — Script auto-detects via `sys.platform`. Windows uses `DETACHED_PROCESS`; macOS/Linux uses `start_new_session=True`.
5. **How will the script be scheduled?** — Task Scheduler interval, cron expression, or manual.

Only after gathering this information should you generate the script.

---

## Common Mistakes to Avoid

| Mistake | Correct Behavior |
|---------|-----------------|
| Single-shot check with no retry | Retry at least 3 times with 2-second intervals |
| Timeout < 3 seconds | Use ≥ 5s for port, ≥ 8s for HTTP |
| Bare `except:` catching all errors identically | Distinguish `ConnectionRefusedError` (dead) from `timeout` (slow) |
| Starting a new process without checking if port is occupied | Always call `is_port_in_use(port)` before `Popen` |
| Skipping restart because port is occupied by a zombie/orphan process | Call `kill_port_process(port)` to terminate the defunct process before launching a new one |
| Using `localhost` in probes | Use `127.0.0.1` to skip DNS resolution |
| Auto-restarting external tunnel services on check failure | Mark external URLs with `auto_restart: False` |
| Printing output when all services are healthy | Stay silent on success (exit 0 with no stdout) |
| Using a flat list for start commands with per-service `if/elif` branches | Use a structured dict (`{cmd, cwd}`) per service |
| Leaving child process stdout/stderr connected to parent | Redirect to `DEVNULL` to prevent zombie handles |
| Hardcoding service list in multiple places | Single `SERVICES` dict is the source of truth for both checks and restarts |
| Hardcoding `netstat` or `DETACHED_PROCESS` without OS check | Use `sys.platform` to branch: `netstat`/`DETACHED_PROCESS` on Windows, `lsof`/`start_new_session` on macOS |
| Using `lsof` without `-t` flag on macOS | Always use `-t` (terse) to get just PIDs, easier to parse |

---

## Appendix: Client-Side Load Balancer Probing (Browser/Mobile)

When deploying backend services behind **ngrok** (or similar tunnels) and using a **client-side load balancer** in the frontend to pick the healthiest endpoint, special care must be taken with **CORS (Cross-Origin Resource Sharing)**.

### The Problem

On **mobile browsers** (iOS Safari, Chrome Android), CORS is strictly enforced:

1. **CORS mode fetch** (`mode: "cors"`) fails if the server doesn't return `Access-Control-Allow-Origin` header
2. **no-cors fallback** (`mode: "no-cors"`) returns an **opaque response** — the status code (200 vs 502) is hidden from JavaScript
3. A naive load balancer may mark dead endpoints as "healthy" because `fetch()` didn't throw, even though ngrok returned a 502 error page

### Backend Requirements

**Every ngrok-exposed backend MUST include CORS middleware** that:

```python
# FastAPI example
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allow any origin (ngrok public URLs)
    allow_credentials=False,      # Must be False when origins=["*"]
    allow_methods=["*"],          # Allow all HTTP methods
    allow_headers=["*"],          # Must include custom headers like "ngrok-skip-browser-warning"
)
```

**Critical**: The `allow_headers=["*"]` is required because the load balancer sends `ngrok-skip-browser-warning: 1` to bypass ngrok's interstitial page.

### Client-Side Probing Strategy

```javascript
async function probeEndpoint(endpoint) {
  const start = performance.now();
  
  // Strategy 1: CORS mode — can read status and body
  try {
    const res = await fetch(endpoint, {
      method: "GET",
      mode: "cors",
      signal: AbortSignal.timeout(5000),
      headers: { "ngrok-skip-browser-warning": "1" },
    });
    
    if (!res.ok) return { endpoint, healthy: false };
    
    const text = await res.text();
    const isNgrokError = text.includes("ngrok") && 
                        (text.includes("ERR_NGROK") || text.includes("Tunnel not found"));
    
    return { 
      endpoint, 
      healthy: !isNgrokError, 
      latency: isNgrokError ? Infinity : performance.now() - start 
    };
  } catch {
    // CORS blocked or network error — try no-cors
  }
  
  // Strategy 2: no-cors mode — opaque response, cannot verify health
  try {
    await fetch(endpoint, {
      method: "HEAD",
      mode: "no-cors",
      signal: AbortSignal.timeout(5000),
    });
    // Server responded, but we can't distinguish 200 OK from 502 Error
    // MUST mark as unhealthy to avoid false positives
    return { endpoint, healthy: false };
  } catch {
    return { endpoint, healthy: false };
  }
}
```

### Key Takeaways

| Scenario | Mobile Detection | Desktop Detection |
|----------|---------------|-------------------|
| Backend alive + CORS headers | ✅ Works | ✅ Works |
| Backend alive, no CORS | ❌ Shows offline (safe) | ⚠️ May work (browser-dependent) |
| Backend dead (502) + no CORS | ❌ Shows offline (correct) | ⚠️ May show online (false positive) |
| Backend dead (502) + CORS | ❌ Shows offline (correct) | ❌ Shows offline (correct) |

**Bottom line**: Always add CORS middleware to ngrok-exposed backends. Without it, mobile users will see services as offline even when they're running.
