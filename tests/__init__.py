"""Suite test CodinX. Jalankan:  python3 -m unittest discover -s tests -t . -v

HOME diarahkan ke folder sementara SEBELUM modul cx diimpor (path data dihitung saat impor), sehingga test tidak
menyentuh ~/.codinx milik pengguna.
"""
import atexit
import os
import shutil
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)
_HOME = tempfile.mkdtemp(prefix="codinx-test-home-")
os.environ["HOME"] = _HOME
os.environ["NO_COLOR"] = "1"
for _k in list(os.environ):
    if _k.startswith("CODINX_"):
        del os.environ[_k]
atexit.register(shutil.rmtree, _HOME, ignore_errors=True)
