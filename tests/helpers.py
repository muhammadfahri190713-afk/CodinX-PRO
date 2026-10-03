import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from . import ROOT, mock_proxy

_WRAP = ("import sys; sys.path.insert(0, %r); from cx import guard; guard.check = lambda: None; "
         "from cx.cli import main; sys.exit(main(sys.argv[1:]))") % ROOT


def run_cli(home, cwd, args, env=None, timeout=180):
    """Jalankan CodinX di subproses terisolasi (HOME sendiri), melewati syarat root agar test jalan di CI non-root."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("CODINX_")}
    e.update(HOME=home, NO_COLOR="1")
    e.update(env or {})
    p = subprocess.run([sys.executable, "-c", _WRAP] + list(args), cwd=cwd, env=e, capture_output=True, text=True, timeout=timeout,
                       stdin=subprocess.DEVNULL)
    return p.stdout + p.stderr


def read(path):
    with open(path) as f:
        return f.read()


def run_cli_open_stdin(home, cwd, args, env=None, wait=25, code=None):
    """Seperti cron/CI: stdin berupa pipa TERBUKA yang tak pernah ditulisi (bukan terminal, bukan EOF).
    Mengembalikan (keluaran, selesai_tepat_waktu). `code` = kode Python pengganti (untuk menguji helper ini)."""
    e = {k: v for k, v in os.environ.items() if not k.startswith("CODINX_")}
    e.update(HOME=home, NO_COLOR="1")
    e.update(env or {})
    argv = [sys.executable, "-c", code] if code else [sys.executable, "-c", _WRAP] + list(args)
    p = subprocess.Popen(argv, cwd=cwd, env=e, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    finished = True
    try:
        p.wait(timeout=wait)                      # JANGAN communicate(): itu menutup stdin dan menyembunyikan bug gantung
    except subprocess.TimeoutExpired:
        finished = False
        p.kill()
        p.wait()
    out = p.stdout.read()
    p.stdout.close()
    p.stdin.close()
    return out, finished


class TempDirs:
    def __init__(self, *names):
        self.base = tempfile.mkdtemp(prefix="codinx-t-")
        self.paths = {}
        for n in names:
            self.paths[n] = os.path.join(self.base, n)
            os.makedirs(self.paths[n])

    def __getitem__(self, n):
        return self.paths[n]

    def cleanup(self):
        shutil.rmtree(self.base, ignore_errors=True)


class ProxyCase(unittest.TestCase):
    """Mulai proxy tiruan sekali per kelas test."""
    @classmethod
    def setUpClass(cls):
        cls.srv, cls.port = mock_proxy.start()
        cls.url = f"http://127.0.0.1:{cls.port}/v1"

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()
        cls.srv.server_close()

    def cli(self, home, cwd, model, args, extra=None):
        env = {"CODINX_BASE_URL": self.url, "CODINX_API_KEY": "k", "CODINX_MODEL": model}
        env.update(extra or {})
        return run_cli(home, cwd, ["run", "--no-color"] + list(args), env)
