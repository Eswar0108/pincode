import asyncio
import os
import sys
from androidtvremote2 import AndroidTVRemote

CERTS_DIR = os.path.dirname(os.path.abspath(__file__))
CERT_FILE = os.path.join(CERTS_DIR, "cert.pem")
KEY_FILE = os.path.join(CERTS_DIR, "key.pem")
TV_IP = "192.168.1.6"

async def main():
    remote = AndroidTVRemote(
        client_name="MacBook Remote",
        certfile=CERT_FILE,
        keyfile=KEY_FILE,
        host=TV_IP,
    )
    
    print("Connecting to TV...")
    is_connected = await remote.async_connect()
    if not is_connected:
        print("Could not connect to TV. Make sure TV is on.")
        return

    print("Connected! Sending command to switch to AV (Composite)...")
    # Send KEYCODE_TV_INPUT_COMPOSITE_1
    remote.send_key_command("KEYCODE_TV_INPUT_COMPOSITE_1")
    await asyncio.sleep(1)
    remote.disconnect()
    print("Command sent successfully!")

if __name__ == "__main__":
    asyncio.run(main())
