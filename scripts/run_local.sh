#!/usr/bin/env bash
# Run ArcReel locally (backend + frontend) without Docker, with one Ctrl+C to stop both.
#
# Both servers start from a minimal environment (env -i), so no ANTHROPIC_* / CLAUDE_CODE_*
# variables from the host shell or the Claude desktop app reach the embedded Agent. With no
# Anthropic credential configured in Settings, the Agent then uses the local Claude Code login.
# Configuration comes from the repository-root .env (AUTH_*, ARCREEL_DATA_DIR, CORS_ORIGINS, TZ).
# The backend applies database migrations on startup.
#
# Usage: scripts/run_local.sh [--setup] [--reload | --no-reload]
#   --setup      run `uv sync` and `pnpm install` before starting
#   --reload     restart the backend when a .py file under server/ or lib/ changes; for code editing.
#                A restart interrupts running Agent turns and waits for running generation tasks.
#   --no-reload  default: keep the backend running until Ctrl+C; use for normal and unattended runs
#
# uvicorn drops connections still open GRACEFUL_SHUTDOWN_SECONDS after a stop or reload begins. The
# browser's SSE streams never end on their own, so without this limit a stop or reload would wait for
# them forever; the frontend reconnects automatically.
#
# Compatible with macOS /bin/bash 3.2.

set -euo pipefail

API_PORT=1241
WEB_PORT=5173
GRACEFUL_SHUTDOWN_SECONDS=3
MIN_NODE_MAJOR=24
MIN_NODE_MINOR=12

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SETUP=false
RELOAD=false
for arg in "$@"; do
  case "$arg" in
    --setup) SETUP=true ;;
    --reload) RELOAD=true ;;
    --no-reload) RELOAD=false ;;
    -h|--help) sed -n '2,/^# Compatible with/p' "$0" | sed 's/^# \{0,1\}//'; exit 0 ;;
    *) echo "Unknown option: $arg (see --help)" >&2; exit 2 ;;
  esac
done

die() { echo "run_local: $*" >&2; exit 1; }

node_ok() {
  # $1 = path to a node binary
  local version major minor
  version="$("$1" --version 2>/dev/null)" || return 1
  version="${version#v}"
  major="${version%%.*}"
  minor="${version#*.}"; minor="${minor%%.*}"
  [ "$major" -gt "$MIN_NODE_MAJOR" ] || { [ "$major" -eq "$MIN_NODE_MAJOR" ] && [ "$minor" -ge "$MIN_NODE_MINOR" ]; }
}

find_node_bin() {
  local candidate
  if candidate="$(command -v node 2>/dev/null)" && node_ok "$candidate"; then
    dirname "$candidate"; return 0
  fi
  # Newest nvm-installed Node that satisfies the engines constraint.
  for candidate in $(ls -d "$HOME"/.nvm/versions/node/v*/bin/node 2>/dev/null | sort -V -r); do
    if node_ok "$candidate"; then dirname "$candidate"; return 0; fi
  done
  return 1
}

[ -f "$ROOT/.env" ] || die ".env not found in $ROOT (copy deploy/.env.example and fill AUTH_*, ARCREEL_DATA_DIR)"
UV_BIN="$(command -v uv)" || die "uv not found in PATH"
NODE_BIN="$(find_node_bin)" || die "Node >= $MIN_NODE_MAJOR.$MIN_NODE_MINOR not found (try: nvm install $MIN_NODE_MAJOR)"
[ -x "$NODE_BIN/pnpm" ] || command -v pnpm >/dev/null || die "pnpm not found"

for port in "$API_PORT" "$WEB_PORT"; do
  if pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null)" && [ -n "$pids" ]; then
    die "port $port already in use by PID(s) $(echo $pids) — stop it first (kill $(echo $pids))"
  fi
done

CLEAN_PATH="$NODE_BIN:$(dirname "$UV_BIN"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
clean() {
  env -i HOME="$HOME" USER="${USER:-$(id -un)}" LOGNAME="${USER:-$(id -un)}" \
    LANG="${LANG:-en_US.UTF-8}" TERM="${TERM:-xterm-256color}" PATH="$CLEAN_PATH" "$@"
}

