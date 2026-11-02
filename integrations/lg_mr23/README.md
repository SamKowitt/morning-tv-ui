# LG MR23 Raspberry Pi 5 integration

Working LG Magic Remote Bluetooth integration for MorningUI.

- Low-lag Bluetooth input and persistent LG webOS connection
- Automatic routing between LG TV and MorningUI
- Scroll wheel: one Up/Down action per tick
- Green: launch/restart a single MorningUI instance
- Input: switch directly to HDMI 1
- Input Hub: Bluetooth button code 804500
- Blue/Red: existing TV lift controller commands
- Bluetooth bridge: automatic systemd startup
- MorningUI: on-demand launch, not automatic at boot

The deployed service files use the Raspberry Pi's local paths.

Local authentication files, webOS pairing credentials, logs,
runtime sockets and virtual environments are not included.
