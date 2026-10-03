"""Colour themes (names mirror opencode's built-ins) + truecolor/256 fallback."""
import os
import sys


def _t(accent, accent2, text, muted, ok, warn, err, info):
    return dict(accent=accent, accent2=accent2, text=text, muted=muted,
                ok=ok, warn=warn, err=err, info=info)


THEMES = {
    "codinx":     _t("#8B7CFF", "#22E6C4", "#E8E8F2", "#7C7C96", "#5CF28E", "#F5E27A", "#FF6B7A", "#5CC8FF"),
    "tokyonight": _t("#7AA2F7", "#BB9AF7", "#C0CAF5", "#565F89", "#9ECE6A", "#E0AF68", "#F7768E", "#7DCFFF"),
    "catppuccin": _t("#CBA6F7", "#89DCEB", "#CDD6F4", "#6C7086", "#A6E3A1", "#F9E2AF", "#F38BA8", "#89B4FA"),
    "gruvbox":    _t("#FE8019", "#B8BB26", "#EBDBB2", "#928374", "#B8BB26", "#FABD2F", "#FB4934", "#83A598"),
    "kanagawa":   _t("#7E9CD8", "#957FB8", "#DCD7BA", "#727169", "#98BB6C", "#E6C384", "#E82424", "#7FB4CA"),
    "nord":       _t("#88C0D0", "#81A1C1", "#ECEFF4", "#616E88", "#A3BE8C", "#EBCB8B", "#BF616A", "#5E81AC"),
    "one-dark":   _t("#61AFEF", "#C678DD", "#ABB2BF", "#5C6370", "#98C379", "#E5C07B", "#E06C75", "#56B6C2"),
    "everforest": _t("#A7C080", "#7FBBB3", "#D3C6AA", "#859289", "#A7C080", "#DBBC7F", "#E67E80", "#83C092"),
    "ayu":        _t("#FFB454", "#39BAE6", "#B3B1AD", "#626A73", "#AAD94C", "#FFB454", "#F07178", "#59C2FF"),
    "matrix":     _t("#00FF41", "#00D9A0", "#B6FFB6", "#2E7D32", "#00FF41", "#CCFF00", "#FF3131", "#00D9A0"),
    "system":     _t("ansi:35", "ansi:36", "ansi:39", "ansi:90", "ansi:32", "ansi:33", "ansi:31", "ansi:34"),
}

RESET = "\033[0m"
BOLD = "\033[1m"
UNBOLD = "\033[22m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
YELLOW_BRIGHT = "\033[1;93m"   # permission prompt: always bright yellow

_cur = "codinx"
ENABLED = sys.stdout.isatty() and not os.environ.get("NO_COLOR")
TRUE = os.environ.get("COLORTERM", "").lower() in ("truecolor", "24bit")


def set_enabled(v):
    global ENABLED
    ENABLED = bool(v)


def names():
    return list(THEMES)


def current():
    return _cur


def set_theme(name):
    global _cur
    if name in THEMES:
        _cur = name
        return True
    return False


def _fg(spec):
    if spec.startswith("ansi:"):
        return "\033[%sm" % spec[5:]
    h = spec.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    if TRUE:
        return f"\033[38;2;{r};{g};{b}m"

    def q(v):
        return 0 if v < 48 else 1 if v < 115 else (v - 35) // 40
    return f"\033[38;5;{16 + 36 * q(r) + 6 * q(g) + q(b)}m"


def fg(role):
    return _fg(THEMES[_cur][role]) if ENABLED else ""


def hexfg(hexv):
    return _fg(hexv) if ENABLED else ""


def c(role, text, bold=False, dim=False, italic=False):
    if not ENABLED:
        return text
    pre = (BOLD if bold else "") + (DIM if dim else "") + (ITALIC if italic else "")
    return f"{pre}{fg(role)}{text}{RESET}"


def lerp_hex(a, b, t):
    a, b = a.lstrip("#"), b.lstrip("#")
    ca = [int(a[i:i + 2], 16) for i in (0, 2, 4)]
    cb = [int(b[i:i + 2], 16) for i in (0, 2, 4)]
    return "#%02X%02X%02X" % tuple(round(x + (y - x) * t) for x, y in zip(ca, cb))


def gradient(text, t0=0.0, t1=1.0):
    """Colour each char between accent and accent2 (falls back to accent for ansi themes)."""
    th = THEMES[_cur]
    if not ENABLED or th["accent"].startswith("ansi:"):
        return c("accent", text, bold=True)
    out = []
    n = max(len(text) - 1, 1)
    for i, ch in enumerate(text):
        if ch == " ":
            out.append(ch)
            continue
        out.append(_fg(lerp_hex(th["accent"], th["accent2"], t0 + (t1 - t0) * i / n)) + ch)
    return BOLD + "".join(out) + RESET
