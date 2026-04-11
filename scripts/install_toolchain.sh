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
  sudo apt-get update
  sudo apt-get install -y "${APT_PACKAGES[@]}"
  if command -v go >/dev/null 2>&1; then
    for package in "${GO_PACKAGES[@]}"; do
      go install "${package}"
    done
  else
    echo "go not found; skipping Go tools" >&2
  fi
  if command -v cargo >/dev/null 2>&1; then
    cargo install feroxbuster || true
  else
    echo "cargo not found; skipping feroxbuster" >&2
  fi
  python -m pip install "${PIP_PACKAGES[@]}"
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
