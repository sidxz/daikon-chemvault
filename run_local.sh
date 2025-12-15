#!/usr/bin/env bash
# run_local.sh — mirror the Dockerfile locally (Python 3.12 + Pipenv)
# Usage:
#   chmod +x run_local.sh
#   ./run_local.sh              # normal start
#   ./run_local.sh --reload     # uvicorn auto-reload (dev)

set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

PORT=10001
APP_IMPORT="app.main:app"   # change if your FastAPI entrypoint differs
UVICORN_OPTS="--host 0.0.0.0 --port ${PORT}"
if [[ "${1:-}" == "--reload" ]]; then
    UVICORN_OPTS="${UVICORN_OPTS} --reload"
fi

echo "==> Working directory: $PROJECT_DIR"

# ------------------------------
# 0) OS-level deps (best effort)
# ------------------------------
install_apt_packages() {
    sudo apt-get update
    sudo apt-get install -y \
    gcc \
    libpq-dev \
    libexpat1 \
    libexpat1-dev \
    libxrender1 \
    libxext6 \
    postgresql-client
}

install_brew_packages() {
    # Best-effort equivalents for macOS (adjust as needed)
    # libpq installs client; you may need to add to PATH manually.
    brew update
    brew install gcc expat libx11 libpng libpq
    # Ensure psql is reachable (optional):
    if ! command -v psql >/dev/null 2>&1; then
        brew link --force libpq || true
    fi
}

echo "==> Checking system packages (best effort)…"
if command -v apt-get >/dev/null 2>&1; then
    install_apt_packages
    elif command -v brew >/dev/null 2>&1; then
    install_brew_packages
else
    echo "!! Skipping system package install (no apt-get/brew found)."
    echo "   If builds fail, install equivalents for: gcc, libpq (client+dev), expat, Xrender, Xext."
fi

# --------------------------------
# 1) Python 3.12 & Pipenv tooling
# --------------------------------
need_pyver=3.12
have_pyver="$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))' 2>/dev/null || echo "none")"

if [[ "$have_pyver" != "$need_pyver" ]]; then
    echo "!! Python $need_pyver not default. Trying python$need_pyver…"
    if command -v "python${need_pyver}" >/dev/null 2>&1; then
        PY="python${need_pyver}"
    else
        echo "!! Python ${need_pyver} not found. Install Python ${need_pyver} and re-run."
        exit 1
    fi
else
    PY=python3
fi

if ! $PY -m pip --version >/dev/null 2>&1; then
    echo "==> Installing pip for ${PY}…"
    curl -sS https://bootstrap.pypa.io/get-pip.py | $PY
fi

if ! $PY -m pip show pipenv >/dev/null 2>&1; then
    echo "==> Installing Pipenv…"
    $PY -m pip install --user pipenv
fi

# Ensure we can call pipenv
if ! command -v pipenv >/dev/null 2>&1; then
    # Add user-base bin to PATH for this shell
    USER_BASE="$($PY -m site --user-base)"
    export PATH="$USER_BASE/bin:$PATH"
fi

command -v pipenv >/dev/null 2>&1 || { echo "!! pipenv not on PATH. Add your user bin dir to PATH and retry."; exit 1; }

# ------------------------------------------------
# 2) Project venv in-repo (mirror PIPENV_VENV_IN_PROJECT)
# ------------------------------------------------
export PIPENV_VENV_IN_PROJECT=1

echo "==> Creating/using Pipenv with Python ${need_pyver}…"
pipenv --python "${need_pyver}"

# --------------------------------
# 3) Install Python dependencies
# --------------------------------
if [[ -f Pipfile.lock ]]; then
    echo "==> Installing from Pipfile.lock (deploy)…"
    # Mirrors: pipenv install --deploy
    pipenv sync --dev
else
    echo "==> Pipfile.lock not found; installing from Pipfile…"
    pipenv install --dev
fi

# If you rely on uvicorn explicitly, ensure present (Dockerfile commented it; add if needed)
if ! pipenv run python -c "import uvicorn" >/dev/null 2>&1; then
    echo "==> Adding uvicorn (not found in lock)…"
    pipenv install uvicorn
fi

# --------------------------------
# 4) Mirror Dockerfile file perms & entrypoint
# --------------------------------
if [[ -f docker-entrypoint.sh ]]; then
    echo "==> Making docker-entrypoint.sh executable…"
    chmod +x docker-entrypoint.sh
fi

# --------------------------------
# 5) Run the app (mirror ENTRYPOINT)
# --------------------------------
# Prefer the same entrypoint; fall back to direct uvicorn if not present.
echo "==> Starting service on port ${PORT}…"
if [[ -f docker-entrypoint.sh ]]; then
    exec pipenv run bash ./docker-entrypoint.sh
else
    echo "==> docker-entrypoint.sh not found; running uvicorn directly."
    echo "    Using app: ${APP_IMPORT}"
    exec pipenv run uvicorn "${APP_IMPORT}" ${UVICORN_OPTS}
fi
