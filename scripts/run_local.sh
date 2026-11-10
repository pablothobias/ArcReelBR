#!/usr/bin/env bash
# Run ArcReel locally (backend + frontend) without Docker, with one Ctrl+C to stop both.
#
# Each server runs in its own session without a terminal and with no terminal input, so nothing it starts
# can freeze it; the launcher still warns if a server is stopped, and Ctrl+C or closing the terminal stops both.
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

# PIDs in the given process groups that are stopped (state T). A stopped process still passes `kill -0`
# and leaves a plain `kill` (TERM) pending until it is continued, so it needs its own checks.
stopped_in_groups() {
  ps -ax -o pgid= -o pid= -o stat= 2>/dev/null | awk -v groups="$*" '
    BEGIN { n = split(groups, list, " "); for (i = 1; i <= n; i++) wanted[list[i]] = 1 }
    ($1 in wanted) && $3 ~ /^T/ { print $2 }' || true
}

for port in "$API_PORT" "$WEB_PORT"; do
  if pids="$(lsof -nP -tiTCP:"$port" -sTCP:LISTEN 2>/dev/null)" && [ -n "$pids" ]; then
    for pid in $pids; do
      pgid="$(ps -o pgid= -p "$pid" 2>/dev/null | tr -d ' ')" || pgid=""
      if [ -n "$pgid" ] && [ -n "$(stopped_in_groups "$pgid")" ]; then
        # Kill the whole group only when it is a server group started by this script (current or older
        # versions); otherwise the group may include unrelated processes, such as the shell that started it.
        target="$pid"
        if ps -o command= -p "$pgid" 2>/dev/null | awk '
            ($1 ~ /(^|\/)bash$/ && $2 ~ /(^|\/)run_local\.sh$/) || /uv run .*uvicorn server\.app:app/ || /pnpm dev --host 127\.0\.0\.1/ { found = 1 }
            END { exit !found }'; then
          target="-$pgid"
        fi
        die "port $port is held by PID $pid, which is frozen (stopped); a plain kill cannot stop it. Run: kill -KILL $target"
      fi
    done
    die "port $port already in use by PID(s) $(echo $pids) — stop it first (kill $(echo $pids))"
  fi
done

CLEAN_PATH="$NODE_BIN:$(dirname "$UV_BIN"):/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"
CLEAN_ENV=(env -i HOME="$HOME" USER="${USER:-$(id -un)}" LOGNAME="${USER:-$(id -un)}"
  LANG="${LANG:-en_US.UTF-8}" TERM="${TERM:-xterm-256color}" PATH="$CLEAN_PATH")
clean() { "${CLEAN_ENV[@]}" "$@"; }

