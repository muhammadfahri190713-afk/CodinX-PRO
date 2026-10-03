"""Encrypted API-key storage (stdlib only).

The key lives in a hidden file (~/.codinx/.key.enc, mode 600) encrypted with
an HMAC-SHA256 keystream (encrypt-then-MAC), keyed from this machine's id via
PBKDF2. It stops casual reads and copies to other machines; root on the same
box can still decrypt it.
"""
import base64
import hashlib
import hmac
import os

MAGIC = b"CX1"


def _machine_secret():
    for p in ("/etc/machine-id", "/var/lib/dbus/machine-id"):
        try:
            with open(p) as f:
                v = f.read().strip()
            if v:
                return v.encode()
        except OSError:
            pass
    return os.uname().nodename.encode()


def _keys():
    k = hashlib.pbkdf2_hmac("sha256", _machine_secret(), b"codinx-vault-v1", 200_000, 64)
    return k[:32], k[32:]


def _stream(key, nonce, n):
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hmac.new(key, nonce + ctr.to_bytes(8, "big"), hashlib.sha256).digest()
        ctr += 1
    return bytes(out[:n])


def encrypt(text):
    ek, mk = _keys()
    raw = text.encode()
    nonce = os.urandom(16)
    ct = bytes(a ^ b for a, b in zip(raw, _stream(ek, nonce, len(raw))))
    tag = hmac.new(mk, MAGIC + nonce + ct, hashlib.sha256).digest()
    return base64.b64encode(MAGIC + nonce + ct + tag)


def decrypt(blob):
    ek, mk = _keys()
    data = base64.b64decode(blob)
    if data[:3] != MAGIC or len(data) < 3 + 16 + 32:
        raise ValueError("bad key file")
    nonce, ct, tag = data[3:19], data[19:-32], data[-32:]
    good = hmac.new(mk, MAGIC + nonce + ct, hashlib.sha256).digest()
    if not hmac.compare_digest(tag, good):
        raise ValueError("key file corrupted or from another machine")
    return bytes(a ^ b for a, b in zip(ct, _stream(ek, nonce, len(ct)))).decode()
