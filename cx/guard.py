"""Legacy root guard; normal CodinX execution supports regular users and Termux."""
import os
import socket
import sys


def check():
    # Hanya aktif bila instalasi lama memang meminta mode root secara eksplisit.
    if os.environ.get("CODINX_REQUIRE_ROOT", "").lower() not in ("1", "true", "yes"):
        return
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return
    host = socket.gethostname().split(".")[0]
    sys.stderr.write(
        "CodinX hanya bisa dijalankan sebagai root (root@localhost atau root@host lain).\n"
        f"  terdeteksi: user bukan root @ {host}\n"
    )
    sys.exit(77)
