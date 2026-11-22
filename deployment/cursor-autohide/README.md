# MorningUI HDMI Cursor Auto-Hide V1

## Purpose

Hide the Raspberry Pi computer cursor automatically when the
MorningUI dashboard starts or restarts.

This implementation uses labwc's native `HideCursor` action.
It does not modify MorningUI's Python code, QML weather
renderer, screen resolution, scaling, or LG remote navigation.

## Components

- `labwc-keybind.xml`: labwc keyboard configuration fragment.
- `mui-hide-cursor-on-morningui-v1`: executable helper.
- `mui-cursor-autohide-v1.service`: systemd user service.

## Requirements

- Raspberry Pi with labwc Wayland compositor
- wtype
- wlrctl
- morningui-remote.service
- A MorningUI window titled "Morning TV UI"

## Installation

Merge `labwc-keybind.xml` into the existing
`~/.config/labwc/rc.xml`, preserving existing settings.

Do not add a duplicate keyboard section or keybinding.

Reload labwc using its running process ID:

```bash
LABWC_PID="$(pgrep -u "$(id -u)" -x labwc)" \
  labwc --reconfigure
```

Install the helper and service:

```bash
install -m 755 mui-hide-cursor-on-morningui-v1 \
  "$HOME/.local/bin/mui-hide-cursor-on-morningui-v1"

mkdir -p "$HOME/.config/systemd/user"

install -m 644 mui-cursor-autohide-v1.service \
  "$HOME/.config/systemd/user/mui-cursor-autohide-v1.service"

systemctl --user daemon-reload

systemctl --user enable mui-cursor-autohide-v1.service

systemctl --user start mui-cursor-autohide-v1.service
```

## Verification

```bash
systemctl --user is-enabled mui-cursor-autohide-v1.service

journalctl --user \
  -u mui-cursor-autohide-v1.service \
  -n 15 --no-pager -o cat
```

Expected success marker:

`MUI_CURSOR_AUTOHIDE_V1: HideCursor sent to labwc`

## Behavior

The helper waits for the running MorningUI window and invokes
the labwc Alt+Super+H shortcut.

The systemd user service is enabled to run when MorningUI starts.

Labwc can reveal the pointer again following physical mouse movement.
This version hides the cursor on startup; it does not continuously
suppress the pointer during mouse movement.

## Rollback

Disable the user service and remove its installed helper/unit.
Restore the prior labwc rc.xml from its local backup if desired.

The MorningUI application itself is unaffected.
