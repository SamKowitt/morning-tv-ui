#!/usr/bin/env bash
set -Eeuo pipefail

PROJECT_ROOT="${1:-/home/${USER}/morning-tv-ui}"
VENV_PATH="${PROJECT_ROOT}/.venv3"

DISPLAY_SCRIPT="${HOME}/.local/bin/morning-ui-display"
LAUNCH_SCRIPT="${HOME}/.local/bin/fetchnews"
OLD_LAUNCH_SCRIPT="${HOME}/.local/bin/morning-ui"

BASHRC_PATH="${HOME}/.bashrc"
LABWC_DIR="${HOME}/.config/labwc"
LABWC_AUTOSTART="${LABWC_DIR}/autostart"

if [[ "$(uname -s)" != "Linux" ]]; then
    echo "This script must run on the Raspberry Pi." >&2
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/main.py" ]]; then
    echo "main.py was not found at:" >&2
    echo "  ${PROJECT_ROOT}/main.py" >&2
    exit 1
fi

if [[ ! -f "${PROJECT_ROOT}/requirements.txt" ]]; then
    echo "requirements.txt was not found at:" >&2
    echo "  ${PROJECT_ROOT}/requirements.txt" >&2
    exit 1
fi

echo
echo "===== INSTALLING PI SYSTEM PACKAGES ====="

sudo apt-get update

sudo DEBIAN_FRONTEND=noninteractive apt-get install -y \
    avahi-daemon \
    chromium \
    fontconfig \
    fonts-noto-color-emoji \
    grim \
    python3 \
    python3-pip \
    python3-venv \
    wayvnc \
    wlr-randr

sudo systemctl enable --now avahi-daemon >/dev/null 2>&1 || true

echo
echo "===== ENABLING SSH AND VNC ====="

if command -v raspi-config >/dev/null 2>&1; then
    sudo raspi-config nonint do_ssh 0 || true
    sudo raspi-config nonint do_vnc 0 || true
fi

echo
echo "===== CREATING PYTHON ENVIRONMENT ====="

if [[ ! -x "${VENV_PATH}/bin/python" ]]; then
    python3 -m venv "${VENV_PATH}"
fi

"${VENV_PATH}/bin/python" -m pip install --upgrade \
    pip \
    setuptools \
    wheel

"${VENV_PATH}/bin/python" -m pip install \
    -r "${PROJECT_ROOT}/requirements.txt"

"${VENV_PATH}/bin/python" -m pip check

echo
echo "===== CREATING DISPLAY CONFIGURATION ====="

mkdir -p \
    "${HOME}/.local/bin" \
    "${LABWC_DIR}"

cat > "${DISPLAY_SCRIPT}" <<'DISPLAY_EOF'
#!/usr/bin/env bash
set -u

if ! command -v wlr-randr >/dev/null 2>&1; then
    exit 0
fi

for _ in $(seq 1 30); do
    OUTPUT_NAME=""

    if wlr-randr 2>/dev/null | grep -q '^NOOP-1 '; then
        OUTPUT_NAME="NOOP-1"
    else
        OUTPUT_NAME="$(
            wlr-randr 2>/dev/null |
            awk '/^[^[:space:]]/ { print $1; exit }'
        )"
    fi

    if [[ -n "${OUTPUT_NAME}" ]]; then
        wlr-randr \
            --output "${OUTPUT_NAME}" \
            --mode 1280x720 \
            --scale 1 >/dev/null 2>&1 || true

        exit 0
    fi

    sleep 1
done

exit 0
DISPLAY_EOF

chmod +x "${DISPLAY_SCRIPT}"

echo
echo "===== CREATING MORNING UI LAUNCH COMMAND ====="

cat > "${LAUNCH_SCRIPT}" <<LAUNCH_EOF
#!/usr/bin/env bash
set -Eeuo pipefail

export QT_FONT_DPI=72

cd "${PROJECT_ROOT}"

"${DISPLAY_SCRIPT}" || true

source "${VENV_PATH}/bin/activate"

exec python main.py
LAUNCH_EOF

chmod +x "${LAUNCH_SCRIPT}"

# Remove the previous launcher name.
rm -f "${OLD_LAUNCH_SCRIPT}"

echo
echo "===== CONFIGURING TERMINAL DEFAULTS ====="

touch "${BASHRC_PATH}"

sed -i \
    '/# BEGIN MORNING TV UI SHELL/,/# END MORNING TV UI SHELL/d' \
    "${BASHRC_PATH}"

cat >> "${BASHRC_PATH}" <<BASHRC_EOF

# BEGIN MORNING TV UI SHELL
export QT_FONT_DPI=72

if [[ \$- == *i* ]] && \
   [[ -f "${VENV_PATH}/bin/activate" ]]; then
    cd "${PROJECT_ROOT}"
    source "${VENV_PATH}/bin/activate"
fi
# END MORNING TV UI SHELL
BASHRC_EOF

echo
echo "===== CONFIGURING 1280x720 AT DESKTOP LOGIN ====="

touch "${LABWC_AUTOSTART}"

sed -i \
    '/# BEGIN MORNING TV UI DISPLAY/,/# END MORNING TV UI DISPLAY/d' \
    "${LABWC_AUTOSTART}"

cat >> "${LABWC_AUTOSTART}" <<AUTOSTART_EOF

# BEGIN MORNING TV UI DISPLAY
"${DISPLAY_SCRIPT}" &
# END MORNING TV UI DISPLAY
AUTOSTART_EOF

fc-cache -f

"${DISPLAY_SCRIPT}" || true

echo
echo "===== PI BOOTSTRAP COMPLETE ====="
echo
echo "Project:"
echo "  ${PROJECT_ROOT}"
echo
echo "Python:"
echo "  ${VENV_PATH}/bin/python"
echo
echo "Chromium:"
command -v chromium || true
echo
echo "Morning UI launch command:"
echo "  fetchnews"
echo
echo "A reboot is recommended after the fonts are copied."
