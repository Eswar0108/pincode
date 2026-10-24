import os
import sys
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

TV_IP = "192.168.1.6"
KEY_PATH = os.path.expanduser("~/.android/adbkey")

def switch_to_av():
    with open(KEY_PATH) as f:
        priv = f.read()
    with open(KEY_PATH + ".pub") as f:
        pub = f.read()

    signer = PythonRSASigner(pub, priv)
    device = AdbDeviceTcp(TV_IP, 5555, default_transport_timeout_s=5.0)
    device.connect(rsa_keys=[signer], auth_timeout_s=5)

    intent_uri = "content://android.media.tv/passthrough/com.tcl.tvinput%2F.TvPassThroughService%2FHW3"
    cmd = f'am start -a android.intent.action.VIEW -d "{intent_uri}" -f 0x10000000'
    print(f"Switching TV to AV...")
    result = device.shell(cmd)
    print("Result:", result.strip())
    device.close()

if __name__ == "__main__":
    switch_to_av()
