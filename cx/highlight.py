"""Syntax highlighting lewat Pygments (salinan vendor di cx/vendor, BSD-2). Gagal/tak tersedia -> None (UI pakai teks polos)."""
import os
import sys

from . import themes as T

_VENDOR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor")
_S = {"ready": None}
STYLE = {"codinx": "monokai", "tokyonight": "material", "catppuccin": "dracula", "gruvbox": "gruvbox-dark",
         "kanagawa": "zenburn", "nord": "nord", "one-dark": "one-dark", "everforest": "gruvbox-dark",
         "ayu": "native", "matrix": "fruity", "system": "native"}
MAX_LINES = 400


def _init():
    if _S["ready"] is None:
        try:
            if os.path.isdir(os.path.join(_VENDOR, "pygments")) and _VENDOR not in sys.path:
                sys.path.insert(0, _VENDOR)
            from pygments import highlight
            from pygments.formatters import Terminal256Formatter, TerminalTrueColorFormatter
            from pygments.lexers import get_lexer_by_name
            _S.update(ready=True, highlight=highlight, lexer=get_lexer_by_name,
                      f256=Terminal256Formatter, ftc=TerminalTrueColorFormatter)
        except Exception:
            _S["ready"] = False
    return _S["ready"]


def available():
    return bool(_init())


def render(code, lang):
    """-> list baris ber-ANSI, atau None bila tidak bisa di-highlight."""
    if not (T.ENABLED and lang and _init()) or code.count("\n") > MAX_LINES:
        return None
    try:
        lexer = _S["lexer"](lang.split()[0].lower().strip("{}."), stripnl=False)
    except Exception:
        return None
    fmt_cls = _S["ftc"] if T.TRUE else _S["f256"]
    try:
        fmt = fmt_cls(style=STYLE.get(T.current(), "monokai"))
    except Exception:
        fmt = fmt_cls(style="default")
    try:
        out = _S["highlight"](code, lexer, fmt)
    except Exception:
        return None
    return out.rstrip("\n").split("\n")
