#!/usr/bin/env bash
set -Eeuo pipefail

PI_HOST="${1:-fetchnews.local}"
PI_USER="${2:-mrkowitt}"
REMOTE_PROJECT="${3:-/home/${PI_USER}/morning-tv-ui}"
TARGET="${PI_USER}@${PI_HOST}"

ssh "${TARGET}" bash -s -- "${REMOTE_PROJECT}" <<'REMOTE_EOF'
set -Eeuo pipefail

PROJECT_ROOT="$1"
PYTHON="${PROJECT_ROOT}/.venv3/bin/python"

echo "===== PYTHON ====="
"${PYTHON}" --version
"${PYTHON}" -m pip check
"${PYTHON}" -c '
import holidays
import PySide6
from PIL import Image
from websocket import create_connection
print("PySide6:", PySide6.__version__)
print("Pillow:", Image.__version__)
print("holidays:", holidays.__version__)
print("websocket-client import: OK")
'

echo
echo "===== REQUIRED PACKAGES ====="
"${PYTHON}" -m pip freeze |
grep -Ei '^(holidays|pillow|websocket-client)=='

echo
echo "===== CHROMIUM ====="
command -v chromium
chromium --version

echo
echo "===== FONT DPI ====="
grep -n 'QT_FONT_DPI' "${PROJECT_ROOT}/main.py"
grep -n 'QT_FONT_DPI' "${HOME}/.bashrc" || true

echo
echo "===== FONTS ====="
for family in \
    "Times New Roman" \
    "Georgia" \
    "Rockwell" \
    "American Typewriter" \
    "Bodoni 72" \
    "Apple Color Emoji" \
    "Noto Color Emoji"
do
    printf '%-24s -> ' "${family}"
    fc-match "${family}" | head -n 1
done

echo
echo "===== DISPLAY ====="
wlr-randr 2>/dev/null || \
    echo "Display details require a Pi desktop session."

echo
echo "===== LAUNCHERS ====="
ls -l \
    "${HOME}/.local/bin/fetchnews" \
    "${HOME}/.local/bin/morning-ui-display"

grep -n 'exec python main.py' \
    "${HOME}/.local/bin/fetchnews"

if [[ -e "${HOME}/.local/bin/morning-ui" ]]; then
    echo "Old morning-ui launcher still exists." >&2
    exit 1
fi

echo
echo "Verification completed."
REMOTE_EOF