# Prefix that runs a command in a new session with no controlling terminal (macOS has no setsid
# command). Nothing a server starts can then open /dev/tty, so terminal job control (SIGTTIN/SIGTTOU)
# can never stop it, and its session and process group ID equal the PID that `$!` reports.
# INT/QUIT go back to default: bash starts background commands with them ignored.
PERL_BIN="$(command -v perl)" || die "perl not found in PATH (needed to detach the servers from the terminal)"
DETACH=("$PERL_BIN" -MPOSIX -e '
  $SIG{INT} = $SIG{QUIT} = "DEFAULT";
  defined(POSIX::setsid()) or die "run_local: setsid failed: $!\n";
  exec { $ARGV[0] } @ARGV or die "run_local: cannot run $ARGV[0]: $!\n";' --)

# Non-fatal warnings for the subscription setup: an Anthropic credential saved in Settings takes
# precedence over the local Claude Code login and bills the API per request.
check_subscription_mode() {
  local data_dir db
  # `|| true`: with pipefail, a .env without the key would otherwise end the script silently here.
  data_dir="$({ grep -E '^ARCREEL_DATA_DIR=' "$ROOT/.env" || true; } | tail -1 | cut -d= -f2-)"
  data_dir="${data_dir%\"}"; data_dir="${data_dir#\"}"
  data_dir="${data_dir//\$HOME/$HOME}"; data_dir="${data_dir/#\~/$HOME}"
  db="$data_dir/arcreel.db"
  if [ -n "$data_dir" ] && [ -f "$db" ]; then
    # mode=ro without immutable=1: the read includes changes still in the -wal file, which is where the
    # newest settings live after an unclean stop; immutable=1 would skip them.
    if (cd "$ROOT" && clean uv run python -I -c '
import sqlite3, sys
c = sqlite3.connect("file:" + sys.argv[1] + "?mode=ro", uri=True)
n = c.execute("select count(*) from agent_anthropic_credentials where is_active = 1").fetchone()[0]
n += c.execute("select count(*) from system_setting where key = ? and value <> \"\"", ("anthropic_api_key",)).fetchone()[0]
sys.exit(0 if n else 1)
' "$db" 2>/dev/null); then
      echo "run_local: WARNING: an Anthropic API key is configured in Settings; the Agent will bill the API instead of using the Claude Code login." >&2
    fi
  fi
  # Check the login the backend sees: the SDK's bundled CLI, the clean environment, no terminal input,
  # and a time limit so a Keychain prompt or network stall cannot hang startup. The subscription test
  # mirrors verify_local_subscription in lib/backends/text_backends/claude_subscription.py.
  # Distinct exit codes, so a failure of cd, uv or Python itself (often exit 1) reads as "could not check".
  local login_status=0
  (cd "$ROOT" && clean uv run python -I -c '
import json, subprocess, sys
from importlib.resources import files
# 10: claude.ai subscription login; 11: not logged in; 12: logged in without a subscription.
try:
    cli = str(files("claude_agent_sdk").joinpath("_bundled", "claude"))
    out = subprocess.run([cli, "auth", "status", "--json"], stdin=subprocess.DEVNULL,
                         capture_output=True, timeout=15, check=False).stdout
    status = json.loads(out)
    logged_in = status.get("loggedIn") is True
    subscription = (logged_in and status.get("authMethod") == "claude.ai"
                    and status.get("apiProvider") == "firstParty" and bool(status.get("subscriptionType")))
except Exception:
    sys.exit(2)
sys.exit(10 if subscription else 12 if logged_in else 11)
' 2>/dev/null) || login_status=$?
  case "$login_status" in
    10) ;;
    11) echo "run_local: WARNING: Claude Code is not logged in; run 'claude' and /login, or the Agent will fail to start." >&2 ;;
    12) echo "run_local: WARNING: Claude Code is logged in without a claude.ai subscription; the Agent will not run on a subscription and internal text generation will refuse to run." >&2 ;;
    *) echo "run_local: WARNING: could not check the Claude Code login (bundled CLI missing, timed out or unreadable)." >&2 ;;
  esac
}
check_subscription_mode

if $SETUP; then
  echo "run_local: uv sync"
  (cd "$ROOT" && clean uv sync)
  echo "run_local: pnpm install (frontend)"
  (cd "$ROOT/frontend" && clean pnpm install --frozen-lockfile)
fi

# Each server runs in its own session and process group (DETACH), so the whole tree (uv, uvicorn
# workers, vite) can be stopped as one group, and nothing in it can touch the terminal. Before, servers
# shared the terminal's session: when the backend started a child that read or configured the terminal
# (such as `claude auth status`), SIGTTIN/SIGTTOU stopped the whole backend and requests hung forever.
API_PID=""
WEB_PID=""

