import asyncio
import sys
from bscpylgtv import WebOsClient

async def main():
    client = await WebOsClient.create(
        "192.168.86.43",
        states=[],
        ping_interval=None
    )
    await client.connect()

    async def on_app(app):
        if app:
            print("APP " + app, flush=True)

    try:
        await client.subscribe_current_app(on_app)
        await on_app(await client.get_current_app())
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
                    await client.set_input("HDMI_1")
                else:
                    await client.button(button)
                print("SENT " + button, flush=True)
            except Exception as exc:
                print("ERROR " + button + ": " + str(exc),
                      flush=True)
    finally:
        await client.disconnect()

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
