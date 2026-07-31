#!/usr/bin/env bash
set -Eeuo pipefail

PI_HOST="${1:-fetchnews.local}"
PI_USER="${2:-mrkowitt}"
REMOTE_PROJECT="${3:-/home/${PI_USER}/morning-tv-ui}"

TARGET="${PI_USER}@${PI_HOST}"

SCRIPT_DIR="$(
    cd "$(dirname "${BASH_SOURCE[0]}")"
    pwd
)"

PI_BOOTSTRAP="${SCRIPT_DIR}/pi_bootstrap.sh"
PRIVATE_FONTS="${SCRIPT_DIR}/private-fonts"
REMOTE_FONT_DIR="/home/${PI_USER}/.local/share/fonts/morning-tv-ui"

if [[ "$(uname -s)" != "Darwin" ]]; then
    echo "This script must be run from the Mac." >&2
    exit 1
fi

if [[ ! -f "${PI_BOOTSTRAP}" ]]; then
    echo "Missing file:" >&2
    echo "  ${PI_BOOTSTRAP}" >&2
    exit 1
fi

mkdir -p "${PRIVATE_FONTS}"

echo
echo "===== REFRESHING PRIVATE FONT COLLECTION ====="

find "${PRIVATE_FONTS}" \
    -mindepth 1 \
    -maxdepth 1 \
    -type f \
    -delete

SEARCH_ROOTS=(
    "/System/Library/Fonts"
    "/Library/Fonts"
    "${HOME}/Library/Fonts"
)

FONT_PATTERNS=(
    "AmericanTypewriter*.ttc"
    "Rockwell*.ttc"
    "Bodoni 72*.ttc"
    "Bodoni 72*.ttf"
    "Apple Color Emoji*.ttc"
    "Georgia*.ttf"
    "Times New Roman*.ttf"
    "Arial*.ttf"
    "Courier New*.ttf"
)

for pattern in "${FONT_PATTERNS[@]}"; do
    while IFS= read -r -d '' font_path; do
        cp -f \
            "${font_path}" \
            "${PRIVATE_FONTS}/$(basename "${font_path}")"
    done < <(
        find "${SEARCH_ROOTS[@]}" \
            -type f \
            -iname "${pattern}" \
            -print0 2>/dev/null
    )
done

FONT_COUNT="$(
    find "${PRIVATE_FONTS}" \
        -maxdepth 1 \
        -type f |
    wc -l |
    tr -d ' '
)"

if [[ "${FONT_COUNT}" -eq 0 ]]; then
    echo "No matching font files were found on the Mac." >&2
    exit 1
fi

echo "Collected ${FONT_COUNT} private font files:"

find "${PRIVATE_FONTS}" \
    -maxdepth 1 \
    -type f \
    -print |
    sort

echo
echo "===== CHECKING REMOTE PROJECT ====="

ssh "${TARGET}" \
    "test -f '${REMOTE_PROJECT}/main.py' &&
     test -f '${REMOTE_PROJECT}/requirements.txt'"

echo "Remote project found at:"
echo "  ${REMOTE_PROJECT}"

echo
echo "===== UPLOADING PI BOOTSTRAP ====="

scp \
    "${PI_BOOTSTRAP}" \
    "${TARGET}:/tmp/morning-ui-pi-bootstrap.sh"

echo
echo "===== CONFIGURING PI ====="

ssh -t "${TARGET}" \
    "bash /tmp/morning-ui-pi-bootstrap.sh '${REMOTE_PROJECT}';
     rm -f /tmp/morning-ui-pi-bootstrap.sh"

echo
echo "===== COPYING PRIVATE MAC FONTS ====="

ssh "${TARGET}" \
    "mkdir -p '${REMOTE_FONT_DIR}'"

scp -r \
    "${PRIVATE_FONTS}/." \
    "${TARGET}:${REMOTE_FONT_DIR}/"

echo
echo "===== REBUILDING PI FONT CACHE ====="

ssh "${TARGET}" "
    fc-cache -f

    for family in \
        'Times New Roman' \
        'Georgia' \
        'Rockwell' \
        'American Typewriter' \
        'Bodoni 72' \
        'Apple Color Emoji' \
        'Noto Color Emoji'
    do
        printf '%-24s -> ' \"\$family\"
        fc-match \"\$family\" | head -n 1
    done
"

echo
echo "===== DEPLOYMENT CONFIGURATION COMPLETE ====="
echo
echo "Reboot the Pi with:"
echo "  ssh ${TARGET} sudo reboot"
echo
echo "After reboot, launch Morning TV UI with:"
echo "  fetchnews"