stop_all() {
  # No `set -e` here: when the terminal is closed (HUP), echo fails, and the servers must still be stopped.
  set +e
  trap - INT TERM HUP EXIT
  echo
  echo "run_local: stopping..."
  for pid in "$WEB_PID" "$API_PID"; do
    [ -n "$pid" ] || continue
    # The PID too: right after start, the server may not have created its own group yet.
    kill -TERM -- "-$pid" "$pid" 2>/dev/null
    # CONT after TERM: a stopped group only receives the pending TERM once continued.
    kill -CONT -- "-$pid" "$pid" 2>/dev/null
  done
  # Up to 10 s: uvicorn drains connections for GRACEFUL_SHUTDOWN_SECONDS, then runs the app's shutdown.
  for _ in $(seq 1 20); do
    alive=false
    for pid in "$WEB_PID" "$API_PID"; do
      [ -n "$pid" ] && { kill -0 -- "-$pid" || kill -0 "$pid"; } 2>/dev/null && alive=true
    done
    $alive || break
    sleep 0.5
  done
  for pid in "$WEB_PID" "$API_PID"; do
    [ -n "$pid" ] && kill -KILL -- "-$pid" "$pid" 2>/dev/null
  done
  echo "run_local: stopped."
}
# HUP: closing the terminal window also stops the servers, which no longer receive the terminal's signals.
# Each signal exits after stopping (with the conventional 128+signal status); otherwise the script would
# resume its watch loop and report that a server exited.
trap 'stop_all; exit 130' INT
trap 'stop_all; exit 143' TERM
trap 'stop_all; exit 129' HUP
trap stop_all EXIT

# The prefixer stays in the launcher's process group, which receives Ctrl+C from the terminal; it ignores
# INT/TERM so the servers' shutdown logs are still printed, and it exits on EOF when its server's output
# closes.
prefix() { trap '' INT TERM; awk -v p="$1" '{ print p $0; fflush() }'; }

UVICORN_ARGS=(server.app:app --host 127.0.0.1 --port "$API_PORT" --timeout-graceful-shutdown "$GRACEFUL_SHUTDOWN_SECONDS")
if $RELOAD; then
  UVICORN_ARGS+=(--reload --reload-dir server --reload-dir lib)
fi
echo "run_local: backend auto-reload $($RELOAD && echo on || echo off)"

FROZEN_HINT="press Ctrl+C and run again"

cd "$ROOT"
# A simple command (not the `clean` function), so `$!` is the server's own PID and therefore its group ID.
"${DETACH[@]}" "${CLEAN_ENV[@]}" uv run --extra speech-review uvicorn "${UVICORN_ARGS[@]}" </dev/null > >(prefix "[api] ") 2>&1 &
API_PID=$!
# Disowned jobs are still stopped by PID/process group, but bash no longer prints "Terminated" notices for them.
disown "$API_PID"

echo "run_local: waiting for backend on http://127.0.0.1:$API_PORT/health ..."
for _ in $(seq 1 120); do
  curl -sf -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 && break
  kill -0 "$API_PID" 2>/dev/null || die "backend exited during startup (see [api] output above)"
  [ -z "$(stopped_in_groups "$API_PID")" ] || die "backend is frozen (stopped) during startup; $FROZEN_HINT"
  sleep 1
done
curl -sf -m 2 "http://127.0.0.1:$API_PORT/health" >/dev/null 2>&1 || die "backend did not become healthy in 120s"

cd "$ROOT/frontend"
"${DETACH[@]}" "${CLEAN_ENV[@]}" pnpm dev --host 127.0.0.1 --port "$WEB_PORT" --strictPort </dev/null > >(prefix "[web] ") 2>&1 &
WEB_PID=$!
disown "$WEB_PID"
cd "$ROOT"

echo "run_local: ArcReel is up — open http://127.0.0.1:$WEB_PORT (Ctrl+C stops both)"

# bash 3.2 has no `wait -n`: poll until either server exits. Also warn once when a server is frozen
# (stopped, for example by an explicit SIGSTOP): it still counts as running, so it would otherwise hang
# without a message.
frozen_warned=false
while kill -0 "$API_PID" 2>/dev/null && kill -0 "$WEB_PID" 2>/dev/null; do
  if [ -n "$(stopped_in_groups "$API_PID" "$WEB_PID")" ]; then
    $frozen_warned || echo "run_local: WARNING: a server is frozen (stopped) and will not answer requests; $FROZEN_HINT." >&2
    frozen_warned=true
  else
    frozen_warned=false
  fi
  sleep 1
done
echo "run_local: a server exited; shutting down the other."
