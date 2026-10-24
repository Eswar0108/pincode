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
    
    await remote.async_generate_cert_if_missing()
    print("Initiating pairing with TCL TV at", TV_IP, "...")
    try:
        await remote.async_start_pairing()
        print("SUCCESS: A 6-character code is now displayed on your TV screen!")
        print("Please check your TV screen now.")
    except Exception as e:
        print("Error during pairing initiation:", e)
        sys.exit(1)

    code = input("Enter the 6-character code from your TV: ").strip()
    try:
        await remote.async_finish_pairing(code)
        print("Pairing successful! Certificates saved.")
    except Exception as e:
        print("Failed to complete pairing:", e)
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
