#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
PID_FILE="${REPO_ROOT}/runtime/competition.pid"
LOG_FILE="${REPO_ROOT}/runtime/competition.log"
RUN_ID_FILE="${REPO_ROOT}/runtime/competition.run_id"
UI_PID_FILE="${REPO_ROOT}/runtime/ui.pid"
UI_LOG_FILE="${REPO_ROOT}/runtime/ui.log"
USE_UV="${REMOTE_CONTROL_USE_UV:-1}"

usage() {
  cat <<'EOF'
Usage: scripts/remote_control.sh <command>

Commands:
  help                 Show this help message
  update               Pull latest code and reinstall editable package
  debug                Start interactive debug mode without updating
  debug-update         Update, then start interactive debug mode
  competition-start    Start competition mode in background without updating
  competition-restart  Update, then start competition mode in background
  competition-stop     Stop background competition mode
  competition-status   Show background competition process status
  ui-start             Start web UI in background with reload enabled
  ui-restart           Restart web UI in background with reload enabled
  ui-stop              Stop background web UI
  ui-status            Show background web UI status
  ui-logs              Tail the web UI log
  logs                 Tail the competition log
EOF
}

BOOTSTRAP_CLEAN_PATHS=(
  "scripts/"
  "scripts/remote_control.sh"
)

err() {
  echo "Unknown command: $1" >&2
  usage >&2
  exit 1
}

is_bootstrap_dirty_line() {
  local line="${1}"
  local path="${line:3}"
  for allowed in "${BOOTSTRAP_CLEAN_PATHS[@]}"; do
    if [[ "${path}" == "${allowed}" ]]; then
      return 0
    fi
  done
  return 1
}

cleanup_bootstrap_artifacts_if_safe() {
  local status
  status="$(git -C "${REPO_ROOT}" status --porcelain)"
  [[ -z "${status}" ]] && return 0

  local line
  while IFS= read -r line; do
    [[ -z "${line}" ]] && continue
    if ! is_bootstrap_dirty_line "${line}"; then
      return 0
    fi
  done <<< "${status}"

  rm -rf "${REPO_ROOT}/scripts"
}

ensure_clean_git_tree() {
  cleanup_bootstrap_artifacts_if_safe
  if [[ -n "$(git -C "${REPO_ROOT}" status --porcelain)" ]]; then
    echo "Git working tree is dirty. Commit, stash, or clean changes before running update." >&2
    git -C "${REPO_ROOT}" status --short >&2
    exit 2
  fi
}

ensure_runtime_dir() {
  mkdir -p "${REPO_ROOT}/runtime"
}

ensure_venv() {
  if [[ "${REMOTE_CONTROL_SKIP_INSTALL:-0}" == "1" ]]; then
    return 0
  fi
  if [[ "${USE_UV}" == "1" ]] && command -v uv >/dev/null 2>&1; then
    return 0
  fi
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    python3 -m venv "${VENV_DIR}"
  fi
}

install_project() {
  if [[ "${REMOTE_CONTROL_SKIP_INSTALL:-0}" == "1" ]]; then
    return 0
  fi
  if [[ "${USE_UV}" == "1" ]] && command -v uv >/dev/null 2>&1; then
    (cd "${REPO_ROOT}" && uv sync) >/dev/null
    return 0
  fi
  "${VENV_DIR}/bin/python" -m pip install --upgrade pip >/dev/null
  "${VENV_DIR}/bin/python" -m pip install -e '.[dev]' >/dev/null
}

load_env() {
  if [[ ! -f "${REPO_ROOT}/.env" ]]; then
    echo ".env not found at ${REPO_ROOT}/.env" >&2
    exit 3
  fi

  set -a
  # shellcheck disable=SC1090
  source "${REPO_ROOT}/.env"
  set +a
}

git_pull_with_retry() {
  local attempt
  for attempt in 1 2 3; do
    if git -C "${REPO_ROOT}" -c http.version=HTTP/1.1 pull --ff-only origin main; then
      return 0
    fi
    if [[ "${attempt}" -lt 3 ]]; then
      echo "git pull failed on attempt ${attempt}, retrying..." >&2
      sleep "${attempt}"
    fi
  done
  echo "git pull failed after 3 attempts" >&2
  exit 4
}

update_repo() {
  ensure_clean_git_tree
  git_pull_with_retry
  ensure_venv
  install_project
}

competition_pid() {
  if [[ -f "${PID_FILE}" ]]; then
    cat "${PID_FILE}"
  fi
}

