#!/usr/bin/env bash
set -euo pipefail

MODE="${1:-install}"
export DEBIAN_FRONTEND=noninteractive
export NEEDRESTART_MODE=a

APT_PACKAGES=(
  python3
  python3-pip
  python3.12-venv
  cargo
  rustc
  curl
  jq
  ripgrep
  netcat-openbsd
  dnsutils
  ffuf
  gobuster
  nikto
  nmap
  masscan
  whatweb
  sqlmap
  openssl
  redis-tools
  mysql-client
  postgresql-client
  socat
  proxychains4
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
  bloodhound-python
  netexec
)

promote_user_binaries() {
  local source_dir
  for source_dir in "${HOME}/go/bin" "${HOME}/.local/bin" "${HOME}/.cargo/bin"; do
    [[ -d "${source_dir}" ]] || continue
    find "${source_dir}" -maxdepth 1 -type f -perm -111 | while read -r binary; do
      sudo ln -sf "${binary}" "/usr/local/bin/$(basename "${binary}")"
    done
  done
}

install_github_binary() {
  local repo="$1"
  local asset_pattern="$2"
  local binary_name="$3"
  local tmpdir
  tmpdir="$(mktemp -d)"
  local url
  url="$(python3 - <<PY
import json, sys, urllib.request
repo = ${repo@Q}
pattern = ${asset_pattern@Q}
with urllib.request.urlopen(f"https://api.github.com/repos/{repo}/releases/latest") as resp:
    data = json.load(resp)
for asset in data.get("assets", []):
    if pattern in asset.get("name", ""):
        print(asset["browser_download_url"])
        sys.exit(0)
sys.exit(1)
PY
)" || return 1
  local asset_path="${tmpdir}/asset"
  curl -fsSL "${url}" -o "${asset_path}"
  case "${url}" in
    *.zip)
      python3 - <<PY
import zipfile
from pathlib import Path
archive = Path(${asset_path@Q})
target = Path(${tmpdir@Q})
with zipfile.ZipFile(archive) as zf:
    zf.extractall(target)
PY
      ;;
    *.tar.gz|*.tgz)
      tar -xzf "${asset_path}" -C "${tmpdir}"
      ;;
    *)
      chmod +x "${asset_path}"
      ;;
  esac
  local binary_path
  binary_path="$(find "${tmpdir}" -maxdepth 3 -type f -name "${binary_name}" | head -n 1)"
  if [[ -z "${binary_path}" && -x "${asset_path}" ]]; then
    binary_path="${asset_path}"
  fi
  [[ -n "${binary_path}" ]] || return 1
  sudo install -m 0755 "${binary_path}" "/usr/local/bin/${binary_name}"
  rm -rf "${tmpdir}"
}

print_plan() {
  echo "APT: sudo apt-get update && sudo apt-get install -y ${APT_PACKAGES[*]}"
  echo "GO : $(printf 'go install %s && ' "${GO_PACKAGES[@]}")true"
  echo "PIP: python3 -m pip install --user ${PIP_PACKAGES[*]}"
}

install_plan() {
  local failures=()
  if ! sudo apt-get update -o Dir::Etc::sourceparts=/dev/null -o Dir::Etc::sourcelist=/etc/apt/sources.list; then
    sudo apt-get update
  fi
  if ! sudo apt-get install -y -o Dir::Etc::sourceparts=/dev/null -o Dir::Etc::sourcelist=/etc/apt/sources.list "${APT_PACKAGES[@]}"; then
    sudo apt-get install -y "${APT_PACKAGES[@]}"
  fi
  if command -v go >/dev/null 2>&1; then
    for package in "${GO_PACKAGES[@]}"; do
      if ! go install "${package}"; then
        echo "go install failed: ${package}" >&2
        if [[ "${package}" == github.com/projectdiscovery/nuclei/v3/cmd/nuclei@latest ]]; then
          install_github_binary "projectdiscovery/nuclei" "linux_amd64.zip" "nuclei" || failures+=("binary:nuclei")
        elif [[ "${package}" == github.com/projectdiscovery/httpx/cmd/httpx@latest ]]; then
          install_github_binary "projectdiscovery/httpx" "linux_amd64.zip" "httpx" || failures+=("binary:httpx")
        else
          failures+=("go:${package}")
        fi
      fi
    done
  else
    echo "go not found; skipping Go tools" >&2
    failures+=("go:missing")
  fi
  if command -v cargo >/dev/null 2>&1; then
    if ! cargo install feroxbuster; then
      echo "cargo install failed: feroxbuster" >&2
      install_github_binary "epi052/feroxbuster" "x86_64-linux-feroxbuster.zip" "feroxbuster" || failures+=("binary:feroxbuster")
    fi
  else
    echo "cargo not found; skipping feroxbuster" >&2
    install_github_binary "epi052/feroxbuster" "x86_64-linux-feroxbuster.zip" "feroxbuster" || failures+=("binary:feroxbuster")
  fi
  if ! python3 -m pip install --user --break-system-packages "${PIP_PACKAGES[@]}"; then
    echo "pip install failed: ${PIP_PACKAGES[*]}" >&2
    failures+=("pip:${PIP_PACKAGES[*]}")
  fi
  promote_user_binaries
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
