# Morning TV UI — Raspberry Pi Deployment

This folder is stored inside the Morning TV UI GitHub repository.

## Fresh Pi prerequisites

1. Install Raspberry Pi OS Desktop.
2. Configure the user, hostname, Wi-Fi, and SSH.
3. Copy or clone the Morning TV UI project to:

   /home/mrkowitt/morning-tv-ui

## Configure a fresh Pi

Run from the Mac:

   cd /Users/lindsaykowitt/Desktop/MorningUI/morning-tv-ui/morning-tv-ui-local-deploy
   ./deploy_fresh_pi.sh fetchnews.local mrkowitt

This automatically configures:

- Chromium
- Python .venv3
- Project requirements
- Exact Mac fonts
- Emoji fonts
- QT_FONT_DPI=72
- 1280x720 resolution
- Wayland scale 1.0
- SSH and VNC
- Automatic terminal virtual-environment activation
- The fetchnews launch command

## Verify the Pi

   ./verify_pi.sh fetchnews.local mrkowitt

## Launch Morning TV UI on the Pi

   fetchnews

## Repository assets

The private-fonts and backups directories are included in this repository. Large font and archive files are tracked with Git LFS.
