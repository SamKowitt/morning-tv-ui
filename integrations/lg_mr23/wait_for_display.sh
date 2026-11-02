#!/usr/bin/env bash
# Wait for the logged-in user's Wayland compositor.
UID_VALUE="$(id -u mrkowitt)"

for i in $(seq 1 120); do
    for path in "/run/user/$UID_VALUE"/wayland-*; do
        if [ -S "$path" ]; then
            exit 0
        fi
    done
    sleep 1
done

echo "Wayland display not available" >&2
exit 1
