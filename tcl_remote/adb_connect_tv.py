import os
import sys
from adb_shell.adb_device import AdbDeviceTcp
from adb_shell.auth.keygen import keygen
from adb_shell.auth.sign_pythonrsa import PythonRSASigner

KEY_PATH = os.path.expanduser("~/.android/adbkey")
if not os.path.exists(KEY_PATH):
    os.makedirs(os.path.dirname(KEY_PATH), exist_ok=True)
    keygen(KEY_PATH)

with open(KEY_PATH) as f:
    priv = f.read()
with open(KEY_PATH + ".pub") as f:
    pub = f.read()

signer = PythonRSASigner(pub, priv)
device = AdbDeviceTcp("192.168.1.6", 5555, default_transport_timeout_s=9.0)

print("Connecting to TCL TV over ADB...")
print("Look at your TV screen! If a popup says 'Allow USB debugging?', check 'Always allow' and click OK.")

try:
    device.connect(rsa_keys=[signer], auth_timeout_s=30)
    print("ADB CONNECTED SUCCESSFULLY!")
    
    # Query TV inputs
    out = device.shell("dumpsys tv_input | grep -i inputid")
    print("--- TV INPUTS DETECTED ---")
    print(out)
    print("--------------------------")
except Exception as e:
    print("Connection error / waiting for approval:", e)
