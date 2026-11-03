import asyncio
import sys
from bscpylgtv import WebOsClient

async def main():
    client = await WebOsClient.create(
        "192.168.86.43",
        states=[],
        ping_interval=None
    )
    await asyncio.wait_for(client.connect(), timeout=12)

    async def on_app(app):
        if app:
            print("APP " + app, flush=True)

    try:
        await asyncio.wait_for(client.subscribe_current_app(on_app), timeout=12)
        await on_app(await asyncio.wait_for(client.get_current_app(), timeout=8))
        print("READY", flush=True)

        while True:
            line = await asyncio.to_thread(sys.stdin.readline)
            if not line:
                break

            button = line.strip()
            if not button:
                continue

            try:
                if button == "__SET_HDMI1__":
                    await asyncio.wait_for(client.set_input("HDMI_1"), timeout=8)
                else:
                    await asyncio.wait_for(client.button(button), timeout=8)
                print("SENT " + button, flush=True)
            except Exception as exc:
                # MR23_WEBOS_RECOVERY_V1
                print("ERROR " + button + ": " + str(exc),
                      flush=True)

                message = str(exc).lower()
                connection_error = (
                    isinstance(
                        exc,
                        (asyncio.TimeoutError, ConnectionError, OSError)
                    )
                    or any(
                        word in message
                        for word in (
                            "connection closed",
                            "not connected",
                            "websocket",
                            "timed out",
                            "connection lost"
                        )
                    )
                )

                if connection_error:
                    print(
                        "WEBOS CONNECTION UNHEALTHY - RECONNECTING",
                        flush=True
                    )
                    raise
    finally:
        # MR23_WEBOS_RECOVERY_V1
        try:
            await asyncio.wait_for(
                client.disconnect(),
                timeout=3
            )
        except Exception as exc:
            print(
                "WEBOS DISCONNECT WARNING:",
                repr(exc),
                flush=True
            )

while True:
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        break
    except Exception as exc:
        print("WEBOS RETRY: " + repr(exc), flush=True)
        import time
        time.sleep(5)
    else:
        break
