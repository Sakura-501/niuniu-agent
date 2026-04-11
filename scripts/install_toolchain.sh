#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-install}"

APT_PACKAGES=(
  python3
  python3-pip
  python3.12-venv
  curl
  jq
  ripgrep
  netcat-openbsd
  dnsutils
  ffuf
  nikto
  nmap
  masscan
  whatweb
  sqlmap
  openssl
  redis-tools
  mysql-client
  postgresql-client
  smbclient
  ldap-utils
  hydra
  john
  hashcat
)

GO_PACKAGES=(
  github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest
  github.com/projectdiscovery/httpx/cmd/httpx@latest
  github.com/ropnop/kerbrute@latest
)

PIP_PACKAGES=(
  impacket
  bloodhound
  netexec
)

print_plan() {
  echo "APT: sudo apt-get update && sudo apt-get install -y ${APT_PACKAGES[*]}"
  echo "GO : $(printf 'go install %s && ' "${GO_PACKAGES[@]}")true"
  echo "PIP: python -m pip install ${PIP_PACKAGES[*]}"
}

install_plan() {
  local failures=()
  sudo apt-get update
  sudo apt-get install -y "${APT_PACKAGES[@]}"
  if command -v go >/dev/null 2>&1; then
    for package in "${GO_PACKAGES[@]}"; do
      if ! go install "${package}"; then
        echo "go install failed: ${package}" >&2
        failures+=("go:${package}")
      fi
    done
  else
    echo "go not found; skipping Go tools" >&2
    failures+=("go:missing")
  fi
  if command -v cargo >/dev/null 2>&1; then
    if ! cargo install feroxbuster; then
      echo "cargo install failed: feroxbuster" >&2
      failures+=("cargo:feroxbuster")
    fi
  else
    echo "cargo not found; skipping feroxbuster" >&2
    failures+=("cargo:missing")
  fi
  if ! python -m pip install "${PIP_PACKAGES[@]}"; then
    echo "pip install failed: ${PIP_PACKAGES[*]}" >&2
    failures+=("pip:${PIP_PACKAGES[*]}")
  fi
  if [[ "${#failures[@]}" -gt 0 ]]; then
    echo "INSTALL FAILURES: ${failures[*]}" >&2
    return 1
  fi
}

case "${MODE}" in
  print|--print|dry-run|--dry-run)
    print_plan
    ;;
  install)
    install_plan
    ;;
  *)
    echo "Usage: scripts/install_toolchain.sh [install|print]" >&2
    exit 1
    ;;
esac