# Non-fatal warnings for the subscription setup: an Anthropic credential saved in Settings takes
# precedence over the local Claude Code login and bills the API per request.
check_subscription_mode() {
  local data_dir db
  data_dir="$(grep -E '^ARCREEL_DATA_DIR=' "$ROOT/.env" | tail -1 | cut -d= -f2-)"
  data_dir="${data_dir%\"}"; data_dir="${data_dir#\"}"
  data_dir="${data_dir//\$HOME/$HOME}"; data_dir="${data_dir/#\~/$HOME}"
  db="$data_dir/arcreel.db"
  if [ -n "$data_dir" ] && [ -f "$db" ]; then
    # immutable=1 reads the file without creating -shm/-wal files next to it.
    if (cd "$ROOT" && clean uv run python -I -c '
import sqlite3, sys
c = sqlite3.connect("file:" + sys.argv[1] + "?mode=ro&immutable=1", uri=True)
n = c.execute("select count(*) from agent_anthropic_credentials where is_active = 1").fetchone()[0]
n += c.execute("select count(*) from system_setting where key = ? and value <> \"\"", ("anthropic_api_key",)).fetchone()[0]
sys.exit(0 if n else 1)
' "$db" 2>/dev/null); then
      echo "run_local: WARNING: an Anthropic API key is configured in Settings; the Agent will bill the API instead of using the Claude Code login." >&2
    fi
  fi
  if command -v claude >/dev/null 2>&1; then
    claude auth status 2>/dev/null | grep -q '"loggedIn": true' \
      || echo "run_local: WARNING: Claude Code is not logged in; run 'claude' and /login, or the Agent will fail to start." >&2
  else
    echo "run_local: WARNING: 'claude' CLI not found; cannot check the subscription login." >&2
  fi
}
check_subscription_mode

if $SETUP; then
  echo "run_local: uv sync"
  (cd "$ROOT" && clean uv sync)
  echo "run_local: pnpm install (frontend)"
  (cd "$ROOT/frontend" && clean pnpm install --frozen-lockfile)
fi

# Each server runs in its own process group so the whole tree (uv, uvicorn workers, vite) can be stopped.
set -m
API_PID=""
WEB_PID=""

stop_all() {
  trap - INT TERM EXIT
  echo
  echo "run_local: stopping..."
  for pid in "$WEB_PID" "$API_PID"; do
    [ -n "$pid" ] && kill -TERM -- "-$pid" 2>/dev/null || true
  done
  # Up to 10 s: uvicorn drains connections for GRACEFUL_SHUTDOWN_SECONDS, then runs the app's shutdown.
  for _ in $(seq 1 20); do
    alive=false
    for pid in "$WEB_PID" "$API_PID"; do
      [ -n "$pid" ] && kill -0 -- "-$pid" 2>/dev/null && alive=true
    done
    $alive || break
    sleep 0.5
  done
  for pid in "$WEB_PID" "$API_PID"; do
    [ -n "$pid" ] && kill -KILL -- "-$pid" 2>/dev/null || true
  done
  echo "run_local: stopped."
}
trap stop_all INT TERM EXIT

# The prefixer ignores INT/TERM so it survives the group-wide TERM in stop_all and keeps printing the
# servers' shutdown logs; it exits on EOF when the server closes its output (or on the final KILL).
prefix() { trap '' INT TERM; awk -v p="$1" '{ print p $0; fflush() }'; }

UVICORN_ARGS=(server.app:app --host 127.0.0.1 --port "$API_PORT" --timeout-graceful-shutdown "$GRACEFUL_SHUTDOWN_SECONDS")
if $RELOAD; then
  UVICORN_ARGS+=(--reload --reload-dir server --reload-dir lib)
fi
echo "run_local: backend auto-reload $($RELOAD && echo on || echo off)"

cd "$ROOT"
clean uv run --extra speech-review uvicorn "${UVICORN_ARGS[@]}" > >(prefix "[api] ") 2>&1 &
API_PID=$!
# Disowned jobs are still stopped by PID/process group, but bash no longer prints "Terminated" notices for them.
disown "$API_PID"

echo "run_local: waiting for backend on http://127.0.0.1:$API_PORT/health ..."
for _ in $(seq 1 120); do
  curl -sf -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
  kill -0 "$API_PID" 2>/dev/null || die "backend exited during startup (see [api] output above)"
  sleep 1
done
curl -sf -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 || die "backend did not become healthy in 120s"

cd "$ROOT/frontend"
clean pnpm dev --host 127.0.0.1 --port "$WEB_PORT" --strictPort > >(prefix "[web] ") 2>&1 &
WEB_PID=$!
disown "$WEB_PID"
cd "$ROOT"

echo "run_local: ArcReel is up — open http://127.0.0.1:$WEB_PORT (Ctrl+C stops both)"

# bash 3.2 has no `wait -n`: poll until either server exits.
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  sleep 1
done
echo "run_local: a server exited; shutting down the other."
