"""CodinX runs only as root (root@localhost or root@<any host>). Non-root is refused."""
import os
import socket
import sys


def check():
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        return
    host = socket.gethostname().split(".")[0]
    sys.stderr.write(
        "CodinX hanya bisa dijalankan sebagai root (root@localhost atau root@host lain).\n"
        f"  terdeteksi: user bukan root @ {host}\n"
    )
    sys.exit(77)
  
