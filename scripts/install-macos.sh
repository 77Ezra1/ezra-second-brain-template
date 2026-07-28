#!/usr/bin/env bash
set -euo pipefail

TARGET="${SECOND_BRAIN_HOME:-$HOME/second-brain}"
SKIP_TESTS=""
FORCE=""

while [[ $# -gt 0 ]]; do
  case "$1" in
    --target)
      TARGET="$2"
      shift 2
      ;;
    --target=*)
      TARGET="${1#--target=}"
      shift
      ;;
    --force)
      FORCE="--force"
      shift
      ;;
    --skip-tests)
      SKIP_TESTS="--skip-tests"
      shift
      ;;
    -h|--help)
      cat <<'EOF'
Install ezra-second-brain-template on macOS.

Usage:
  bash scripts/install-macos.sh [--target ~/second-brain] [--force] [--skip-tests]

Remote one-liner:
  curl -fsSL https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install-macos.sh | bash
EOF
      exit 0
      ;;
    *)
      echo "Unknown argument: $1" >&2
      exit 2
      ;;
  esac
done

if command -v python3 >/dev/null 2>&1; then
  PYTHON=python3
elif command -v python >/dev/null 2>&1; then
  PYTHON=python
else
  echo "Python 3.11+ is required. Install it from https://www.python.org/downloads/ or Homebrew, then retry." >&2
  exit 1
fi

"$PYTHON" -c "import urllib.request; exec(urllib.request.urlopen('https://raw.githubusercontent.com/77Ezra1/ezra-second-brain-template/master/scripts/install.py').read())" -- --platform macos --target "$TARGET" $FORCE $SKIP_TESTS