competition_running() {
  local pid
  pid="$(competition_pid || true)"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

start_competition() {
  ensure_runtime_dir
  if competition_running; then
    echo "competition mode already running (pid=$(competition_pid))"
    return 0
  fi

  load_env
  local run_id
  if command -v python3 >/dev/null 2>&1; then
    run_id="$(python3 -c 'from uuid import uuid4; print(uuid4().hex[:8])')"
  else
    run_id="$(date +%s)"
  fi
  if [[ "${USE_UV}" == "1" ]] && command -v uv >/dev/null 2>&1; then
    nohup env NIUNIU_AGENT_RUNTIME_DIR="${REPO_ROOT}/runtime" NIUNIU_AGENT_COMPETITION_RUN_ID="${run_id}" uv run niuniu-agent run --mode competition >>"${LOG_FILE}" 2>&1 &
  else
    nohup env NIUNIU_AGENT_RUNTIME_DIR="${REPO_ROOT}/runtime" NIUNIU_AGENT_COMPETITION_RUN_ID="${run_id}" "${VENV_DIR}/bin/niuniu-agent" run --mode competition >>"${LOG_FILE}" 2>&1 &
  fi
  echo $! >"${PID_FILE}"
  echo "${run_id}" >"${RUN_ID_FILE}"
  echo "competition mode started (pid=$!)"
}

stop_competition() {
  if ! competition_running; then
    rm -f "${PID_FILE}"
    rm -f "${RUN_ID_FILE}"
    echo "competition mode is not running"
    return 0
  fi

  local pid
  pid="$(competition_pid)"
  kill "${pid}"
  rm -f "${PID_FILE}"
  rm -f "${RUN_ID_FILE}"
  echo "competition mode stopped (pid=${pid})"
}

show_competition_status() {
  if competition_running; then
    echo "competition mode running (pid=$(competition_pid))"
  else
    echo "competition mode stopped"
  fi
}

ui_pid() {
  if [[ -f "${UI_PID_FILE}" ]]; then
    cat "${UI_PID_FILE}"
  fi
}

ui_running() {
  local pid
  pid="$(ui_pid || true)"
  [[ -n "${pid}" ]] && kill -0 "${pid}" 2>/dev/null
}

start_ui() {
  ensure_runtime_dir
  if ui_running; then
    echo "web UI already running (pid=$(ui_pid))"
    return 0
  fi

  load_env
  if [[ "${USE_UV}" == "1" ]] && command -v uv >/dev/null 2>&1; then
    nohup env NIUNIU_AGENT_RUNTIME_DIR="${REPO_ROOT}/runtime" uv run uvicorn niuniu_agent.web.app:app \
      --host "${NIUNIU_AGENT_WEB_HOST:-0.0.0.0}" \
      --port "${NIUNIU_AGENT_WEB_PORT:-8081}" \
      --reload >>"${UI_LOG_FILE}" 2>&1 &
  else
    nohup "${VENV_DIR}/bin/python" -m uvicorn niuniu_agent.web.app:app \
      --host "${NIUNIU_AGENT_WEB_HOST:-0.0.0.0}" \
      --port "${NIUNIU_AGENT_WEB_PORT:-8081}" \
      --reload >>"${UI_LOG_FILE}" 2>&1 &
  fi
  echo $! >"${UI_PID_FILE}"
  echo "web UI started (pid=$!, port=${NIUNIU_AGENT_WEB_PORT:-8081})"
}

stop_ui() {
  if ! ui_running; then
    rm -f "${UI_PID_FILE}"
    echo "web UI is not running"
    return 0
  fi

  local pid
  pid="$(ui_pid)"
  kill "${pid}"
  rm -f "${UI_PID_FILE}"
  echo "web UI stopped (pid=${pid})"
}

restart_ui() {
  stop_ui || true
  ensure_venv
  install_project
  start_ui
}

show_ui_status() {
  if ui_running; then
    echo "web UI running (pid=$(ui_pid), port=${NIUNIU_AGENT_WEB_PORT:-8081})"
  else
    echo "web UI stopped"
  fi
}

tail_ui_logs() {
  ensure_runtime_dir
  touch "${UI_LOG_FILE}"
  exec tail -f "${UI_LOG_FILE}"
}

run_debug() {
  ensure_runtime_dir
  load_env
  if [[ "${USE_UV}" == "1" ]] && command -v uv >/dev/null 2>&1; then
    exec env NIUNIU_AGENT_RUNTIME_DIR="${REPO_ROOT}/runtime" uv run niuniu-agent run --mode debug
  fi
  exec "${VENV_DIR}/bin/niuniu-agent" run --mode debug
}

run_debug_update() {
  update_repo
  run_debug
}

restart_competition() {
  stop_competition || true
  update_repo
  start_competition
}

tail_logs() {
  ensure_runtime_dir
  touch "${LOG_FILE}"
  exec tail -f "${LOG_FILE}"
}

main() {
  local command="${1:-help}"
  cd "${REPO_ROOT}"

  case "${command}" in
    help|-h|--help)
      usage
      ;;
    update)
      update_repo
      ;;
    debug)
      run_debug
      ;;
    debug-update)
      run_debug_update
      ;;
    competition-start)
      start_competition
      ;;
    competition-restart)
      restart_competition
      ;;
    competition-stop)
      stop_competition
      ;;
    competition-status)
      show_competition_status
      ;;
    ui-start)
      start_ui
      ;;
    ui-restart)
      restart_ui
      ;;
    ui-stop)
      stop_ui
      ;;
    ui-status)
      show_ui_status
      ;;
    ui-logs)
      tail_ui_logs
      ;;
    logs)
      tail_logs
      ;;
    *)
      err "${command}"
      ;;
  esac
}

main "$@"
