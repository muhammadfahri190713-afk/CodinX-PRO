import argparse
import json
import os
import sys

from . import __version__, api, config, tiers
from . import themes as T
from .session import Session


def main(argv=None):
    ap = argparse.ArgumentParser(prog="codinx", description="CodinX — agent coding di terminal (Linux, Termux, dan container).")
    ap.add_argument("-V", "--version", action="store_true")
    ap.add_argument("-m", "--model", help="model untuk sesi ini")
    ap.add_argument("--no-color", action="store_true")
    sub = ap.add_subparsers(dest="cmd")
    r = sub.add_parser("run", help="jalankan satu prompt non-interaktif (pakai '-' untuk baca stdin)")
    r.add_argument("message", nargs="+")
    r.add_argument("-m", "--model")
    r.add_argument("-c", "--continue", dest="cont", action="store_true", help="lanjutkan sesi terakhir")
    r.add_argument("--auto", action="store_true", help="auto-izinkan semua tool (hard-deny tetap berlaku)")
    r.add_argument("--plan", action="store_true", help="mode read-only")
    r.add_argument("--format", choices=["text", "json"], default="text")
    r.add_argument("--no-color", action="store_true")
    r.add_argument("--no-probe", action="store_true", help="lewati diagnosa otomatis")
    sub.add_parser("connect", help="atur endpoint + API key")
    sub.add_parser("doctor", help="diagnosa proxy: riwayat percakapan + tool")
    mp = sub.add_parser("models", help="daftar model & paket")
    mp.add_argument("filter", nargs="?", default="")
    sub.add_parser("sessions", help="daftar sesi")
    lp = sub.add_parser("logs", help="tampilkan log debug terbaru (aktifkan: CODINX_DEBUG=1)")
    lp.add_argument("-n", type=int, default=40)
    args = ap.parse_args(argv)

    if args.version:
        print(f"CodinX {__version__}")
        return 0
    if "--no-color" in (argv if argv is not None else sys.argv[1:]):
        T.set_enabled(False)

    from .app import App
    cfg = config.load()
    app = App(cfg)
    if args.model:
        cfg["model"] = args.model

    if args.cmd == "connect":
        return 0 if app.connect_wizard() else 1
    if args.cmd == "doctor":
        if not app.ensure_connected():
            return 2
        app.cmd_doctor("")
        return 0
    if args.cmd == "logs":
        from . import log
        for ln in log.tail(args.n):
            print(ln)
        return 0
    if args.cmd == "models":
        app.ensure_connected()
        _list_models(app, args.filter)
        return 0
    if args.cmd == "sessions":
        rows = [[i["id"], i["title"][:40], i["n"]] for i in Session.list_all()[:30]]
        app.ui.table(["id", "judul", "pesan"], rows, "Sesi")
        return 0
    if args.cmd == "run":
        if not app.ensure_connected():
            return 2
        ok, _, msg = tiers.can_use_model(cfg, cfg["model"])
        if not ok:
            app.ui.err(msg)
            return 3
        app.perms.auto = args.auto
        if args.plan:
            app.ctx.mode = "plan"
        if args.cont:
            prev = Session.latest_for(app.cwd)
            if prev:
                app.set_session(prev)
        text = (sys.stdin.read() if args.message == ["-"] else " ".join(args.message)).strip()
        if text.startswith("/"):                    # /skill web-check ..., /memory, /doctor ... juga jalan di mode run
            app.slash(text)
            return 0
        if args.no_probe:
            cfg["auto_probe"] = False
        app.ui.quiet = args.format == "json"
        if not app.ui.quiet:
            app.maybe_probe()
        final = app.submit(text)
        if args.format == "json":
            print(json.dumps({"session": app.session.id, "model": cfg["model"], "text": final,
                              "tokens": app.session.tokens_total}, ensure_ascii=False))
        else:
            print()
        return 0

    if not sys.stdin.isatty():
        ap.error("mode interaktif butuh terminal. Pakai: codinx run \"pesan\"")
    app.repl()
    return 0


def _list_models(app, flt):
    q = flt.lower()
    cat = list(tiers.catalog())
    known = {m["id"] for m in cat}
    if app.key:
        try:
            cat += [m for m in api.list_model_specs(app.cfg, app.key) if m["id"] not in known]
        except api.ApiError:
            pass
    rows = [[m["name"], m["id"], m["role"], m["trial"] or ""] for m in cat
            if not q or q in m["id"].lower() or q in m["name"].lower() or q == m["role"].lower()]
    app.ui.table(["nama", "backend id", "paket", "trial"], rows, f"{len(rows)} model")
