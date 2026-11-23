# MorningUI HDMI Cursor Lifecycle V2

## Purpose

Hide the Raspberry Pi computer cursor when MorningUI is displayed
and restore the normal cursor when MorningUI closes or stops.

The implementation uses the existing labwc HideCursor shortcut,
wtype, wlrctl, and a systemd user service.

## Files

- `mui-hide-cursor-on-morningui-v1` — V2 lifecycle helper
- `mui-cursor-autohide-v1.service` — V2 systemd user service
- `labwc-keybind.xml` — existing labwc HideCursor shortcut

The original V1 filenames remain unchanged for compatibility.

## Cursor behavior

| Event | Intended behavior |
|---|---|
| MorningUI window appears | Hide cursor |
| MorningUI closes normally | Restore cursor |
| MorningUI is manually terminated | Restore cursor |
| MorningUI service stops | Restore cursor |
| MorningUI starts again | Hide cursor |
| Pi shuts down | Attempt restoration during shutdown |

On a new desktop session the normal cursor is available until
MorningUI starts and the helper hides it.

The helper also monitors the MorningUI window.

The systemd service includes `BindsTo=morningui-remote.service`
and an `ExecStopPost` restoration handler.

## Hiding and restoration

The existing labwc configuration binds `Alt+Super+H`
to the `HideCursor` action.

The helper sends that shortcut using wtype.

Restoration uses synthetic pointer movement via wlrctl,
which was independently tested on the Pi's HDMI display.

Physical mouse movement can reveal a hidden cursor.
This version does not continuously suppress pointer movement.

## Installation

Ensure the existing labwc HideCursor binding is installed.
Merge `labwc-keybind.xml` into the labwc configuration if absent.

Do not overwrite other labwc configuration or duplicate bindings.

Install the helper and unit in their established locations:

```bash
install -m 755 mui-hide-cursor-on-morningui-v1 \
  "$HOME/.local/bin/mui-hide-cursor-on-morningui-v1"

mkdir -p "$HOME/.config/systemd/user"

install -m 644 mui-cursor-autohide-v1.service \
  "$HOME/.config/systemd/user/mui-cursor-autohide-v1.service"

systemctl --user daemon-reload
systemctl --user enable mui-cursor-autohide-v1.service
```

Service activation should follow MorningUI's lifecycle.

## Verification

```bash
systemctl --user show mui-cursor-autohide-v1.service \
  -p ActiveState -p SubState -p MainPID \
  -p BindsTo -p ExecStopPost --no-pager

journalctl --user \
  -u mui-cursor-autohide-v1.service \
  -n 20 --no-pager -o cat
```

The successful V2 startup marker is:

`MUI_CURSOR_LIFECYCLE_V2: CURSOR_HIDDEN`

Automatic restoration on an actual MorningUI close and
system shutdown should be separately verified on the Pi.

## Rollback

Restore the previously backed-up V1 helper and unit,
then reload the systemd user manager.

The previous GitHub version is available in commit:

`394525ee2e53724de0907a0aa8fa9726d6966a9a`

No MorningUI application source changes are required.

## Scope

This cursor automation does not change:

- MorningUI Python application code
- Native weather QML animations
- LG remote navigation
- TV lift behavior
- Fonts or UI layout
- Display resolution or scaling
