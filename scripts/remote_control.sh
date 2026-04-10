#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_DIR="${REPO_ROOT}/.venv"
PID_FILE="${REPO_ROOT}/runtime/competition.pid"
LOG_FILE="${REPO_ROOT}/runtime/competition.log"

usage() {
  cat <<'EOF'
Usage: scripts/remote_control.sh <command>

Commands:
  help                 Show this help message
  update               Pull latest code and reinstall editable package
  debug                Update, then start interactive debug mode
  competition-start    Update, then start competition mode in background
  competition-stop     Stop background competition mode
  competition-status   Show background competition process status
  logs                 Tail the competition log
EOF
}

err() {
  echo "Unknown command: $1" >&2
  usage >&2
  exit 1
}

ensure_clean_git_tree() {
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
  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    python3 -m venv "${VENV_DIR}"
  fi
}

install_project() {
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

update_repo() {
  ensure_clean_git_tree
  git -C "${REPO_ROOT}" pull --ff-only origin main
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

  update_repo
  load_env
  nohup "${VENV_DIR}/bin/niuniu-agent" run --mode competition >>"${LOG_FILE}" 2>&1 &
  echo $! >"${PID_FILE}"
  echo "competition mode started (pid=$!)"
}

stop_competition() {
  if ! competition_running; then
    rm -f "${PID_FILE}"
    echo "competition mode is not running"
    return 0
  fi

  local pid
  pid="$(competition_pid)"
  kill "${pid}"
  rm -f "${PID_FILE}"
  echo "competition mode stopped (pid=${pid})"
}

show_competition_status() {
  if competition_running; then
    echo "competition mode running (pid=$(competition_pid))"
  else
    echo "competition mode stopped"
  fi
}

run_debug() {
  ensure_runtime_dir
  update_repo
  load_env
  exec "${VENV_DIR}/bin/niuniu-agent" run --mode debug
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
    competition-start)
      start_competition
      ;;
    competition-stop)
      stop_competition
      ;;
    competition-status)
      show_competition_status
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
