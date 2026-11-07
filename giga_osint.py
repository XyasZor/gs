#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GIGA OSINT v2.0 - Toolkit OSINT Terminal (Windows / Linux / macOS / Termux)
Only Education. | Github : XyasZor | Jangan Disalah Gunakan!

Jalankan : python3 giga_osint.py          (Windows: python giga_osint.py)
Opsi     : --cepat   tanpa animasi         --ascii  tanpa simbol unicode
           --polos   tanpa warna           --bantuan  tampilkan bantuan ini
Catatan  : Gunakan hanya untuk tujuan sah, edukasi, dan target milik sendiri / berizin tertulis.
"""
import os, sys, re, json, ssl, time, shutil, socket, hashlib, platform, subprocess, webbrowser
import getpass, smtplib, random, string, datetime, base64, ipaddress, importlib, shlex
import threading, atexit, tarfile, zipfile, sysconfig, tempfile, unicodedata, math
import urllib.request, urllib.parse, urllib.error
import email.message, email.utils
from html.parser import HTMLParser
from xml.etree import ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

APP = "Giga OSINT"
VERSION = "3.0"
HOME = os.path.expanduser("~")
DATA_DIR = os.path.join(HOME, ".giga_osint")
TOOLS_DIR = os.path.join(DATA_DIR, "tools")
BIN_DIR = os.path.join(TOOLS_DIR, "bin")
OUT_DIR = os.path.join(DATA_DIR, "hasil")
CONF_FILE = os.path.join(DATA_DIR, "config.json")
IS_WIN = os.name == "nt"
IS_MAC = sys.platform == "darwin"
IS_TERMUX = ("com.termux" in os.environ.get("PREFIX", "")) or os.path.isdir("/data/data/com.termux")
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
      "Chrome/124.0 Safari/537.36")

ARGS = set(a.lower() for a in sys.argv[1:])
USAGE = """Giga OSINT v%s  -  Toolkit OSINT terminal
Pemakaian : python3 giga_osint.py [opsi]
  --cepat    matikan animasi (cocok untuk koneksi SSH lambat)
  --ascii    pakai simbol ASCII saja (terminal lama)
  --polos    matikan warna
  --bantuan  tampilkan bantuan ini
Di dalam tool: ketik NOMOR lalu Enter. 0 = kembali / keluar. /kata = cari. h = panduan.""" % VERSION
if ARGS & {"--bantuan", "--help", "-h"}:
    print(USAGE)
    sys.exit(0)

TTY = bool(getattr(sys.stdout, "isatty", lambda: False)())
if IS_WIN:
    os.system("")  # aktifkan ANSI di Windows 10+
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

# ----------------------------------------------------------------- pengaturan
DEFAULT_CFG = {"anim": True, "speed": "normal", "mask": True, "theme": "neon"}


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    try:
        with open(CONF_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            cfg.update({k: v for k, v in data.items() if k in DEFAULT_CFG})
    except Exception:
        pass
    return cfg


def save_cfg():
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(CONF_FILE, "w", encoding="utf-8") as f:
            json.dump(CFG, f, indent=2)
    except Exception:
        pass


CFG = load_cfg()
MASK_PASSWORD = bool(CFG.get("mask", True))   # True = password hasil kebocoran disamarkan
SPEEDS = {"cepat": 0.45, "normal": 1.0, "lambat": 1.7}
ANIM = bool(CFG.get("anim", True)) and TTY and "--cepat" not in ARGS and not os.environ.get("GIGA_NO_ANIM")

# ----------------------------------------------------------------- kemampuan terminal
def _detect_color():
    forced = os.environ.get("GIGA_COLOR", "")
    if forced in ("0", "1", "2", "3"):
        return int(forced)
    if "--polos" in ARGS or os.environ.get("NO_COLOR") or not TTY or os.environ.get("TERM") == "dumb":
        return 0
    ct = os.environ.get("COLORTERM", "").lower()
    if "truecolor" in ct or "24bit" in ct:
        return 3
    if IS_WIN or IS_TERMUX or os.environ.get("WT_SESSION"):
        return 3
    if os.environ.get("TERM_PROGRAM") in ("vscode", "iTerm.app", "WezTerm", "Apple_Terminal", "ghostty"):
        return 3 if os.environ.get("TERM_PROGRAM") != "Apple_Terminal" else 2
    if "256" in os.environ.get("TERM", ""):
        return 2
    return 1


def _detect_unicode():
    if "--ascii" in ARGS or os.environ.get("GIGA_ASCII"):
        return False
    enc = (getattr(sys.stdout, "encoding", "") or "").lower()
    if "utf" not in enc:
        return False
    return os.environ.get("TERM", "") not in ("linux", "vt100", "dumb")


COLOR_LVL = _detect_color()
UNI = _detect_unicode()

ANSI_RE = re.compile(r"\x1b\[[0-9;?]*[A-Za-z]")


def _rgb256(r, g, b):
    if abs(r - g) < 10 and abs(g - b) < 10:
        gray = int(round((r - 8) / 247.0 * 24))
        if gray <= 0:
            return 16
        if gray >= 24:
            return 231
        return 232 + gray - 1
    return 16 + 36 * int(round(r / 255.0 * 5)) + 6 * int(round(g / 255.0 * 5)) + int(round(b / 255.0 * 5))


def _rgb16(r, g, b):
    m = max(r, g, b)
    if m < 70:
        return 90
    code = 30 + (1 if r > m * 0.55 else 0) + (2 if g > m * 0.55 else 0) + (4 if b > m * 0.55 else 0)
    if code == 30:
        code = 37
    return code + 60 if m > 170 else code


def fg(r, g, b):
    if COLOR_LVL >= 3:
        return "\033[38;2;%d;%d;%dm" % (r, g, b)
    if COLOR_LVL == 2:
        return "\033[38;5;%dm" % _rgb256(r, g, b)
    if COLOR_LVL == 1:
        return "\033[%dm" % _rgb16(r, g, b)
    return ""


# Warna dasar (nama lama dipertahankan agar semua modul tetap bekerja)
R = "\033[0m" if COLOR_LVL else ""
B = "\033[1m" if COLOR_LVL else ""
Y = "\033[93m" if COLOR_LVL else ""          # kuning: nomor fitur
W = "\033[97m" if COLOR_LVL else ""          # putih: judul & nama fitur
D = fg(128, 140, 165)                        # abu-abu: keterangan
CY = fg(0, 214, 255)
G = fg(80, 250, 140)
RD = fg(255, 90, 100)
MG = fg(200, 130, 255)
BL = fg(110, 160, 255)

THEMES = {
    "neon": [(0, 240, 255), (48, 140, 255), (140, 90, 255), (255, 70, 200)],
    "aurora": [(0, 255, 170), (0, 200, 255), (90, 120, 255), (190, 90, 255)],
    "senja": [(255, 214, 10), (255, 140, 40), (255, 80, 100), (200, 60, 220)],
    "matriks": [(0, 255, 120), (0, 215, 70), (0, 170, 50), (140, 255, 170)],
    "es": [(235, 242, 255), (165, 182, 215), (105, 124, 165), (235, 242, 255)],
}
THEME_LABEL = {"neon": "Neon Siber", "aurora": "Aurora", "senja": "Senja", "matriks": "Matriks", "es": "Es (monokrom)"}


def stops():
    return THEMES.get(CFG.get("theme"), THEMES["neon"])


def grad(t):
    st = stops()
    t = 0.0 if t < 0 else 1.0 if t > 1 else t
    n = len(st) - 1
    i = min(int(t * n), n - 1)
    f = t * n - i
    a, b = st[i], st[i + 1]
    return (int(a[0] + (b[0] - a[0]) * f), int(a[1] + (b[1] - a[1]) * f), int(a[2] + (b[2] - a[2]) * f))


def gc(t):
    """Kode warna gradien pada posisi t (0..1)."""
    return fg(*grad(t))


def gtext(s, t0=0.0, t1=1.0, bold=False):
    """Teks dengan gradien warna per karakter."""
    if not COLOR_LVL:
        return s
    n = max(1, len(s) - 1)
    out = [B] if bold else []
    for i, ch in enumerate(s):
        out.append(ch if ch == " " else gc(t0 + (t1 - t0) * i / n) + ch)
    out.append(R)
    return "".join(out)


# ----------------------------------------------------------------- glyph (unicode / ascii)
if UNI:
    GL = dict(tl="╭", tr="╮", bl="╰", br="╯", h="─", v="│", jl="┤", jr="├", dot="●", ring="○", info="◆",
              warn="▲", err="■", ok="●", arr="▸", prompt="❯", sep="·", bar_f="█", bar_e="░", ell="…",
              rule="━", bullet="▪", up="▲", cross="╳")
    SPIN = "⠋⠙⠹⠸⠼⠴⠦⠧⠇⠏"
else:
    GL = dict(tl="+", tr="+", bl="+", br="+", h="-", v="|", jl="[", jr="]", dot="*", ring="o", info="i",
              warn="!", err="x", ok="+", arr=">", prompt=">", sep="-", bar_f="#", bar_e=".", ell="...",
              rule="=", bullet="-", up="^", cross="x")
    SPIN = "|/-\\"


# ----------------------------------------------------------------- ukuran & teks
def term_w():
    return shutil.get_terminal_size((80, 24)).columns


def term_h():
    return shutil.get_terminal_size((80, 24)).lines


def content_w():
    return max(34, min(term_w() - 2, 122))


def _cw(ch):
    o = ord(ch)
    if o < 32 or 0x7F <= o < 0xA0:
        return 0
    if unicodedata.combining(ch):
        return 0
    return 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1


def vlen(s):
    return sum(_cw(c) for c in ANSI_RE.sub("", s))


def trunc(s, w):
    """Potong teks polos (tanpa ANSI) ke lebar w dengan elipsis."""
    if vlen(s) <= w:
        return s
    out, n = [], 0
    for ch in s:
        k = _cw(ch)
        if n + k > w - len(GL["ell"]):
            break
        out.append(ch)
        n += k
    return "".join(out) + GL["ell"]


def padr(s, w):
    return s + " " * max(0, w - vlen(s))


def center(s):
    return " " * max(0, (term_w() - vlen(s)) // 2) + s


def _wrap_one(s, width):
    lines, cur, cw, active = [], "", 0, ""
    lead = True   # indentasi di awal paragraf dipertahankan (untuk indentasi gantung)
    for p in re.split(r"(\x1b\[[0-9;?]*[A-Za-z])", s):
        if not p:
            continue
        if p[0] == "\x1b":
            cur += p
            active = "" if p == "\033[0m" else active + p
            continue
        for w in re.findall(r"\s+|\S+", p):
            if w.isspace():
                if cw == 0:
                    if lead and len(w) < width // 2:
                        cur += w
                        cw += len(w)
                    continue
                if cw + len(w) <= width:
                    cur += w
                    cw += len(w)
                else:
                    lines.append(cur + R)
                    cur, cw = active, 0
                continue
            lead = False
            wl = vlen(w)
            if wl > width:
                if cw > 0:
                    lines.append(cur + R)
                    cur, cw = active, 0
                for ch in w:
                    k = _cw(ch)
                    if cw + k > width:
                        lines.append(cur + R)
                        cur, cw = active, 0
                    cur += ch
                    cw += k
                continue
            if cw + wl > width and cw > 0:
                lines.append(cur.rstrip() + R)
                cur, cw = active, 0
            cur += w
            cw += wl
    lines.append(cur)
    return lines


def wrap_ansi(s, width):
    out = []
    for para in str(s).split("\n"):
        out.extend(_wrap_one(para, max(8, width)))
    return out


# ----------------------------------------------------------------- layar & animasi
_cursor_hidden = False


def hide_cursor():
    global _cursor_hidden
    if TTY and COLOR_LVL:
        sys.stdout.write("\033[?25l")
        sys.stdout.flush()
        _cursor_hidden = True


def show_cursor():
    global _cursor_hidden
    if TTY:
        sys.stdout.write("\033[?25h" + R)
        sys.stdout.flush()
    _cursor_hidden = False


atexit.register(show_cursor)


def nap(sec):
    if ANIM and sec > 0:
        time.sleep(sec * SPEEDS.get(CFG.get("speed", "normal"), 1.0))


def clear(full=False):
    if TTY:
        sys.stdout.write("\033[2J\033[3J\033[H" if full else "\033[2J\033[H")
        sys.stdout.flush()
    else:
        print()


def emit(lines, delay=0.0):
    """Cetak banyak baris; bila animasi aktif, muncul bertahap (efek wipe)."""
    if not (ANIM and delay > 0):
        sys.stdout.write("\n".join(lines) + "\n")
        sys.stdout.flush()
        return
    for ln in lines:
        sys.stdout.write(ln + "\n")
        sys.stdout.flush()
        nap(delay)


def typewrite(s, delay=0.006, color=""):
    if not ANIM:
        sys.stdout.write(color + s + R + "\n")
        return
    sys.stdout.write(color)
    for ch in s:
        sys.stdout.write(ch)
        sys.stdout.flush()
        nap(delay)
    sys.stdout.write(R + "\n")


class Spinner(object):
    """Spinner animasi + waktu berjalan. Pakai:  with Spinner('Memeriksa...'): ..."""

    def __init__(self, label):
        self.label = label
        self._stop = threading.Event()
        self._th = None
        self._t0 = 0.0

    def _run(self):
        i = 0
        while not self._stop.is_set():
            el = int(time.time() - self._t0)
            sys.stdout.write("\r\033[K  %s%s%s %s%s%s %s%d:%02d%s" % (
                gc((i % 20) / 20.0), SPIN[i % len(SPIN)], R, W, self.label, R, D, el // 60, el % 60, R))
            sys.stdout.flush()
            i += 1
            self._stop.wait(0.08)

    def __enter__(self):
        self._t0 = time.time()
        if TTY and COLOR_LVL:
            hide_cursor()
            self._th = threading.Thread(target=self._run, daemon=True)
            self._th.start()
        else:
            print("  ... " + self.label)
        return self

    def __exit__(self, *a):
        self._stop.set()
        if self._th:
            self._th.join(timeout=1)
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()
            show_cursor()
        return False


def bar(frac, width=20, t0=0.0, t1=1.0):
    frac = 0.0 if frac < 0 else 1.0 if frac > 1 else frac
    n = int(round(frac * width))
    full = "".join(gc(t0 + (t1 - t0) * i / max(1, width - 1)) + GL["bar_f"] for i in range(n))
    return full + D + GL["bar_e"] * (width - n) + R


def hline(n, t0=0.0, t1=1.0, ch=None):
    return gtext((ch or GL["h"]) * max(0, n), t0, t1)


# ----------------------------------------------------------------- banner
BIG = {
    "G": [" ██████╗ ", "██╔════╝ ", "██║  ███╗", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "I": ["██╗", "██║", "██║", "██║", "██║", "╚═╝"],
    "A": [" █████╗ ", "██╔══██╗", "███████║", "██╔══██║", "██║  ██║", "╚═╝  ╚═╝"],
    "O": [" ██████╗ ", "██╔═══██╗", "██║   ██║", "██║   ██║", "╚██████╔╝", " ╚═════╝ "],
    "S": ["███████╗", "██╔════╝", "███████╗", "╚════██║", "███████║", "╚══════╝"],
    "N": ["███╗   ██╗", "████╗  ██║", "██╔██╗ ██║", "██║╚██╗██║", "██║ ╚████║", "╚═╝  ╚═══╝"],
    "T": ["████████╗", "╚══██╔══╝", "   ██║   ", "   ██║   ", "   ██║   ", "   ╚═╝   "],
}
SMALL = {
    "G": ["▄▀▀▀", "█ ▀█", "▀▄▄▀"], "I": ["▀█▀", " █ ", "▄█▄"], "A": ["▄▀▀▄", "█▀▀█", "█  █"],
    "O": ["▄▀▀▄", "█  █", "▀▄▄▀"], "S": ["▄▀▀▀", "▀▀▀▄", "▄▄▄▀"], "N": ["█▄ █", "█ ▀█", "█  █"],
    "T": ["▀█▀", " █ ", " █ "],
}
SUBTITLE = "Only Education. | Github: XyasZor | Jangan Disalah Gunakan!"


def _word(font, word, gap):
    h = len(next(iter(font.values())))
    return [(" " * gap).join(font[c][r] for c in word) for r in range(h)]


def banner_rows():
    """Pilih banner sesuai lebar/tinggi terminal. Mengembalikan baris teks polos."""
    w, h = term_w(), term_h()
    if w >= 76 and h >= 26:
        a, b = _word(BIG, "GIGA", 0), _word(BIG, "OSINT", 0)
        rows = [x + "   " + y for x, y in zip(a, b)]
    elif w >= 46:
        a, b = _word(SMALL, "GIGA", 1), _word(SMALL, "OSINT", 1)
        rows = [x + "   " + y for x, y in zip(a, b)]
    else:
        rows = ["G I G A   O S I N T"]
    if not UNI:
        rows = [re.sub(r"[█▄▀]", "#", re.sub(r"[╗╔╝╚║═]", " ", r)) for r in rows]
    width = max(len(r) for r in rows)
    return [r.ljust(width) for r in rows]



def banner_frame(rows, reveal=None, shimmer=None, seed=7):
    """Satu frame banner: reveal = 0..1 (efek dekode), shimmer = posisi kilau."""
    rnd = random.Random(seed)
    width = len(rows[0])
    height = len(rows)
    pad = " " * max(0, (term_w() - width) // 2)
    glyphs = "01<>/\\|#%&$?" if not UNI else "░▒▓█▀▄▌▐01<>/"
    out = []
    for y, row in enumerate(rows):
        buf = []
        for x, ch in enumerate(row):
            if ch == " ":
                buf.append(" ")
                continue
            t = (x / float(max(1, width - 1))) * 0.82 + (y / float(max(1, height))) * 0.18
            if reveal is not None:
                th = (x / float(max(1, width - 1))) * 0.8 + rnd.random() * 0.2
                if th > reveal:
                    buf.append(fg(70, 85, 120) + rnd.choice(glyphs))
                    continue
            r_, g_, b_ = grad(t)
            if shimmer is not None:
                k = max(0.0, 1.0 - abs((x + y * 3) - shimmer) / 9.0)
                k = k * k * 0.9
                r_, g_, b_ = int(r_ + (255 - r_) * k), int(g_ + (255 - g_) * k), int(b_ + (255 - b_) * k)
            buf.append(fg(r_, g_, b_) + B + ch)
        out.append(pad + "".join(buf) + R)
    return out


def banner_static():
    return banner_frame(banner_rows())


def banner_play(rows):
    """Animasi: dekode huruf lalu kilau menyapu. Selesai dengan banner statis."""
    n = len(rows)
    if not (ANIM and COLOR_LVL):
        emit(banner_frame(rows))
        return
    hide_cursor()
    try:
        steps = 16
        for f in range(steps + 1):
            sys.stdout.write("\n".join(banner_frame(rows, reveal=f / float(steps), seed=f)) + "\n")
            sys.stdout.write("\033[%dA" % n)
            sys.stdout.flush()
            nap(0.028)
        width = len(rows[0]) + n * 3
        for pos in range(-8, width + 10, 3):
            sys.stdout.write("\n".join(banner_frame(rows, shimmer=pos)) + "\n")
            sys.stdout.write("\033[%dA" % n)
            sys.stdout.flush()
            nap(0.012)
    except KeyboardInterrupt:
        pass
    finally:
        sys.stdout.write("\n".join(banner_frame(rows)) + "\n")
        sys.stdout.flush()
        show_cursor()


def subtitle_lines():
    """Subjudul putih; dipecah dua baris bila terminal sempit."""
    if term_w() >= len(SUBTITLE) + 2:
        return [center(W + SUBTITLE + R)]
    a, b = SUBTITLE.rsplit(" | ", 1)
    return [center(W + a + R), center(W + b + R)]


def rule_line():
    n = max(10, min(term_w() - 4, 100))
    return center(hline(n, 0, 1, GL["rule"]))


def hud_line():
    tools_ok, tools_all = tool_counts()
    bits = ["%s%s%s %sSISTEM ONLINE%s" % (G, GL["dot"], R, G, R),
            "%sv%s%s" % (D, VERSION, R),
            "%s%s%s" % (D, platform.system() or "OS", R),
            "%sPython %s%s" % (D, platform.python_version(), R),
            "%sTool repo %d/%d%s" % (D, tools_ok, tools_all, R)]
    sep = " %s%s%s " % (D, GL["sep"], R)
    line = sep.join(bits)
    for keep in (bits[:2] + bits[4:], bits[:1] + bits[4:], bits[:1]):
        if vlen(line) <= term_w() - 2:
            break
        line = sep.join(keep)
    return center(line)


def brand_header(trail=None):
    """Header ringkas untuk layar di dalam kategori."""
    head = "%s%s%s %s %s%s%s" % (gc(0.0), GL["tl"], R, gtext("GIGA OSINT", 0.0, 1.0, True), gc(1.0), GL["tr"], R)
    crumb = ""
    if trail:
        crumb = "  " + (" %s%s%s " % (D, GL["arr"], R)).join(W + t + R for t in trail)
    lines = ["", head + crumb, hline(content_w(), 0, 1)]
    return lines


# ----------------------------------------------------------------- komponen tampilan
def panel(title, lines, color=None, width=None, footer=None):
    """Panel dengan bingkai gradien. 'lines' boleh berisi kode warna ANSI."""
    w = width or content_w()
    inner = w - 4
    if title and vlen(title) + 4 > w - 4:
        title = trunc(title, max(4, w - 8))
    if footer and (vlen(title or "") + 4 + vlen(footer) + 4 > w - 4):
        footer = None
    t_part = ""
    if title:
        t_part = "%s %s%s%s%s %s" % (gc(0.0) + GL["jl"], R, W + B, title, R, gc(0.0) + GL["jr"])
        t_vis = vlen(title) + 4
    else:
        t_vis = 0
    f_part, f_vis = "", 0
    if footer:
        f_part = "%s %s%s%s %s" % (gc(1.0) + GL["jl"], R + D, footer, R, gc(1.0) + GL["jr"])
        f_vis = vlen(footer) + 4
    fill = max(1, w - 4 - t_vis - f_vis)
    top = gc(0.0) + GL["tl"] + GL["h"] + R + t_part + hline(fill, 0.08, 0.92) + f_part + gc(1.0) + GL["h"] + GL["tr"] + R
    lc, rc = gc(0.0) + GL["v"] + R, gc(1.0) + GL["v"] + R
    out = [top]
    for ln in lines:
        for sub in (wrap_ansi(ln, inner) if ln else [""]):
            out.append("%s %s%s %s" % (lc, sub, " " * max(0, inner - vlen(sub)), rc))
    out.append(gc(0.0) + GL["bl"] + R + hline(w - 2, 0.0, 1.0) + gc(1.0) + GL["br"] + R)
    return out


def box(title, lines, color=None):
    """Kompatibel dengan kode lama: cetak panel."""
    sys.stdout.write("\n".join(panel(title, lines)) + "\n")
    sys.stdout.flush()


def _msg(glyph, color, text, tcolor=""):
    w = max(20, term_w() - 6)
    parts = wrap_ansi(text, w)
    out = ["  %s%s%s %s%s%s" % (color, glyph, R, tcolor, parts[0], R)]
    for p in parts[1:]:
        out.append("    %s%s%s" % (tcolor, p, R))
    print("\n".join(out))


def p_ok(t):
    _msg(GL["ok"], G, t, W)


def p_info(t):
    _msg(GL["info"], CY, t, W)


def p_warn(t):
    _msg(GL["warn"], Y, t, W)


def p_err(t):
    _msg(GL["err"], RD, t, W)


def kv(k, v, w=22):
    if v is None or v == "":
        v = "-"
    w = min(w, max(10, term_w() // 3))
    avail = max(12, term_w() - w - 6)
    lines = wrap_ansi(str(v), avail)
    print("  %s%-*s%s %s%s%s %s%s%s" % (CY, w, trunc(str(k), w), R, D, GL["v"], R, W, lines[0], R))
    for extra in lines[1:]:
        print("  %s %s %s%s%s" % (" " * w, D + GL["v"] + R, W, extra, R))


def sec(t):
    n = max(6, min(term_w() - vlen(t) - 8, 70))
    print("\n  %s%s%s %s%s%s%s %s" % (gc(0.0), GL["info"], R, W, B, t, R, hline(n, 0.1, 1.0)))


def hint_bar(pairs):
    """pairs = [(tombol, keterangan)] -> satu atau beberapa baris petunjuk."""
    cells = ["%s%s%s %s%s%s" % (Y, k, R, D, d, R) for k, d in pairs]
    sep = "  %s%s%s  " % (D, GL["sep"], R)
    lines, cur = [], ""
    for c in cells:
        cand = c if not cur else cur + sep + c
        if vlen(cand) > term_w() - 3 and cur:
            lines.append(cur)
            cur = c
        else:
            cur = cand
    if cur:
        lines.append(cur)
    return ["  " + l for l in lines]


# ----------------------------------------------------------------- input
try:
    import readline  # noqa: F401  (riwayat & edit baris di Linux/Termux)
    HAS_RL = True
except ImportError:
    HAS_RL = False


def rl(s):
    """Bungkus kode warna agar readline tidak salah menghitung lebar prompt."""
    if IS_WIN or not HAS_RL or not sys.stdin.isatty():
        return s
    return re.sub(r"(\x1b\[[0-9;]*m)", "\001\\1\002", s)


def ask(question=""):
    """Baca input. Mengembalikan None bila EOF / Ctrl+C."""
    try:
        if question:
            for i, ln in enumerate(wrap_ansi(question, max(20, term_w() - 6))):
                print("  %s%s%s %s%s%s" % (gc(0.0), GL["arr"] if i == 0 else " ", R, W, ln, R))
        return input(rl("  " + gc(0.0) + GL["v"] + R + gc(0.5) + GL["prompt"] + R + " " + W)).strip()
    except EOFError:
        return None
    except KeyboardInterrupt:
        print(R)
        return None
    finally:
        sys.stdout.write(R)


def yes_no(question):
    while True:
        a = ask(question + " (y/n)")
        if a is None:
            return False
        a = a.lower()
        if a in ("y", "ya", "yes"):
            return True
        if a in ("n", "t", "tidak", "no", "0", ""):
            return False
        p_warn("Ketik y (ya) atau n (tidak).")


def pause():
    try:
        input(rl(D + "\n  Tekan Enter untuk kembali..." + R))
    except (EOFError, KeyboardInterrupt):
        pass


# ----------------------------------------------------------------- HTTP
def _ssl_ctx():
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


class _Resp(object):
    def __init__(self, status=0, headers=None, body=b"", url="", ms=0, err=""):
        self.status, self.headers, self.body, self.url, self.ms, self.err = \
            status, headers or email.message.Message(), body, url, ms, err


def fetch(url, method="GET", data=None, headers=None, timeout=15, limit=3000000):
    """Permintaan HTTP lengkap: status, header, isi, URL akhir, waktu, dan pesan galat."""
    h = {"User-Agent": UA, "Accept": "text/html,application/json,*/*;q=0.8", "Accept-Language": "id,en;q=0.8"}
    if headers:
        h.update(headers)
    if isinstance(data, (dict, list)):
        data = json.dumps(data).encode("utf-8")
        h.setdefault("Content-Type", "application/json")
    elif isinstance(data, str):
        data = data.encode("utf-8")
    t0 = time.time()
    try:
        req = urllib.request.Request(url, data=data, headers=h, method=method)
    except Exception as e:
        return _Resp(0, err=str(e), url=url)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_ssl_ctx()) as r:
            body = r.read(limit)
            return _Resp(r.getcode(), r.headers, body, r.geturl(), int((time.time() - t0) * 1000))
    except urllib.error.HTTPError as e:
        try:
            body = e.read(limit)
        except Exception:
            body = b""
        return _Resp(e.code, e.headers, body, url, int((time.time() - t0) * 1000))
    except Exception as e:
        reason = getattr(e, "reason", e)
        return _Resp(0, body=str(reason).encode("utf-8", "ignore"), url=url, ms=int((time.time() - t0) * 1000),
                     err=str(reason))


def http(url, method="GET", data=None, headers=None, timeout=15):
    r = fetch(url, method, data, headers, timeout)
    return r.status, r.headers, r.body


def text_of(b):
    return b.decode("utf-8", "replace") if isinstance(b, (bytes, bytearray)) else str(b)


def http_json(url, **kw):
    st, hd, body = http(url, **kw)
    try:
        return st, json.loads(text_of(body))
    except Exception:
        return st, None


def q(s):
    return urllib.parse.quote(str(s), safe="")


def copy_text(s):
    """Salin teks ke clipboard bila ada utilitasnya. True bila berhasil."""
    cmds = []
    if IS_TERMUX:
        cmds.append(["termux-clipboard-set"])
    if IS_WIN:
        cmds.append(["clip"])
    if IS_MAC:
        cmds.append(["pbcopy"])
    cmds += [["wl-copy"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]
    for c in cmds:
        if shutil.which(c[0]):
            try:
                p = subprocess.Popen(c, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                p.communicate(s.encode("utf-8"), timeout=5)
                return p.returncode == 0
            except Exception:
                continue
    return False


def open_browser(url):
    """Membuka browser. Hanya dipakai sebagai pilihan TERAKHIR atas permintaan pengguna."""
    print("  %sTautan%s : %s%s%s" % (CY, R, BL, url, R))
    try:
        if IS_TERMUX and shutil.which("termux-open-url"):
            subprocess.call(["termux-open-url", url])
        elif not webbrowser.open(url):
            p_warn("Browser tidak ditemukan. Salin tautan di atas ke browsermu.")
    except Exception:
        p_warn("Gagal membuka browser. Salin tautan di atas.")


# ----------------------------------------------------------------- registry modul
MODULES = {}


def module(key, about, how):
    def deco(f):
        MODULES[key] = (f, about, how)
        return f
    return deco


# =====================================================================
#  v3 - ANTARMUKA: jam hidup, info perangkat/IP/Python, output merah, tengah layar, petunjuk keluar
# =====================================================================
CFG.setdefault("outred", True)
CFG.setdefault("pubip", True)
CFG.setdefault("clock", True)
DEFAULT_CFG.setdefault("outred", True)
DEFAULT_CFG.setdefault("pubip", True)
DEFAULT_CFG.setdefault("clock", True)

IN_ENTRY = False          # True selama sebuah fitur/tool dijalankan (petunjuk keluar aktif)
_HINT_SHOWN = False
PM = [0]                  # margin kiri prompt (menu rata tengah); 0 = bawaan 2 spasi
LAST_URLS = []            # tautan terakhir yang ditampilkan fitur (dipakai opsi 'o' = buka di browser)
OUT_TINT = fg(255, 96, 96) if COLOR_LVL else ""
_DAYS = ["Sen", "Sel", "Rab", "Kam", "Jum", "Sab", "Min"]
_MONTHS = ["Jan", "Feb", "Mar", "Apr", "Mei", "Jun", "Jul", "Agu", "Sep", "Okt", "Nov", "Des"]


# ---------- warna merah untuk keluaran fitur ----------
class RedOut(object):
    """Pembungkus stdout: baris polos (tanpa kode warna) diberi warna merah; baris berwarna dibiarkan."""

    def __init__(self, real):
        self._real = real
        self._open = False

    def write(self, s):
        if not s:
            return 0
        out = []
        for seg in re.split(r"(\r\n|\n|\r)", s):
            if seg in ("\n", "\r\n", "\r"):
                if self._open:
                    out.append("\033[0m")
                    self._open = False
                out.append(seg)
            elif not seg:
                continue
            elif "\033" in seg or not seg.strip():
                out.append(seg)
            else:
                if not self._open:
                    out.append(OUT_TINT)
                    self._open = True
                out.append(seg)
        self._real.write("".join(out))
        return len(s)

    def flush(self):
        try:
            self._real.flush()
        except Exception:
            pass

    def __getattr__(self, name):
        return getattr(self._real, name)


class _RedCtx(object):
    def __enter__(self):
        self.prev = sys.stdout
        if CFG.get("outred", True) and COLOR_LVL and TTY and not isinstance(sys.stdout, RedOut):
            sys.stdout = RedOut(sys.stdout)
        return self

    def __exit__(self, *a):
        try:
            sys.stdout.write(R)
            sys.stdout.flush()
        except Exception:
            pass
        sys.stdout = self.prev
        return False


def red_output():
    return _RedCtx()


def tint_bytes(chunk, state):
    """Versi byte untuk keluaran proses anak (run_cmd). state = dict(open=False)."""
    if not (CFG.get("outred", True) and COLOR_LVL):
        return chunk
    out = []
    for seg in re.split(rb"(\r\n|\n|\r)", chunk):
        if seg in (b"\n", b"\r\n", b"\r"):
            if state["open"]:
                out.append(b"\033[0m")
                state["open"] = False
            out.append(seg)
        elif not seg:
            continue
        elif b"\x1b" in seg or not seg.strip():
            out.append(seg)
        else:
            if not state["open"]:
                out.append(OUT_TINT.encode())
                state["open"] = True
            out.append(seg)
    return b"".join(out)


class entry_mode(object):
    """Konteks: fitur sedang berjalan (petunjuk keluar aktif + keluaran merah)."""

    def __enter__(self):
        global IN_ENTRY, _HINT_SHOWN
        self.prev = IN_ENTRY
        IN_ENTRY, _HINT_SHOWN = True, False
        self.red = _RedCtx()
        self.red.__enter__()
        return self

    def __exit__(self, *a):
        global IN_ENTRY
        self.red.__exit__()
        IN_ENTRY = self.prev
        return False


# ---------- info sistem ----------
SYS = {"pub": None, "pub_state": "idle"}


def local_ip():
    for target in (("10.255.255.255", 1), ("8.8.8.8", 80)):
        s = None
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.settimeout(0.4)
            s.connect(target)
            ip = s.getsockname()[0]
            if ip and not ip.startswith("0."):
                return ip
        except Exception:
            pass
        finally:
            if s is not None:
                try:
                    s.close()
                except Exception:
                    pass
    try:
        return socket.gethostbyname(socket.gethostname())
    except Exception:
        return "127.0.0.1"


def device_label():
    s = platform.system() or "OS"
    try:
        if IS_TERMUX:
            s = "Android (Termux)"
        elif s == "Linux":
            try:
                rel = platform.freedesktop_os_release()
                s = rel.get("NAME") or "Linux"
            except Exception:
                s = "Linux"
        elif s == "Darwin":
            s = "macOS " + (platform.mac_ver()[0] or "")
        elif s == "Windows":
            s = "Windows " + (platform.release() or "")
    except Exception:
        pass
    return ("%s %s" % (s.strip(), platform.machine() or "")).strip()


SYS["dev"] = device_label()
SYS["host"] = platform.node() or "-"
SYS["py"] = platform.python_version()
SYS["ip"] = "..."


def _bg_ips():
    SYS["ip"] = local_ip()
    if not CFG.get("pubip", True):
        SYS["pub_state"] = "off"
        return
    SYS["pub_state"] = "wait"
    for url in ("https://api.ipquery.io/", "https://api.ipify.org", "https://ifconfig.me/ip"):
        try:
            r = fetch(url, timeout=6)
            txt = (r.body or b"").decode("utf-8", "replace").strip()
            if txt.startswith("{"):
                txt = (json.loads(txt).get("ip") or "").strip()
            ipaddress.ip_address(txt)
            SYS["pub"] = txt
            SYS["pub_state"] = "ok"
            return
        except Exception:
            continue
    SYS["pub_state"] = "fail"


def start_sysinfo():
    t = threading.Thread(target=_bg_ips, daemon=True)
    t.start()
    return t


def hud_time():
    return time.strftime("%H:%M:%S")


def hud_date():
    lt = time.localtime()
    return "%s, %02d %s %d" % (_DAYS[lt.tm_wday], lt.tm_mday, _MONTHS[lt.tm_mon - 1], lt.tm_year)


def _fit(segs, limit, sep):
    """segs = [(polos, berwarna, wajib)] -> gabung; buang segmen opsional dari belakang hingga muat."""
    segs = list(segs)
    while True:
        line = sep.join(s[1] for s in segs)
        if vlen(line) <= limit or all(s[2] for s in segs):
            return line
        for i in range(len(segs) - 1, -1, -1):
            if not segs[i][2]:
                del segs[i]
                break


def hud_block():
    """Dua baris HUD (rata tengah): status + jam hidup + tanggal ; IP + perangkat + Python."""
    sep = " %s%s%s " % (D, GL["sep"], R)
    lim = term_w() - 2
    tools_ok, tools_all = tool_counts()
    l1 = _fit([("", "%s%s%s %sONLINE%s" % (G, GL["dot"], R, G, R), True),
               ("", "%s%s%s" % (W + B, hud_time(), R), True),
               ("", "%s%s%s" % (D, hud_date(), R), False),
               ("", "%sv%s%s" % (D, VERSION, R), False)], lim, sep)
    pub = ""
    if SYS["pub_state"] == "ok":
        pub = "%sIP publik%s %s%s%s" % (CY, R, W, SYS["pub"], R)
    elif SYS["pub_state"] == "wait":
        pub = "%sIP publik%s %s...%s" % (CY, R, D, R)
    segs = [("", "%sIP%s %s%s%s" % (CY, R, W, SYS["ip"], R), True)]
    if pub:
        segs.append(("", pub, False))
    segs += [("", "%s%s%s" % (D, SYS["dev"], R), False),
             ("", "%sPython%s %s%s%s" % (CY, R, W, SYS["py"], R), True),
             ("", "%sTool%s %s%d/%d%s" % (CY, R, W, tools_ok, tools_all, R), False)]
    l2 = _fit(segs, lim, sep)
    return [center(l1), center(l2)]


def hud_line():
    return hud_block()[0]


def find_clock(lines):
    """Cari (indeks_baris, kolom_1based) teks jam HH:MM:SS pada baris layar (untuk jam hidup)."""
    for i, ln in enumerate(lines):
        plain = ANSI_RE.sub("", ln)
        m = re.search(r"\b\d\d:\d\d:\d\d\b", plain)
        if m:
            return i, vlen(plain[:m.start()]) + 1
    return None


class LiveClock(object):
    """Jam bergerak: menulis ulang HH:MM:SS pada posisi tetap setiap detik (kursor input tidak terganggu)."""

    def __init__(self):
        self.ev = None
        self.th = None

    def start(self, row, col):
        self.stop()
        if not (TTY and COLOR_LVL and ANIM and CFG.get("clock", True)) or IS_WIN and not os.environ.get("WT_SESSION"):
            return
        ev = threading.Event()
        self.ev = ev

        def loop():
            while not ev.wait(1.0):
                try:
                    sys.stdout.write("\0337\033[%d;%dH%s%s%s\0338" % (row, col, W + B, hud_time(), R))
                    sys.stdout.flush()
                except Exception:
                    return
        self.th = threading.Thread(target=loop, daemon=True)
        self.th.start()

    def stop(self):
        if self.ev is not None:
            self.ev.set()
        if self.th is not None:
            self.th.join(0.3)
        self.ev = self.th = None


LIVE = LiveClock()


# ---------- tata letak tengah ----------
def mg():
    return max(0, (term_w() - content_w()) // 2)


def pad_lines(lines):
    m = " " * mg()
    return [(m + ln) if ln else ln for ln in lines]


def brand_header(trail=None):
    """Header ringkas untuk layar di dalam kategori: logo + jalur + jam hidup."""
    head = "%s%s%s %s %s%s%s" % (gc(0.0), GL["tl"], R, gtext("GIGA OSINT", 0.0, 1.0, True), gc(1.0), GL["tr"], R)
    crumb = ""
    if trail:
        crumb = "  " + (" %s%s%s " % (D, GL["arr"], R)).join(W + t + R for t in trail)
    sep = " %s%s%s " % (D, GL["sep"], R)
    hud = _fit([("", "%s%s%s" % (W + B, hud_time(), R), True), ("", "%sIP %s%s" % (D, SYS["ip"], R), False),
                ("", "%sPython %s%s" % (D, SYS["py"], R), False), ("", "%s%s%s" % (D, SYS["dev"], R), False)], content_w(), sep)
    return pad_lines(["", head + crumb, hline(content_w(), 0, 1), hud])


# ---------- input dengan petunjuk keluar ----------
def ask(question=""):
    """Baca input. Mengembalikan None bila EOF / Ctrl+C. Di dalam fitur: 0/q/keluar/batal = '0'."""
    global _HINT_SHOWN
    lead = " " * max(2, PM[0])
    try:
        if question:
            for i, ln in enumerate(wrap_ansi(question, max(20, term_w() - len(lead) - 4))):
                print("%s%s%s%s %s%s%s" % (lead, gc(0.0), GL["arr"] if i == 0 else " ", R, W, ln, R))
            if IN_ENTRY and not _HINT_SHOWN and "0" not in question and "(y/n)" not in question:
                _HINT_SHOWN = True
                print("%s  %sketik 0 atau q untuk batal / kembali  %s  Ctrl+C untuk berhenti%s" % (lead, D, GL["sep"], R))
        v = input(rl(lead + gc(0.0) + GL["v"] + R + gc(0.5) + GL["prompt"] + R + " " + W)).strip()
        if IN_ENTRY and v.lower() in ("q", "exit", "keluar", "batal", "kembali", "cancel"):
            return "0"
        return v
    except EOFError:
        return None
    except KeyboardInterrupt:
        print(R)
        return None
    finally:
        sys.stdout.write(R)


def kv(k, v, w=22):
    """Baris 'label : nilai'. Di dalam fitur nilai berwarna merah muda-merah (keluaran)."""
    if v is None or v == "":
        v = "-"
    w = min(max(w, min(len(str(k)), 30)), max(10, term_w() // 3))   # label panjang diperlebar, bukan dipotong
    avail = max(12, term_w() - w - 6)
    lines = wrap_ansi(str(v), avail)
    vc = OUT_TINT if (IN_ENTRY and OUT_TINT and CFG.get("outred", True)) else W
    print("  %s%-*s%s %s%s%s %s%s%s" % (CY, w, trunc(str(k), w), R, D, GL["v"], R, vc, lines[0], R))
    for extra in lines[1:]:
        print("  %s %s %s%s%s" % (" " * w, D + GL["v"] + R, vc, extra, R))


def exit_notice(extra=""):
    """Baris petunjuk keluar yang selalu terlihat di atas fitur yang berjalan."""
    line = "%sKeluar kapan saja:%s ketik %s0%s atau %sq%s di kolom input  %s  tekan %sCtrl+C%s untuk menghentikan." % (
        D, R, Y, R, Y, R, GL["sep"], Y, R)
    if extra:
        line += "  " + extra
    for ln in wrap_ansi(line, max(20, term_w() - 4)):
        print("  " + ln)


# =====================================================================
#  INSTALASI OTOMATIS & PENJALAN TOOL GITHUB
# =====================================================================
def refresh_path():
    extra = [BIN_DIR, os.path.join(HOME, "go", "bin"), os.path.join(HOME, ".local", "bin")]
    try:
        extra.append(sysconfig.get_path("scripts"))
        extra.append(sysconfig.get_path("scripts", "nt_user" if IS_WIN else "posix_user"))
    except Exception:
        pass
    if shutil.which("go"):
        try:
            gp = subprocess.check_output(["go", "env", "GOPATH"], text=True, stderr=subprocess.DEVNULL).strip()
            if gp:
                extra.append(os.path.join(gp, "bin"))
        except Exception:
            pass
    cur = os.environ.get("PATH", "").split(os.pathsep)
    for e in extra:
        if e and os.path.isdir(e) and e not in cur:
            cur.append(e)
    os.environ["PATH"] = os.pathsep.join(cur)


refresh_path()


def pm_name():
    if IS_TERMUX or (shutil.which("pkg") and not shutil.which("apt-get")):
        return "pkg"
    for name in ("apt-get", "brew", "dnf", "pacman"):
        if shutil.which(name):
            return "apt" if name == "apt-get" else name
    if IS_WIN and shutil.which("winget"):
        return "winget"
    return None


def sudo_prefix():
    if IS_WIN or IS_TERMUX:
        return ""
    try:
        if os.geteuid() == 0:
            return ""
    except AttributeError:
        return ""
    return "sudo " if shutil.which("sudo") else ""


def pm_install_cmd(pm, pkg):
    s = sudo_prefix()
    return {
        "pkg": "pkg install -y %s" % pkg,
        "apt": "%sapt-get install -y %s" % (s, pkg),
        "brew": "brew install %s" % pkg,
        "dnf": "%sdnf install -y %s" % (s, pkg),
        "pacman": "%spacman -S --noconfirm %s" % (s, pkg),
        "winget": "winget install -e --id %s" % pkg,
    }[pm]


def sys_pkg(t, pm):
    sp = t.get("sys")
    if not sp or not pm:
        return None
    if isinstance(sp, dict):
        return sp.get(pm) or sp.get("*")
    return None if pm == "winget" else sp


def run_quiet(argv, label, cwd=None, shell=False, env=None):
    """Jalankan perintah tanpa menampilkan keluarannya (spinner saja). Return (kode, 12 baris terakhir)."""
    p = None
    try:
        with Spinner(label):
            p = subprocess.Popen(argv, cwd=cwd, shell=shell, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
            out, _ = p.communicate()
    except KeyboardInterrupt:
        if p:
            try:
                p.kill()
            except Exception:
                pass
        raise
    except OSError as e:
        return 127, str(e)
    tail = "\n".join(text_of(out).strip().splitlines()[-12:])
    return p.returncode, tail


def show_tail(tail):
    if tail:
        for ln in tail.splitlines()[-8:]:
            print("   %s%s%s" % (D, trunc(ln, term_w() - 6), R))


def pip_install(pkgs, label="Memasang paket Python"):
    if isinstance(pkgs, str):
        pkgs = [pkgs]
    base = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check"]
    tails = ""
    for extra in ([], ["--user"], ["--break-system-packages"], ["--user", "--break-system-packages"]):
        rc, tail = run_quiet(base + extra + list(pkgs), "%s: %s" % (label, " ".join(pkgs)[:50]))
        if rc == 0:
            importlib.invalidate_caches()
            return True
        tails = tail
    show_tail(tails)
    return False


def ensure_pip_module(mod, pipname, purpose):
    try:
        return importlib.import_module(mod)
    except ImportError:
        pass
    p_warn("Fitur ini membutuhkan paket Python '%s' (%s)." % (pipname, purpose))
    if not yes_no("Pasang '%s' otomatis sekarang?" % pipname):
        return None
    if not pip_install(pipname):
        p_err("Instalasi gagal. Coba manual: %s -m pip install %s" % (sys.executable, pipname))
        return None
    importlib.invalidate_caches()
    try:
        import site
        site.addsitedir(site.getusersitepackages())
    except Exception:
        pass
    try:
        return importlib.import_module(mod)
    except ImportError:
        p_err("Paket terpasang tetapi belum bisa dimuat. Jalankan ulang Giga OSINT.")
        return None


def go_ready():
    if shutil.which("go"):
        return True
    pm = pm_name()
    names = {"apt": "golang-go", "pkg": "golang", "brew": "go", "dnf": "golang",
             "pacman": "go", "winget": "GoLang.Go"}
    if not pm:
        p_err("Go belum terpasang dan package manager tidak dikenali. Pasang Go dari https://go.dev/dl/")
        return False
    p_info("Memasang Go (dibutuhkan untuk tool ini)...")
    subprocess.call(pm_install_cmd(pm, names[pm]), shell=True)
    refresh_path()
    return bool(shutil.which("go"))


def git_ready():
    if shutil.which("git"):
        return True
    pm = pm_name()
    if pm:
        p_info("Git belum ada, memasang git...")
        subprocess.call(pm_install_cmd(pm, "git"), shell=True)
    refresh_path()
    return bool(shutil.which("git"))


def req_install(d, req):
    base = [sys.executable, "-m", "pip", "install", "--disable-pip-version-check", "-r", req]
    tails = ""
    for extra in ([], ["--user"], ["--break-system-packages"], ["--user", "--break-system-packages"]):
        rc, tail = run_quiet(base[:5] + extra + base[5:], "Memasang dependensi (%s)" % req, cwd=d)
        if rc == 0:
            return True
        tails = tail
    show_tail(tails)
    return False


def git_install(g):
    os.makedirs(TOOLS_DIR, exist_ok=True)
    d = os.path.join(TOOLS_DIR, g["dir"])
    if not git_ready():
        p_err("Git tidak tersedia, tidak bisa mengunduh repo.")
        return False
    if not os.path.isdir(d):
        cmd = ["git", "clone", "--depth", "1"] + (["--branch", g["ref"]] if g.get("ref") else []) + [g["url"], d]
        rc, tail = run_quiet(cmd, "Mengunduh repo %s" % g["dir"])
        if rc != 0:
            show_tail(tail)
            return False
    req = g.get("req")
    if req and os.path.exists(os.path.join(d, req)):
        return req_install(d, req)
    return True


# ---------- rilis biner GitHub (tanpa perlu Go) ----------
def os_arch_tokens():
    sysname = platform.system().lower()
    mach = platform.machine().lower()
    os_t = {"linux": ["linux"], "darwin": ["darwin", "macos", "mac", "osx"], "windows": ["windows", "win64", "win"]}.get(sysname, [sysname])
    if mach in ("x86_64", "amd64", "x64"):
        ar = ["amd64", "x86_64", "x64", "64bit"]
    elif mach in ("aarch64", "arm64", "armv8l"):
        ar = ["arm64", "aarch64"]
    elif mach.startswith("armv7") or mach.startswith("armv6") or mach == "arm":
        ar = ["armv7", "armv6", "arm"]
    else:
        ar = ["386", "i386", "i686", "32bit"]
    return os_t, ar


def _has_token(name, toks):
    for t in toks:
        if re.search(r"(?<![a-z0-9])%s(?![a-z0-9])" % re.escape(t), name):
            return True
    return False


def pick_asset(assets):
    """Pilih aset rilis yang cocok dengan OS & arsitektur. assets = [(nama, url)]."""
    os_t, ar_t = os_arch_tokens()
    bad_ext = (".sha256", ".sha512", ".sig", ".pem", ".txt", ".sbom", ".json", ".deb", ".rpm", ".apk", ".msi",
               ".dmg", ".pkg", ".asc", ".md5", ".sh", ".yaml", ".yml", ".intoto.jsonl", ".bundle")
    best, best_score = None, 0
    for name, url in assets:
        n = name.lower()
        if n.endswith(bad_ext) or "checksum" in n or "sbom" in n:
            continue
        if not (_has_token(n, os_t) and _has_token(n, ar_t)):
            continue
        score = 10
        if IS_WIN and n.endswith(".zip"):
            score += 3
        elif not IS_WIN and n.endswith((".tar.gz", ".tgz")):
            score += 3
        elif n.endswith((".zip", ".tar.gz", ".tgz")):
            score += 1
        if score > best_score:
            best, best_score = (name, url), score
    return best


def gh_assets(repo):
    st, o = http_json("https://api.github.com/repos/%s/releases/latest" % repo,
                      headers={"Accept": "application/vnd.github+json"}, timeout=25)
    if st == 200 and isinstance(o, dict) and o.get("assets"):
        return [(a.get("name", ""), a.get("browser_download_url", "")) for a in o["assets"]]
    r = fetch("https://github.com/%s/releases/latest" % repo, timeout=25)
    m = re.search(r"/releases/tag/([^/?#\"']+)", r.url or "")
    if m:
        r2 = fetch("https://github.com/%s/releases/expanded_assets/%s" % (repo, m.group(1)), timeout=25)
        links = re.findall(r'href="(/%s/releases/download/[^"]+)"' % re.escape(repo), text_of(r2.body))
        return [(l.rsplit("/", 1)[-1], "https://github.com" + l) for l in links]
    return []


def download_file(url, dest, label):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60, context=_ssl_ctx()) as r, open(dest, "wb") as f:
        total = int(r.headers.get("Content-Length") or 0)
        got = 0
        while True:
            chunk = r.read(65536)
            if not chunk:
                break
            f.write(chunk)
            got += len(chunk)
            if TTY and COLOR_LVL:
                frac = (got / float(total)) if total else 0.0
                sys.stdout.write("\r  %s %s%s%s %s%.1f MB%s" % (bar(frac, 22), W, label[:28], R, D, got / 1048576.0, R))
                sys.stdout.flush()
    if TTY and COLOR_LVL:
        sys.stdout.write("\r\033[K")


def extract_bin(archive, fname, binname, dest_dir):
    """Ambil SATU berkas biner bernama binname dari arsip (tanpa mengekstrak path arsip)."""
    want = (binname + ".exe").lower() if IS_WIN else binname.lower()
    os.makedirs(dest_dir, exist_ok=True)
    target = os.path.join(dest_dir, binname + (".exe" if IS_WIN else ""))
    data = None
    low = fname.lower()
    if low.endswith(".zip"):
        with zipfile.ZipFile(archive) as z:
            for n in z.namelist():
                if os.path.basename(n).lower() == want:
                    data = z.read(n)
                    break
    elif low.endswith((".tar.gz", ".tgz")):
        with tarfile.open(archive, "r:gz") as tf:
            for m in tf.getmembers():
                if m.isfile() and os.path.basename(m.name).lower() == want:
                    data = tf.extractfile(m).read()
                    break
    else:
        with open(archive, "rb") as f:
            data = f.read()
    if not data:
        return None
    with open(target, "wb") as f:
        f.write(data)
    if not IS_WIN:
        os.chmod(target, 0o755)
    return target


def rel_install(rel, binname):
    p_info("Mencari rilis biner terbaru di GitHub: %s" % rel["repo"])
    with Spinner("Membaca daftar rilis"):
        assets = gh_assets(rel["repo"])
    pick = pick_asset(assets) if assets else None
    if not pick:
        p_warn("Rilis biner yang cocok untuk %s/%s tidak ditemukan." % (platform.system(), platform.machine()))
        return False
    name, url = pick
    tmp = os.path.join(tempfile.gettempdir(), "giga_" + re.sub(r"[^A-Za-z0-9._-]", "_", name))
    try:
        download_file(url, tmp, name)
        got = extract_bin(tmp, name, binname, BIN_DIR)
    except (OSError, urllib.error.URLError, zipfile.BadZipFile, tarfile.TarError) as e:
        p_warn("Unduhan/ekstraksi gagal: %s" % e)
        return False
    finally:
        try:
            os.remove(tmp)
        except OSError:
            pass
    if not got:
        p_warn("Berkas '%s' tidak ada di dalam arsip %s." % (binname, name))
        return False
    p_ok("Biner terpasang: %s" % got)
    refresh_path()
    return True


def find_tool(t):
    for b in t.get("bins", []):
        p = shutil.which(b)
        if p:
            return [p], None
    g = t.get("git")
    if g:
        d = os.path.join(TOOLS_DIR, g["dir"])
        if os.path.exists(os.path.join(d, g["entry"])):
            return [sys.executable, g["entry"]], d
    return None


def tool_counts():
    try:
        return sum(1 for t in TOOLS.values() if find_tool(t)), len(TOOLS)
    except Exception:
        return 0, len(TOOLS)


def install_plan(t):
    pm = pm_name()
    steps = []
    order = t.get("order") or ["pip", "git", "rel", "sys", "go"]
    if IS_TERMUX:
        order = ["sys"] + [o for o in order if o != "sys"]
    for kind in order:
        if kind == "sys":
            sp = sys_pkg(t, pm)
            if sp:
                steps.append(("sys", "Paket sistem", pm_install_cmd(pm, sp)))
        elif kind == "rel" and t.get("rel") and not IS_TERMUX:
            steps.append(("rel", "Rilis GitHub", "unduh biner terbaru dari github.com/%s/releases" % t["rel"]["repo"]))
        elif kind == "go" and t.get("go"):
            steps.append(("go", "Go", "go install -v %s@latest" % t["go"]))
        elif kind == "pip" and t.get("pip"):
            steps.append(("pip", "Pip", "%s -m pip install %s" % (os.path.basename(sys.executable), " ".join(t["pip"]))))
        elif kind == "git" and t.get("git"):
            g = t["git"]
            steps.append(("git", "Git", "git clone --depth 1 %s%s  +  pip install -r %s" % (
                g["url"], (" --branch " + g["ref"]) if g.get("ref") else "", g.get("req", "-"))))
    return steps


def install_tool(t):
    steps = install_plan(t)
    if not steps:
        p_warn("Tidak ada metode instalasi otomatis untuk sistem ini.")
        if t.get("manual"):
            p_info("Unduh manual: " + t["manual"])
        return False
    lines = ["%s%d.%s %s%-12s%s %s%s%s" % (Y, i + 1, R, W, lab, R, D, c, R) for i, (_, lab, c) in enumerate(steps)]
    lines.append(D + "Metode dicoba berurutan sampai tool berhasil terpasang." + R)
    if t.get("note"):
        lines.append(Y + "Catatan: " + R + t["note"])
    sys.stdout.write("\n".join(panel("RENCANA INSTALASI OTOMATIS  " + GL["sep"] + "  " + t["title"], lines)) + "\n")
    if not yes_no("Lanjutkan instalasi otomatis %s?" % t["title"]):
        p_warn("Instalasi dibatalkan.")
        return False
    for kind, lab, cmd in steps:
        p_info("Metode: %s" % lab)
        try:
            if kind == "sys":
                subprocess.call(cmd, shell=True)
            elif kind == "rel":
                rel_install(t["rel"], t["bins"][0])
            elif kind == "go":
                if go_ready():
                    rc, tail = run_quiet(["go", "install", "-v", t["go"] + "@latest"], "Kompilasi dengan Go (butuh beberapa menit)")
                    if rc != 0:
                        show_tail(tail)
            elif kind == "pip":
                pip_install(t["pip"])
            elif kind == "git":
                git_install(t["git"])
        except KeyboardInterrupt:
            p_warn("Instalasi dihentikan pengguna.")
            return False
        refresh_path()
        if find_tool(t):
            p_ok("%s berhasil terpasang." % t["title"])
            return True
    p_err("Instalasi belum berhasil.")
    if t.get("note"):
        p_info(t["note"])
    if t.get("manual"):
        p_info("Unduh manual: " + t["manual"])
    return False


def authorize():
    box("PERINGATAN ETIKA & HUKUM",
        [W + "Tool ini melakukan pemindaian AKTIF ke target." + R,
         W + "Gunakan HANYA pada sistem milikmu sendiri atau yang kamu punya izin tertulis" + R,
         W + "(mis. program bug bounty resmi dan sesuai scope-nya). Jangan Disalah Gunakan!" + R])
    return yes_no("Saya memiliki izin sah untuk menguji target ini")


# ---------- validasi input ----------
def clean_input(kind, v):
    """Return (ok, nilai_bersih, petunjuk)."""
    v = (v or "").strip()
    if kind == "domain":
        v = re.sub(r"^[a-z]+://", "", v, flags=re.I).split("/")[0].split("?")[0].lower()
        return bool(re.fullmatch(r"[a-z0-9._-]+\.[a-z0-9-]{2,}", v)), v, "contoh yang benar: example.com"
    if kind == "url":
        if not re.match(r"^https?://", v, re.I):
            v = "https://" + v
        return bool(re.match(r"^https?://[^\s]+\.[^\s]+$", v)), v, "contoh yang benar: https://example.com"
    if kind == "email":
        v = v.lower()
        return bool(EMAIL_RE.match(v)), v, "contoh yang benar: nama@domain.com"
    if kind == "user":
        v = v.lstrip("@")
        return bool(re.fullmatch(r"[\w.\-]{1,64}", v)) and not v.startswith("-"), v, "tanpa spasi dan tanpa @, contoh: budi123"
    if kind == "host":
        try:
            ipaddress.ip_address(v)
            return True, v, ""
        except ValueError:
            return clean_input("domain", v)
    if kind == "phone":
        d = re.sub(r"\D", "", v)
        if v.startswith("+") and 7 <= len(d) <= 15:
            return True, "+" + d, ""
        if d.startswith("0") and 8 <= len(d) <= 14:
            return True, "+62" + d[1:], ""
        if d.startswith("62") and 9 <= len(d) <= 15:
            return True, "+" + d, ""
        return False, v, "awali dengan + dan kode negara, contoh: +6281234567890 (atau 0812... untuk Indonesia)"
    if kind == "file":
        v = os.path.expanduser(v.strip("\"'"))
        return os.path.isfile(v), v, "file tidak ditemukan; tulis path lengkap, contoh: /sdcard/foto.jpg"
    if kind == "num":
        return v.isdigit(), v, "masukkan angka saja"
    return bool(v) and not v.startswith("-"), v, "tidak boleh kosong atau diawali tanda minus"


ANSI_B = re.compile(rb"\x1b\[[0-9;?]*[A-Za-z]")


def run_cmd(argv, cwd=None, interactive=False, log_name="hasil"):
    """Jalankan perintah. Non-interaktif: keluaran ditampilkan langsung DAN disimpan ke file log."""
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    if interactive or not TTY or not hasattr(sys.stdout, "buffer"):
        return subprocess.call(argv, cwd=cwd, env=env), None
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "%s-%s.txt" % (re.sub(r"[^A-Za-z0-9_.-]", "_", log_name), time.strftime("%Y%m%d-%H%M%S")))
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as e:
        p_err("Gagal menjalankan: %s" % e)
        return 127, None
    try:
        with open(path, "wb") as lf:
            reader = getattr(proc.stdout, "read1", None) or proc.stdout.read
            while True:
                chunk = reader(4096)
                if not chunk:
                    break
                sys.stdout.buffer.write(chunk)
                sys.stdout.buffer.flush()
                lf.write(ANSI_B.sub(b"", chunk))
        proc.wait()
    except KeyboardInterrupt:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            pass
        p_warn("Dihentikan oleh pengguna (Ctrl+C).")
    return proc.returncode, path


def run_tool(key, preset=None):
    t = TOOLS[key]
    print()
    sys.stdout.write("\n".join(panel(t["title"], [CY + "Tentang    " + R + W + t["about"] + R,
                                                  CY + "Cara input " + R + W + t["how"] + R,
                                                  CY + "Sumber     " + R + D + tool_source(t) + R])) + "\n")
    if t.get("auth") and not preset and not authorize():
        p_warn("Dibatalkan. Izin sah wajib dikonfirmasi.")
        return
    found = find_tool(t)
    if not found:
        p_warn("%s belum terpasang di perangkat ini." % t["title"])
        if not install_tool(t):
            return
        found = find_tool(t)
        if not found:
            p_err("Tool tidak ditemukan setelah instalasi. Buka ulang terminal lalu coba lagi.")
            return
    vals = dict(preset or {})
    for pr in t.get("prompts", []):
        k, label, default, kind = pr[0], pr[1], pr[2], pr[3]
        when = pr[4] if len(pr) > 4 else None
        if k in vals or (when and not when(vals)):
            continue
        while True:
            v = ask(label + ("  [Enter = %s]" % default if default else "") + "  (0 = batal)")
            if v is None or v == "0":
                p_warn("Dibatalkan.")
                return
            if v == "" and default:
                v = default
            ok, cleaned, hint = clean_input(kind, v)
            if ok:
                vals[k] = cleaned
                break
            p_warn("Input tidak valid: %s" % hint)
    argv = found[0] + t["build"](vals)
    print("\n  %sPerintah%s : %s%s%s\n" % (CY, R, G, " ".join(shlex.quote(a) for a in argv), R))
    cwd = found[1]
    if t.get("outcwd"):
        os.makedirs(OUT_DIR, exist_ok=True)
        cwd = OUT_DIR
        if found[1]:
            argv = [argv[0], os.path.join(found[1], t["git"]["entry"])] + argv[2:]
    try:
        rc, logp = run_cmd(argv, cwd=cwd, interactive=bool(t.get("inter")), log_name=key)
    except Exception as e:
        p_err("Gagal menjalankan: %s" % e)
        return
    if rc not in (0, None):
        p_warn("Tool selesai dengan kode %s. Bila ada pesan galat di atas, periksa input atau coba pasang ulang." % rc)
    if logp:
        p_ok("Salinan hasil tersimpan: %s" % logp)
    if t.get("outcwd"):
        p_info("File keluaran tool (bila ada) disimpan di: %s" % OUT_DIR)


def tool_source(t):
    if t.get("git"):
        return t["git"]["url"].replace(".git", "")
    if t.get("rel"):
        return "https://github.com/" + t["rel"]["repo"]
    for p in t.get("pip", []):
        if p.startswith("git+"):
            return p[4:].split("@")[0].replace(".git", "")
    if t.get("go"):
        return "https://" + t["go"].split("/cmd/")[0].split("/v")[0]
    if t.get("pip"):
        return "https://pypi.org/project/" + re.split(r"[<>=\[ ]", t["pip"][0])[0]
    return t.get("manual", "paket sistem")


# =====================================================================
#  REGISTRY TOOL GITHUB   prompts = (kunci, pertanyaan, default, jenis[, kondisi])
# =====================================================================
TOOLS = {
    "harvester": dict(
        title="theHarvester", group="Domain & Jaringan", bins=["theHarvester", "theharvester"],
        sys={"apt": "theharvester", "brew": "theharvester"},
        pip=["git+https://github.com/laramies/theHarvester.git@4.10.0"],
        note="Versi terbaru butuh Python 3.12+. Bila Python-mu lebih lama, perbarui Python atau pakai Kali Linux (apt install theharvester).",
        about="Mengumpulkan email, subdomain, host, dan nama dari sumber terbuka untuk sebuah domain.",
        how="Input: domain target, contoh example.com. Beberapa sumber butuh API key (opsional).",
        prompts=[("domain", "Masukkan domain target (contoh: example.com)", None, "domain"),
                 ("lim", "Batas hasil per sumber (angka)", "100", "num")],
        build=lambda v: ["-d", v["domain"], "-b", "all", "-l", v["lim"]]),
    "maltego": dict(
        title="Maltego", group="Kerangka Kerja OSINT", bins=["maltego"], sys={"apt": "maltego", "brew": "maltego"},
        manual="https://www.maltego.com/downloads/", inter=True,
        about="Aplikasi grafis analisis tautan/relasi data OSINT (orang, domain, email, infrastruktur).",
        how="Membuka aplikasi Maltego. Perlu akun gratis Maltego CE saat pertama kali dijalankan.",
        prompts=[], build=lambda v: []),
    "nmap": dict(
        title="Nmap", group="Pemindaian (Izin Sah)", bins=["nmap"], sys={"*": "nmap", "winget": "Insecure.Nmap"}, auth=True,
        manual="https://nmap.org/download.html",
        about="Pemindai port dan layanan jaringan paling populer untuk audit keamanan jaringan.",
        how="Input: IP/domain milikmu atau berizin, lalu pilih profil 1 (cepat), 2 (standar), 3 (lengkap).",
        prompts=[("target", "Masukkan target (IP/domain berizin)", None, "host"),
                 ("mode", "Pilih profil: 1=Cepat  2=Standar (versi layanan)  3=Lengkap (semua port, lama)", "2", "num")],
        build=lambda v: (["-F", v["target"]] if v["mode"] == "1" else
                         ["-p-", "-sV", v["target"]] if v["mode"] == "3" else
                         ["-sV", "--top-ports", "1000", v["target"]])),
    "dirsearch": dict(
        title="dirsearch", group="Pemindaian (Izin Sah)", bins=["dirsearch"], sys={"apt": "dirsearch"}, pip=["dirsearch"],
        auth=True, outcwd=True,
        about="Mencari direktori dan file tersembunyi pada web server dengan wordlist (brute-force path).",
        how="Input: URL lengkap dengan http/https, contoh https://target.com . Hanya pada target berizin.",
        prompts=[("url", "Masukkan URL target (contoh: https://target.com)", None, "url")],
        build=lambda v: ["-u", v["url"], "-e", "php,html,js,txt"]),
    "nuclei": dict(
        title="Nuclei", group="Pemindaian (Izin Sah)", bins=["nuclei"], sys={"apt": "nuclei", "brew": "nuclei", "pkg": "nuclei"},
        rel=dict(repo="projectdiscovery/nuclei"), go="github.com/projectdiscovery/nuclei/v3/cmd/nuclei", auth=True,
        about="Pemindai kerentanan berbasis template YAML dari komunitas ProjectDiscovery.",
        how="Input: URL target berizin. Template diunduh otomatis pada eksekusi pertama.",
        prompts=[("url", "Masukkan URL target (contoh: https://target.com)", None, "url")],
        build=lambda v: ["-u", v["url"], "-severity", "low,medium,high,critical"]),
    "dalfox": dict(
        title="Dalfox", group="Pemindaian (Izin Sah)", bins=["dalfox"], sys={"brew": "dalfox", "apt": "dalfox"},
        rel=dict(repo="hahwul/dalfox"), go="github.com/hahwul/dalfox/v2", auth=True,
        about="Pemindai dan analisis parameter untuk mendeteksi celah XSS pada aplikasi web.",
        how="Input: URL yang memiliki parameter, contoh https://target.com/cari?q=test (target berizin).",
        prompts=[("url", "Masukkan URL berparameter (contoh: https://target.com/cari?q=test)", None, "url")],
        build=lambda v: ["url", v["url"]]),
    "katana": dict(
        title="Katana", group="Pemindaian (Izin Sah)", bins=["katana"], sys={"brew": "katana", "apt": "katana"},
        rel=dict(repo="projectdiscovery/katana"), go="github.com/projectdiscovery/katana/cmd/katana", auth=True,
        about="Crawler web cepat untuk mengumpulkan endpoint, URL, dan file JavaScript.",
        how="Input: URL awal dan kedalaman crawl (default 2). Hanya pada target berizin.",
        prompts=[("url", "Masukkan URL target (contoh: https://target.com)", None, "url"),
                 ("depth", "Kedalaman crawl (angka)", "2", "num")],
        build=lambda v: ["-u", v["url"], "-d", v["depth"]]),
    "subfinder": dict(
        title="Subfinder", group="Domain & Jaringan", bins=["subfinder"], sys={"apt": "subfinder", "brew": "subfinder", "pkg": "subfinder"},
        rel=dict(repo="projectdiscovery/subfinder"), go="github.com/projectdiscovery/subfinder/v2/cmd/subfinder",
        about="Penemuan subdomain pasif dari banyak sumber publik (tanpa menyentuh server target).",
        how="Input: domain utama, contoh example.com.",
        prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")],
        build=lambda v: ["-d", v["domain"]]),
    "paramspider": dict(
        title="ParamSpider", group="Pemindaian (Izin Sah)", bins=["paramspider"], outcwd=True,
        pip=["git+https://github.com/devanshbatham/ParamSpider.git"],
        about="Mengumpulkan URL berparameter dari arsip web (pasif) untuk bahan pengujian bug bounty.",
        how="Input: domain, contoh example.com. Hasil disimpan di folder 'results' pada folder hasil Giga OSINT.",
        prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")],
        build=lambda v: ["-d", v["domain"]]),
    "photon": dict(
        title="Photon", group="Pemindaian (Izin Sah)", bins=["photon"], auth=True,
        git=dict(url="https://github.com/s0md3v/Photon.git", dir="Photon", entry="photon.py", req="requirements.txt"),
        about="Crawler OSINT cepat: mengekstrak URL, email, file, kunci API, dan subdomain dari situs.",
        how="Input: URL awal (https://...). Hasil disimpan di folder hasil Giga OSINT (subfolder photon).",
        prompts=[("url", "Masukkan URL target (contoh: https://target.com)", None, "url")],
        build=lambda v: ["-u", v["url"], "-o", os.path.join(OUT_DIR, "photon")]),
    "sherlock": dict(
        title="Sherlock", group="Username & Sosial", bins=["sherlock"], sys={"apt": "sherlock"}, pip=["sherlock-project"], outcwd=True,
        about="Mencari satu username di ratusan situs sosial sekaligus.",
        how="Input: username tanpa spasi dan tanpa @, contoh budi123.",
        prompts=[("user", "Masukkan username (contoh: budi123)", None, "user")],
        build=lambda v: [v["user"], "--print-found", "--timeout", "20"]),
    "mrholmes": dict(
        title="Mr.Holmes", group="Kerangka Kerja OSINT", bins=["mrholmes"], inter=True,
        git=dict(url="https://github.com/Lucksi/Mr.Holmes.git", dir="Mr.Holmes", entry="MrHolmes.py", req="requirements.txt"),
        about="Framework OSINT interaktif: username, domain, nomor telepon, email, dan lainnya.",
        how="Akan membuka menu Mr.Holmes sendiri; ikuti petunjuk di layar (ketik nomor menu).",
        prompts=[], build=lambda v: []),
    "exiftool": dict(
        title="ExifTool", group="Gambar, Video & Metadata", bins=["exiftool"],
        sys={"apt": "libimage-exiftool-perl", "pkg": "exiftool", "brew": "exiftool", "winget": "OliverBetz.ExifTool"},
        manual="https://exiftool.org/",
        about="Membaca, menganalisis, dan mengedit metadata ratusan jenis file (foto, video, PDF, dokumen).",
        how="Input: path file lengkap. Hasil metadata ditampilkan langsung di terminal.",
        prompts=[("path", "Masukkan path file (contoh: /sdcard/foto.jpg)", None, "file")],
        build=lambda v: [v["path"]]),
    # ---------------- tambahan v2 ----------------
    "maigret": dict(
        title="Maigret", group="Username & Sosial", bins=["maigret"], pip=["maigret"], outcwd=True,
        about="Menyusun dossier akun dari satu username di ribuan situs, lengkap dengan data profil yang terbaca.",
        how="Input: username (tanpa @). Mode 1 = 500 situs populer (cepat), mode 2 = semua situs (lama).",
        prompts=[("user", "Masukkan username (contoh: budi123)", None, "user"),
                 ("mode", "Mode: 1 = situs populer (cepat)   2 = semua situs (lama)", "1", "num")],
        build=lambda v: [v["user"], "--timeout", "20"] + (["-a"] if v["mode"] == "2" else [])),
    "holehe": dict(
        title="Holehe", group="Email & Kebocoran", bins=["holehe"], pip=["holehe"],
        about="Memeriksa email terdaftar di puluhan situs (mode aman: tanpa memicu pemulihan password).",
        how="Input: email lengkap. Hanya situs tempat email terdaftar yang ditampilkan.",
        prompts=[("email", "Masukkan email (contoh: nama@domain.com)", None, "email")],
        build=lambda v: [v["email"], "--only-used", "--no-color", "-NP"]),
    "socialscan": dict(
        title="Socialscan", group="Username & Sosial", bins=["socialscan"], pip=["socialscan"],
        about="Memeriksa apakah username atau email sudah dipakai di platform besar (cepat dan akurat).",
        how="Input: satu username atau email. Hasil menunjukkan tersedia / sudah dipakai per platform.",
        prompts=[("q", "Masukkan username atau email", None, "text")],
        build=lambda v: [v["q"], "--show-urls"]),
    "blackbird": dict(
        title="Blackbird", group="Username & Sosial", bins=["blackbird"], inter=False,
        git=dict(url="https://github.com/p1ngul1n0/blackbird.git", dir="blackbird", entry="blackbird.py", req="requirements.txt"),
        about="Mencari akun berdasarkan username di ratusan situs memakai daftar WhatsMyName.",
        how="Input: username tanpa @. Hasil juga disimpan oleh tool di folder blackbird.",
        prompts=[("user", "Masukkan username (contoh: budi123)", None, "user")],
        build=lambda v: ["-u", v["user"]]),
    "phoneinfoga": dict(
        title="PhoneInfoga", group="Telepon", bins=["phoneinfoga"], sys={"brew": "phoneinfoga"},
        rel=dict(repo="sundowndev/phoneinfoga"),
        about="Memindai nomor telepon internasional: format, operator, negara, dan pencarian jejak publik.",
        how="Input: nomor format internasional (+6281234567890) atau diawali 0 untuk Indonesia.",
        prompts=[("num", "Masukkan nomor telepon (contoh: +6281234567890)", None, "phone")],
        build=lambda v: ["scan", "-n", v["num"]]),
    "dnsrecon": dict(
        title="DNSRecon", group="Domain & Jaringan", bins=["dnsrecon"], sys={"apt": "dnsrecon"}, pip=["dnsrecon"],
        about="Enumerasi DNS standar: SOA, NS, MX, A, AAAA, TXT, SRV, dan uji transfer zona.",
        how="Input: domain, contoh example.com.",
        prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")],
        build=lambda v: ["-d", v["domain"]]),
    "dnstwist": dict(
        title="dnstwist", group="Domain & Jaringan", bins=["dnstwist"], sys={"apt": "dnstwist"}, pip=["dnstwist"],
        about="Mendeteksi domain tiruan (typosquatting / phishing) yang sudah terdaftar mirip domain aslinya.",
        how="Input: domain milikmu atau yang ingin dilindungi, contoh example.com.",
        prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")],
        build=lambda v: ["--registered", v["domain"]]),
    "gau": dict(
        title="gau (GetAllUrls)", group="Domain & Jaringan", bins=["gau"], rel=dict(repo="lc/gau"),
        go="github.com/lc/gau/v2/cmd/gau", sys={"brew": "gau"},
        about="Mengambil semua URL lama sebuah domain dari Wayback Machine, Common Crawl, dan OTX (pasif).",
        how="Input: domain, contoh example.com. Hasil bisa panjang; salinan disimpan otomatis.",
        prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")],
        build=lambda v: [v["domain"]]),
    "waybackurls": dict(
        title="waybackurls", group="Domain & Jaringan", bins=["waybackurls"], rel=dict(repo="tomnomnom/waybackurls"),
        go="github.com/tomnomnom/waybackurls", sys={"brew": "waybackurls"},
        about="Mengambil daftar URL arsip sebuah domain dari Wayback Machine (pasif).",
        how="Input: domain, contoh example.com.",
        prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")],
        build=lambda v: [v["domain"]]),
    "whatweb": dict(
        title="WhatWeb", group="Domain & Jaringan", bins=["whatweb"], sys={"apt": "whatweb", "brew": "whatweb", "pkg": "whatweb"},
        manual="https://github.com/urbanadventurer/WhatWeb",
        about="Mengenali teknologi situs: CMS, framework, server, JavaScript, dan analytics.",
        how="Input: URL situs, contoh https://example.com.",
        prompts=[("url", "Masukkan URL situs (contoh: https://example.com)", None, "url")],
        build=lambda v: ["-a", "1", v["url"]]),
    "wafw00f": dict(
        title="wafw00f", group="Pemindaian (Izin Sah)", bins=["wafw00f"], sys={"apt": "wafw00f"}, pip=["wafw00f"], auth=True,
        about="Mendeteksi firewall aplikasi web (WAF) yang melindungi sebuah situs.",
        how="Input: URL situs berizin, contoh https://example.com.",
        prompts=[("url", "Masukkan URL situs (contoh: https://example.com)", None, "url")],
        build=lambda v: [v["url"]]),
    "spiderfoot": dict(
        title="SpiderFoot", group="Kerangka Kerja OSINT", bins=["spiderfoot"],
        git=dict(url="https://github.com/smicallef/spiderfoot.git", dir="spiderfoot", entry="sf.py", req="requirements.txt"),
        about="Mesin otomasi OSINT: memindai domain/IP/email secara pasif dari ratusan modul sumber data.",
        how="Input: target (domain, IP, atau email). Mode pasif: tidak menyentuh server target.",
        prompts=[("target", "Masukkan target (domain / IP / email)", None, "text")],
        build=lambda v: ["-s", v["target"], "-u", "passive", "-o", "tab", "-q"]),
    "reconng": dict(
        title="Recon-ng", group="Kerangka Kerja OSINT", bins=["recon-ng"], inter=True,
        git=dict(url="https://github.com/lanmaster53/recon-ng.git", dir="recon-ng", entry="recon-ng", req="REQUIREMENTS"),
        about="Framework recon modular bergaya Metasploit untuk pengumpulan informasi web.",
        how="Membuka konsol recon-ng. Ketik 'marketplace search' lalu 'help' untuk mulai.",
        prompts=[], build=lambda v: []),
    "shodan": dict(
        title="Shodan CLI", group="Intelijen Ancaman", bins=["shodan"], pip=["shodan", "setuptools<81"],
        about="Mesin pencari perangkat internet: info host, port terbuka, dan banner untuk sebuah IP.",
        how="Butuh API key gratis dari account.shodan.io. Mode 1 menyimpan key, mode 2 mengecek sebuah IP.",
        prompts=[("mode", "Mode: 1 = simpan API key (sekali saja)   2 = cek sebuah IP", "2", "num"),
                 ("key", "Tempel API key Shodan", None, "text", lambda v: v.get("mode") == "1"),
                 ("ip", "Masukkan alamat IP (contoh: 8.8.8.8)", None, "host", lambda v: v.get("mode") != "1")],
        build=lambda v: ["init", v["key"]] if v.get("mode") == "1" else ["host", v["ip"]]),
    "ffprobe": dict(
        title="FFprobe (FFmpeg)", group="Gambar, Video & Metadata", bins=["ffprobe"],
        sys={"apt": "ffmpeg", "pkg": "ffmpeg", "brew": "ffmpeg", "dnf": "ffmpeg", "pacman": "ffmpeg", "winget": "Gyan.FFmpeg"},
        manual="https://ffmpeg.org/download.html",
        about="Menganalisis file video/audio: codec, durasi, resolusi, bitrate, dan tag metadata (tanggal, perangkat).",
        how="Input: path file video/audio, contoh /sdcard/video.mp4.",
        prompts=[("path", "Masukkan path file video/audio", None, "file")],
        build=lambda v: ["-hide_banner", "-show_format", "-show_streams", "-pretty", v["path"]]),
    "ytdlp": dict(
        title="yt-dlp (Metadata Video)", group="Gambar, Video & Metadata", bins=["yt-dlp", "yt_dlp"], pip=["yt-dlp"],
        sys={"apt": "yt-dlp", "brew": "yt-dlp", "pkg": "yt-dlp"},
        about="Membaca metadata video YouTube/TikTok/IG dan situs lain tanpa mengunduh videonya.",
        how="Input: tautan video lengkap (https://...). Menampilkan kanal, tanggal unggah, statistik, dan deskripsi.",
        prompts=[("url", "Masukkan tautan video (https://...)", None, "url")],
        build=lambda v: ["--skip-download", "--no-warnings", "--no-playlist",
                         "--print", "Judul          : %(title)s",
                         "--print", "Kanal          : %(channel)s (%(channel_id)s)",
                         "--print", "Pengunggah     : %(uploader)s (%(uploader_id)s)",
                         "--print", "Tanggal unggah : %(upload_date)s",
                         "--print", "Durasi         : %(duration_string)s",
                         "--print", "Penayangan     : %(view_count)s",
                         "--print", "Suka           : %(like_count)s",
                         "--print", "Komentar       : %(comment_count)s",
                         "--print", "Kategori       : %(categories)s",
                         "--print", "Tag            : %(tags)s",
                         "--print", "Lokasi         : %(location)s",
                         "--print", "Ketersediaan   : %(availability)s",
                         "--print", "Tautan         : %(webpage_url)s",
                         "--print", "Deskripsi      : %(description).400s", v["url"]]),
}
import importlib.util


# =====================================================================
#  v3 - DASAR REGISTRY TOOL GITHUB: jenis tool, peringatan API (kuning), kunci API, prasyarat
#  Jenis tool (t["kind"]):
#    cli       program baris perintah (bawaan; bins / git / pip / rel / go seperti v2)
#    lib       pustaka Python: pip + pymod (nama import) + code (potongan Python yang membaca sys.argv[1:])
#    platform  aplikasi server/GUI berat (docker/manual): hanya panduan + opsi clone
#    data      kumpulan data / daftar (awesome-list, dataset): clone + baca README di terminal
#    dead      repo tidak ditemukan / tidak relevan: hanya info alasan (tidak bisa dipasang)
# =====================================================================
MOD_API = {}                      # kunci modul -> teks peringatan API (ditampilkan KUNING)
KEYS_FILE = os.path.join(DATA_DIR, "keys.json")
STATUS_INFO = {                   # status repo -> (label, warna)
    "aktif": ("aktif", G), "jarang": ("jarang diperbarui", Y), "usang": ("tidak aktif", Y),
    "arsip": ("diarsipkan", RD), "mati": ("repo tidak ditemukan", RD), "tidakrelevan": ("kurang relevan untuk OSINT", Y),
}


def _load_keys():
    try:
        with open(KEYS_FILE, "r", encoding="utf-8") as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except Exception:
        return {}


def api_key(name, label, url, env=None, required=True):
    """Ambil API key: env var -> berkas ~/.giga_osint/keys.json -> tanya pengguna (disimpan, izin 600).
    Mengembalikan string key, atau "" bila pengguna melewati."""
    env = env or (re.sub(r"[^A-Z0-9]", "_", name.upper()) + "_API_KEY")
    v = os.environ.get(env, "").strip()
    if v:
        return v
    keys = _load_keys()
    if keys.get(name):
        return keys[name]
    print()
    p_warn("%s membutuhkan API key (%s)." % (label, "wajib" if required else "opsional, tanpa key hasil terbatas"))
    p_info("Dapatkan key (umumnya gratis): %s" % url)
    p_info("Atau set variabel lingkungan %s sebelum menjalankan Giga OSINT." % env)
    v = (ask("Tempel API key %s  (Enter = lewati)" % label) or "").strip()
    if not v:
        return ""
    if re.search(r"\s", v) or len(v) < 6:
        p_warn("Key tampak tidak valid (ada spasi / terlalu pendek); tidak disimpan.")
        return ""
    keys[name] = v
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        with open(KEYS_FILE, "w", encoding="utf-8") as f:
            json.dump(keys, f, indent=2)
        try:
            os.chmod(KEYS_FILE, 0o600)
        except OSError:
            pass
        p_ok("Key disimpan di %s (izin 600). Hapus lewat menu Pengaturan > Kunci API." % KEYS_FILE)
    except OSError as e:
        p_warn("Key dipakai untuk sesi ini saja (gagal menyimpan: %s)." % e)
    return v


def GH(key, repo, group, title, about, how, **kw):
    """Daftarkan tool repo GitHub ke TOOLS. Kolom wajib: key, repo (owner/nama), group, title, about, how.
    Opsional: kind, status, last, why, api, pip, pymod, code, bins, git, rel, go, sys, py_min, needs, guide, note,
    manual, prompts, build, auth, inter, outcwd, order."""
    t = dict(title=title, group=group, repo=repo, about=about, how=how, prompts=[], build=(lambda v: []))
    t.update(kw)
    kind = t.setdefault("kind", "cli")
    t.setdefault("status", "aktif")
    if kind in ("cli",) and "bins" not in t:
        t["bins"] = [key]
    if kind in ("platform", "data", "dead", "lib"):
        t.setdefault("bins", [])
    if key in TOOLS:          # duplikat: biarkan yang lama
        return TOOLS[key]
    TOOLS[key] = t
    return t


def tool_api_note(t):
    return t.get("api") or ""


# ---------- prasyarat (go, node, docker, ...) ----------
PREREQ = {
    "git": dict(bins=["git"], label="Git", sys={"apt": "git", "brew": "git", "pkg": "git", "dnf": "git", "pacman": "git", "winget": "Git.Git"}),
    "go": dict(bins=["go"], label="Go", sys={"apt": "golang", "brew": "go", "pkg": "golang", "dnf": "golang", "pacman": "go", "winget": "GoLang.Go"}),
    "node": dict(bins=["node", "npm"], label="Node.js + npm", sys={"apt": "nodejs npm", "brew": "node", "pkg": "nodejs", "dnf": "nodejs npm", "pacman": "nodejs npm", "winget": "OpenJS.NodeJS"}),
    "docker": dict(bins=["docker"], label="Docker", sys={"apt": "docker.io", "brew": "--cask docker", "pkg": None, "dnf": "docker", "pacman": "docker", "winget": "Docker.DockerDesktop"},
                   manual="https://docs.docker.com/get-docker/"),
    "java": dict(bins=["java"], label="Java (JRE)", sys={"apt": "default-jre", "brew": "openjdk", "pkg": "openjdk-17", "dnf": "java-17-openjdk", "pacman": "jre-openjdk", "winget": "EclipseAdoptium.Temurin.17.JRE"}),
    "cargo": dict(bins=["cargo"], label="Rust (cargo)", sys={"apt": "cargo", "brew": "rust", "pkg": "rust", "dnf": "cargo", "pacman": "rust", "winget": "Rustlang.Rustup"}),
    "cmake": dict(bins=["cmake"], label="CMake", sys={"apt": "cmake", "brew": "cmake", "pkg": "cmake", "dnf": "cmake", "pacman": "cmake", "winget": "Kitware.CMake"}),
    "make": dict(bins=["make"], label="make / build tools", sys={"apt": "build-essential", "brew": "make", "pkg": "make clang", "dnf": "make gcc", "pacman": "base-devel"}),
    "ffmpeg": dict(bins=["ffmpeg"], label="FFmpeg", sys={"apt": "ffmpeg", "brew": "ffmpeg", "pkg": "ffmpeg", "dnf": "ffmpeg", "pacman": "ffmpeg", "winget": "Gyan.FFmpeg"}),
    "tesseract": dict(bins=["tesseract"], label="Tesseract OCR", sys={"apt": "tesseract-ocr", "brew": "tesseract", "pkg": "tesseract", "dnf": "tesseract", "pacman": "tesseract", "winget": "UB-Mannheim.TesseractOCR"}),
    "perl": dict(bins=["perl"], label="Perl", sys={"apt": "perl", "brew": "perl", "pkg": "perl", "dnf": "perl", "pacman": "perl"}),
    "pip": dict(bins=[], label="pip (Python)", pymod="pip"),
}


def prereq_ok(name):
    p = PREREQ.get(name)
    if not p:
        return True
    if p.get("pymod"):
        try:
            return importlib.util.find_spec(p["pymod"]) is not None
        except Exception:
            return False
    return all(shutil.which(b) for b in p["bins"])


def prereq_missing(t):
    return [n for n in t.get("needs", []) if not prereq_ok(n)]


def prereq_cmd(name):
    p = PREREQ[name]
    pm = pm_name()
    pk = (p.get("sys") or {}).get(pm)
    if not pk:
        return None
    return pm_install_cmd(pm, pk)


def prereq_panel(t):
    """Tampilkan status prasyarat; bila ada yang belum terpasang, tanya y/n untuk memasangnya. True = lanjut."""
    needs = t.get("needs", [])
    if not needs:
        return True
    rows = []
    for n in needs:
        ok = prereq_ok(n)
        rows.append("%s%s%s %s%-16s%s %s" % (G if ok else RD, GL["dot"] if ok else GL["cross"], R, W, PREREQ[n]["label"], R,
                                             (D + "terpasang" + R) if ok else (Y + "BELUM terpasang" + R)))
    sys.stdout.write("\n".join(panel("PEMERIKSAAN PRASYARAT", rows)) + "\n")
    for n in prereq_missing(t):
        cmd = prereq_cmd(n)
        pr = PREREQ[n]
        if not cmd:
            p_warn("%s belum ada dan tidak bisa dipasang otomatis di sistem ini." % pr["label"])
            if pr.get("manual"):
                p_info("Unduh/panduan: " + pr["manual"])
            if not yes_no("Lanjut tanpa %s (mungkin gagal)?" % pr["label"]):
                return False
            continue
        p_info("%s dibutuhkan. Perintah pemasangan: %s" % (pr["label"], cmd))
        if yes_no("Pasang %s sekarang?" % pr["label"]):
            try:
                subprocess.call(cmd, shell=True)
            except KeyboardInterrupt:
                p_warn("Dihentikan.")
                return False
            refresh_path()
            if prereq_ok(n):
                p_ok("%s terpasang." % pr["label"])
            else:
                p_warn("%s belum terdeteksi. Buka ulang terminal lalu coba lagi." % pr["label"])
                if not yes_no("Tetap lanjut?"):
                    return False
        elif not yes_no("Lanjut tanpa %s (mungkin gagal)?" % pr["label"]):
            return False
    return True


# ---------- tool jenis 'lib' (pustaka Python) ----------
_find_tool_v2 = find_tool


def find_tool(t):
    if t.get("kind") == "lib":
        try:
            if importlib.util.find_spec(t["pymod"]) is not None:
                return [sys.executable, "-c", t["code"]], None
        except Exception:
            pass
        return None
    if t.get("kind") in ("platform", "data", "dead"):
        g = t.get("git")
        if g:
            d = os.path.join(TOOLS_DIR, g["dir"])
            if os.path.isdir(os.path.join(d, ".git")) or os.path.isdir(d):
                return [sys.executable], d
        return None
    return _find_tool_v2(t)


# =====================================================================
#  v3 - MENJALANKAN TOOL: tidak pernah menggantung, selalu ada jalan keluar dan keluaran jelas
# =====================================================================
EXIT_HINTS = {
    "spiderfoot": "Server web SpiderFoot berjalan: buka alamat yang tampil di browser. Tekan Ctrl+C di sini untuk menghentikan server dan kembali.",
    "reconng": "Ketik exit lalu Enter untuk keluar dari recon-ng (atau tekan Ctrl+D). Ketik help untuk daftar perintah.",
    "mrholmes": "Pakai menu Mr.Holmes; pilih opsi keluar di menunya, atau tekan Ctrl+C untuk kembali ke Giga OSINT.",
    "maltego": "Maltego adalah aplikasi jendela: tutup jendelanya untuk kembali, atau tekan Ctrl+C di sini.",
    "nxa": "Pilih opsi keluar (0) di menu NXA, atau tekan Ctrl+C untuk kembali ke Giga OSINT.",
}
DEFAULT_EXIT_HINT = "Ketik exit atau quit, atau tekan Ctrl+C / Ctrl+D untuk keluar dari tool dan kembali ke Giga OSINT."

_install_tool_v2 = install_tool
_clean_input_v2 = clean_input
_tool_source_v2 = tool_source


def tool_source(t):
    if t.get("repo"):
        return "https://github.com/" + t["repo"]
    return _tool_source_v2(t)


def clean_input(kind, v):
    if kind == "repo":
        s = (v or "").strip().rstrip("/")
        m = re.match(r"^(?:https?://)?(?:www\.)?github\.com/([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?(?:/.*)?$", s, re.I)
        if not m:
            m = re.match(r"^([A-Za-z0-9_.-]+)/([A-Za-z0-9_.-]+?)(?:\.git)?$", s)
        if m and not m.group(1).startswith("-") and not m.group(2).startswith("-"):
            return True, "https://github.com/%s/%s" % (m.group(1), m.group(2)), ""
        return False, s, "contoh yang benar: owner/repo atau https://github.com/owner/repo"
    return _clean_input_v2(kind, v)


def _refresh_python_paths():
    importlib.invalidate_caches()
    try:
        import site
        us = site.getusersitepackages()
        if us and os.path.isdir(us) and us not in sys.path:
            site.addsitedir(us)
    except Exception:
        pass
    importlib.invalidate_caches()


def install_tool(t):
    """Pasang tool: periksa prasyarat (y/n) lalu jalankan rencana instalasi v2."""
    if not prereq_panel(t):
        return False
    ok = _install_tool_v2(t)
    _refresh_python_paths()
    return ok


def fmt_secs(x):
    return ("%.1f dtk" % x) if x < 60 else ("%d mnt %d dtk" % (x // 60, x % 60))


def run_cmd(argv, cwd=None, interactive=False, log_name="hasil", hint=None):
    """Jalankan perintah. Non-interaktif: stdin ditutup (tak mungkin menggantung menunggu ketikan), keluaran
    ditampilkan langsung (merah), disimpan ke log, ada pemberitahuan bila diam lama atau tanpa keluaran."""
    env = dict(os.environ)
    env.setdefault("PYTHONUNBUFFERED", "1")
    env.setdefault("PYTHONIOENCODING", "utf-8")
    t0 = time.time()
    if interactive or not TTY or not hasattr(sys.stdout, "buffer"):
        if interactive and TTY:
            print("  %s%s%s %sMasuk ke tool.%s %s%s%s" % (gc(0.0), GL["info"], R, W + B, R, Y, hint or DEFAULT_EXIT_HINT, R))
            print()
        try:
            rc = subprocess.call(argv, cwd=cwd, env=env, stdin=(None if interactive else subprocess.DEVNULL))
        except KeyboardInterrupt:
            print()
            p_warn("Dihentikan oleh pengguna (Ctrl+C).")
            rc = 130
        except OSError as e:
            p_err("Gagal menjalankan: %s" % e)
            rc = 127
        if interactive and TTY:
            print()
            p_ok("Kembali ke Giga OSINT (setelah %s)." % fmt_secs(time.time() - t0))
        return rc, None
    os.makedirs(OUT_DIR, exist_ok=True)
    path = os.path.join(OUT_DIR, "%s-%s.txt" % (re.sub(r"[^A-Za-z0-9_.-]", "_", log_name), time.strftime("%Y%m%d-%H%M%S")))
    try:
        proc = subprocess.Popen(argv, cwd=cwd, env=env, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    except OSError as e:
        p_err("Gagal menjalankan: %s" % e)
        return 127, None
    print("  %sBerjalan. Tekan Ctrl+C untuk menghentikan dan kembali ke menu.%s\n" % (D, R))
    st = {"bytes": 0, "lines": 0, "last": time.time(), "done": False, "warned": 0.0}
    lock = threading.Lock()

    def watchdog():
        while not st["done"]:
            time.sleep(1.0)
            now = time.time()
            if st["done"]:
                return
            quiet = now - st["last"]
            if quiet >= 12 and now - st["warned"] >= 15:
                st["warned"] = now
                with lock:
                    sys.stdout.write("\n  %s%s Tool masih berjalan (%s) tetapi belum ada keluaran baru. Ini normal untuk proses lama; "
                                     "tekan Ctrl+C bila ingin berhenti.%s\n" % (Y, GL["warn"], fmt_secs(now - t0), R))
                    sys.stdout.flush()
    wd = threading.Thread(target=watchdog, daemon=True)
    wd.start()
    tint = {"open": False}
    interrupted = False
    try:
        with open(path, "wb") as lf:
            reader = getattr(proc.stdout, "read1", None) or proc.stdout.read
            while True:
                chunk = reader(4096)
                if not chunk:
                    break
                st["last"] = time.time()
                st["bytes"] += len(chunk)
                st["lines"] += chunk.count(b"\n")
                with lock:
                    sys.stdout.buffer.write(tint_bytes(chunk, tint))
                    sys.stdout.buffer.flush()
                lf.write(ANSI_B.sub(b"", chunk))
        proc.wait()
    except KeyboardInterrupt:
        interrupted = True
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except Exception:
            try:
                proc.kill()
            except Exception:
                pass
        print()
        p_warn("Dihentikan oleh pengguna (Ctrl+C).")
    finally:
        st["done"] = True
        if tint["open"]:
            sys.stdout.buffer.write(b"\033[0m")
            sys.stdout.buffer.flush()
    rc = proc.returncode
    el = fmt_secs(time.time() - t0)
    print()
    if interrupted:
        p_info("Berhenti setelah %s; keluaran sebagian tersimpan." % el)
    elif st["bytes"] == 0:
        p_warn("Tool selesai dalam %s TANPA keluaran apa pun (kode %s)." % (el, rc))
        p_info("Artinya biasanya: tidak ada hasil untuk input ini, tool butuh API key/akun, atau input kurang tepat.")
        p_info("Coba: input lain, jalankan ulang dengan argumen --help, atau buka Pusat Bantuan (tombol b) > Diagnosa.")
    else:
        p_ok("Selesai dalam %s  %s  %d baris keluaran  %s  kode %s" % (el, GL["sep"], st["lines"], GL["sep"], rc))
    return rc, path


# ---------- kartu tool (peringatan API kuning, status, versi Python) ----------
def tool_card(t, key=None):
    lines = [CY + "Tentang    " + R + W + t["about"] + R,
             CY + "Cara input " + R + W + t["how"] + R,
             CY + "Sumber     " + R + D + tool_source(t) + R]
    lab, col = STATUS_INFO.get(t.get("status", "aktif"), ("aktif", G))
    meta = "%s%s %s%s" % (col, GL["dot"], lab, R)
    if t.get("last"):
        meta += "%s   commit terakhir %s%s" % (D, t["last"], R)
    lines.append(CY + "Status     " + R + meta)
    if t.get("why"):
        lines.append(Y + "Catatan    " + R + Y + t["why"] + R)
    if t.get("api"):
        lines.append(Y + "PERINGATAN " + R + Y + t["api"] + R)
    pm = t.get("py_min")
    if pm and sys.version_info[:2] < tuple(pm):
        lines.append(Y + "Python     " + R + Y + "Tool ini butuh Python %d.%d atau lebih baru; perangkat Anda memakai %s." % (pm[0], pm[1], SYS["py"]) + R)
    if t.get("note"):
        lines.append(D + "Tips       " + R + D + t["note"] + R)
    return lines


def _clone_spec(t):
    g = t.get("git")
    if g:
        return g["url"], g["dir"]
    repo = t.get("repo", "")
    return "https://github.com/%s.git" % repo, repo.split("/")[-1]


def _clone_repo(t):
    git = shutil.which("git")
    if not git:
        p_warn("Git belum terpasang.")
        if not prereq_panel(dict(needs=["git"])):
            return None
        git = shutil.which("git")
        if not git:
            p_err("Git tetap tidak ditemukan. Buka ulang terminal lalu coba lagi.")
            return None
    url, d = _clone_spec(t)
    dest = os.path.join(TOOLS_DIR, d)
    os.makedirs(TOOLS_DIR, exist_ok=True)
    if os.path.isdir(dest):
        p_ok("Folder sudah ada: %s" % dest)
        return dest
    rc, tail = run_quiet([git, "clone", "--depth", "1", url, dest], "Mengunduh %s" % url)
    if rc != 0:
        p_err("Gagal mengunduh repo (kode %s)." % rc)
        for ln in (tail or [])[-4:]:
            print("    " + D + ln + R)
        p_info("Penyebab umum: tidak ada internet, GitHub diblokir jaringan, atau repo dipindah/dihapus. Coba lagi atau buka Pusat Bantuan (b).")
        return None
    p_ok("Repo tersimpan di: %s" % dest)
    return dest


def guide_flow(key):
    """Tool jenis platform/data/dead: panduan langkah, pemeriksaan prasyarat, clone, dan baca README di terminal."""
    t = TOOLS[key]
    kind = t.get("kind")
    if kind == "dead":
        p_warn("Repo ini tidak bisa dipasang: %s" % (t.get("why") or "tidak ditemukan"))
        if t.get("alt"):
            p_info("Penggantinya yang ditemukan: https://github.com/%s" % t["alt"])
        open_choices([("Halaman repo di GitHub (pratinjau terminal)", "https://github.com/" + t["repo"])])
        return
    steps = t.get("guide") or []
    if steps:
        rows = []
        for i, (ttl, txt) in enumerate(steps, 1):
            rows.append("%s[%s%d%s]%s %s%s%s" % (W, Y, i, W, R, W + B, ttl, R))
            for ln in wrap_ansi(txt, max(24, content_w() - 10)):
                rows.append("     " + G + ln + R)
        sys.stdout.write("\n".join(panel("PANDUAN LANGKAH", rows)) + "\n")
    prereq_panel(t)
    while True:
        print()
        print("  %s %sPasang / unduh repo ke perangkat ini (git clone)%s" % (num_tag(1), W, R))
        print("  %s %sBaca README di terminal%s" % (num_tag(2), W, R))
        print("  %s %sTampilkan perintah yang bisa disalin%s" % (num_tag(3), W, R))
        print("  %s %sKembali%s" % (num_tag(0), W, R))
        c = ask("Pilih nomor")
        if c is None or c == "0":
            return
        if c == "1":
            dest = _clone_repo(t)
            if dest:
                p_info("Langkah berikutnya: ikuti panduan langkah di atas dari folder %s" % dest)
        elif c == "2":
            repo = t.get("repo", "")
            for fn in ("README.md", "README.rst", "README"):
                st, _, _ = http("https://raw.githubusercontent.com/%s/HEAD/%s" % (repo, fn), timeout=15)
                if st == 200:
                    peek("https://raw.githubusercontent.com/%s/HEAD/%s" % (repo, fn), label="README " + t["title"])
                    break
            else:
                peek("https://github.com/" + repo, label=t["title"])
        elif c == "3":
            url, d = _clone_spec(t)
            sec("Perintah (salin dan tempel di terminal)")
            print("  git clone --depth 1 %s" % url)
            for ttl, txt in steps:
                if re.match(r"^[a-z]+ ", txt or "") or "&&" in (txt or ""):
                    print("  # %s" % ttl)
                    print("  %s" % txt)
        else:
            p_warn("Pilihan tidak valid.")


def _generic_cli(t, found, key):
    base = found[0]
    sec("Bantuan tool (--help)")
    rc, _ = run_cmd(base + ["--help"], cwd=found[1], log_name=key + "-help")
    if rc not in (0, None):
        run_cmd(base + ["-h"], cwd=found[1], log_name=key + "-help")
    while True:
        s = ask("Ketik argumen untuk %s (lihat contoh di bantuan di atas). Enter atau 0 = selesai" % t["title"])
        if not s or s == "0":
            return
        try:
            args = shlex.split(s)
        except ValueError as e:
            p_warn("Tanda kutip tidak seimbang: %s" % e)
            continue
        print("\n  %sPerintah%s : %s%s%s\n" % (CY, R, G, " ".join(shlex.quote(a) for a in base + args), R))
        run_cmd(base + args, cwd=found[1], log_name=key)


def run_tool(key, preset=None):
    t = TOOLS[key]
    print()
    sys.stdout.write("\n".join(panel(t["title"], tool_card(t, key))) + "\n")
    exit_notice()
    kind = t.get("kind", "cli")
    if kind in ("platform", "data", "dead"):
        guide_flow(key)
        return
    if t.get("auth") and not preset and not authorize():
        p_warn("Dibatalkan. Izin sah wajib dikonfirmasi.")
        return
    pm = t.get("py_min")
    if pm and sys.version_info[:2] < tuple(pm) and not yes_no("Versi Python Anda lebih lama dari yang dibutuhkan. Tetap coba lanjutkan"):
        return
    found = find_tool(t)
    if not found:
        p_warn("%s belum terpasang di perangkat ini." % t["title"])
        if not install_tool(t):
            p_info("Pemasangan dibatalkan / gagal. Lihat Pusat Bantuan (tombol b) untuk solusi masalah instalasi.")
            return
        found = find_tool(t)
        if not found:
            p_err("Tool tidak ditemukan setelah instalasi. Buka ulang terminal lalu coba lagi (PATH mungkin belum diperbarui).")
            p_info("Solusi lengkap: Pusat Bantuan (tombol b) > Masalah umum > 'perintah tidak ditemukan setelah instal'.")
            return
    if kind == "lib" and not t.get("prompts"):
        argv = found[0]
    elif kind == "cli" and not t.get("prompts") and not t.get("inter"):
        _generic_cli(t, found, key)
        return
    else:
        argv = None
    vals = dict(preset or {})
    for pr in t.get("prompts", []):
        k, label, default, pkind = pr[0], pr[1], pr[2], pr[3]
        when = pr[4] if len(pr) > 4 else None
        if k in vals or (when and not when(vals)):
            continue
        while True:
            v = ask(label + ("  [Enter = %s]" % default if default else "") + "  (0 = batal)")
            if v is None or v == "0":
                p_warn("Dibatalkan.")
                return
            if v == "" and default:
                v = default
            ok, cleaned, hint = clean_input(pkind, v)
            if ok:
                vals[k] = cleaned
                break
            p_warn("Input tidak valid: %s" % hint)
    if argv is None:
        argv = found[0] + t["build"](vals)
    print("\n  %sPerintah%s : %s%s%s\n" % (CY, R, G, " ".join(shlex.quote(a) for a in argv), R))
    cwd = found[1]
    if t.get("outcwd"):
        os.makedirs(OUT_DIR, exist_ok=True)
        cwd = OUT_DIR
        if found[1]:
            argv = [argv[0], os.path.join(found[1], t["git"]["entry"])] + argv[2:]
    try:
        rc, logp = run_cmd(argv, cwd=cwd, interactive=bool(t.get("inter")), log_name=key,
                           hint=EXIT_HINTS.get(key) if t.get("inter") else None)
    except Exception as e:
        p_err("Gagal menjalankan: %s" % e)
        return
    if rc not in (0, None, 130):
        p_warn("Tool selesai dengan kode %s. Bila ada pesan galat di atas: periksa input, pasang ulang tool, atau buka Pusat Bantuan (b)." % rc)
    if logp:
        p_ok("Salinan hasil tersimpan: %s" % logp)
    if t.get("outcwd"):
        p_info("File keluaran tool (bila ada) disimpan di: %s" % OUT_DIR)

# data status repo (hasil verifikasi git ls-remote + clone dangkal, 5 Nov 2026)
GH_STAT = {"khast3x/h8mail":["usang","2022-06-25"],
"antoniaci/blackbird":["aktif","2026-11-03"],
"instaloader/instaloader":["aktif","2026-11-01"],
"OWASP/www-project-social-osint-agent":["aktif","2026-04-28"],
"ArthurHeitmann/arctic_shift":["aktif","2026-10-11"],
"praw-dev/praw":["aktif","2026-11-05"],
"DocNow/twarc":["jarang","2025-10-31"],
"halcy/Mastodon.py":["aktif","2026-10-29"],
"bluesky-social/atproto":["aktif","2026-11-05"],
"yt-dlp/yt-dlp":["aktif","2026-11-04"],
"davidteather/TikTok-Api":["aktif","2026-08-23"],
"DIYgod/RSSHub":["aktif","2026-11-05"],
"discourse/discourse":["aktif","2026-11-05"],
"LemmyNet/lemmy":["aktif","2026-11-04"],
"HackerNews/API":["jarang","2025-01-01"],
"element-hq/element-web":["aktif","2026-11-05"],
"zulip/zulip":["aktif","2026-11-05"],
"mattermost/mattermost":["aktif","2026-11-05"],
"Tyrrrz/DiscordChatExporter":["aktif","2026-11-04"],
"matrix-org/matrix-js-sdk":["aktif","2026-11-04"],
"FreshRSS/FreshRSS":["aktif","2026-11-02"],
"miniflux/v2":["aktif","2026-11-03"],
"RSS-Bridge/rss-bridge":["aktif","2026-11-03"],
"huginn/huginn":["aktif","2026-11-05"],
"streamlink/streamlink":["aktif","2026-11-02"],
"PythonistaGuild/TwitchIO":["aktif","2026-10-03"],
"Owez/yark":["aktif","2025-12-17"],
"jdepoix/youtube-transcript-api":["aktif","2026-11-03"],
"egbertbouman/pytchat":["mati",""],
"FFmpeg/FFmpeg":["aktif","2026-11-05"],
"openai/whisper":["aktif","2026-08-31"],
"ggml-org/whisper.cpp":["aktif","2026-11-05"],
"bibanon/tubeup":["aktif","2026-10-26"],
"MobSF/Mobile-Security-Framework-MobSF":["aktif","2026-11-04"],
"Exodus-Privacy/exodus":["aktif","2026-09-13"],
"skylot/jadx":["aktif","2026-11-02"],
"iBotPeaches/Apktool":["aktif","2026-10-28"],
"androguard/androguard":["aktif","2026-10-25"],
"frida/frida":["aktif","2026-11-04"],
"sensepost/objection":["aktif","2026-10-27"],
"mvt-project/mvt":["aktif","2026-10-29"],
"facundoolano/app-store-scraper":["jarang","2025-07-27"],
"JoMingyu/google-play-scraper":["usang","2024-06-07"],
"MISP/MISP":["aktif","2026-11-01"],
"OpenCTI-Platform/opencti":["aktif","2026-11-05"],
"intelowlproject/IntelOwl":["aktif","2026-09-02"],
"mitre-attack/attack-stix-data":["aktif","2026-10-13"],
"SigmaHQ/sigma":["aktif","2026-11-05"],
"VirusTotal/yara":["aktif","2026-10-27"],
"VirusTotal/yara-x":["aktif","2026-11-05"],
"CVEProject/cvelistV5":["aktif","2026-11-05"],
"google/osv-scanner":["aktif","2026-11-05"],
"cisagov/known-exploited-vulnerabilities-catalog":["mati",""],
"owasp-amass/amass":["aktif","2026-10-25"],
"rthalley/dnspython":["aktif","2026-11-04"],
"john-kurkowski/tldextract":["aktif","2026-10-04"],
"CaliDog/certstream-python":["usang","2021-08-12"],
"projectdiscovery/subfinder":["aktif","2026-11-05"],
"nttgin/BGPalerter":["jarang","2025-08-07"],
"secynic/ipwhois":["usang","2024-10-15"],
"joepie91/python-whois":["usang","2014-07-30"],
"aquasecurity/trivy":["aktif","2026-11-05"],
"zeek/zeek":["aktif","2026-11-04"],
"qgis/QGIS":["aktif","2026-11-05"],
"geopandas/geopandas":["aktif","2026-10-31"],
"gboeing/osmnx":["aktif","2026-07-31"],
"opengeos/leafmap":["aktif","2026-10-31"],
"gee-community/geemap":["aktif","2026-11-04"],
"keplergl/kepler.gl":["aktif","2026-11-05"],
"CesiumGS/cesium":["aktif","2026-11-04"],
"OSGeo/gdal":["aktif","2026-11-03"],
"rasterio/rasterio":["aktif","2026-11-02"],
"jblindsay/whitebox-tools":["aktif","2026-05-26"],
"exiftool/exiftool":["aktif","2026-10-28"],
"tesseract-ocr/tesseract":["aktif","2026-11-02"],
"JaidedAI/EasyOCR":["aktif","2025-12-05"],
"PaddlePaddle/PaddleOCR":["aktif","2026-09-16"],
"MediaArea/MediaInfo":["aktif","2026-11-05"],
"ImageMagick/ImageMagick":["aktif","2026-11-04"],
"opencv/opencv":["aktif","2026-11-05"],
"contentauth/c2pa-rs":["aktif","2026-11-04"],
"apache/tika":["aktif","2026-11-04"],
"gildas-lormeau/SingleFile":["aktif","2026-11-05"],
"OpenRefine/OpenRefine":["aktif","2026-11-04"],
"pandas-dev/pandas":["aktif","2026-11-04"],
"pola-rs/polars":["aktif","2026-11-05"],
"duckdb/duckdb":["aktif","2026-11-05"],
"networkx/networkx":["aktif","2026-11-04"],
"WestHealth/pyvis":["usang","2023-02-10"],
"explosion/spaCy":["aktif","2026-10-27"],
"UKPLab/sentence-transformers":["aktif","2026-11-04"],
"simonw/datasette":["aktif","2026-11-01"],
"google/timesketch":["aktif","2026-11-03"],
"lockfale/OSINT-Framework":["aktif","2026-10-22"],
"bellingcat/toolkit":["aktif","2026-11-02"],
"alephdata/aleph":["aktif","2025-12-19"],
"opensanctions/followthemoney":["aktif","2026-11-02"],
"AccentuSoft/LinkScope_Client":["jarang","2025-02-06"],
"flowsint/flowsint":["mati",""],
"ArchiveBox/ArchiveBox":["aktif","2026-11-03"],
"webrecorder/browsertrix":["aktif","2026-11-03"],
"29a/chrome-forensics":["mati",""],
"sleuthkit/autopsy":["aktif","2026-05-04"],
"volatilityfoundation/volatility3":["aktif","2026-10-12"],
"Yamato-Security/hayabusa":["aktif","2026-11-04"],
"WithSecureLabs/chainsaw":["aktif","2026-10-14"],
"simsong/bulk_extractor":["aktif","2026-10-11"],
"ReFirmLabs/binwalk":["aktif","2026-08-11"],
"CesiumGS/cesium-native":["aktif","2026-11-04"],
"pixelbubble/ProtOSINT":["aktif","2026-07-19"],
"ThoughtfulDev/EagleEye":["usang","2021-10-19"],
"kpcyrd/sn0int":["aktif","2026-09-20"],
"iojw/socialscan":["usang","2024-01-20"],
"osintshifu/awesome-osint-repos":["aktif","2026-11-05"],
"OpenOSINT/OpenOSINT":["aktif","2026-11-05"],
"djbpm/osint-toolkit":["aktif","2026-02-11"],
"4CAT4/4CAT":["mati",""],
"mediacloud/MediaCloud":["usang","2022-01-28"],
"mediacloud/api":["mati",""],
"ICIJ/datashare":["aktif","2026-11-04"],
"ICIJ/rigour":["mati",""],
"opensanctions/opensanctions":["aktif","2026-11-05"],
"opensanctions/yente":["aktif","2026-11-03"],
"opencorporates/opencorporates":["mati",""],
"WorldMonitor/WorldMonitor":["mati",""],
"Recon-ng/recon-ng":["mati",""],
"blacklanternsecurity/bbot":["aktif","2026-08-24"],
"yogeshojha/rengine":["aktif","2025-11-16"],
"shmilylty/OneForAll":["aktif","2026-11-02"],
"Findomain/Findomain":["aktif","2026-11-02"],
"aboul3la/Sublist3r":["usang","2020-07-29"],
"dnstwist/dnstwist":["mati",""],
"s0md3v/Photon":["aktif","2026-10-18"],
"jaeles-project/gospider":["usang","2024-03-22"],
"projectdiscovery/dnsx":["aktif","2026-11-02"],
"projectdiscovery/chaos-client":["aktif","2026-11-05"],
"projectdiscovery/alterx":["aktif","2026-11-05"],
"projectdiscovery/uncover":["aktif","2026-11-05"],
"projectdiscovery/naabu":["aktif","2026-11-02"],
"projectdiscovery/httpx":["aktif","2026-11-05"],
"projectdiscovery/katana":["aktif","2026-11-05"],
"projectdiscovery/mapcidr":["aktif","2026-10-31"],
"projectdiscovery/cdncheck":["aktif","2026-11-05"],
"projectdiscovery/tlsx":["aktif","2026-11-03"],
"unclecode/crawl4ai":["aktif","2026-11-04"],
"apify/crawlee":["aktif","2026-11-05"],
"scrapinghub/portia":["usang","2019-07-10"],
"internetarchive/heritrix3":["aktif","2026-11-05"],
"internetarchive/warcprox":["aktif","2026-05-11"],
"ArchiveTeam/grab-site":["jarang","2025-05-23"],
"webrecorder/pywb":["aktif","2026-11-04"],
"webrecorder/warcio":["aktif","2026-10-28"],
"webrecorder/browsertrix-crawler":["aktif","2026-11-03"],
"ivbeg/awesome-italian-news":["mati",""],
"GoogleTrends/data":["jarang","2025-10-06"],
"gsantopaolo/gdelt":["mati",""],
"opensources/awesome-public-apis":["mati",""],
"OWASP/ThreatDragon":["mati",""],
"OWASP/CheatSheetSeries":["aktif","2026-11-03"],
"ossf/scorecard":["aktif","2026-11-05"],
"ossf/malicious-packages":["aktif","2026-11-05"],
"anchore/grype":["aktif","2026-11-04"],
"anchore/syft":["aktif","2026-11-04"],
"DependencyTrack/dependency-track":["aktif","2026-11-04"],
"semgrep/semgrep":["aktif","2026-11-02"],
"securego/gosec":["aktif","2026-11-03"],
"mitre/caldera":["aktif","2026-08-26"],
"mitre/cti":["aktif","2026-10-13"],
"mandiant/capa":["aktif","2026-11-03"],
"mandiant/flare-floss":["aktif","2026-10-22"],
"mandiant/flare-vm":["aktif","2026-10-07"],
"mandiant/flare-emu":["jarang","2025-08-05"],
"blacktop/ipsw":["aktif","2026-11-05"],
"blacktop/ipsw-diffs":["aktif","2026-11-04"],
"fox-it/dissect":["aktif","2026-11-01"],
"fox-it/mitm6":["usang","2022-02-22"],
"fox-it/BloodHound.py":["aktif","2026-10-23"],
"fox-it/monkey365":["mati",""],
"WithSecureLabs/usbarmory":["mati",""],
"stratosphereips/StratosphereLinuxIPS":["aktif","2026-09-30"],
"activecm/rita":["aktif","2026-06-17"],
"ntop/nDPI":["aktif","2026-11-03"],
"ntop/ntopng":["aktif","2026-11-05"],
"CIRCL/hashlookup":["mati",""],
"CIRCL/PyMISP":["mati",""],
"CIRCL/vulnerability-lookup":["mati",""],
"CIRCL/AIL-framework":["aktif","2026-11-05"],
"CIRCL/stix2":["mati",""],
"MISP/misp-galaxy":["aktif","2026-11-02"],
"MISP/misp-taxonomies":["aktif","2026-10-11"],
"mitre/attack-navigator":["usang","2018-12-17"],
"elastic/detection-rules":["aktif","2026-11-05"],
"elastic/security-docs":["aktif","2026-10-26"],
"StratosphereLinuxIPS/StratosphereLinuxIPS":["mati",""],
"inspektor-gadget/inspektor-gadget":["aktif","2026-11-05"],
"derailed/k9s":["aktif","2026-11-03"],
"kubernetes/kube-state-metrics":["aktif","2026-11-05"],
"aquasecurity/kube-bench":["aktif","2026-10-05"],
"aquasecurity/kube-hunter":["usang","2024-03-19"],
"fkie-cad/nvd-json-data-feeds":["aktif","2026-11-05"],
"cisagov/decider":["jarang","2025-04-01"],
"cisagov/ScubaGear":["aktif","2026-11-04"],
"cisagov/RedEye":["usang","2023-10-20"],
"cisagov/Maritime-Security":["mati",""],
"aircrack-ng/aircrack-ng":["aktif","2026-10-09"],
"wireshark/wireshark":["aktif","2026-11-05"],
"OWASP/Amass":["aktif","2026-10-25"],
"ayaavdews/AppCekOngkir":["usang","2020-08-24"],
"pentagonal/Indonesia-Postal-Code":["usang","2022-07-29"],
"rfahmi/kode-pos-indonesia":["usang","2019-09-20"],
"erlange/Kodepos-Wilayah-Indonesia":["usang","2021-12-28"],
"bachors/Kode-Pos-API":["usang","2017-05-03"],
"w3appdev/kodepos":["usang","2023-05-19"],
"im-hanzou/cekrekening":["jarang","2025-01-28"],
"zifaucode/cek-lulus":["aktif","2026-07-29"],
"galihazizif/mutasi-bni":["usang","2019-07-02"],
"namtxs/cek-nik":["usang","2020-03-19"],
"izulwahidin/mutasi-qris.id":["jarang","2024-11-28"],
"ilhamjaya08/cek-username":["usang","2024-06-11"],
"hajirodeon/cekresi":["usang","2018-03-08"],
"arief125/ceksubs":["usang","2019-08-02"],
"sandrocods/API-Cek":["usang","2023-03-27"],
"bachors/Android-Hybrid-Cek-NISN":["usang","2017-05-05"],
"OSINT-mindset/pinterest-email-checker":["usang","2022-10-02"],
"bugr7/osint-tool":["jarang","2025-11-03"],
"initstring/linkedin2username":["aktif","2026-05-21"],
"ismailtsdln/NebulaOSINT":["aktif","2026-01-11"],
"brainphreak/hacker-game-suite":["aktif","2025-11-30"],
"Berchez/SteamReveal":["aktif","2026-10-28"],
"defaultnamehere/tinder-detective":["usang","2018-03-05"],
"thewhiteh4t/pwnedOrNot":["aktif","2026-03-28"],
"kinghacker0/WhatsApp-OSINT":["jarang","2025-10-16"],
"6abd/horus":["aktif","2026-07-29"],
"yezz123/SoIG":["aktif","2026-06-28"],
"xray-web/web-check-api":["usang","2024-07-07"],
"The-Osint-Toolbox/OSINT-Toolbox-Peripherals":["aktif","2026-08-09"],
"XyasZor/Genetic":["aktif","2026-11-02"],
"XyasZor/nxa":["aktif","2026-11-02"]}


# =====================================================================
#  v3 - REGISTRY TOOL GITHUB (diverifikasi 5 Nov 2026: git ls-remote + clone dangkal + PyPI + struktur repo)
#  Status: aktif <= 365 hari sejak commit terakhir, jarang <= 730 hari, usang > 730 hari, mati = repo tidak ditemukan.
# =====================================================================
SUB_U = "Username & Akun Sosial"
SUB_E = "Email, Kebocoran & Kredensial"
SUB_D = "Domain, Subdomain & DNS"
SUB_N = "Jaringan, IP & Infrastruktur"
SUB_C = "Crawler, Scraper & Arsip Web"
SUB_V = "Video, Audio & Streaming"
SUB_I = "Gambar, OCR & Metadata Berkas"
SUB_G = "Geospasial & Peta"
SUB_A = "Analisis Data, Grafik & NLP"
SUB_T = "Threat Intel & Kerentanan"
SUB_F = "Forensik, Malware & Reverse Engineering"
SUB_M = "Aplikasi Mobile & Android"
SUB_K = "Kerangka OSINT & Platform Investigasi"
SUB_ID = "Data & Layanan Indonesia"
SUB_P = "Platform Komunitas, Feed & Pesan"
SUB_S = "Pemindai Keamanan, Cloud & Kontainer"
SUB_X = "Pemeriksa Repo (Genetic) & NXA"
SUB_Z = "Tidak Aktif, Arsip & Tidak Relevan"
GH_SUBS = [
    (SUB_U, "Cari jejak akun, profil, dan username lintas platform sosial."),
    (SUB_E, "Periksa email, kebocoran data, dan akun terkait (hanya untuk data milik sendiri atau izin sah)."),
    (SUB_D, "Temukan subdomain, catatan DNS, dan pemetaan permukaan serangan sebuah domain."),
    (SUB_N, "Pemindaian jaringan, IP, ASN, TLS, dan infrastruktur server."),
    (SUB_C, "Perayap web, scraper, dan pengarsip halaman agar bukti tidak hilang."),
    (SUB_V, "Unduh, rekam, dan transkripsi video, audio, serta siaran langsung."),
    (SUB_I, "OCR, metadata berkas, analisis gambar, dan verifikasi keaslian media."),
    (SUB_G, "Peta, data satelit, dan analisis geospasial (GEOINT)."),
    (SUB_A, "Olah data besar, graf hubungan, NLP, dan eksplorasi dataset investigasi."),
    (SUB_T, "Platform intelijen ancaman, aturan deteksi, dan basis data kerentanan."),
    (SUB_F, "Forensik digital, analisis malware, dan rekayasa balik."),
    (SUB_M, "Analisis aplikasi Android/iOS dan perangkat seluler."),
    (SUB_K, "Kerangka kerja dan platform investigasi OSINT lengkap."),
    (SUB_ID, "Data dan layanan khusus Indonesia (kode pos, cek resi, dll.)."),
    (SUB_P, "Pembaca RSS, forum, dan pesan: memantau komunitas dan feed."),
    (SUB_S, "Pemindai kerentanan, SBOM, kode, cloud, dan kontainer."),
    (SUB_X, "Periksa keamanan repo GitHub sebelum dipasang (tombol x) dan Nexus OSINT."),
    (SUB_Z, "Dipisahkan dari yang aktif: repo lama, diarsipkan, tidak ditemukan, atau kurang relevan untuk OSINT."),
]
_REF_DAY = datetime.date(2026, 11, 5)
_DEF_HOW = {
    "cli": "Pasang otomatis (y/n); lihat bantuan --help, lalu ketik argumen yang diinginkan.",
    "lib": "Pustaka Python: dipasang otomatis (y/n) lalu dites dengan contoh singkat.",
    "platform": "Aplikasi server/GUI: ikuti panduan langkah; repo bisa diunduh lewat menu.",
    "data": "Kumpulan data/daftar: unduh repo atau baca README langsung di terminal.",
    "dead": "Repo tidak bisa dipasang; lihat alasan dan penggantinya.",
}
_GH_IRR = "Aplikasi server/pustaka pengembang, bukan alat pengumpul data OSINT."


def _age_status(last):
    try:
        days = (_REF_DAY - datetime.date.fromisoformat(last)).days
    except Exception:
        return "aktif"
    return "aktif" if days <= 365 else ("jarang" if days <= 730 else "usang")


def _r(key, repo, sub, title, kind, about, how=None, **kw):
    if key in TOOLS:          # kunci lama menang (v2)
        return TOOLS[key]
    st = GH_STAT.get(repo, [None, ""])
    last = kw.pop("last", None) or st[1]
    status = kw.pop("status", None) or (st[0] if st[0] in ("aktif", "jarang", "usang", "mati") else None) or (_age_status(last) if last else "aktif")
    if kind != "dead" and status == "mati":
        status = _age_status(last) if last else "aktif"
    why = kw.pop("why", None)
    if status == "usang" and not why:
        why = "Terakhir diperbarui %s (lebih dari 2 tahun): bisa tidak lagi cocok dengan layanan atau versi terbaru." % (last or "lama")
    if status == "jarang" and not why:
        why = "Jarang diperbarui (commit terakhir %s); periksa dulu apakah masih berfungsi." % (last or "lama")
    if kind == "dead" or status in ("usang", "arsip", "mati", "tidakrelevan"):
        place = SUB_Z
    else:
        place = sub
    t = GH(key, repo, place, title, about, how or _DEF_HOW[kind], kind=kind, status=status, last=last, **kw)
    t["sub"] = place
    t["orig_sub"] = sub
    if why:
        t["why"] = why
    return t


def _irr(key, repo, sub, title, kind, about, **kw):
    kw.setdefault("why", _GH_IRR)
    return _r(key, repo, sub, title, kind, about, status="tidakrelevan", **kw)


_DK = lambda *a: [("Pasang Docker", "Unduh dan pasang Docker (lihat panduan resmi), lalu jalankan docker --version untuk memastikan.")] + list(a)
_P = lambda d, name=None: dict(git=dict(url="https://github.com/%s.git" % d, dir=name or d.split("/")[1]))
_CODE_VER = "import {m}, sys\nprint('Terpasang:', getattr({m}, '__version__', 'versi tidak diketahui'))\nprint('Lokasi  :', {m}.__file__)"

# ------------------------------------------------------------------ Username & Akun Sosial
_r("instaloader", "instaloader/instaloader", SUB_U, "Instaloader", "cli",
   "Mengambil metadata profil, post, dan story Instagram publik dari terminal.",
   "Input: username Instagram tanpa @. Hanya metadata (tanpa unduh foto/video) agar cepat; file keluaran disimpan di folder hasil.",
   pip=["instaloader"], py_min=(3, 10), outcwd=True,
   api="Disarankan login Instagram; tanpa login sering dibatasi (HTTP 429/403).",
   prompts=[("user", "Masukkan username Instagram (contoh: nasa)", None, "user")],
   build=lambda v: ["--no-pictures", "--no-videos", "--no-video-thumbnails", v["user"]])
_r("social_osint_agent", "OWASP/www-project-social-osint-agent", SUB_U, "OWASP Social OSINT Agent", "data",
   "Halaman proyek OWASP tentang agen OSINT sosial (dokumentasi dan rujukan).", **_P("OWASP/www-project-social-osint-agent"))
_r("praw", "praw-dev/praw", SUB_U, "PRAW (Reddit API)", "lib", "Pustaka Python resmi untuk membaca data Reddit lewat API.",
   "Dipakai dari skrip Python Anda: import praw. Butuh akun Reddit dan client id/secret.",
   pip=["praw"], pymod="praw", code=_CODE_VER.format(m="praw"), py_min=(3, 10),
   api="Butuh client_id dan client_secret gratis dari https://www.reddit.com/prefs/apps")
_r("twarc", "DocNow/twarc", SUB_U, "twarc (X/Twitter)", "cli", "Pengumpul data X/Twitter untuk penelitian lewat API resmi.",
   pip=["twarc"], bins=["twarc2"], status="jarang",
   why="Pengembang menyatakan twarc tidak lagi aktif didukung setelah perubahan API X; akses API X kini berbayar.",
   api="Butuh akses API X/Twitter (umumnya berbayar) dan twarc2 configure.")
_r("mastodonpy", "halcy/Mastodon.py", SUB_U, "Mastodon.py", "lib", "Pustaka Python untuk membaca timeline dan profil Mastodon/fediverse.",
   "Dipakai dari skrip Python: from mastodon import Mastodon. Data publik bisa dibaca tanpa akun di banyak server.",
   pip=["Mastodon.py"], pymod="mastodon", code=_CODE_VER.format(m="mastodon"),
   api="Opsional: beberapa endpoint butuh akun/token dari server Mastodon yang dipakai.")
_r("atproto", "bluesky-social/atproto", SUB_U, "AT Protocol SDK (Bluesky)", "lib", "SDK Python untuk jaringan Bluesky: baca profil dan post publik.",
   "Dipakai dari skrip Python: from atproto import Client. Banyak fungsi butuh akun + app password.",
   pip=["atproto"], pymod="atproto", code=_CODE_VER.format(m="atproto"), py_min=(3, 9),
   api="Butuh akun Bluesky dan app password (Settings > App Passwords) untuk banyak fungsi.")
_r("tiktokapi", "davidteather/TikTok-Api", SUB_U, "TikTok-Api (tidak resmi)", "lib", "Pembungkus Python tidak resmi untuk data TikTok publik.",
   "Dipakai dari skrip Python. Butuh browser Playwright; TikTok sering memblokir klien otomatis.",
   pip=["TikTokApi"], pymod="TikTokApi", code=_CODE_VER.format(m="TikTokApi"),
   note="Setelah pasang jalankan: python -m playwright install chromium. Butuh cookie ms_token dari browser Anda.",
   api="Butuh cookie ms_token dari sesi TikTok Anda; sering berubah atau diblokir.")
_r("linkedin2username", "initstring/linkedin2username", SUB_U, "linkedin2username", "cli",
   "Membuat daftar kemungkinan username karyawan sebuah perusahaan dari LinkedIn.",
   "Input: nama perusahaan. Butuh akun LinkedIn sendiri; gunakan hanya untuk asesmen yang sah.",
   git=dict(url="https://github.com/initstring/linkedin2username.git", dir="linkedin2username", entry="linkedin2username.py", req=None),
   pip=None, py_min=(3, 10), auth=True, inter=True, outcwd=True,
   api="Butuh login akun LinkedIn Anda (email + password) saat dijalankan.")
_r("nebulaosint", "ismailtsdln/NebulaOSINT", SUB_U, "NebulaOSINT", "cli", "Pemindai username lintas situs (reconnaissance username).",
   "Input: username. Hasil menunjukkan situs tempat username ditemukan.",
   pip=["git+https://github.com/ismailtsdln/NebulaOSINT.git"], bins=["nebula"], py_min=(3, 10),
   prompts=[("user", "Masukkan username (contoh: budi123)", None, "user")], build=lambda v: [v["user"]])
_r("protosint", "pixelbubble/ProtOSINT", SUB_E, "ProtOSINT", "cli", "Menyelidiki akun ProtonMail: validitas email dan info pembuatan kunci.",
   "Input: alamat email ProtonMail. Hasil: apakah akun ada dan kapan kunci PGP dibuat.",
   git=dict(url="https://github.com/pixelbubble/ProtOSINT.git", dir="ProtOSINT", entry="protosint.py", req="requirements.txt"),
   prompts=[("email", "Masukkan email ProtonMail (contoh: nama@proton.me)", None, "email")], build=lambda v: ["-m", v["email"]])
_r("steamreveal", "Berchez/SteamReveal", SUB_U, "SteamReveal", "platform", "Aplikasi web untuk menelusuri profil Steam: riwayat nama dan inventaris.",
   guide=[("Pasang Node.js dan pnpm", "Pasang Node.js 20+, lalu: npm install -g pnpm"), ("Unduh repo", "git clone https://github.com/Berchez/SteamReveal.git && cd SteamReveal"),
          ("Jalankan", "pnpm install && pnpm dev  (lalu buka http://localhost:3000)")], needs=["git", "node"])
_r("whatsapp_osint", "kinghacker0/WhatsApp-OSINT", SUB_U, "WhatsApp-OSINT", "cli",
   "Mengambil foto profil, status/about, dan info bisnis dari nomor WhatsApp lewat layanan pihak ketiga.",
   "Input: nomor dengan kode negara. Butuh API key layanan pihak ketiga sesuai README.",
   git=dict(url="https://github.com/kinghacker0/WhatsApp-OSINT.git", dir="WhatsApp-OSINT", entry="whatsapp-osint.py", req="requirements.txt"),
   status="jarang", inter=True, api="Butuh API key layanan pihak ketiga (lihat .env.example di repo).")
_r("osint_tool_bugr7", "bugr7/osint-tool", SUB_U, "osint-tool (bugr7)", "data", "Alat OSINT berbasis web yang mengambil tautan dari Facebook, X, YouTube, Reddit.", **_P("bugr7/osint-tool"))
_r("soig", "yezz123/SoIG", SUB_U, "SoIG (Instagram OSINT)", "cli", "Mengambil informasi dari profil Instagram (API lokal Python).",
   git=dict(url="https://github.com/yezz123/SoIG.git", dir="SoIG", entry="main.py", req="requirements.txt"), inter=True,
   api="Butuh login/sesi Instagram; tanpa itu hasil terbatas.")
_r("horus", "6abd/horus", SUB_U, "Horus", "cli", "Pengumpul jejak OSINT berbasis Python (lihat README untuk modul yang tersedia).",
   git=dict(url="https://github.com/6abd/horus.git", dir="horus", entry="horus.py", req="requirements.txt"), inter=True)
_r("pwnedornot", "thewhiteh4t/pwnedOrNot", SUB_E, "pwnedOrNot", "cli", "Mengecek apakah email muncul di kebocoran data (HIBP/Dehashed) dan mencari kata sandinya.",
   "Input: email milik sendiri. Hasil: daftar kebocoran. Pencarian sandi butuh API key.",
   git=dict(url="https://github.com/thewhiteh4t/pwnedOrNot.git", dir="pwnedOrNot", entry="pwnedornot.py", req=None),
   pip=None, inter=True, note="Edit config.json di folder tool untuk memasukkan API key HIBP.",
   api="Butuh API key Have I Been Pwned (berbayar) agar pencarian email berfungsi penuh.")
_r("h8mail", "khast3x/h8mail", SUB_E, "h8mail", "cli", "Mencari email di basis data kebocoran dan mengambil kredensial bocor.",
   "Input: email target. Banyak sumber butuh API key (opsional) di berkas konfigurasi.",
   pip=["h8mail"], prompts=[("email", "Masukkan email (contoh: nama@contoh.com)", None, "email")], build=lambda v: ["-t", v["email"]],
   api="Opsional: sumber seperti Snusbase/Hunter/HIBP butuh API key lewat berkas konfigurasi.")

# ------------------------------------------------------------------ Domain, Subdomain & DNS
_r("amass", "owasp-amass/amass", SUB_D, "OWASP Amass", "cli", "Pemetaan permukaan serangan dan penemuan subdomain terlengkap dari OWASP.",
   "Pasang otomatis, lihat bantuan, lalu jalankan misalnya: enum -d example.com (tambahkan -passive agar tidak menyentuh target).",
   go="github.com/owasp-amass/amass/v5/cmd/amass", sys={"apt": "amass", "brew": "amass"}, needs=["go"], auth=True,
   note="Repo OWASP/Amass lama sudah pindah ke owasp-amass/amass. Bila go gagal, pakai paket sistem: apt install amass.")
_r("dnspython", "rthalley/dnspython", SUB_D, "dnspython", "lib", "Pustaka DNS Python; di sini dipakai untuk melihat catatan A, AAAA, MX, NS, TXT, CNAME.",
   "Input: domain. Hasil: daftar catatan DNS domain tersebut.",
   pip=["dnspython"], pymod="dns", py_min=(3, 11),
   code=("import sys, dns.resolver\nd = sys.argv[1]\nfor t in ('A', 'AAAA', 'MX', 'NS', 'TXT', 'CNAME'):\n    try:\n"
         "        for r in dns.resolver.resolve(d, t):\n            print(t.ljust(6), r.to_text())\n    except Exception as e:\n        print(t.ljust(6), '-', e.__class__.__name__)"),
   prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")], build=lambda v: [v["domain"]])
_r("tldextract", "john-kurkowski/tldextract", SUB_D, "tldextract", "lib", "Memecah URL menjadi subdomain, domain, dan akhiran (TLD) dengan benar.",
   "Input: URL atau domain. Hasil: bagian subdomain, domain, suffix.",
   pip=["tldextract"], pymod="tldextract",
   code="import sys, tldextract\nfor u in sys.argv[1:]:\n    e = tldextract.extract(u)\n    print('subdomain :', e.subdomain or '-')\n    print('domain    :', e.domain)\n    print('suffix    :', e.suffix)\n    print('registered:', e.registered_domain)",
   prompts=[("u", "Masukkan URL atau domain (contoh: https://blog.example.co.id/x)", None, "text")], build=lambda v: [v["u"]])
_r("bbot", "blacklanternsecurity/bbot", SUB_D, "BBOT", "cli", "Kerangka recon otomatis modular: subdomain, port, teknologi, dan banyak lagi.",
   pip=["bbot"], py_min=(3, 9), auth=True, note="Pemasangan besar (banyak dependensi). Contoh: bbot -t example.com -p subdomain-enum (lihat --help).")
_r("rengine", "yogeshojha/rengine", SUB_D, "reNgine", "platform", "Platform web recon dan pemindai kerentanan dengan antarmuka dashboard.",
   guide=_DK(("Unduh repo", "git clone https://github.com/yogeshojha/rengine && cd rengine"), ("Atur kredensial", "Edit berkas .env (nama pengguna/sandi), lalu: sudo ./install.sh"),
             ("Buka dashboard", "Buka https://127.0.0.1 di browser dan login memakai kredensial tadi.")), needs=["docker", "git"], auth=True,
   note="Butuh RAM minimal 4 GB. Gunakan hanya pada target yang Anda punya izin.")
_r("oneforall", "shmilylty/OneForAll", SUB_D, "OneForAll", "cli", "Pengumpul subdomain sangat lengkap (sumber CT log, DNS, mesin pencari).",
   "Input: domain. Hasil disimpan sebagai berkas di folder hasil.",
   git=dict(url="https://github.com/shmilylty/OneForAll.git", dir="OneForAll", entry="oneforall.py", req="requirements.txt"), outcwd=True, py_min=(3, 7),
   prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")], build=lambda v: ["--target", v["domain"], "run"],
   note="Dokumentasi berbahasa Mandarin; gunakan terjemahan peramban untuk README.")
_r("findomain", "Findomain/Findomain", SUB_D, "Findomain", "cli", "Penemuan subdomain cepat dari banyak sumber (ditulis dengan Rust).",
   "Input: domain. Hasil: daftar subdomain.", rel=dict(repo="Findomain/Findomain"), sys={"brew": "findomain"},
   prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")], build=lambda v: ["-t", v["domain"]],
   api="Opsional: sebagian sumber (Virustotal, Spyse, dll.) butuh API key lewat variabel lingkungan.")
_r("dnsx", "projectdiscovery/dnsx", SUB_D, "dnsx", "cli", "Toolkit DNS cepat dari ProjectDiscovery: resolusi massal dan berbagai tipe catatan.",
   go="github.com/projectdiscovery/dnsx/cmd/dnsx", needs=["go"])
_r("chaos", "projectdiscovery/chaos-client", SUB_D, "Chaos Client", "cli", "Klien dataset subdomain Chaos milik ProjectDiscovery.",
   go="github.com/projectdiscovery/chaos-client/cmd/chaos", bins=["chaos"], needs=["go"],
   api="Butuh API key Chaos (gratis, daftar di https://cloud.projectdiscovery.io).")
_r("alterx", "projectdiscovery/alterx", SUB_D, "AlterX", "cli", "Pembuat daftar kata subdomain (permutasi) memakai pola DSL.",
   go="github.com/projectdiscovery/alterx/cmd/alterx", needs=["go"])
_r("sublist3r", "aboul3la/Sublist3r", SUB_D, "Sublist3r", "cli", "Pencari subdomain lewat mesin pencari dan layanan DNS publik.",
   "Input: domain. Hasil: subdomain yang ditemukan.", pip=["Sublist3r"], bins=["sublist3r"], status="usang",
   prompts=[("domain", "Masukkan domain (contoh: example.com)", None, "domain")], build=lambda v: ["-d", v["domain"]],
   why="Terakhir diperbarui Juli 2020; beberapa mesin pencari sudah memblokirnya, hasil bisa sedikit. Pakai Subfinder/Amass sebagai gantinya.")

# ------------------------------------------------------------------ Jaringan, IP & Infrastruktur
_r("uncover", "projectdiscovery/uncover", SUB_N, "uncover", "cli", "Menemukan host terbuka di internet lewat Shodan, Censys, Fofa, dll. sekaligus.",
   go="github.com/projectdiscovery/uncover/cmd/uncover", needs=["go"],
   api="Butuh API key mesin pencari yang dipakai (Shodan, Censys, Fofa, dll.).")
_r("naabu", "projectdiscovery/naabu", SUB_N, "naabu", "cli", "Pemindai port cepat dari ProjectDiscovery.",
   go="github.com/projectdiscovery/naabu/v2/cmd/naabu", needs=["go"], auth=True, note="Butuh libpcap (apt install libpcap-dev). Pindai hanya server milik/izin Anda.")
_r("httpx_pd", "projectdiscovery/httpx", SUB_N, "httpx (ProjectDiscovery)", "cli", "Penyelidik HTTP cepat: status, judul, teknologi, TLS untuk banyak host.",
   "Input: URL. Hasil: kode status, judul, dan teknologi situs.",
   go="github.com/projectdiscovery/httpx/cmd/httpx", bins=["httpx"], needs=["go"],
   prompts=[("url", "Masukkan URL (contoh: https://example.com)", None, "url")], build=lambda v: ["-u", v["url"], "-title", "-status-code", "-tech-detect"],
   note="Bentrok nama dengan perintah httpx milik pustaka Python. Bila hasilnya aneh, jalankan httpx -version; versi ProjectDiscovery menampilkan 'projectdiscovery'.")
_r("mapcidr", "projectdiscovery/mapcidr", SUB_N, "mapcidr", "cli", "Utilitas CIDR/IP: hitung, pecah, dan gabung rentang alamat IP.",
   go="github.com/projectdiscovery/mapcidr/cmd/mapcidr", needs=["go"])
_r("cdncheck", "projectdiscovery/cdncheck", SUB_N, "cdncheck", "cli", "Mendeteksi apakah sebuah IP berada di CDN, cloud, atau WAF.",
   go="github.com/projectdiscovery/cdncheck/cmd/cdncheck", needs=["go"])
_r("tlsx", "projectdiscovery/tlsx", SUB_N, "tlsx", "cli", "Pengambil data TLS: sertifikat, cipher, dan nama alternatif host.",
   go="github.com/projectdiscovery/tlsx/cmd/tlsx", needs=["go"])
_r("ipwhois", "secynic/ipwhois", SUB_N, "ipwhois", "lib", "Pustaka Python untuk RDAP/WHOIS IP: pemilik jaringan, ASN, dan CIDR.",
   "Input: alamat IP. Hasil: ASN, pemilik jaringan, rentang CIDR, negara.",
   pip=["ipwhois"], pymod="ipwhois",
   code=("import sys\nfrom ipwhois import IPWhois\nr = IPWhois(sys.argv[1]).lookup_rdap(depth=1)\nprint('ASN       :', r.get('asn'), '-', r.get('asn_description'))\n"
         "print('Negara    :', r.get('asn_country_code'))\nn = r.get('network') or {}\nprint('Jaringan  :', n.get('name'))\nprint('CIDR      :', n.get('cidr'))\nprint('Terdaftar :', r.get('asn_date'))"),
   prompts=[("ip", "Masukkan alamat IP (contoh: 8.8.8.8)", None, "host")], build=lambda v: [v["ip"]])
_r("bgpalerter", "nttgin/BGPalerter", SUB_N, "BGPalerter", "platform", "Pemantau BGP: peringatan hijack dan perubahan rute prefiks IP.",
   guide=[("Unduh biner", "Buka https://github.com/nttgin/BGPalerter/releases dan unduh berkas untuk sistem Anda."), ("Beri izin jalan", "chmod +x bgpalerter-linux-x64"),
          ("Jalankan", "./bgpalerter-linux-x64  (ikuti pembuatan berkas konfigurasi pertama)")], status="jarang")
_r("rita", "activecm/rita", SUB_N, "RITA (Active Countermeasures)", "platform", "Mendeteksi beaconing/C2 dari log jaringan Zeek.",
   guide=_DK(("Unduh repo", "git clone https://github.com/activecm/rita.git"), ("Ikuti instalasi", "Baca README: instalasi memakai Docker Compose dan data log Zeek.")), needs=["docker", "git"])
_r("slips", "stratosphereips/StratosphereLinuxIPS", SUB_N, "Slips (Stratosphere IPS)", "platform", "Sistem pencegah intrusi berbasis pembelajaran mesin untuk lalu lintas jaringan.",
   guide=_DK(("Tarik image", "docker pull stratosphereips/slips"), ("Jalankan", "Ikuti README untuk menjalankan pada berkas pcap atau interface.")), needs=["docker"],
   note="Repo StratosphereLinuxIPS/StratosphereLinuxIPS di daftar lama sudah pindah ke stratosphereips/StratosphereLinuxIPS.")
_r("ntopng", "ntop/ntopng", SUB_N, "ntopng", "platform", "Pemantau lalu lintas jaringan berbasis web (flow, host, aplikasi).",
   guide=[("Pasang", "Linux: ikuti paket di https://packages.ntop.org ; macOS: brew install ntopng"), ("Jalankan", "sudo ntopng -i eth0   (ganti eth0 dengan interface Anda)"),
          ("Buka dashboard", "Buka http://localhost:3000 di browser.")])
_r("wireshark", "wireshark/wireshark", SUB_N, "Wireshark", "platform", "Penganalisis paket jaringan terkenal (GUI) dan tshark (baris perintah).",
   guide=[("Pasang", "Debian/Ubuntu: sudo apt install wireshark tshark ; macOS: brew install --cask wireshark ; Windows: winget install WiresharkFoundation.Wireshark"),
          ("Izin capture", "Linux: sudo dpkg-reconfigure wireshark-common lalu tambahkan akun Anda ke grup wireshark."), ("Buka", "Jalankan wireshark atau tshark -D untuk melihat interface.")])
_r("aircrack", "aircrack-ng/aircrack-ng", SUB_N, "Aircrack-ng", "cli", "Rangkaian alat audit keamanan Wi-Fi (hanya untuk jaringan milik/izin Anda).",
   sys={"apt": "aircrack-ng", "brew": "aircrack-ng", "pacman": "aircrack-ng", "dnf": "aircrack-ng"}, bins=["aircrack-ng"], auth=True,
   note="Butuh adapter Wi-Fi yang mendukung monitor mode dan hak root. Tidak berjalan di Termux tanpa root.")
_r("zeek", "zeek/zeek", SUB_N, "Zeek", "platform", "Monitor keamanan jaringan: mengubah lalu lintas menjadi log kaya konteks.",
   guide=[("Pasang", "Ikuti https://docs.zeek.org/en/master/install.html (paket resmi tersedia untuk Debian, Ubuntu, Fedora; atau Docker)."),
          ("Uji pada pcap", "zeek -r contoh.pcap  (log tersimpan di folder saat ini)")])

# ------------------------------------------------------------------ Crawler, Scraper & Arsip Web
_r("crawl4ai", "unclecode/crawl4ai", SUB_C, "Crawl4AI", "lib", "Perayap web ramah LLM: mengubah halaman menjadi teks Markdown bersih.",
   "Input: URL. Hasil: isi halaman dalam Markdown (3000 karakter pertama).",
   pip=["crawl4ai"], pymod="crawl4ai", py_min=(3, 10),
   code=("import asyncio, sys\nfrom crawl4ai import AsyncWebCrawler\nasync def main():\n    async with AsyncWebCrawler() as c:\n        r = await c.arun(url=sys.argv[1])\n        print(str(r.markdown)[:3000])\nasyncio.run(main())"),
   prompts=[("url", "Masukkan URL (contoh: https://example.com)", None, "url")], build=lambda v: [v["url"]],
   note="Setelah pasang jalankan: crawl4ai-setup (mengunduh browser). Pemasangan besar.")
_r("crawlee", "apify/crawlee", SUB_C, "Crawlee (Python)", "lib", "Kerangka perayap dan scraper web dengan antrean dan proxy.",
   "Dipakai dari skrip Python: from crawlee.crawlers import ... (lihat dokumentasi).", pip=["crawlee"], pymod="crawlee", code=_CODE_VER.format(m="crawlee"), py_min=(3, 10))
_r("archivebox", "ArchiveBox/ArchiveBox", SUB_C, "ArchiveBox", "cli", "Mengarsipkan halaman web (HTML, PDF, screenshot, WARC) ke koleksi sendiri.",
   pip=["archivebox"], py_min=(3, 13), note="Mulai dengan: archivebox init  lalu  archivebox add https://example.com . Butuh Python 3.13+.")
_r("pywb", "webrecorder/pywb", SUB_C, "pywb (Web Archive Replay)", "cli", "Server pemutar arsip web (WARC): merekam dan memutar ulang halaman.",
   "Menjalankan server di port 8080: buka alamat yang tampil. Tekan Ctrl+C untuk berhenti.",
   pip=["pywb"], bins=["wayback"], inter=True, prompts=[], build=lambda v: [])
_r("warcio", "webrecorder/warcio", SUB_C, "warcio", "cli", "Membaca dan menulis berkas WARC; ada perintah warcio index/extract.", pip=["warcio"])
_r("warcprox", "internetarchive/warcprox", SUB_C, "warcprox", "cli", "Proxy yang merekam lalu lintas HTTP/HTTPS ke berkas WARC.",
   pip=["warcprox"], inter=True, py_min=(3, 9), note="Atur proxy peramban ke localhost:8000 untuk merekam. Ctrl+C untuk berhenti.")
_r("browsertrix", "webrecorder/browsertrix", SUB_C, "Browsertrix", "platform", "Platform perayap berbasis browser skala besar (butuh Kubernetes).",
   guide=[("Baca panduan resmi", "Browsertrix butuh klaster Kubernetes; pemula disarankan memakai layanan hosting atau browsertrix-crawler.")])
_r("browsertrix_crawler", "webrecorder/browsertrix-crawler", SUB_C, "Browsertrix Crawler", "platform", "Perayap browser mandiri via Docker yang menghasilkan arsip WACZ.",
   guide=_DK(("Jalankan perayap", "docker run -v $PWD/crawls:/crawls/ -it webrecorder/browsertrix-crawler crawl --url https://example.com --generateWACZ --collection uji"),
             ("Ambil hasil", "Berkas .wacz tersimpan di folder crawls/collections.")), needs=["docker"])
_r("singlefile", "gildas-lormeau/SingleFile", SUB_C, "SingleFile", "platform", "Menyimpan halaman web lengkap menjadi satu berkas HTML (ekstensi + CLI).",
   guide=[("Pasang CLI", "npm install -g single-file-cli  (butuh Node.js dan Chrome/Chromium)"), ("Simpan halaman", "single-file https://example.com contoh.html"),
          ("Atau ekstensi", "Pasang ekstensi SingleFile di Chrome/Firefox dari toko resmi.")], needs=["node"])
_r("heritrix3", "internetarchive/heritrix3", SUB_C, "Heritrix 3", "platform", "Perayap arsip web milik Internet Archive (server Java).",
   guide=[("Pasang Java", "Butuh Java 11+ (java -version)."), ("Unduh rilis", "Unduh heritrix-*-dist.zip dari halaman Releases GitHub, ekstrak."),
          ("Jalankan", "bin/heritrix -a admin:sandi  lalu buka https://localhost:8443")], needs=["java"])
_r("grabsite", "ArchiveTeam/grab-site", SUB_C, "grab-site", "platform", "Perayap arsip situs lengkap dengan dasbor (dipakai Archive Team).",
   guide=[("Baca syarat", "Butuh Python 3.7+ dan pustaka build; ikuti bagian Install di README."), ("Pasang", "pip install --user grab-site  (atau ikuti skrip instalasi di README)"),
          ("Jalankan", "grab-site https://example.com")], status="jarang")
_r("portia", "scrapinghub/portia", SUB_C, "Portia", "dead", "Scraper visual lama dari Scrapinghub.", why="Terakhir diperbarui 2019 dan memakai teknologi lama; tidak lagi dipelihara. Pakai Scrapy/Crawl4AI.")

# ------------------------------------------------------------------ Video, Audio & Streaming
_r("streamlink", "streamlink/streamlink", SUB_V, "Streamlink", "cli", "Mengambil tautan siaran langsung dari Twitch, YouTube, dll. untuk diputar atau direkam.",
   "Input: URL siaran. Hasil: alamat stream langsung (tanpa mengunduh).", pip=["streamlink"], py_min=(3, 10), sys={"apt": "streamlink", "brew": "streamlink", "pkg": "streamlink"},
   prompts=[("url", "Masukkan URL siaran (contoh: https://www.twitch.tv/nama)", None, "url")], build=lambda v: ["--stream-url", v["url"], "best"])
_r("twitchio", "PythonistaGuild/TwitchIO", SUB_V, "TwitchIO", "lib", "Pustaka Python untuk bot/API Twitch.", "Dipakai dari skrip Python: import twitchio.",
   pip=["TwitchIO"], pymod="twitchio", code=_CODE_VER.format(m="twitchio"), py_min=(3, 11),
   api="Butuh Client ID dan Client Secret Twitch (gratis di https://dev.twitch.tv/console).")
_r("yark", "Owez/yark", SUB_V, "Yark", "cli", "Mengarsipkan kanal YouTube beserta riwayat perubahan judul, komentar, dan video terhapus.",
   pip=["yark"], note="Contoh: yark new nama https://www.youtube.com/@kanal  lalu  yark refresh nama  dan  yark view nama.")
_r("yt_transcript", "jdepoix/youtube-transcript-api", SUB_V, "YouTube Transcript API", "cli", "Mengambil teks transkrip video YouTube tanpa API key.",
   "Input: ID video (bagian setelah v= di URL). Hasil: transkrip teks.", pip=["youtube-transcript-api"], bins=["youtube_transcript_api"],
   prompts=[("id", "Masukkan ID video YouTube (contoh: dQw4w9WgXcQ)", None, "user")], build=lambda v: [v["id"]])
_r("pytchat", "taizan-hokuto/pytchat", SUB_V, "pytchat", "lib", "Mengambil chat YouTube Live tanpa API key.", "Dipakai dari skrip Python: import pytchat.",
   pip=["pytchat"], pymod="pytchat", code=_CODE_VER.format(m="pytchat"), last="2021-07-24",
   note="Alamat dikoreksi dari egbertbouman/pytchat (repo lama sudah pindah).")
_r("ffmpeg", "FFmpeg/FFmpeg", SUB_V, "FFmpeg", "cli", "Pengolah audio/video serba bisa: konversi, potong, ekstrak audio.",
   sys={"apt": "ffmpeg", "brew": "ffmpeg", "pkg": "ffmpeg", "dnf": "ffmpeg", "pacman": "ffmpeg", "winget": "Gyan.FFmpeg"})
_r("whisper", "openai/whisper", SUB_V, "OpenAI Whisper", "cli", "Transkripsi suara menjadi teks (banyak bahasa, termasuk Indonesia) secara lokal.",
   "Input: path berkas audio/video. Hasil: transkrip teks di folder hasil. Pemasangan besar (PyTorch).",
   pip=["openai-whisper"], bins=["whisper"], needs=["ffmpeg"], outcwd=True,
   prompts=[("f", "Path berkas audio/video (contoh: /sdcard/rekaman.mp3)", None, "file"), ("model", "Model (tiny/base/small)", "base", "text")],
   build=lambda v: [v["f"], "--model", v["model"], "--language", "Indonesian"], note="Model diunduh saat pertama dijalankan. Butuh ruang disk beberapa GB.")
_r("whispercpp", "ggml-org/whisper.cpp", SUB_V, "whisper.cpp", "platform", "Whisper versi C/C++ yang ringan dan cepat tanpa Python.",
   guide=[("Siapkan alat build", "Butuh git, cmake, dan compiler C++."), ("Unduh dan bangun", "git clone https://github.com/ggml-org/whisper.cpp && cd whisper.cpp && cmake -B build && cmake --build build -j"),
          ("Unduh model", "sh ./models/download-ggml-model.sh base"), ("Jalankan", "./build/bin/whisper-cli -m models/ggml-base.bin -f berkas.wav")], needs=["git", "cmake", "make"])
_r("tubeup", "bibanon/tubeup", SUB_V, "Tubeup", "cli", "Mengunggah video dari YouTube dan situs lain ke Internet Archive.",
   pip=["tubeup"], py_min=(3, 10), api="Butuh akun archive.org dan jalankan: ia configure.")
_r("discordchatexporter", "Tyrrrz/DiscordChatExporter", SUB_P, "DiscordChatExporter", "platform", "Mengekspor riwayat chat Discord ke HTML/JSON/CSV.",
   guide=[("Unduh", "Ambil rilis terbaru (CLI atau GUI) dari halaman Releases GitHub."), ("Ambil token", "Disarankan memakai TOKEN BOT sendiri; token akun pribadi melanggar ketentuan Discord."),
          ("Ekspor", "DiscordChatExporter.Cli export -t TOKEN -c ID_CHANNEL")],
   api="Butuh token bot/akun Discord. Memakai token akun pribadi melanggar ketentuan layanan Discord.")

# ------------------------------------------------------------------ Gambar, OCR & Metadata Berkas
_r("tesseract", "tesseract-ocr/tesseract", SUB_I, "Tesseract OCR", "cli", "Mengenali teks dari gambar (OCR) dengan banyak bahasa.",
   "Input: path gambar. Hasil: teks yang terbaca ditampilkan langsung.",
   sys={"apt": "tesseract-ocr", "brew": "tesseract", "pkg": "tesseract", "dnf": "tesseract", "pacman": "tesseract", "winget": "UB-Mannheim.TesseractOCR"},
   prompts=[("f", "Path gambar (contoh: foto.png)", None, "file")], build=lambda v: [v["f"], "stdout"],
   note="Untuk bahasa Indonesia pasang paket tesseract-ocr-ind lalu tambahkan -l ind.")
_r("easyocr", "JaidedAI/EasyOCR", SUB_I, "EasyOCR", "cli", "OCR berbasis AI untuk 80+ bahasa, termasuk Indonesia.",
   "Input: path gambar. Hasil: teks dan posisinya. Pemasangan besar (PyTorch).", pip=["easyocr"],
   prompts=[("f", "Path gambar (contoh: foto.png)", None, "file")], build=lambda v: ["-l", "id", "en", "-f", v["f"]], note="Model bahasa diunduh saat pertama dijalankan.")
_r("paddleocr", "PaddlePaddle/PaddleOCR", SUB_I, "PaddleOCR", "cli", "OCR dan pengolah dokumen berakurasi tinggi dari Baidu.",
   pip=["paddleocr", "paddlepaddle"], py_min=(3, 8), note="Pemasangan besar. Lihat paddleocr --help untuk subperintah.")
_r("mediainfo", "MediaArea/MediaInfo", SUB_I, "MediaInfo", "cli", "Menampilkan metadata teknis berkas video/audio: codec, durasi, tanggal.",
   "Input: path berkas media. Hasil: daftar metadata lengkap.",
   sys={"apt": "mediainfo", "brew": "mediainfo", "pkg": "mediainfo", "dnf": "mediainfo", "pacman": "mediainfo", "winget": "MediaArea.MediaInfo.CLI"},
   prompts=[("f", "Path berkas media (contoh: video.mp4)", None, "file")], build=lambda v: [v["f"]])
_r("imagemagick", "ImageMagick/ImageMagick", SUB_I, "ImageMagick", "cli", "Memeriksa dan mengolah gambar; di sini untuk menampilkan metadata gambar.",
   "Input: path gambar. Hasil: info verbose (ukuran, profil warna, EXIF).",
   sys={"apt": "imagemagick", "brew": "imagemagick", "pkg": "imagemagick", "dnf": "ImageMagick", "pacman": "imagemagick", "winget": "ImageMagick.ImageMagick"}, bins=["identify"],
   prompts=[("f", "Path gambar (contoh: foto.jpg)", None, "file")], build=lambda v: ["-verbose", v["f"]])
_r("opencv", "opencv/opencv", SUB_I, "OpenCV", "lib", "Pustaka visi komputer: baca gambar, deteksi wajah/objek, olah citra.",
   "Input: path gambar. Hasil: dimensi dan jumlah kanal gambar.", pip=["opencv-python-headless"], pymod="cv2",
   code="import cv2, sys\nim = cv2.imread(sys.argv[1])\nprint('Versi OpenCV:', cv2.__version__)\nprint('Gambar tidak terbaca' if im is None else 'Dimensi (tinggi, lebar, kanal): %s' % (im.shape,))",
   prompts=[("f", "Path gambar (contoh: foto.jpg)", None, "file")], build=lambda v: [v["f"]])
_r("tika", "apache/tika", SUB_I, "Apache Tika", "lib", "Mengekstrak teks dan metadata dari ratusan jenis berkas (PDF, Office, gambar).",
   "Input: path berkas. Hasil: metadata dan 1500 karakter pertama isi.", pip=["tika"], pymod="tika", needs=["java"],
   code="import sys\nfrom tika import parser\nr = parser.from_file(sys.argv[1])\nfor k, v in list((r.get('metadata') or {}).items())[:25]:\n    print(str(k)[:28].ljust(29), str(v)[:70])\nprint('--- isi ---')\nprint((r.get('content') or '')[:1500])",
   prompts=[("f", "Path berkas (contoh: dokumen.pdf)", None, "file")], build=lambda v: [v["f"]], note="Pertama kali dijalankan mengunduh server Tika (butuh internet dan Java).")
_r("c2patool", "contentauth/c2pa-rs", SUB_I, "c2pa (Content Credentials)", "platform", "Memverifikasi Content Credentials (C2PA) untuk melacak asal dan suntingan media.",
   guide=[("Pasang Rust", "Butuh cargo (https://rustup.rs)."), ("Pasang alat", "cargo install c2patool"), ("Periksa berkas", "c2patool gambar.jpg")], needs=["cargo"])

# ------------------------------------------------------------------ Geospasial & Peta
_r("qgis", "qgis/QGIS", SUB_G, "QGIS", "platform", "Aplikasi SIG (GIS) bebas: membuka, menganalisis, dan memetakan data geospasial.",
   guide=[("Pasang", "Windows/macOS: unduh di https://qgis.org/download ; Debian/Ubuntu: sudo apt install qgis ; macOS: brew install --cask qgis"), ("Jalankan", "Buka QGIS dari menu aplikasi atau ketik qgis.")])
_r("geopandas", "geopandas/geopandas", SUB_G, "GeoPandas", "lib", "Pustaka Python data geospasial (shapefile, GeoJSON) setara pandas.",
   "Input: path berkas GeoJSON/Shapefile. Hasil: sistem koordinat dan beberapa baris pertama.", pip=["geopandas"], pymod="geopandas", py_min=(3, 11),
   code="import geopandas as gpd, sys\ng = gpd.read_file(sys.argv[1])\nprint('Jumlah fitur:', len(g))\nprint('CRS         :', g.crs)\nprint(g.head(10).to_string())",
   prompts=[("f", "Path berkas geospasial (contoh: peta.geojson)", None, "file")], build=lambda v: [v["f"]])
_r("osmnx", "gboeing/osmnx", SUB_G, "OSMnx", "lib", "Mengunduh dan menganalisis jaringan jalan/bangunan dari OpenStreetMap.",
   "Input: nama tempat. Hasil: koordinat (lintang, bujur) dari OpenStreetMap.", pip=["osmnx"], pymod="osmnx", py_min=(3, 11),
   code="import osmnx as ox, sys\nq = ' '.join(sys.argv[1:])\nprint('Lintang, bujur:', ox.geocode(q))",
   prompts=[("q", "Masukkan nama tempat (contoh: Monas, Jakarta)", None, "text")], build=lambda v: [v["q"]])
_r("leafmap", "opengeos/leafmap", SUB_G, "leafmap", "lib", "Membuat peta interaktif dan analisis geospasial dari Python/Jupyter.",
   pip=["leafmap"], pymod="leafmap", code=_CODE_VER.format(m="leafmap"), py_min=(3, 9))
_r("geemap", "gee-community/geemap", SUB_G, "geemap", "lib", "Peta interaktif dan analisis data satelit lewat Google Earth Engine.",
   pip=["geemap"], pymod="geemap", code=_CODE_VER.format(m="geemap"), py_min=(3, 12),
   api="Butuh akun Google Earth Engine (gratis non-komersial) dan menjalankan earthengine authenticate.")
_r("kepler", "keplergl/kepler.gl", SUB_G, "kepler.gl", "platform", "Alat visualisasi peta data besar (web, tanpa pemasangan).",
   guide=[("Pakai langsung", "Buka https://kepler.gl/demo di browser dan seret berkas CSV/GeoJSON."), ("Opsional lokal", "git clone https://github.com/keplergl/kepler.gl lalu ikuti README (Node.js).")])
_r("cesium", "CesiumGS/cesium", SUB_G, "CesiumJS", "platform", "Pustaka JavaScript untuk globe 3D dan peta 2D.",
   guide=[("Pasang", "npm install cesium"), ("Token", "Daftarkan token gratis di https://ion.cesium.com untuk data bawaan.")], needs=["node"], api="Beberapa data bawaan butuh token Cesium ion (gratis).")
_r("gdal", "OSGeo/gdal", SUB_G, "GDAL", "cli", "Pustaka dan alat baris perintah untuk data raster/vektor geospasial.",
   "Input: path berkas raster/vektor. Hasil: gdalinfo (ukuran, proyeksi, metadata).", sys={"apt": "gdal-bin", "brew": "gdal", "pkg": "gdal", "dnf": "gdal", "pacman": "gdal"}, bins=["gdalinfo"],
   prompts=[("f", "Path berkas (contoh: citra.tif)", None, "file")], build=lambda v: [v["f"]])
_r("rasterio", "rasterio/rasterio", SUB_G, "Rasterio", "lib", "Membaca dan menulis data raster geospasial (GeoTIFF) dari Python.",
   "Input: path raster. Hasil: ukuran, jumlah band, proyeksi, bounds.", pip=["rasterio"], pymod="rasterio",
   code="import rasterio, sys\nwith rasterio.open(sys.argv[1]) as d:\n    print('Ukuran :', d.width, 'x', d.height)\n    print('Band   :', d.count)\n    print('CRS    :', d.crs)\n    print('Bounds :', d.bounds)",
   prompts=[("f", "Path raster (contoh: citra.tif)", None, "file")], build=lambda v: [v["f"]])
_r("whitebox", "jblindsay/whitebox-tools", SUB_G, "WhiteboxTools", "data", "Alat analisis geospasial (hidrologi, medan); repo ditandai legacy.",
   status="jarang", why="Repo ditandai legacy; pengembangan berlanjut di Whitebox Workflows.", **_P("jblindsay/whitebox-tools"))

# ------------------------------------------------------------------ Analisis Data, Grafik & NLP
_r("pandas", "pandas-dev/pandas", SUB_A, "pandas", "lib", "Pustaka analisis data tabel (CSV/Excel). Di sini: ringkasan cepat sebuah CSV.",
   "Input: path berkas CSV. Hasil: dimensi, 10 baris pertama, ringkasan statistik.", pip=["pandas"], pymod="pandas", py_min=(3, 11),
   code="import pandas as pd, sys\ndf = pd.read_csv(sys.argv[1])\nprint('Baris x kolom:', df.shape)\nprint(df.head(10).to_string())\nprint(df.describe(include='all').T.head(25).to_string())",
   prompts=[("f", "Path berkas CSV (contoh: data.csv)", None, "file")], build=lambda v: [v["f"]])
_r("polars", "pola-rs/polars", SUB_A, "Polars", "lib", "Pustaka DataFrame super cepat. Di sini: ringkasan cepat sebuah CSV.",
   "Input: path CSV. Hasil: dimensi, 10 baris pertama, statistik.", pip=["polars"], pymod="polars", py_min=(3, 10),
   code="import polars as pl, sys\ndf = pl.read_csv(sys.argv[1])\nprint('Baris x kolom:', df.shape)\nprint(df.head(10))\nprint(df.describe())",
   prompts=[("f", "Path berkas CSV (contoh: data.csv)", None, "file")], build=lambda v: [v["f"]])
_r("duckdb", "duckdb/duckdb", SUB_A, "DuckDB", "lib", "Basis data analitik: query SQL langsung ke CSV/Parquet.",
   "Input: path CSV atau Parquet. Hasil: 10 baris pertama dan jumlah baris.", pip=["duckdb"], pymod="duckdb", py_min=(3, 9),
   code="import duckdb, sys\np = sys.argv[1].replace(\"'\", \"''\")\nprint(duckdb.sql(\"select count(*) as jumlah_baris from '%s'\" % p))\nprint(duckdb.sql(\"select * from '%s' limit 10\" % p))",
   prompts=[("f", "Path berkas CSV/Parquet (contoh: data.csv)", None, "file")], build=lambda v: [v["f"]])
_r("networkx", "networkx/networkx", SUB_A, "NetworkX", "lib", "Pustaka analisis graf/jaringan hubungan. Di sini: ringkasan graf dari daftar sisi.",
   "Input: path berkas teks berisi pasangan 'a b' per baris. Hasil: jumlah simpul/sisi dan simpul terpopuler.", pip=["networkx"], pymod="networkx",
   code="import networkx as nx, sys\ng = nx.read_edgelist(sys.argv[1])\nprint('Simpul:', g.number_of_nodes(), ' Sisi:', g.number_of_edges())\nfor n, d in sorted(g.degree, key=lambda x: -x[1])[:10]:\n    print('  ', n, d)",
   prompts=[("f", "Path berkas daftar sisi (contoh: hubungan.txt)", None, "file")], build=lambda v: [v["f"]])
_r("pyvis", "WestHealth/pyvis", SUB_A, "pyvis", "lib", "Membuat graf jaringan interaktif (HTML) dari Python.", pip=["pyvis"], pymod="pyvis", code=_CODE_VER.format(m="pyvis"))
_r("spacy", "explosion/spaCy", SUB_A, "spaCy", "lib", "Pustaka NLP industri: tokenisasi, entitas, dan analisis teks.",
   "Input: kalimat. Hasil: daftar token (tokenisasi bahasa Indonesia tanpa model besar).", pip=["spacy"], pymod="spacy", py_min=(3, 9),
   code="import spacy, sys\nnlp = spacy.blank('id')\ndoc = nlp(' '.join(sys.argv[1:]))\nprint('spaCy', spacy.__version__)\nprint([t.text for t in doc])",
   prompts=[("t", "Masukkan kalimat", None, "text")], build=lambda v: [v["t"]], note="Untuk pengenalan entitas, pasang model: python -m spacy download en_core_web_sm.")
_r("sbert", "UKPLab/sentence-transformers", SUB_A, "Sentence-Transformers", "lib", "Mengukur kemiripan makna dua kalimat (embedding), banyak bahasa.",
   "Input: dua kalimat. Hasil: skor kemiripan 0-1. Model ~400 MB diunduh saat pertama dipakai.", pip=["sentence-transformers"], pymod="sentence_transformers", py_min=(3, 10),
   code="import sys\nfrom sentence_transformers import SentenceTransformer, util\nm = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')\ne = m.encode(sys.argv[1:3])\nprint('Kemiripan:', round(float(util.cos_sim(e[0], e[1])), 3))",
   prompts=[("a", "Kalimat pertama", None, "text"), ("b", "Kalimat kedua", None, "text")], build=lambda v: [v["a"], v["b"]])
_r("datasette", "simonw/datasette", SUB_A, "Datasette", "cli", "Menjelajahi basis data SQLite lewat antarmuka web lokal.",
   "Input: path berkas .db. Buka alamat yang tampil (http://127.0.0.1:8001) di browser; Ctrl+C untuk berhenti.", pip=["datasette"], py_min=(3, 10), inter=True,
   prompts=[("f", "Path berkas SQLite (contoh: data.db)", None, "file")], build=lambda v: [v["f"]])
_r("openrefine", "OpenRefine/OpenRefine", SUB_A, "OpenRefine", "platform", "Membersihkan dan menyatukan data berantakan (alat favorit jurnalis data).",
   guide=[("Pasang Java", "Butuh Java 11+ (java -version)."), ("Unduh", "Unduh dari https://openrefine.org/download lalu ekstrak."), ("Jalankan", "./refine (Linux/macOS) atau openrefine.exe (Windows); buka http://127.0.0.1:3333")], needs=["java"])
_r("googletrends_data", "GoogleTrends/data", SUB_A, "GoogleTrends/data", "data", "Berkas data tren pencarian Google (arsip akademik).", **_P("GoogleTrends/data"))
_r("timesketch", "google/timesketch", SUB_F, "Timesketch", "platform", "Platform analisis linimasa forensik kolaboratif.",
   guide=_DK(("Unduh skrip", "curl -s -O https://raw.githubusercontent.com/google/timesketch/master/contrib/deploy_timesketch.sh"), ("Jalankan", "sudo bash deploy_timesketch.sh")), needs=["docker"])

# ------------------------------------------------------------------ Threat Intel & Kerentanan
_r("misp", "MISP/MISP", SUB_T, "MISP", "platform", "Platform berbagi intelijen ancaman (IOC) milik komunitas.",
   guide=_DK(("Unduh repo Docker", "git clone https://github.com/MISP/misp-docker && cd misp-docker"), ("Siapkan", "cp template.env .env  (ubah sandi dan URL)"), ("Jalankan", "docker compose up -d lalu buka https://localhost")),
   needs=["docker", "git"], note="Butuh RAM 4 GB+.")
_r("opencti", "OpenCTI-Platform/opencti", SUB_T, "OpenCTI", "platform", "Platform pengetahuan intelijen ancaman siber (graf pengetahuan).",
   guide=_DK(("Unduh", "git clone https://github.com/OpenCTI-Platform/docker && cd docker"), ("Atur .env", "Isi token, sandi, dan UUID di berkas .env"), ("Jalankan", "docker compose up -d lalu buka http://localhost:8080")), needs=["docker", "git"])
_r("intelowl", "intelowlproject/IntelOwl", SUB_T, "IntelOwl", "platform", "Satu API untuk menganalisis file/domain/IP memakai puluhan layanan intelijen sekaligus.",
   guide=_DK(("Unduh", "git clone https://github.com/intelowlproject/IntelOwl && cd IntelOwl"), ("Siapkan", "./initialize.sh"), ("Jalankan", "./start prod up")), needs=["docker", "git"],
   api="Banyak analyzer butuh API key layanan pihak ketiga (VirusTotal, Shodan, dll.).")
_r("attack_stix", "mitre-attack/attack-stix-data", SUB_T, "MITRE ATT&CK STIX Data", "data", "Data resmi MITRE ATT&CK dalam format STIX.", **_P("mitre-attack/attack-stix-data"))
_r("sigma_rules", "SigmaHQ/sigma", SUB_T, "Sigma Rules", "data", "Kumpulan aturan deteksi Sigma. Untuk mengonversi aturan pasang sigma-cli (pip install sigma-cli).", **_P("SigmaHQ/sigma"))
_r("yara", "VirusTotal/yara", SUB_F, "YARA", "cli", "Mencocokkan berkas dengan aturan pola (identifikasi malware).",
   "Input: path berkas aturan .yar dan berkas yang diperiksa. Hasil: aturan yang cocok.", sys={"apt": "yara", "brew": "yara", "dnf": "yara", "pacman": "yara"},
   prompts=[("rules", "Path berkas aturan YARA (contoh: aturan.yar)", None, "file"), ("f", "Path berkas/folder yang diperiksa", None, "file")], build=lambda v: [v["rules"], v["f"]],
   note="Proyek dalam mode pemeliharaan; penerusnya adalah YARA-X.")
_r("yarax", "VirusTotal/yara-x", SUB_F, "YARA-X", "cli", "Penerus YARA yang ditulis ulang dengan Rust: lebih cepat dan aman.",
   "Input: aturan dan berkas. Hasil: kecocokan.", rel=dict(repo="VirusTotal/yara-x"), sys={"brew": "yara-x"}, bins=["yr"],
   prompts=[("rules", "Path berkas aturan YARA (contoh: aturan.yar)", None, "file"), ("f", "Path berkas/folder yang diperiksa", None, "file")], build=lambda v: ["scan", v["rules"], v["f"]])
_r("cvelist", "CVEProject/cvelistV5", SUB_T, "CVE List V5", "data", "Basis data resmi CVE (format JSON v5).",
   note="Repo sangat besar (lebih dari 1 GB). Pakai --depth 1 (otomatis) atau cari CVE lewat modul NVD.", **_P("CVEProject/cvelistV5"))
_r("kevdata", "cisagov/kev-data", SUB_T, "CISA KEV Data", "data", "Katalog kerentanan yang diketahui sedang dieksploitasi (CISA KEV).",
   note="Alamat dikoreksi dari cisagov/known-exploited-vulnerabilities-catalog (repo lama dipindah).", **_P("cisagov/kev-data"))
_r("mitre_cti", "mitre/cti", SUB_T, "MITRE CTI", "data", "Data ATT&CK dan CAPEC dalam format STIX 2.0 (versi lama).", **_P("mitre/cti"))
_r("pymisp", "MISP/PyMISP", SUB_T, "PyMISP", "lib", "Pustaka Python untuk berinteraksi dengan server MISP.", "Dipakai dari skrip Python: from pymisp import PyMISP.",
   pip=["pymisp"], pymod="pymisp", code=_CODE_VER.format(m="pymisp"), note="Alamat dikoreksi dari CIRCL/PyMISP.", api="Butuh URL dan API key server MISP milik Anda/organisasi.")
_r("stix2", "oasis-open/cti-python-stix2", SUB_T, "stix2 (OASIS)", "lib", "Pustaka Python untuk membuat dan membaca objek STIX 2.",
   pip=["stix2"], pymod="stix2", code=_CODE_VER.format(m="stix2"), note="Alamat dikoreksi dari CIRCL/stix2.")
_r("misp_galaxy", "MISP/misp-galaxy", SUB_T, "MISP Galaxy", "data", "Kluster pengetahuan ancaman (aktor, malware) untuk MISP.", **_P("MISP/misp-galaxy"))
_r("misp_taxonomies", "MISP/misp-taxonomies", SUB_T, "MISP Taxonomies", "data", "Pustaka klasifikasi umum untuk pelabelan intelijen ancaman.", **_P("MISP/misp-taxonomies"))
_r("elastic_rules", "elastic/detection-rules", SUB_T, "Elastic Detection Rules", "data", "Aturan deteksi keamanan siap pakai dari Elastic.", **_P("elastic/detection-rules"))
_r("nvd_feeds", "fkie-cad/nvd-json-data-feeds", SUB_T, "NVD JSON Data Feeds", "data", "Rekonstruksi komunitas atas feed JSON NVD (CVE).", **_P("fkie-cad/nvd-json-data-feeds"))
_r("malicious_packages", "ossf/malicious-packages", SUB_T, "OpenSSF Malicious Packages", "data", "Laporan paket berbahaya di npm, PyPI, dan lainnya.", **_P("ossf/malicious-packages"))
_r("hashlookup", "hashlookup/hashlookup-server", SUB_T, "hashlookup-server", "platform", "Server pencarian hash berkas dikenal (CIRCL hashlookup).",
   guide=[("Baca README", "Ikuti README resmi untuk memasang server dan memuat dataset hash."), ("Atau layanan publik", "Pakai layanan CIRCL: https://hashlookup.circl.lu")],
   last="2026-01-26", note="Alamat dikoreksi dari CIRCL/hashlookup.")
_r("vulnerability_lookup", "vulnerability-lookup/vulnerability-lookup", SUB_T, "Vulnerability-Lookup", "platform", "Platform pencarian kerentanan cepat (CIRCL).",
   guide=[("Pakai layanan publik", "Buka https://vulnerability.circl.lu"), ("Pasang sendiri", "Ikuti README repo (Python + Valkey/Redis).")], last="2026-11-05", note="Alamat dikoreksi dari CIRCL/vulnerability-lookup.")
_r("ail", "CIRCL/AIL-framework", SUB_T, "AIL Framework", "platform", "Kerangka analisis kebocoran informasi: mengumpulkan paste, Tor, dan kanal pesan.",
   guide=[("Unduh", "git clone https://github.com/CIRCL/AIL-framework.git && cd AIL-framework"), ("Pasang dependensi", "./installing_deps.sh  (Ubuntu disarankan)"), ("Jalankan", "Ikuti README untuk memulai layanan dan membuka antarmuka web.")], needs=["git"])
_r("attack_navigator", "mitre-attack/attack-navigator", SUB_T, "ATT&CK Navigator", "platform", "Antarmuka web untuk memetakan teknik ATT&CK pada matriks.",
   guide=[("Pakai langsung", "Buka https://mitre-attack.github.io/attack-navigator/ di browser."), ("Atau lokal", "git clone lalu ikuti README (Node.js).")], last="2026-09-10",
   note="Alamat dikoreksi dari mitre/attack-navigator (lama).")
_r("deciderapp", "cisagov/decider", SUB_T, "Decider (CISA)", "platform", "Aplikasi web untuk memetakan perilaku ancaman ke ATT&CK.",
   guide=_DK(("Unduh", "git clone https://github.com/cisagov/decider.git"), ("Jalankan", "Ikuti README (docker compose).")), needs=["docker", "git"], status="jarang")

# ------------------------------------------------------------------ Forensik, Malware & Reverse Engineering
_r("volatility3", "volatilityfoundation/volatility3", SUB_F, "Volatility 3", "cli", "Kerangka forensik memori (RAM): proses, jaringan, malware.",
   pip=["volatility3"], bins=["vol"], note="Butuh tabel simbol sesuai OS sampel. Contoh: vol -f memori.raw windows.pslist")
_r("autopsy", "sleuthkit/autopsy", SUB_F, "Autopsy", "platform", "Platform forensik digital berbasis GUI (analisis disk).",
   guide=[("Unduh", "Windows: pasang dari https://www.autopsy.com/download ; Linux: ikuti Running_Linux_OSX.md di repo (butuh Java dan The Sleuth Kit)."), ("Jalankan", "Buka Autopsy lalu buat kasus baru.")], needs=["java"])
_r("hayabusa", "Yamato-Security/hayabusa", SUB_F, "Hayabusa", "platform", "Pembuat linimasa forensik cepat dari log Windows (EVTX).",
   guide=[("Unduh rilis", "Ambil zip sesuai OS dari halaman Releases GitHub dan ekstrak."), ("Perbarui aturan", "./hayabusa update-rules"), ("Jalankan", "./hayabusa csv-timeline -d folder_evtx -o linimasa.csv")])
_r("chainsaw", "WithSecureLabs/chainsaw", SUB_F, "Chainsaw", "platform", "Mencari jejak ancaman cepat di artefak forensik Windows (EVTX).",
   guide=[("Unduh rilis", "Ambil zip dari halaman Releases GitHub dan ekstrak."), ("Jalankan", "./chainsaw hunt folder_evtx -s sigma/ --mapping mappings/sigma-event-logs-all.yml")])
_r("bulk_extractor", "simsong/bulk_extractor", SUB_F, "bulk_extractor", "cli", "Mengekstrak email, URL, kartu kredit, dll. dari citra disk tanpa parse sistem berkas.",
   sys={"apt": "bulk-extractor", "brew": "bulk_extractor"}, prompts=[("f", "Path citra disk/berkas", None, "file")], build=lambda v: ["-o", os.path.join(OUT_DIR, "bulk_out"), v["f"]],
   how="Input: path citra disk atau berkas. Hasil: berkas laporan di folder hasil/bulk_out.")
_r("binwalk", "ReFirmLabs/binwalk", SUB_F, "Binwalk", "cli", "Menganalisis firmware: menemukan berkas dan data tertanam di dalam citra biner.",
   "Input: path berkas firmware. Hasil: daftar signature yang ditemukan.", sys={"apt": "binwalk", "brew": "binwalk"},
   prompts=[("f", "Path berkas firmware", None, "file")], build=lambda v: [v["f"]])
_r("capa", "mandiant/capa", SUB_F, "capa", "cli", "Mengenali kemampuan program (malware) dari berkas eksekusi tanpa menjalankannya.",
   "Input: path berkas eksekusi. Hasil: daftar kemampuan terdeteksi (ATT&CK).", pip=["flare-capa"], bins=["capa"], py_min=(3, 10),
   prompts=[("f", "Path berkas eksekusi (.exe/.dll/.elf)", None, "file")], build=lambda v: [v["f"]])
_r("floss", "mandiant/flare-floss", SUB_F, "FLOSS", "cli", "Menarik string tersembunyi/terenkripsi dari malware.",
   "Input: path berkas eksekusi. Hasil: string tersembunyi.", pip=["flare-floss"], bins=["floss"], py_min=(3, 10),
   prompts=[("f", "Path berkas eksekusi", None, "file")], build=lambda v: [v["f"]])
_r("flarevm", "mandiant/flare-vm", SUB_F, "FLARE-VM", "platform", "Skrip memasang lab analisis malware lengkap di Windows.",
   guide=[("Siapkan VM", "Gunakan mesin virtual Windows bersih (bukan komputer utama)."), ("Ikuti README", "Jalankan skrip instalasi PowerShell sesuai petunjuk di README resmi.")])
_r("flareemu", "mandiant/flare-emu", SUB_F, "flare-emu", "platform", "Emulasi kode untuk IDA Pro/Ghidra membantu analisis malware.",
   guide=[("Baca README", "Plugin untuk IDA Pro; ikuti petunjuk pemasangan di README.")], status="jarang")
_r("ipsw", "blacktop/ipsw", SUB_F, "ipsw", "cli", "Pisau lipat riset iOS/macOS: unduh firmware, parse IPSW, ekstrak kernel.",
   go="github.com/blacktop/ipsw/cmd/ipsw", sys={"brew": "blacktop/tap/ipsw"}, needs=["go"])
_r("dissect", "fox-it/dissect", SUB_F, "Dissect", "cli", "Kerangka forensik dan respons insiden (Fox-IT) untuk membaca citra dan koleksi.",
   pip=["dissect"], bins=["target-query"], py_min=(3, 10), note="Perintah utama: target-query, target-shell, target-info.")
_r("hindsight", "obsidianforensics/hindsight", SUB_F, "Hindsight (forensik Chrome)", "platform", "Menganalisis riwayat dan artefak peramban Chrome/Chromium.",
   guide=[("Pasang", "pip install pyhindsight"), ("Jalankan", "hindsight.py -i \"folder profil Chrome\" -o hasil")], last="2026-10-30",
   note="Pengganti serupa untuk 29a/chrome-forensics yang repo-nya sudah tidak ada.")
_r("monkey365", "silverhack/monkey365", SUB_S, "Monkey365", "platform", "Audit keamanan Microsoft 365, Azure, dan Entra ID (PowerShell).",
   guide=[("Butuh PowerShell 5.1+", "pwsh --version"), ("Unduh", "git clone https://github.com/silverhack/monkey365.git"), ("Ikuti README", "Import-Module .\\monkey365.psm1 lalu Invoke-Monkey365 (lihat README).")], needs=["git"],
   auth=True, last="2026-10-23", note="Alamat dikoreksi dari fox-it/monkey365.")
_r("dependencytrack", "DependencyTrack/dependency-track", SUB_S, "Dependency-Track", "platform", "Platform analisis komponen perangkat lunak (SBOM) dan kerentanannya.",
   guide=_DK(("Unduh compose", "curl -LO https://dependencytrack.org/docker-compose.yml"), ("Jalankan", "docker compose up -d lalu buka http://localhost:8080 (admin/admin, ganti sandi)")), needs=["docker"])
_r("caldera", "mitre/caldera", SUB_S, "MITRE Caldera", "platform", "Platform emulasi musuh otomatis untuk uji pertahanan (tim merah/biru).",
   guide=[("Unduh", "git clone https://github.com/mitre/caldera.git --recursive && cd caldera"), ("Pasang", "pip3 install -r requirements.txt"), ("Jalankan", "python3 server.py --insecure lalu buka http://localhost:8888")],
   needs=["git"], auth=True, note="Gunakan hanya di lab/lingkungan milik sendiri.")

# ------------------------------------------------------------------ Aplikasi Mobile & Android
_r("mobsf", "MobSF/Mobile-Security-Framework-MobSF", SUB_M, "MobSF", "platform", "Kerangka analisis keamanan aplikasi Android/iOS (statis dan dinamis).",
   guide=_DK(("Tarik image", "docker pull opensecurity/mobile-security-framework-mobsf:latest"), ("Jalankan", "docker run -it --rm -p 8000:8000 opensecurity/mobile-security-framework-mobsf:latest"),
             ("Buka", "Buka http://localhost:8000 (login awal: mobsf / mobsf) lalu unggah APK.")), needs=["docker"])
_r("exodus", "Exodus-Privacy/exodus", SUB_M, "Exodus Privacy", "platform", "Platform audit privasi aplikasi Android: pelacak dan izin.",
   guide=[("Pakai layanan publik", "Buka https://reports.exodus-privacy.eu.org dan cari nama aplikasi."), ("Atau pasang sendiri", "Lihat README repo (Docker).")])
_r("jadx", "skylot/jadx", SUB_M, "JADX", "cli", "Dekompiler APK/DEX ke kode Java yang bisa dibaca.",
   sys={"apt": "jadx", "brew": "jadx"}, needs=["java"], manual="https://github.com/skylot/jadx/releases",
   note="Bila paket sistem tidak ada, unduh zip dari halaman Releases lalu jalankan bin/jadx.")
_r("apktool", "iBotPeaches/Apktool", SUB_M, "Apktool", "cli", "Membongkar dan merakit ulang APK (resource dan smali).",
   sys={"apt": "apktool", "brew": "apktool"}, needs=["java"], manual="https://apktool.org/docs/install")
_r("androguard", "androguard/androguard", SUB_M, "Androguard", "cli", "Toolkit analisis APK dengan Python (manifest, izin, kode).", pip=["androguard"])
_r("frida", "frida/frida", SUB_M, "Frida", "cli", "Instrumentasi dinamis untuk menyelidiki aplikasi saat berjalan.",
   pip=["frida-tools"], bins=["frida"], note="Untuk perangkat Android butuh frida-server di perangkat (lihat dokumentasi resmi).")
_r("objection", "sensepost/objection", SUB_M, "Objection", "cli", "Eksplorasi runtime aplikasi seluler berbasis Frida.", pip=["objection"], py_min=(3, 10))
_r("mvt", "mvt-project/mvt", SUB_M, "MVT (Mobile Verification Toolkit)", "cli", "Memeriksa ponsel dari tanda spyware (Pegasus dll.).",
   pip=["mvt"], bins=["mvt-android", "mvt-ios"], py_min=(3, 11), note="Contoh: mvt-android --help atau mvt-ios --help.")
_r("appstore_scraper", "facundoolano/app-store-scraper", SUB_M, "app-store-scraper (Node.js)", "platform", "Pustaka Node.js untuk mengambil data aplikasi App Store.",
   guide=[("Pasang", "npm install app-store-scraper"), ("Contoh", "const store = require('app-store-scraper'); store.app({id: 553834731, country: 'id'}).then(console.log)")], needs=["node"], status="jarang")
_r("gplay_scraper", "JoMingyu/google-play-scraper", SUB_M, "google-play-scraper", "lib", "Mengambil info aplikasi Google Play (judul, skor, jumlah unduhan).",
   "Input: ID aplikasi (contoh com.whatsapp). Hasil: judul, skor, unduhan.", pip=["google-play-scraper"], pymod="google_play_scraper",
   code="import sys\nfrom google_play_scraper import app\nr = app(sys.argv[1], lang='id', country='id')\nfor k in ('title', 'developer', 'score', 'ratings', 'installs', 'version', 'updated'):\n    print(k.ljust(10), r.get(k))",
   prompts=[("id", "Masukkan ID aplikasi (contoh: com.whatsapp)", None, "text")], build=lambda v: [v["id"]])
_r("hacker_games", "brainphreak/hacker-game-suite", SUB_Z, "Hacker Game Suite", "data", "Kumpulan permainan interaktif untuk belajar keamanan siber.",
   status="tidakrelevan", why="Permainan latihan keamanan (HTML), bukan alat OSINT.", **_P("brainphreak/hacker-game-suite"))

# ------------------------------------------------------------------ Kerangka OSINT & Platform Investigasi
_r("sn0int", "kpcyrd/sn0int", SUB_K, "sn0int", "cli", "Kerangka OSINT semi-otomatis: mengumpulkan dan mengelola data target (modul Lua).",
   sys={"apt": "sn0int", "brew": "sn0int", "pacman": "sn0int"}, inter=True, manual="https://github.com/kpcyrd/sn0int/blob/main/README.md",
   note="Ketik help di dalam sn0int untuk perintah; quit untuk keluar.")
_r("openosint", "OpenOSINT/OpenOSINT", SUB_K, "OpenOSINT", "cli", "Toolkit OSINT terbuka berbasis Python (CLI dan server MCP).", pip=["OpenOSINT"], py_min=(3, 10))
_r("bellingcat_toolkit", "bellingcat/toolkit", SUB_K, "Bellingcat Online Investigations Toolkit", "data", "Daftar alat investigasi online dari Bellingcat (sumber situs toolkit).", **_P("bellingcat/toolkit"))
_r("osint_framework", "lockfale/OSINT-Framework", SUB_K, "OSINT Framework (data)", "data", "Sumber data pohon alat OSINT Framework (arf.json).", **_P("lockfale/OSINT-Framework"))
_r("awesome_osint_repos", "osintshifu/awesome-osint-repos", SUB_K, "Awesome OSINT Repositories", "data", "Katalog repo OSINT terkurasi dan ditinjau manual.", **_P("osintshifu/awesome-osint-repos"))
_r("osint_toolkit_djbpm", "djbpm/osint-toolkit", SUB_K, "osint-toolkit (djbpm)", "data", "Indeks OSINT, intelijen ancaman siber, dan alat terkait.", **_P("djbpm/osint-toolkit"))
_r("osint_toolbox_peripherals", "The-Osint-Toolbox/OSINT-Toolbox-Peripherals", SUB_K, "OSINT Toolbox Peripherals", "data", "Daftar alat dan perangkat pendukung kerja OSINT.", **_P("The-Osint-Toolbox/OSINT-Toolbox-Peripherals"))
_r("public_apis", "public-apis/public-apis", SUB_K, "Public APIs", "data", "Daftar ribuan API publik gratis (berguna untuk membuat modul OSINT).",
   note="Alamat dikoreksi dari opensources/awesome-public-apis (repo lama tidak ada).", last="2026-11-05", **_P("public-apis/public-apis"))
_r("linkscope", "AccentuSoft/LinkScope_Client", SUB_K, "LinkScope Client", "platform", "Aplikasi desktop investigasi OSINT berbasis graf.",
   guide=[("Unduh", "Ambil installer dari halaman rilis yang tertaut di README."), ("Atau dari sumber", "git clone lalu pip install -r requirements.txt && python3 LinkScope.py")], needs=["git"], status="jarang")
_r("flowsint", "reconurge/flowsint", SUB_K, "Flowsint", "platform", "Platform investigasi OSINT berbasis graf (self-hosted).",
   guide=_DK(("Unduh", "git clone https://github.com/reconurge/flowsint && cd flowsint"), ("Ikuti README", "Jalankan perintah docker compose sesuai README.")), needs=["docker", "git"],
   last="2026-10-18", note="Alamat dikoreksi dari flowsint/flowsint (repo lama tidak ada).")
_r("aleph", "alephdata/aleph", SUB_K, "Aleph (OCCRP)", "platform", "Platform arsip data investigasi: dokumen, perusahaan, dan hubungan.",
   guide=_DK(("Unduh", "git clone https://github.com/alephdata/aleph && cd aleph"), ("Jalankan", "make all  (lalu buka http://localhost:8080)")), needs=["docker", "git"])
_r("followthemoney", "opensanctions/followthemoney", SUB_K, "FollowTheMoney", "cli", "Model data entitas (orang, perusahaan, aliran uang) dan alat ftm.", pip=["followthemoney"], bins=["ftm"], py_min=(3, 11))
_r("datashare", "ICIJ/datashare", SUB_K, "Datashare (ICIJ)", "platform", "Mesin pencari dokumen mandiri untuk menemukan cerita di ribuan berkas.",
   guide=_DK(("Jalankan", "docker run -ti -p 8080:8080 icij/datashare:latest --mode EMBEDDED"), ("Buka", "Buka http://localhost:8080 lalu pilih folder dokumen.")), needs=["docker"])
_r("rigour", "opensanctions/rigour", SUB_K, "rigour", "lib", "Pustaka normalisasi nama, alamat, dan identitas untuk pencocokan data.", pip=["rigour"], pymod="rigour",
   code=_CODE_VER.format(m="rigour"), note="Alamat dikoreksi dari ICIJ/rigour.")
_r("opensanctions", "opensanctions/opensanctions", SUB_K, "OpenSanctions (pipeline)", "platform", "Mengumpulkan data sanksi dan orang berpengaruh (PEP).",
   guide=[("Pakai data siap", "Unduh dataset di https://www.opensanctions.org/datasets/ (gratis untuk non-komersial)."), ("Pipeline sendiri", "Lihat README repo (butuh Docker).")])
_r("yente", "opensanctions/yente", SUB_K, "yente", "platform", "API pencocokan nama ke data sanksi/PEP (self-hosted).",
   guide=_DK(("Jalankan", "docker run -p 8000:8000 ghcr.io/opensanctions/yente:latest"), ("Uji", "Buka http://localhost:8000/docs")), needs=["docker"])
_r("fourcat", "digitalmethodsinitiative/4cat", SUB_P, "4CAT", "platform", "Alat menangkap dan menganalisis data platform daring (forum, media sosial).",
   guide=_DK(("Unduh", "git clone https://github.com/digitalmethodsinitiative/4cat && cd 4cat"), ("Jalankan", "docker compose up -d lalu buka http://localhost")), needs=["docker", "git"],
   note="Alamat dikoreksi dari 4CAT4/4CAT (repo lama tidak ada).")
_r("mediacloud", "mediacloud/api-client", SUB_P, "Media Cloud API Client", "lib", "Klien Python untuk menelusuri berita lewat Media Cloud.", pip=["mediacloud"], pymod="mediacloud",
   code=_CODE_VER.format(m="mediacloud"), api="Butuh API key Media Cloud (akun gratis di https://search.mediacloud.org).",
   note="Alamat dikoreksi dari mediacloud/api dan mediacloud/MediaCloud (repo lama).")
_r("arctic_shift", "ArthurHeitmann/arctic_shift", SUB_P, "Arctic Shift (arsip Reddit)", "data", "Arsip data Reddit untuk peneliti dengan API pencarian gratis.",
   "Dokumentasi API dan unduhan data Reddit. Lihat juga modul Reddit di menu.", **_P("ArthurHeitmann/arctic_shift"))

# ------------------------------------------------------------------ Platform Komunitas, Feed & Pesan
_r("rsshub", "DIYgod/RSSHub", SUB_P, "RSSHub", "platform", "Membuat RSS untuk hampir semua situs (pemantauan sumber tanpa buka halaman).",
   guide=_DK(("Jalankan", "docker run -d --name rsshub -p 1200:1200 diygod/rsshub"), ("Buka", "Buka http://localhost:1200 lalu pilih rute RSS.")), needs=["docker"])
_r("freshrss", "FreshRSS/FreshRSS", SUB_P, "FreshRSS", "platform", "Pembaca RSS mandiri yang ringan untuk memantau banyak sumber.",
   guide=_DK(("Jalankan", "docker run -d --name freshrss -p 8080:80 freshrss/freshrss"), ("Buka", "Buka http://localhost:8080 dan selesaikan pemasangan awal.")), needs=["docker"])
_r("miniflux", "miniflux/v2", SUB_P, "Miniflux", "platform", "Pembaca RSS minimalis (satu biner Go + PostgreSQL).",
   guide=[("Ikuti panduan resmi", "https://miniflux.app/docs/installation.html (paket, biner, atau Docker)."), ("Jalankan", "miniflux -migrate -create-admin lalu miniflux")])
_r("rssbridge", "RSS-Bridge/rss-bridge", SUB_P, "RSS-Bridge", "platform", "Membuat feed untuk situs yang tidak punya RSS (aplikasi PHP).",
   guide=_DK(("Jalankan", "docker run -d --name rss-bridge -p 3000:80 rssbridge/rss-bridge"), ("Buka", "Buka http://localhost:3000")), needs=["docker"])
_r("huginn", "huginn/huginn", SUB_P, "Huginn", "platform", "Membangun agen otomatis yang memantau web dan memicu tindakan.",
   guide=_DK(("Jalankan", "docker run -it -p 3000:3000 ghcr.io/huginn/huginn"), ("Buka", "Buka http://localhost:3000 (admin / password).")), needs=["docker"])
_r("hn_api", "HackerNews/API", SUB_P, "Hacker News API (dokumentasi)", "data", "Dokumentasi API resmi Hacker News (Firebase).", status="jarang", **_P("HackerNews/API"))

# ------------------------------------------------------------------ Pemindai Keamanan, Cloud & Kontainer
_r("osv_scanner", "google/osv-scanner", SUB_S, "OSV-Scanner", "cli", "Memindai dependensi proyek terhadap basis data kerentanan OSV.",
   go="github.com/google/osv-scanner/v2/cmd/osv-scanner", rel=dict(repo="google/osv-scanner"), sys={"brew": "osv-scanner"}, needs=["go"])
_r("trivy", "aquasecurity/trivy", SUB_S, "Trivy", "cli", "Pemindai kerentanan image kontainer, repo, dan konfigurasi.",
   rel=dict(repo="aquasecurity/trivy"), sys={"brew": "trivy"})
_r("scorecard", "ossf/scorecard", SUB_S, "OpenSSF Scorecard", "cli", "Menilai keamanan sebuah repo open source (skor praktik terbaik).",
   "Input: repo GitHub (owner/repo). Hasil: skor tiap pemeriksaan.", rel=dict(repo="ossf/scorecard"), sys={"brew": "scorecard"},
   prompts=[("repo", "Masukkan repo (contoh: owner/repo)", None, "repo")], build=lambda v: ["--repo=" + v["repo"].replace("https://", "")],
   api="Butuh token GitHub gratis di variabel GITHUB_AUTH_TOKEN.")
_r("grype", "anchore/grype", SUB_S, "Grype", "cli", "Pemindai kerentanan untuk image kontainer dan berkas.", "Input: image (alpine:latest) atau dir:folder. Hasil: daftar kerentanan.",
   go="github.com/anchore/grype/cmd/grype", rel=dict(repo="anchore/grype"), sys={"brew": "grype"},
   prompts=[("t", "Masukkan image Docker atau dir:folder (contoh: alpine:latest)", None, "text")], build=lambda v: [v["t"]])
_r("syft", "anchore/syft", SUB_S, "Syft", "cli", "Membuat SBOM (daftar komponen perangkat lunak) dari image/folder.", "Input: image (alpine:latest) atau dir:folder. Hasil: daftar paket.",
   go="github.com/anchore/syft/cmd/syft", rel=dict(repo="anchore/syft"), sys={"brew": "syft"},
   prompts=[("t", "Masukkan image Docker atau dir:folder (contoh: alpine:latest)", None, "text")], build=lambda v: [v["t"]])
_r("semgrep", "semgrep/semgrep", SUB_S, "Semgrep", "cli", "Pemindai kode statis cepat untuk menemukan bug dan celah keamanan.",
   "Input: folder kode. Hasil: temuan aturan p/default.", pip=["semgrep"], py_min=(3, 10),
   prompts=[("d", "Path folder kode (contoh: .)", ".", "file")], build=lambda v: ["scan", "--config", "p/default", "--metrics", "off", v["d"]])
_r("gosec", "securego/gosec", SUB_S, "gosec", "cli", "Pemindai keamanan untuk kode Go.", go="github.com/securego/gosec/v2/cmd/gosec", rel=dict(repo="securego/gosec"), sys={"brew": "gosec"}, needs=["go"])
_r("scubagear", "cisagov/ScubaGear", SUB_S, "ScubaGear", "platform", "Menilai konfigurasi keamanan Microsoft 365 terhadap baseline CISA (PowerShell).",
   guide=[("Butuh PowerShell 5.1", "Windows PowerShell atau pwsh."), ("Pasang modul", "Install-Module -Name ScubaGear"), ("Jalankan", "Invoke-SCuBA")])
_r("kubebench", "aquasecurity/kube-bench", SUB_S, "kube-bench", "cli", "Memeriksa klaster Kubernetes terhadap CIS Benchmark.", rel=dict(repo="aquasecurity/kube-bench"), go="github.com/aquasecurity/kube-bench",
   note="Hanya berguna bila Anda punya klaster Kubernetes.")
_r("bloodhound_py", "fox-it/BloodHound.py", SUB_S, "BloodHound.py", "cli", "Pengumpul data Active Directory untuk BloodHound (uji penetrasi).",
   pip=["bloodhound"], bins=["bloodhound-python"], auth=True, note="Hanya untuk jaringan yang Anda punya izin resmi.")
_r("cheatsheets", "OWASP/CheatSheetSeries", SUB_S, "OWASP Cheat Sheet Series", "data", "Kumpulan lembar contekan keamanan aplikasi dari OWASP.", **_P("OWASP/CheatSheetSeries"))

# ------------------------------------------------------------------ Data & Layanan Indonesia
_r("cekrekening", "im-hanzou/cekrekening", SUB_ID, "Cek Rekening", "platform", "API/web pengecekan nama rekening bank (layanan pihak ketiga).",
   guide=[("Baca README", "Layanan tidak resmi; bisa berbayar/berubah. Gunakan hanya untuk rekening sendiri atau transaksi sah."), ("Pasang (Node.js)", "git clone lalu npm install && npm start (lihat README).")],
   status="jarang", needs=["node", "git"], api="Layanan pihak ketiga; ketentuan dan biaya bisa berubah. Jangan dipakai menelusuri rekening orang lain tanpa hak.")
_r("mutasi_qris", "izulwahidin/mutasi-qris.id", SUB_ID, "mutasi-qris.id", "data", "Pustaka PHP untuk mengambil mutasi transaksi QRIS merchant.", **_P("izulwahidin/mutasi-qris.id"))
for _k, _rp, _tt, _ab in [
        ("apponkir", "ayaavdews/AppCekOngkir", "AppCekOngkir", "Aplikasi PHP cek ongkos kirim dan lacak resi."),
        ("kodepos_pentagonal", "pentagonal/Indonesia-Postal-Code", "Indonesia-Postal-Code", "Data kode pos Indonesia."),
        ("kodepos_rfahmi", "rfahmi/kode-pos-indonesia", "kode-pos-indonesia", "Basis data kode pos seluruh wilayah Indonesia."),
        ("kodepos_erlange", "erlange/Kodepos-Wilayah-Indonesia", "Kodepos-Wilayah-Indonesia", "Kode pos wilayah administratif Indonesia."),
        ("kodepos_bachors", "bachors/Kode-Pos-API", "Kode-Pos-API", "API kode pos berbasis Firebase (contoh)."),
        ("kodepos_w3app", "w3appdev/kodepos", "kodepos (w3appdev)", "Daftar kode wilayah NKRI beserta kode pos."),
        ("cek_lulus", "zifaucode/cek-lulus", "cek-lulus", "Aplikasi web pengumuman kelulusan sekolah."),
        ("mutasi_bni", "galihazizif/mutasi-bni", "mutasi-bni", "Skrip PHP mengambil mutasi dari internet banking BNI."),
        ("cek_nik", "namtxs/cek-nik", "cek-nik", "Skrip pencarian data NIK dari situs KPU."),
        ("cek_username", "ilhamjaya08/cek-username", "cek-username", "Proyek Svelte pengecek username."),
        ("cekresi", "hajirodeon/cekresi", "cekresi", "Cek resi memakai API AfterShip."),
        ("ceksubs", "arief125/ceksubs", "ceksubs", "Proyek cek langganan (tanpa dokumentasi)."),
        ("api_cek", "sandrocods/API-Cek", "API-Cek", "API cek tagihan."),
        ("cek_nisn", "bachors/Android-Hybrid-Cek-NISN", "Android-Hybrid-Cek-NISN", "Aplikasi Android hibrida cek NISN.")]:
    _extra = {}
    if _k in ("mutasi_bni", "cek_nik"):
        _extra["note"] = "Mengambil data dari layanan resmi tanpa izin dapat melanggar ketentuan layanan/privasi; baca README dan hukum terkait."
    if _k in ("cek_lulus",):
        _extra["status"] = "tidakrelevan"
        _extra["why"] = "Aplikasi pengumuman kelulusan sekolah, bukan alat OSINT."
    _r(_k, _rp, SUB_ID, _tt, "data", _ab, **dict(_extra, **_P(_rp)))

# ------------------------------------------------------------------ Dikoreksi / mati / tidak relevan
_r("eagleeye", "ThoughtfulDev/EagleEye", SUB_U, "EagleEye", "data", "Pencarian wajah lintas media sosial (Python lama).", **_P("ThoughtfulDev/EagleEye"))
_r("pinterest_email", "OSINT-mindset/pinterest-email-checker", SUB_E, "pinterest-email-checker", "data", "Memeriksa apakah email terdaftar di Pinterest.", **_P("OSINT-mindset/pinterest-email-checker"))
_r("tinder_detective", "defaultnamehere/tinder-detective", SUB_U, "tinder-detective", "dead", "Alat lama untuk memeriksa pengguna Tinder.",
   why="Pengembang menyatakan sudah tidak berfungsi sejak Tinder menghapus fitur yang dipakai (2018).")
_r("web_check_api", "xray-web/web-check-api", SUB_D, "web-check-api", "data", "API Go di balik Web-Check (analisis situs).", **_P("xray-web/web-check-api"))
_r("mitm6", "fox-it/mitm6", SUB_S, "mitm6", "cli", "Uji penetrasi: memanfaatkan konfigurasi IPv6 bawaan Windows (hanya jaringan sah).", pip=["mitm6"], auth=True)
_r("redeye", "cisagov/RedEye", SUB_S, "RedEye", "platform", "Alat visualisasi log operasi tim merah (CISA).", guide=[("Baca README", "Proyek tidak aktif; lihat README repo untuk rilis terakhir.")])
_r("kubehunter", "aquasecurity/kube-hunter", SUB_S, "kube-hunter", "cli", "Pemburu celah pada klaster Kubernetes.", pip=["kube-hunter"], auth=True,
   why="Pengembang menyatakan tidak lagi aktif dikembangkan.")
_r("certstream", "CaliDog/certstream-python", SUB_D, "certstream-python", "lib", "Memantau sertifikat SSL yang baru diterbitkan secara langsung.",
   pip=["certstream"], pymod="certstream", code=_CODE_VER.format(m="certstream"))
_r("gospider", "jaeles-project/gospider", SUB_C, "GoSpider", "cli", "Perayap web cepat dalam Go.", go="github.com/jaeles-project/gospider", needs=["go"])
_r("pythonwhois", "joepie91/python-whois", SUB_N, "python-whois (joepie91)", "dead", "Pustaka WHOIS Python lama.",
   why="Terakhir diperbarui 2014 dan tidak kompatibel dengan Python 3 modern. Pakai perintah whois sistem atau modul ipwhois.")
_r("mediacloud_old", "mediacloud/MediaCloud", SUB_P, "MediaCloud (kode lama)", "data", "Kode sumber platform Media Cloud (arsip).", **_P("mediacloud/MediaCloud"))
_irr("matrixjs", "matrix-org/matrix-js-sdk", SUB_P, "matrix-js-sdk", "data", "Pustaka JavaScript klien Matrix.", **_P("matrix-org/matrix-js-sdk"))
_irr("zulip", "zulip/zulip", SUB_P, "Zulip", "platform", "Aplikasi obrolan tim bertopik.", guide=[("Pakai hosting", "https://zulip.com atau panduan self-host di dokumentasi resmi.")])
_irr("mattermost", "mattermost/mattermost", SUB_P, "Mattermost", "platform", "Platform kolaborasi tim (alternatif Slack).", guide=[("Panduan resmi", "https://docs.mattermost.com/deploy/deployment-overview.html")])
_irr("elementweb", "element-hq/element-web", SUB_P, "Element Web", "platform", "Klien web Matrix (obrolan terdesentralisasi).", guide=[("Pakai langsung", "Buka https://app.element.io")])
_irr("discourse", "discourse/discourse", SUB_P, "Discourse", "platform", "Perangkat lunak forum komunitas.", guide=[("Panduan resmi", "https://github.com/discourse/discourse_docker")])
_irr("lemmy", "LemmyNet/lemmy", SUB_P, "Lemmy", "platform", "Agregator tautan dan forum fediverse (server).", guide=[("Panduan resmi", "https://join-lemmy.org/docs/administration/install_docker.html")])
_irr("ndpi", "ntop/nDPI", SUB_N, "nDPI", "data", "Pustaka C inspeksi paket mendalam.", **_P("ntop/nDPI"))
_irr("security_docs", "elastic/security-docs", SUB_T, "Elastic security-docs", "data", "Sumber dokumentasi produk Elastic Security.", **_P("elastic/security-docs"))
_irr("inspektor_gadget", "inspektor-gadget/inspektor-gadget", SUB_S, "Inspektor Gadget", "platform", "Observabilitas Kubernetes berbasis eBPF.", guide=[("Panduan resmi", "https://inspektor-gadget.io/docs")])
_irr("k9s", "derailed/k9s", SUB_S, "K9s", "platform", "Antarmuka terminal untuk mengelola klaster Kubernetes.", guide=[("Pasang", "brew install k9s  atau  go install github.com/derailed/k9s@latest")])
_irr("kube_state_metrics", "kubernetes/kube-state-metrics", SUB_S, "kube-state-metrics", "platform", "Layanan metrik status objek Kubernetes.", guide=[("Panduan resmi", "https://github.com/kubernetes/kube-state-metrics#installation")])
_irr("cesium_native", "CesiumGS/cesium-native", SUB_G, "cesium-native", "data", "Pustaka C++ untuk mesin 3D (bukan alat siap pakai).", **_P("CesiumGS/cesium-native"))
_irr("ipsw_diffs", "blacktop/ipsw-diffs", SUB_F, "ipsw-diffs", "data", "Perbedaan kernel/firmware iOS antar versi (riset iOS).", **_P("blacktop/ipsw-diffs"))
_irr("threat_dragon", "OWASP/threat-dragon", SUB_S, "OWASP Threat Dragon", "platform", "Alat pemodelan ancaman desain sistem.", guide=[("Pakai langsung", "Aplikasi desktop/web: https://www.threatdragon.com")],
     last="2026-10-20", note="Alamat dikoreksi dari OWASP/ThreatDragon.")
_r("usbarmory", "WithSecureLabs/usbarmory", SUB_Z, "USB Armory", "dead", "Perangkat keras komputer mini USB (alamat lama).", why="Repo di alamat ini tidak ditemukan dan bukan alat OSINT.")
_r("opencorporates", "opencorporates/opencorporates", SUB_K, "OpenCorporates (repo)", "dead", "Basis data perusahaan terbuka.",
   why="Repo tidak ada. OpenCorporates dipakai lewat situs/API resminya (API key umumnya berbayar).")
_r("worldmonitor", "WorldMonitor/WorldMonitor", SUB_K, "WorldMonitor", "dead", "Pemantau peristiwa dunia.", why="Repo di alamat ini tidak ditemukan. Gunakan modul Pemantauan Internasional di menu.")
_r("italian_news", "ivbeg/awesome-italian-news", SUB_P, "awesome-italian-news", "dead", "Daftar sumber berita Italia.", why="Repo tidak ditemukan.")
_r("gdelt_repo", "gsantopaolo/gdelt", SUB_P, "gsantopaolo/gdelt", "dead", "Proyek GDELT pribadi.", why="Repo tidak ditemukan. Data GDELT resmi: https://www.gdeltproject.org (dipakai modul berita cepat).")
_r("maritime_security", "cisagov/Maritime-Security", SUB_Z, "Maritime-Security (CISA)", "dead", "Materi keamanan maritim.", why="Repo tidak ditemukan.")
_r("mediacloud_api_old", "mediacloud/api", SUB_P, "mediacloud/api", "dead", "Repo API lama Media Cloud.", why="Repo tidak ditemukan; gunakan Media Cloud API Client (mediacloud/api-client).", alt="mediacloud/api-client")

# ------------------------------------------------------------------ Pemeriksa Repo (Genetic) & NXA  (repo XyasZor)
_r("genetic", "XyasZor/Genetic", SUB_X, "Genetic (Repo-ScanGT)", "cli",
   "Memeriksa risiko sebuah repo GitHub sebelum dipasang: persentase bahaya, tingkat risiko, dan temuan mencurigakan.",
   "Tekan x di menu Github Tools, tempel URL repo (atau owner/repo). Hasil: persen bahaya + rincian temuan. Tanpa pustaka tambahan.",
   git=dict(url="https://github.com/XyasZor/Genetic.git", dir="Genetic", entry="genetic.py", req=None), pip=None, last="2026-11-02", status="aktif",
   prompts=[("repo", "Masukkan repo yang akan diperiksa (contoh: owner/repo atau https://github.com/owner/repo)", None, "repo")],
   build=lambda v: [v["repo"]], outcwd=True,
   note="Panduan install.md di repo menyebut main.py, padahal berkas sebenarnya genetic.py (Giga OSINT sudah memakai nama yang benar). "
        "Hasil hanyalah indikator risiko, bukan vonis; tetap baca kodenya sendiri.")
_r("nxa", "XyasZor/nxa", SUB_X, "NXA (Nexus OSINT Toolbox)", "cli",
   "Kotak alat OSINT terminal dengan 1000+ tool dari OSINT Framework; cari, telusuri kategori, dan buka tautan.",
   "Menu interaktif: ketik nomor atau kata kunci untuk mencari tool. Butuh internet saat pertama (mengunduh arf.json). Tanpa pustaka tambahan.",
   git=dict(url="https://github.com/XyasZor/nxa.git", dir="nxa", entry="nxa.py", req=None), pip=None, last="2026-11-02", status="aktif",
   inter=True, prompts=[], build=lambda v: ["--fast"],
   note="Bila daftar bawaan yang kecil muncul, berarti arf.json gagal diunduh: periksa internet lalu jalankan lagi dengan --update.")
_r("apiosintds", "davidonzo/apiosintDS", SUB_T, "apiosintDS (DigitalSide)", "cli",
   "Mencari IP, domain, URL, atau hash di basis ancaman DigitalSide (osint.digitalside.it) tanpa API key.",
   "Input: IP, domain, URL atau hash. Hasil: apakah terdaftar sebagai IoC berbahaya. Data disimpan 7 hari.",
   pip=["apiosintDS"], bins=["apiosintDS"], prompts=[("e", "Masukkan IP, domain, URL atau hash (contoh: 8.8.8.8)", None, "text")],
   build=lambda v: ["-e", v["e"], "-p", "-nc"], last="2024-05-28",
   why="Rilis PyPI terakhir (2.0.3) tahun 2024; layanan DigitalSide bisa tidak lengkap atau lambat.", status="jarang")
# =====================================================================
#  v3.1 - TAMBAHAN REPO GITHUB (Prompt_3, diverifikasi 7 Nov 2026: git ls-remote + clone dangkal + isi README/skrip)
#  Beberapa repo dari daftar TIDAK ditambahkan; alasannya dicatat di ringkasan akhir untuk pengguna, bukan di sini.
# =====================================================================
_r("xophy", "w4sif404/xophy", SUB_K, "XOPHY Framework", "cli",
   "Kerangka pengumpulan informasi: DNS, dork Google, subdomain, media sosial, IoT, pemantau ransomware, dan laporan PDF.",
   "Membuka menu XOPHY sendiri; ikuti petunjuk di layar (pilih nomor modul).",
   git=dict(url="https://github.com/w4sif404/xophy.git", dir="xophy", entry="core/cli.py", req="requirements.txt"),
   inter=True, prompts=[], build=lambda v: [],
   api="Modul Shodan opsional butuh SHODAN_API_KEY sendiri; modul lain tanpa API key.")
_r("phantomrecon", "c0d3s3cl4b/PhantomRecon", SUB_K, "PhantomRecon", "cli",
   "Kerangka OSINT dan rekonaisans modular (delapan mesin) dengan antarmuka terminal Rich.",
   "Membuka menu PhantomRecon sendiri; ikuti petunjuk di layar. Hanya untuk sistem/akun/domain milik sendiri atau berizin sah.",
   git=dict(url="https://github.com/c0d3s3cl4b/PhantomRecon.git", dir="PhantomRecon", entry="phantomrecon.py", req="requirements.txt"),
   inter=True, auth=True, prompts=[], build=lambda v: [])
_r("waspsting", "N00dleN00b/WaspSting", SUB_S, "WaspSting", "cli",
   "Alat dokumentasi pentest sah: enumerasi subdomain, galeri aset, fuzzer payload (SQLi/XSS/SSTI/SSRF), laporan otomatis.",
   "Membuka menu WaspSting sendiri; ikuti petunjuk di layar. Hanya untuk sistem yang kamu miliki atau berizin tertulis.",
   git=dict(url="https://github.com/N00dleN00b/WaspSting.git", dir="WaspSting", entry="waspsting.py", req="requirements.txt"),
   inter=True, auth=True, prompts=[], build=lambda v: [],
   api="Fitur AI lokal opsional (Ollama); tanpa itu tool tetap berjalan penuh.")
_r("apikeyscan", "qyzan/apikeyScan", SUB_E, "apiKeyScan", "cli",
   "Memeriksa apa saja yang bisa dilakukan sebuah API key yang bocor/ditemukan: akses data, kuota, layanan auth, dll.",
   "Input: satu API key (milikmu sendiri, atau yang kamu temukan bocor dan berwenang memeriksanya).",
   git=dict(url="https://github.com/qyzan/apikeyScan.git", dir="apikeyScan", entry="apiKeyScan.py", req="requirements.txt"),
   prompts=[("key", "Masukkan API key yang ingin diperiksa", "AIzaSyXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX", "text")],
   build=lambda v: ["scan", "-k", v["key"], "--all-formats"])
_r("kumo_recon", "karim852/KUMO-Domain-Recon-Tool", SUB_D, "KUMO Domain Recon", "cli",
   "Pemindaian domain: subdomain, DNS, dan 419+ pemeriksaan kerentanan (CVE) web dalam satu mesin.",
   "Input: domain atau URL target (izin sah wajib untuk pemindaian aktif).",
   pip=["flask", "requests", "dnspython", "urllib3"],
   git=dict(url="https://github.com/karim852/KUMO-Domain-Recon-Tool.git", dir="KUMO-Domain-Recon-Tool", entry="kumo.py", req=None),
   auth=True, prompts=[("domain", "Masukkan domain target (contoh: example.com)", None, "domain")],
   build=lambda v: [v["domain"]])
_r("blacktrace", "fawadqureshi007/Black", SUB_K, "BlackTrace", "cli",
   "Kerangka OSINT serba bisa bermenu: username, email, nomor telepon, gambar, IP/domain, dork, dan lokasi.",
   "Membuka menu BlackTrace sendiri (pilih nomor 1-20); ikuti petunjuk di layar.",
   git=dict(url="https://github.com/fawadqureshi007/Black.git", dir="Black", entry="blacktrace.py", req="requirements.txt"),
   inter=True, prompts=[], build=lambda v: [],
   note="Bila fitur analisis gambar/teks gagal karena model bahasa belum ada, pasang manual: python3 -m spacy download en_core_web_sm")
_r("corscan", "Angix-Black/Corscan", SUB_S, "Corscan", "cli",
   "Pemindai kerentanan konfigurasi CORS (Cross-Origin Resource Sharing) pada aplikasi web, dengan laporan HTML/JSON.",
   "Input: URL target (izin sah wajib). Hasil: celah CORS, header keamanan, dan ringkasan risiko.",
   git=dict(url="https://github.com/Angix-Black/Corscan.git", dir="Corscan", entry="main.py", req="requirements.txt"),
   auth=True, prompts=[("url", "Masukkan URL target (contoh: https://target.com)", None, "url")],
   build=lambda v: ["-u", v["url"], "--analyze-headers", "--filter"])
_r("toxssin", "t3l3machus/toxssin", SUB_S, "toxssin", "cli",
   "Kerangka eksploitasi XSS (post-exploitation): server + payload untuk sesi XSS pada pengujian penetrasi berizin.",
   "Butuh server/domain dan sertifikat TLS milikmu sendiri. Hanya untuk pengujian pada sistem berizin sah tertulis.",
   git=dict(url="https://github.com/t3l3machus/toxssin.git", dir="toxssin", entry="toxssin.py", req="requirements.txt"),
   auth=True,
   prompts=[("url", "URL server toxssin-mu (contoh: https://127.0.0.1)", None, "url"),
            ("certfile", "Path file sertifikat TLS (.pem) milikmu", None, "file"),
            ("keyfile", "Path file kunci privat TLS (.pem) milikmu", None, "file")],
   build=lambda v: ["-u", v["url"], "-c", v["certfile"], "-k", v["keyfile"], "-q"])
_r("sapper_v2", "N1nEmAn/sapper-v2", SUB_S, "sapper-v2 (Autonomous Pentest Legion)", "platform",
   "Kerangka orkestrasi multi-agen AI untuk pentest otomatis (juara kompetisi CTF attack-defense). Kompleks: butuh CLI agen AI sendiri (mis. Claude Code/Codex) dan Docker.",
   "Giga OSINT hanya mengunduh repo-nya; pemasangan dan pemakaian penuh mengikuti README resminya (bash install.sh, lalu nvwabase setup).",
   git=_P("N1nEmAn/sapper-v2")["git"],
   guide=[("Baca README resmi dulu", "https://github.com/N1nEmAn/sapper-v2#readme"),
          ("Pasang (di dalam folder repo)", "bash install.sh")],
   note="Hanya untuk pengujian berizin sah; alat ini kompleks dan bukan sekadar skrip sekali jalan.")
_r("osintgram_web", "Datalux/Osintgram", SUB_U, "Osintgram", "platform",
   "Investigasi akun Instagram publik lewat antarmuka web lokal: follower, caption, hashtag, lokasi, kebiasaan posting.",
   "Giga OSINT mengunduh repo-nya; jalankan server lokal lalu buka alamatnya di browser.",
   git=dict(url="https://github.com/Datalux/Osintgram.git", dir="Osintgram", req="requirements.txt"),
   guide=[("Pasang dependensi", "pip install -r requirements.txt"),
          ("Jalankan server lokal", "uvicorn src.web.app:app --host 127.0.0.1 --port 8000"),
          ("Buka di browser", "http://127.0.0.1:8000")],
   api="Beberapa lookup butuh login Instagram sendiri; fitur AI lokal opsional.")
_r("one_liners_bb", "0xPugal/One-Liners", SUB_K, "One-Liners for Bug Bounty", "data",
   "Kumpulan perintah satu baris (subfinder, httpx, nuclei, gau, dll.) untuk alur kerja bug bounty/recon.",
   "Bacaan referensi: unduh repo lalu baca README.md di terminal; bukan tool yang dijalankan langsung.",
   **_P("0xPugal/One-Liners"))


# =====================================================================
#  LINK ENGINE  -  pratinjau tautan LANGSUNG DI TERMINAL (tanpa browser)
# =====================================================================
def num_tag(i, pad=2):
    return "%s[%s%*d%s]%s" % (W, Y, pad, i, W, R)


class _PageText(HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "template", "iframe", "canvas"}
    BREAK = {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "section", "article", "header", "footer", "table"}

    def __init__(self):
        HTMLParser.__init__(self, convert_charrefs=True)
        self.title, self.meta, self.text, self.links, self.forms = "", {}, [], 0, []
        self._skip, self._in_title, self._form = 0, False, None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "title":
            self._in_title = True
        elif tag == "meta":
            k = (a.get("name") or a.get("property") or "").lower()
            if k and a.get("content"):
                self.meta.setdefault(k, a["content"])
        elif tag == "a" and a.get("href"):
            self.links += 1
        elif tag == "form":
            self._form = {"action": a.get("action", ""), "method": (a.get("method") or "GET").upper(), "inputs": []}
            self.forms.append(self._form)
        elif tag in ("input", "select", "textarea") and self._form is not None and a.get("name"):
            self._form["inputs"].append(a["name"])
        if tag in self.SKIP:
            self._skip += 1
        if tag in self.BREAK:
            self.text.append("\n")

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self.SKIP and self._skip:
            self._skip -= 1
        if tag == "form":
            self._form = None
        if tag in self.BREAK:
            self.text.append("\n")

    def handle_data(self, d):
        if self._in_title:
            self.title += d
        elif not self._skip:
            self.text.append(d)


STRONG_BLOCK = ("you have been blocked", "sorry, you have been blocked", "attention required", "just a moment",
                "access denied", "verify you are human", "unusual traffic", "error 1020", "request blocked",
                "pardon our interruption", "are you a robot", "checking your browser", "ddos protection by")
WEAK_BLOCK = ("captcha", "enable javascript", "enable cookies", "cf-chl", "forbidden", "not authorized")
STATE_STYLE = {"ok": (G, "TERSEDIA"), "blok": (RD, "DIBLOKIR"), "limit": (Y, "DIBATASI"), "login": (Y, "BUTUH LOGIN"),
               "hilang": (RD, "TIDAK ADA"), "galat": (RD, "SERVER GALAT"), "mati": (RD, "TIDAK TERSAMBUNG")}


def classify(r, body):
    st = r.status
    low = body[:8000].lower()
    server = (r.headers.get("Server") or "").lower() if r.headers else ""
    cf = "cloudflare" in server or bool(r.headers and r.headers.get("cf-ray"))
    if st == 0:
        return "mati", "Tidak tersambung: %s" % ((r.err or "tidak diketahui")[:90])
    strong = any(s in low for s in STRONG_BLOCK)
    weak = any(s in low for s in WEAK_BLOCK) and (st != 200 or len(low) < 2500)
    if strong or (weak and st in (401, 403, 429, 503)):
        return "blok", "Halaman pemblokir / anti-bot terdeteksi%s" % (" (Cloudflare)" if cf else "")
    if st == 429:
        return "limit", "Terlalu banyak permintaan (rate limit). Tunggu beberapa menit."
    if st in (401,):
        return "login", "Layanan meminta login."
    if st == 403:
        return "blok", "Akses ditolak server (HTTP 403)%s" % (" - Cloudflare menahan permintaan" if cf else "")
    if st == 451:
        return "blok", "Diblokir karena alasan hukum/wilayah (HTTP 451)."
    if st in (404, 410):
        return "hilang", "Halaman tidak ditemukan (HTTP %d)." % st
    if st >= 500:
        return "galat", "Server bermasalah (HTTP %d)." % st
    if 200 <= st < 300:
        return "ok", "Halaman terbaca."
    return "galat", "Respons tidak lazim (HTTP %d)." % st


def decode_body(r):
    ct = (r.headers.get("Content-Type") or "") if r.headers else ""
    m = re.search(r"charset=([\w-]+)", ct, re.I)
    enc = m.group(1) if m else "utf-8"
    try:
        return r.body.decode(enc, "replace")
    except LookupError:
        return r.body.decode("utf-8", "replace")


def probe(url, timeout=15):
    """Cek satu URL. Return dict(state, reason, status, ms, title, final)."""
    r = fetch(url, timeout=timeout, limit=600000)
    body = decode_body(r)
    state, reason = classify(r, body)
    pp = _PageText()
    try:
        pp.feed(body[:400000])
    except Exception:
        pass
    return dict(state=state, reason=reason, status=r.status, ms=r.ms, final=r.url,
                title=re.sub(r"\s+", " ", pp.title).strip())


def page_lines(body, ctype, limit=16):
    """Ringkasan isi halaman sebagai baris teks polos."""
    if "json" in ctype:
        try:
            txt = json.dumps(json.loads(body), indent=2, ensure_ascii=False)
        except Exception:
            txt = body
        return txt.splitlines()[:limit], None
    pp = _PageText()
    try:
        pp.feed(body[:500000])
    except Exception:
        pass
    raw = "".join(pp.text)
    seen, lines = set(), []
    for ln in raw.splitlines():
        ln = re.sub(r"\s+", " ", ln).strip()
        if len(ln) < 4 or ln in seen:
            continue
        seen.add(ln)
        lines.append(ln)
        if len(lines) >= limit:
            break
    return lines, pp


RELATED = [
    (r"email|e-mail|mail|hunter|pwned|breach|leak|bocor", ["holehe"]),
    (r"phone|telepon|nomor|carrier|caller|truecaller|dialer", ["phoneinfoga"]),
    (r"username|user ?name|sherlock|namechk|knowem|whatsmyname|profile|people|person|orang|social network",
     ["sherlock", "maigret", "socialscan", "blackbird"]),
    (r"domain|dns|whois|subdomain|\bip\b|bgp|netcraft|securitytrails|dnsdumpster|viewdns|robtex|certificate|crt\.sh|ssl",
     ["subfinder", "dnsrecon", "harvester", "dnstwist"]),
    (r"shodan|censys|threat|reputation|abuseipdb|virustotal|device|port", ["shodan", "nmap"]),
    (r"archive|wayback|history|capture|cache|snapshot|riwayat", ["gau", "waybackurls", "mod:wayback_cdx"]),
    (r"tech|builtwith|wappalyzer|cms|stack|teknologi", ["whatweb"]),
    (r"youtube|video|tiktok|vimeo|dailymotion|reels|stream", ["ytdlp", "ffprobe"]),
    (r"exif|metadata|photo|image|gambar|foto|picture", ["exiftool"]),
    (r"audio|sound|suara|music|musik|song|lagu", ["ffprobe"]),
    (r"vuln|exploit|cve|bug ?bounty|xss|nuclei|pentest", ["nuclei", "dalfox", "wafw00f"]),
    (r"instagram", ["mod:insta_profile", "sherlock"]),
    (r"github|code|kode|repository|repo", ["mod:github_osint"]),
    (r"telegram", ["mod:telegram_channel"]),
    (r"flight|aircraft|penerbangan|pesawat|aviation|plane", ["mod:flight_track"]),
    (r"sun|solar|matahari|shadow|bayangan", ["mod:sun_calc"]),
    (r"search|cari|engine|pencari", ["mod:web_search"]),
]


def related_tools(ctx):
    c = (ctx or "").lower()
    out = []
    for pat, keys in RELATED:
        if re.search(pat, c):
            for k in keys:
                if k not in out:
                    out.append(k)
    return out[:7]


def run_related(ctx):
    keys = related_tools(ctx)
    if not keys:
        p_info("Belum ada tool GitHub / modul terminal yang terkait dengan tautan ini.")
        return
    sec("Alternatif yang berjalan di terminal (tanpa browser)")
    for i, k in enumerate(keys, 1):
        if k.startswith("mod:"):
            mk = k[4:]
            if mk not in MODULES:
                continue
            print("  %s %s%s%s  %s[modul]%s" % (num_tag(i), W, MODULES[mk][1][:70], R, G, R))
        else:
            t = TOOLS[k]
            st = (G + "terpasang" + R) if find_tool(t) else (D + "belum terpasang" + R)
            print("  %s %s%s%s  %s[repo]%s %s" % (num_tag(i), W, t["title"], R, MG, R, st))
    c = ask("Pilih nomor untuk dijalankan, 0 = batal")
    if not c or not c.isdigit() or not 1 <= int(c) <= len(keys):
        return
    k = keys[int(c) - 1]
    try:
        if k.startswith("mod:"):
            MODULES[k[4:]][0]()
        else:
            run_tool(k)
    except KeyboardInterrupt:
        p_warn("Dihentikan oleh pengguna (Ctrl+C).")


def wayback_closest(url):
    st, o = http_json("https://archive.org/wayback/available?url=" + q(url), timeout=20)
    snap = ((o or {}).get("archived_snapshots") or {}).get("closest") if isinstance(o, dict) else None
    if snap and snap.get("available"):
        return snap.get("url"), snap.get("timestamp")
    return None, None


def peek(url, label="", ctx="", archive=True):
    """Pratinjau tautan di terminal: status, deteksi blokir, ringkasan isi, aksi lanjutan."""
    url = (url or "").strip()
    if not url:
        return
    if not re.match(r"^https?://", url, re.I):
        url = "https://" + url
    host = urllib.parse.urlparse(url).netloc or url
    while True:
        with Spinner("Menghubungi %s" % host):
            r = fetch(url, timeout=18, limit=900000)
        body = decode_body(r)
        ctype = ((r.headers.get("Content-Type") or "") if r.headers else "").lower()
        state, reason = classify(r, body)
        color, word = STATE_STYLE[state]
        server = (r.headers.get("Server") or "-") if r.headers else "-"
        lines, pp = page_lines(body, ctype) if r.status and body else ([], None)
        info = ["%sURL       %s %s%s%s" % (CY, R, BL, trunc(url, content_w() - 16), R),
                "%sStatus    %s %s%s %s%s  %sHTTP %s %s %.2f dtk %s %s%s" % (
                    CY, R, color, GL["dot"], word, R, D, r.status or "-", GL["sep"], r.ms / 1000.0, GL["sep"], server[:24], R),
                "%sKeterangan%s %s%s%s" % (CY, R, W, reason, R)]
        if r.url and r.url != url:
            info.append("%sDialihkan %s %s%s%s" % (CY, R, BL, trunc(r.url, content_w() - 16), R))
        if pp is not None and pp.title.strip():
            info.append("%sJudul     %s %s%s%s" % (CY, R, W, trunc(re.sub(r"\s+", " ", pp.title).strip(), content_w() - 16), R))
        desc = (pp.meta.get("description") or pp.meta.get("og:description") or "") if pp is not None else ""
        if desc:
            info.append("%sDeskripsi %s %s%s%s" % (CY, R, D, trunc(re.sub(r"\s+", " ", desc), 220), R))
        sys.stdout.write("\n" + "\n".join(panel("PRATINJAU TERMINAL" + ((" " + GL["sep"] + " " + label[:40]) if label else ""), info)) + "\n")
        if state == "ok" and lines:
            sec("Isi halaman (ringkas)")
            for ln in lines[:14]:
                print("   %s%s%s" % (W, trunc(ln, term_w() - 6), R))
            if pp is not None and (pp.forms or pp.links):
                print("   %s%d tautan di halaman%s" % (D, pp.links, R))
                for f in pp.forms[:3]:
                    print("   %sForm %s -> %s  input: %s%s" % (D, f["method"], f["action"] or "(halaman sama)", ", ".join(f["inputs"][:6]) or "-", R))
            if len(" ".join(lines)) < 160 and "json" not in ctype:
                p_info("Isi sangat sedikit: situs ini dirender oleh JavaScript atau butuh form/captcha. Pratinjau terminal terbatas.")
        elif state in ("blok", "limit", "login", "galat", "mati", "hilang"):
            print()
            if state == "blok":
                p_warn("Situs menolak permintaan otomatis dari jaringanmu. Ini bukan galat Giga OSINT.")
            p_info("Saran: pilih [2] arsip Wayback, atau [3] tool GitHub yang bekerja tanpa situs ini.")
        acts = [("1", "Muat ulang"), ("2", "Arsip Wayback"), ("3", "Tool GitHub / modul terkait"),
                ("4", "Salin tautan"), ("5", "Buka di browser"), ("0", "Kembali")]
        print()
        for ln in hint_bar(acts):
            print(ln)
        c = ask("Pilih aksi")
        if c is None or c == "0":
            return
        if c == "1":
            continue
        if c == "2":
            if not archive:
                p_warn("Ini sudah salinan arsip.")
                continue
            with Spinner("Mencari salinan di Wayback Machine"):
                snap, ts = wayback_closest(url)
            if snap:
                p_ok("Salinan arsip ditemukan (%s)." % (ts or "-"))
                peek(snap, label="Arsip Wayback", ctx=ctx, archive=False)
            else:
                p_warn("Tidak ada salinan arsip untuk tautan ini.")
        elif c == "3":
            run_related(ctx + " " + label + " " + url)
        elif c == "4":
            if copy_text(url):
                p_ok("Tautan disalin ke clipboard.")
            else:
                p_info("Clipboard tidak tersedia. Salin manual: " + url)
        elif c == "5":
            if yes_no("Buka di browser? (bisa gagal bila situs memblokir jaringanmu)"):
                open_browser(url)
        else:
            p_warn("Pilihan tidak valid.")


def open_url(url):
    """Kompatibilitas: sekarang selalu pratinjau di terminal dulu."""
    peek(url)


def batch_status(rows):
    sec("Cek status semua tautan (paralel)")
    with Spinner("Memeriksa %d tautan" % len(rows)):
        with ThreadPoolExecutor(max_workers=6) as ex:
            res = list(ex.map(lambda r: probe(r[1], 12), rows))
    for i, ((lab, url), pr) in enumerate(zip(rows, res), 1):
        color, word = STATE_STYLE[pr["state"]]
        print("  %s %s%s %-12s%s %s%s%s  %s%s%s" % (num_tag(i), color, GL["dot"], word, R, W, trunc(lab, 34), R, D, trunc(pr["title"] or pr["reason"], max(10, term_w() - 66)), R))


def open_choices(rows, ctx=""):
    """rows = [(label, url)]. Pratinjau di terminal; browser hanya pilihan terakhir di dalam pratinjau."""
    rows = [(lab, u) for lab, u in rows if u]
    if not rows:
        return
    sec("Tautan terkait  (dibuka sebagai pratinjau di terminal)")
    for i, (lab, _) in enumerate(rows, 1):
        print("  %s %s%s%s" % (num_tag(i), W, lab, R))
    while True:
        c = ask("Nomor untuk pratinjau di terminal, a = cek status semua, 0 = selesai")
        if not c or c == "0":
            return
        if c.lower() == "a":
            batch_status(rows)
        elif c.isdigit() and 1 <= int(c) <= len(rows):
            lab, u = rows[int(c) - 1]
            peek(u, label=lab, ctx=ctx + " " + lab)
        else:
            p_warn("Pilihan tidak valid.")


# ---------- pencarian web di terminal ----------
def _strip_tags(s):
    import html as _html
    return _html.unescape(re.sub(r"<[^>]+>", "", s)).strip()


def parse_ddg(html):
    out = []
    links = re.findall(r'<a[^>]+class="[^"]*result__a[^"]*"[^>]+href="([^"]+)"[^>]*>(.*?)</a>', html, re.S)
    snips = re.findall(r'<a[^>]+class="[^"]*result__snippet[^"]*"[^>]*>(.*?)</a>', html, re.S)
    for i, (href, title) in enumerate(links):
        m = re.search(r"uddg=([^&]+)", href)
        url = urllib.parse.unquote(m.group(1)) if m else href
        if url.startswith("//"):
            url = "https:" + url
        if not url.startswith("http"):
            continue
        out.append((_strip_tags(title), url, _strip_tags(snips[i]) if i < len(snips) else ""))
    return out


def parse_bing(html):
    out = []
    for blk in re.findall(r'<li class="b_algo".*?</li>', html, re.S):
        m = re.search(r'<h2[^>]*><a[^>]+href="([^"]+)"[^>]*>(.*?)</a>', blk, re.S)
        if not m:
            continue
        url = m.group(1)
        if "bing.com/ck/a" in url:
            mm = re.search(r"[?&]u=a1([^&]+)", url)
            if mm:
                try:
                    pad = mm.group(1) + "=" * (-len(mm.group(1)) % 4)
                    url = base64.urlsafe_b64decode(pad).decode("utf-8", "ignore")
                except Exception:
                    pass
        sn = re.search(r"<p[^>]*>(.*?)</p>", blk, re.S)
        out.append((_strip_tags(m.group(2)), url, _strip_tags(sn.group(1)) if sn else ""))
    return out


def web_search(query, n=8):
    """Cari di web tanpa browser. Return (daftar_hasil, nama_mesin)."""
    r = fetch("https://html.duckduckgo.com/html/?q=" + q(query), timeout=18, headers={"Accept": "text/html"})
    res = parse_ddg(text_of(r.body)) if r.status == 200 else []
    if res:
        return res[:n], "DuckDuckGo"
    r = fetch("https://www.bing.com/search?q=" + q(query) + "&setlang=id", timeout=18, headers={"Accept": "text/html"})
    res = parse_bing(text_of(r.body)) if r.status == 200 else []
    return res[:n], "Bing"


def search_and_pick(query, ctx=""):
    with Spinner("Mencari: %s" % query[:48]):
        res, eng = web_search(query)
    if not res:
        p_warn("Mesin pencari tidak mengembalikan hasil (kemungkinan memblokir permintaan otomatis dari jaringanmu).")
        p_info("Coba lagi nanti, ganti jaringan/VPN, atau pakai tool GitHub terkait.")
        run_related(ctx + " " + query)
        return
    sec("Hasil pencarian (%s)  -  %s" % (eng, query[:50]))
    for i, (title, url, snip) in enumerate(res, 1):
        print("  %s %s%s%s" % (num_tag(i), W, trunc(title, term_w() - 12), R))
        print("       %s%s%s" % (BL, trunc(url, term_w() - 10), R))
        if snip:
            print("       %s%s%s" % (D, trunc(snip, term_w() - 10), R))
    while True:
        c = ask("Nomor untuk pratinjau, 0 = selesai")
        if not c or c == "0":
            return
        if c.isdigit() and 1 <= int(c) <= len(res):
            peek(res[int(c) - 1][1], label=res[int(c) - 1][0], ctx=ctx + " " + query)
        else:
            p_warn("Pilihan tidak valid.")


@module("web_search", "Mencari di web langsung dari terminal (DuckDuckGo/Bing) dan membuka hasilnya sebagai pratinjau teks.",
        "Input: kata kunci atau dork lengkap, contoh: site:github.com \"nama\" . Pilih nomor hasil untuk pratinjau.")
def web_search_terminal():
    t = ask("Masukkan kata kunci / dork pencarian  (0 = batal)")
    if not t or t == "0":
        return
    search_and_pick(t)


@module("peek_url", "Pratinjau dan cek status URL apa pun di terminal: judul, deteksi blokir, ringkasan isi, arsip Wayback.",
        "Input: URL lengkap (https://contoh.com). Berguna untuk memeriksa situs tanpa membuka browser.")
def peek_url():
    u = ask("Masukkan URL yang ingin dipratinjau  (0 = batal)")
    if not u or u == "0":
        return
    peek(u)


# =====================================================================
#  MODUL BARU v2 (berjalan penuh di terminal)
# =====================================================================
@module("wayback_cdx", "Riwayat arsip sebuah situs/URL dari Wayback Machine: tanggal salinan, kode status, dan tautan salinan.",
        "Input: domain atau URL, contoh example.com atau example.com/halaman. Pilih nomor salinan untuk pratinjau teks.")
def wayback_cdx():
    t = ask("Masukkan domain / URL  (0 = batal)")
    if not t or t == "0":
        return
    t = re.sub(r"^https?://", "", t.strip())
    sec("Arsip Wayback: " + t)
    with Spinner("Menghubungi Wayback Machine"):
        st, o = http_json("https://web.archive.org/cdx/search/cdx?url=%s&output=json&fl=timestamp,original,statuscode,mimetype"
                          "&limit=400&collapse=timestamp:6" % q(t), timeout=40)
    rows = (o or [])[1:] if isinstance(o, list) and len(o) > 1 else []
    if not rows:
        p_warn("Tidak ada arsip ditemukan (HTTP %s)." % st)
        return
    kv("Salinan pertama", "%s-%s-%s" % (rows[0][0][:4], rows[0][0][4:6], rows[0][0][6:8]))
    kv("Salinan terakhir", "%s-%s-%s" % (rows[-1][0][:4], rows[-1][0][4:6], rows[-1][0][6:8]))
    kv("Jumlah (per bulan)", len(rows))
    step = max(1, len(rows) // 24)
    show = rows[::step][:24]
    print()
    for i, (ts, orig, code, mime) in enumerate(show, 1):
        print("  %s %s%s-%s-%s%s  %sHTTP %s%s  %s%s%s" % (num_tag(i), W, ts[:4], ts[4:6], ts[6:8], R, D, code, R, D, mime, R))
    c = ask("Nomor salinan untuk pratinjau teks, 0 = selesai")
    if c and c.isdigit() and 1 <= int(c) <= len(show):
        ts, orig = show[int(c) - 1][0], show[int(c) - 1][1]
        peek("https://web.archive.org/web/%s/%s" % (ts, orig), label="Arsip %s" % ts[:8], archive=False)


@module("github_osint", "OSINT GitHub dari API publik: profil, organisasi, repositori teratas, bahasa, dan email yang tampak di commit publik.",
        "Input: username GitHub tanpa @. Tanpa login batas 60 permintaan/jam (set env GITHUB_TOKEN untuk batas lebih besar).")
def github_osint():
    u = ask("Masukkan username GitHub  (0 = batal)")
    if not u or u == "0":
        return
    u = u.lstrip("@").strip()
    hd = {"Accept": "application/vnd.github+json"}
    if os.environ.get("GITHUB_TOKEN"):
        hd["Authorization"] = "Bearer " + os.environ["GITHUB_TOKEN"]
    sec("GitHub: " + u)
    with Spinner("Membaca API GitHub"):
        r = fetch("https://api.github.com/users/" + q(u), headers=hd, timeout=20)
    if r.status == 404:
        p_err("Akun tidak ditemukan.")
        return
    if r.status in (403, 429):
        reset = r.headers.get("X-RateLimit-Reset") if r.headers else None
        p_warn("Batas permintaan GitHub tercapai%s." % ((" (pulih %s)" % fmt_epoch(reset)) if reset else ""))
        return
    try:
        d = json.loads(text_of(r.body))
    except Exception:
        p_warn("Respons GitHub tidak terbaca (HTTP %s)." % r.status)
        return
    for k, lab in (("name", "Nama"), ("login", "Username"), ("id", "ID akun"), ("company", "Perusahaan"), ("location", "Lokasi (isian)"),
                   ("email", "Email profil"), ("blog", "Situs"), ("twitter_username", "Twitter/X"), ("bio", "Bio"),
                   ("public_repos", "Repo publik"), ("followers", "Pengikut"), ("following", "Mengikuti"),
                   ("created_at", "Dibuat"), ("updated_at", "Diperbarui")):
        kv(lab, d.get(k))
    st2, orgs = http_json("https://api.github.com/users/%s/orgs" % q(u), headers=hd, timeout=20)
    if isinstance(orgs, list) and orgs:
        kv("Organisasi", ", ".join(o.get("login", "") for o in orgs[:10]))
    st3, repos = http_json("https://api.github.com/users/%s/repos?per_page=100&sort=pushed" % q(u), headers=hd, timeout=25)
    if isinstance(repos, list) and repos:
        sec("Repositori teratas (bintang)")
        for rp in sorted(repos, key=lambda x: x.get("stargazers_count", 0), reverse=True)[:6]:
            print("  %s%-30s%s %s* %s%s  %s%s%s" % (W, trunc(rp.get("name", ""), 30), R, Y, rp.get("stargazers_count"), R, D,
                                                   trunc(rp.get("description") or "-", max(10, term_w() - 52)), R))
        langs = {}
        for rp in repos:
            if rp.get("language"):
                langs[rp["language"]] = langs.get(rp["language"], 0) + 1
        if langs:
            kv("Bahasa dominan", ", ".join("%s (%d)" % (k, v) for k, v in sorted(langs.items(), key=lambda x: -x[1])[:5]))
    st4, ev = http_json("https://api.github.com/users/%s/events/public?per_page=100" % q(u), headers=hd, timeout=25)
    emails = {}
    if isinstance(ev, list):
        for e in ev:
            for c in ((e.get("payload") or {}).get("commits") or []):
                a = c.get("author") or {}
                em = a.get("email", "")
                if em and "noreply.github.com" not in em:
                    emails[em] = a.get("name", "")
    sec("Email yang tampak di commit publik (aktivitas terbaru)")
    if emails:
        for em, nm in list(emails.items())[:8]:
            print("  %s%s%s  %s(%s)%s" % (W, em, R, D, nm, R))
        p_info("Email commit bersifat publik di riwayat git, tetapi gunakan hanya untuk verifikasi yang sah.")
    else:
        p_info("Tidak ada email non-noreply pada 100 aktivitas terakhir.")


@module("telegram_channel", "Info channel/grup/bot Telegram publik: judul, deskripsi, jumlah pelanggan, dan pesan terbaru (preview web).",
        "Input: username channel tanpa @ atau tautan t.me. Hanya channel publik yang punya halaman preview.")
def telegram_channel():
    u = ask("Masukkan username channel/grup Telegram  (0 = batal)")
    if not u or u == "0":
        return
    u = re.sub(r"^(https?://)?(t\.me/|telegram\.me/)(s/)?", "", u.strip()).lstrip("@").split("/")[0].split("?")[0]
    sec("Telegram: @" + u)
    with Spinner("Membaca halaman publik"):
        r = fetch("https://t.me/" + q(u), timeout=20)
        r2 = fetch("https://t.me/s/" + q(u), timeout=20)
    html = text_of(r.body)
    if r.status != 200 or "tgme_page_title" not in html:
        p_warn("Halaman tidak terbaca / username tidak ditemukan (HTTP %s)." % r.status)
        return
    m = re.search(r'tgme_page_title[^>]*>(.*?)</div>', html, re.S)
    kv("Judul", _strip_tags(m.group(1)) if m else "-")
    m = re.search(r'tgme_page_extra[^>]*>(.*?)</div>', html, re.S)
    kv("Pelanggan / anggota", _strip_tags(m.group(1)) if m else "-")
    m = re.search(r'tgme_page_description[^>]*>(.*?)</div>', html, re.S)
    kv("Deskripsi", _strip_tags(re.sub(r"<br\s*/?>", " ", m.group(1)))[:300] if m else "-")
    h2 = text_of(r2.body)
    posts = re.findall(r'<time[^>]+datetime="([^"]+)"', h2)
    msgs = re.findall(r'tgme_widget_message_text[^>]*>(.*?)</div>', h2, re.S)
    if msgs:
        sec("Pesan terbaru (preview publik)")
        for i, mtxt in enumerate(msgs[-4:]):
            when = posts[-len(msgs[-4:]) + i][:16].replace("T", " ") if len(posts) >= len(msgs[-4:]) else ""
            print("  %s%s%s  %s%s%s" % (D, when, R, W, trunc(_strip_tags(re.sub(r"<br\s*/?>", " ", mtxt)), term_w() - 24), R))
    else:
        p_info("Tidak ada preview pesan (akun pribadi, grup privat, atau preview dimatikan).")


@module("insta_profile", "Profil Instagram publik lewat Instaloader (GitHub): ID akun, bio, statistik, status privat/verifikasi.",
        "Input: username Instagram tanpa @. Tanpa login, Instagram sering membatasi; bila gagal coba lagi nanti.")
def insta_profile():
    il = ensure_pip_module("instaloader", "instaloader", "membaca profil Instagram publik")
    if not il:
        return
    u = ask("Masukkan username Instagram  (0 = batal)")
    if not u or u == "0":
        return
    u = u.lstrip("@").strip()
    sec("Instagram: @" + u)
    try:
        with Spinner("Membaca profil lewat Instaloader"):
            loader = il.Instaloader(quiet=True, download_pictures=False, download_videos=False, save_metadata=False)
            p = il.Profile.from_username(loader.context, u)
    except Exception as e:
        name = e.__class__.__name__
        if "NotExists" in name:
            p_err("Akun tidak ditemukan.")
        else:
            p_warn("Instagram menolak/membatasi permintaan tanpa login (%s)." % name)
            p_info("Coba lagi beberapa menit lagi, ganti jaringan, atau pakai Sherlock/Maigret untuk memeriksa keberadaan akun.")
        return
    for lab, attr in (("Username", "username"), ("ID akun", "userid"), ("Nama", "full_name"), ("Bio", "biography"),
                      ("Pengikut", "followers"), ("Mengikuti", "followees"), ("Jumlah post", "mediacount"),
                      ("Akun privat", "is_private"), ("Terverifikasi", "is_verified"), ("Akun bisnis", "is_business_account"),
                      ("Kategori bisnis", "business_category_name"), ("Tautan di bio", "external_url")):
        kv(lab, getattr(p, attr, None))


@module("flight_track", "Pelacak penerbangan live dari OpenSky Network: cari callsign/ICAO24 atau semua pesawat di sekitar koordinat.",
        "Input: callsign (mis. GIA123) / kode ICAO24 hex, atau koordinat 'lat,lon' + radius km. Data anonim bisa dibatasi/tertunda.")
def flight_track():
    c = ask("Pilih: 1 = cari callsign / ICAO24    2 = pesawat di sekitar koordinat   (0 = batal)")
    url = "https://opensky-network.org/api/states/all"
    want = None
    if c == "1":
        want = ask("Masukkan callsign atau kode ICAO24  (0 = batal)")
        if not want or want == "0":
            return
        want = want.strip().upper()
    elif c == "2":
        raw = ask("Masukkan koordinat 'lat,lon' (contoh: -6.2,106.8)  (0 = batal)")
        if not raw or raw == "0":
            return
        m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*$", raw)
        if not m:
            p_err("Format koordinat salah. Contoh: -6.2,106.8")
            return
        lat, lon = float(m.group(1)), float(m.group(2))
        km = ask("Radius pencarian km  [Enter = 50]") or "50"
        km = float(km) if re.match(r"^\d+(\.\d+)?$", km) else 50.0
        dl = km / 111.0
        dn = km / (111.0 * max(0.2, math.cos(math.radians(lat))))
        url += "?lamin=%.4f&lomin=%.4f&lamax=%.4f&lomax=%.4f" % (lat - dl, lon - dn, lat + dl, lon + dn)
    else:
        return
    with Spinner("Menghubungi OpenSky Network"):
        st, o = http_json(url, timeout=40)
    if st == 429:
        p_warn("OpenSky membatasi permintaan anonim. Tunggu beberapa menit lalu coba lagi.")
        return
    states = (o or {}).get("states") if isinstance(o, dict) else None
    if not states:
        p_warn("Tidak ada data pesawat (HTTP %s)." % st)
        return
    if want:
        states = [s for s in states if (s[1] or "").strip().upper().startswith(want) or (s[0] or "").upper() == want]
    if not states:
        p_warn("Pesawat tidak ditemukan di data live saat ini (mungkin di darat / di luar jangkauan penerima).")
        return
    sec("%d pesawat ditemukan" % len(states))
    for s in states[:8]:
        print()
        alt = s[13] if s[13] is not None else s[7]
        kv("Callsign / ICAO24", "%s / %s" % ((s[1] or "-").strip(), s[0]))
        kv("Negara registrasi", s[2])
        kv("Posisi", "%s, %s" % (s[6], s[5]) if s[6] is not None else "tidak ada")
        kv("Ketinggian", "%.0f m (%.0f ft)" % (alt, alt * 3.28084) if alt is not None else "-")
        kv("Kecepatan", "%.0f km/jam" % (s[9] * 3.6) if s[9] is not None else "-")
        kv("Arah (derajat)", s[10])
        kv("Di darat", "ya" if s[8] else "tidak")
        kv("Squawk", s[14])
        kv("Kontak terakhir", fmt_epoch(s[4]) if s[4] else "-")
        if s[6] is not None:
            kv("Peta", "https://www.google.com/maps?q=%s,%s" % (s[6], s[5]))
    p_info("Kode squawk 7500 = pembajakan, 7600 = radio rusak, 7700 = darurat. Data adalah posisi ADS-B yang diterima relawan.")


def _sun_core(lat, lon, dt_utc):
    """Posisi matahari (NOAA / Meeus). Return (azimut, elevasi, deklinasi, eqtime_menit)."""
    y, m = dt_utc.year, dt_utc.month
    d = dt_utc.day + (dt_utc.hour + (dt_utc.minute + dt_utc.second / 60.0) / 60.0) / 24.0
    if m <= 2:
        y, m = y - 1, m + 12
    a = y // 100
    b = 2 - a + a // 4
    jd = int(365.25 * (y + 4716)) + int(30.6001 * (m + 1)) + d + b - 1524.5
    t = (jd - 2451545.0) / 36525.0
    l0 = (280.46646 + t * (36000.76983 + t * 0.0003032)) % 360
    mm = 357.52911 + t * (35999.05029 - 0.0001537 * t)
    e = 0.016708634 - t * (0.000042037 + 0.0000001267 * t)
    rm = math.radians(mm)
    c = (math.sin(rm) * (1.914602 - t * (0.004817 + 0.000014 * t)) + math.sin(2 * rm) * (0.019993 - 0.000101 * t)
         + math.sin(3 * rm) * 0.000289)
    true_long = l0 + c
    omega = 125.04 - 1934.136 * t
    lam = true_long - 0.00569 - 0.00478 * math.sin(math.radians(omega))
    eps0 = 23.0 + (26.0 + (21.448 - t * (46.815 + t * (0.00059 - t * 0.001813))) / 60.0) / 60.0
    eps = eps0 + 0.00256 * math.cos(math.radians(omega))
    decl = math.degrees(math.asin(math.sin(math.radians(eps)) * math.sin(math.radians(lam))))
    yy = math.tan(math.radians(eps) / 2.0) ** 2
    rl0 = math.radians(l0)
    eqt = 4.0 * math.degrees(yy * math.sin(2 * rl0) - 2 * e * math.sin(rm) + 4 * e * yy * math.sin(rm) * math.cos(2 * rl0)
                             - 0.5 * yy * yy * math.sin(4 * rl0) - 1.25 * e * e * math.sin(2 * rm))
    minutes = dt_utc.hour * 60 + dt_utc.minute + dt_utc.second / 60.0
    tst = (minutes + eqt + 4.0 * lon) % 1440
    ha = tst / 4.0 - 180.0
    rlat, rdec, rha = math.radians(lat), math.radians(decl), math.radians(ha)
    cosz = max(-1.0, min(1.0, math.sin(rlat) * math.sin(rdec) + math.cos(rlat) * math.cos(rdec) * math.cos(rha)))
    zen = math.degrees(math.acos(cosz))
    elev = 90.0 - zen
    denom = math.cos(rlat) * math.sin(math.radians(zen))
    if abs(denom) < 1e-9:
        az = 180.0 if lat > 0 else 0.0
    else:
        cosaz = max(-1.0, min(1.0, (math.sin(rlat) * cosz - math.sin(rdec)) / denom))
        az0 = math.degrees(math.acos(cosaz))
        az = (az0 + 180.0) % 360 if ha > 0 else (540.0 - az0) % 360
    return az, elev, decl, eqt


def sun_times(lat, lon, day, tz_hours):
    """Terbit, tengah hari, terbenam (menit sejak 00:00 waktu lokal). None bila matahari tak terbit/terbenam."""
    noon_utc = datetime.datetime(day.year, day.month, day.day, 12, 0, 0)
    _, _, decl, eqt = _sun_core(lat, lon, noon_utc)
    rlat, rdec = math.radians(lat), math.radians(decl)
    cosha = math.cos(math.radians(90.833)) / (math.cos(rlat) * math.cos(rdec)) - math.tan(rlat) * math.tan(rdec)
    noon = 720.0 - 4.0 * lon - eqt + tz_hours * 60.0
    if cosha > 1 or cosha < -1:
        return None, noon, None
    ha = math.degrees(math.acos(cosha))
    return noon - 4.0 * ha, noon, noon + 4.0 * ha


def _fmt_min(m):
    if m is None:
        return "tidak ada"
    m = m % 1440
    return "%02d:%02d" % (int(m // 60), int(m % 60))


@module("sun_calc", "Hitung posisi matahari: terbit, tengah hari, terbenam, azimut, elevasi, dan arah/panjang bayangan untuk geolokasi foto.",
        "Input: koordinat 'lat,lon', tanggal (YYYY-MM-DD), zona waktu (mis. 7 untuk WIB), dan jam foto (HH:MM) bila ingin analisis bayangan.")
def sun_calc():
    raw = ask("Masukkan koordinat 'lat,lon' (contoh: -6.2088,106.8456)  (0 = batal)")
    if not raw or raw == "0":
        return
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[,; ]\s*(-?\d+(?:\.\d+)?)\s*$", raw)
    if not m or abs(float(m.group(1))) > 90 or abs(float(m.group(2))) > 180:
        p_err("Koordinat tidak valid. Contoh: -6.2088,106.8456")
        return
    lat, lon = float(m.group(1)), float(m.group(2))
    ds = ask("Tanggal YYYY-MM-DD  [Enter = hari ini]") or ""
    try:
        day = datetime.date.fromisoformat(ds) if ds else datetime.date.today()
    except ValueError:
        p_err("Format tanggal salah. Contoh: 2025-03-21")
        return
    off = datetime.datetime.now().astimezone().utcoffset()
    default_tz = (off.total_seconds() / 3600.0) if off else 0.0
    tzs = ask("Zona waktu jam dari UTC (WIB=7, WITA=8, WIT=9)  [Enter = %g]" % default_tz) or str(default_tz)
    try:
        tz = float(tzs)
    except ValueError:
        p_err("Zona waktu harus angka, contoh 7.")
        return
    sec("Matahari di %.4f, %.4f  pada %s (UTC%+g)" % (lat, lon, day.isoformat(), tz))
    rise, noon, sset = sun_times(lat, lon, day, tz)
    kv("Terbit", _fmt_min(rise))
    kv("Tengah hari surya", _fmt_min(noon))
    kv("Terbenam", _fmt_min(sset))
    if rise is not None and sset is not None:
        kv("Lama siang", "%d jam %d menit" % (int((sset - rise) // 60), int((sset - rise) % 60)))
        for lab, mn in (("Azimut terbit", rise), ("Azimut terbenam", sset)):
            dt = datetime.datetime(day.year, day.month, day.day) + datetime.timedelta(minutes=mn - tz * 60)
            az, el, _, _ = _sun_core(lat, lon, dt)
            kv(lab, "%.1f derajat dari utara" % az)
    else:
        p_info("Pada tanggal ini matahari tidak terbit/terbenam normal (daerah kutub).")
    hm = ask("Jam foto HH:MM untuk analisis bayangan  [Enter = lewati]")
    if hm:
        mm = re.match(r"^(\d{1,2}):(\d{2})$", hm.strip())
        if not mm or int(mm.group(1)) > 23 or int(mm.group(2)) > 59:
            p_err("Format jam salah. Contoh: 14:30")
            return
        local = datetime.datetime(day.year, day.month, day.day, int(mm.group(1)), int(mm.group(2)))
        az, el, _, _ = _sun_core(lat, lon, local - datetime.timedelta(hours=tz))
        sec("Posisi matahari pukul %s" % hm)
        kv("Azimut", "%.1f derajat dari utara" % az)
        kv("Elevasi", "%.1f derajat di atas horizon" % el)
        if el > 1:
            kv("Arah bayangan", "%.1f derajat (berlawanan arah matahari)" % ((az + 180) % 360))
            kv("Panjang bayangan", "%.2f x tinggi benda" % (1.0 / math.tan(math.radians(el))))
        else:
            p_info("Matahari di bawah/dekat horizon: tidak ada bayangan tegas.")
        p_info("Cocokkan arah & panjang bayangan di foto dengan angka ini untuk menguji klaim lokasi dan waktu.")


# =====================================================================
#  MODUL: DNS / WHOIS / UMUM
# =====================================================================
RTYPES = {"A": 1, "NS": 2, "CNAME": 5, "SOA": 6, "MX": 15, "TXT": 16, "AAAA": 28, "CAA": 257}


def doh(name, rtype):
    st, obj = http_json("https://dns.google/resolve?name=%s&type=%s" % (q(name), rtype), timeout=12)
    if not obj:
        return []
    want = RTYPES.get(rtype)
    return [a.get("data", "") for a in obj.get("Answer", []) if a.get("type") == want]


def get_mx(domain):
    out = []
    for r in doh(domain, "MX"):
        parts = r.split()
        if len(parts) == 2 and parts[0].isdigit():
            out.append((int(parts[0]), parts[1].rstrip(".")))
    return [h for _, h in sorted(out)]


def is_ip(s):
    try:
        ipaddress.ip_address(s)
        return True
    except ValueError:
        return False


def extract_host(t):
    t = t.strip()
    if "://" not in t:
        t = "//" + t
    h = urllib.parse.urlparse(t).hostname or ""
    return h.lower()


def vcard_name(ent):
    try:
        for item in ent.get("vcardArray", [None, []])[1]:
            if item[0] == "fn":
                return item[3]
    except Exception:
        pass
    return ent.get("handle", "-")


def rdap_domain(domain):
    st, obj = http_json("https://rdap.org/domain/" + q(domain), timeout=20)
    if not obj or st >= 400:
        p_warn("Data RDAP/WHOIS tidak tersedia untuk %s (HTTP %s)." % (domain, st))
        return
    kv("Domain", obj.get("ldhName", "-"))
    kv("Status", ", ".join(obj.get("status", [])) or "-")
    for ev in obj.get("events", []):
        kv(ev.get("eventAction", "event"), ev.get("eventDate", "-"))
    for ent in obj.get("entities", []):
        kv(",".join(ent.get("roles", [])) or "entitas", vcard_name(ent))
    ns = [n.get("ldhName", "") for n in obj.get("nameservers", [])]
    if ns:
        kv("Nameserver", ", ".join(ns))


def dns_report(domain):
    for rt in ("A", "AAAA", "NS", "MX", "TXT", "CAA"):
        recs = doh(domain, rt)
        kv(rt, " | ".join(recs) if recs else "-")
    dm = doh("_dmarc." + domain, "TXT")
    kv("DMARC", " | ".join(dm) if dm else "tidak ada")


def ip_info(ip):
    st, o = http_json("https://ipwho.is/" + q(ip), timeout=12)
    if not o or not o.get("success", False):
        p_warn("Info IP tidak tersedia (HTTP %s)." % st)
        return
    conn = o.get("connection", {}) or {}
    tz = o.get("timezone", {}) or {}
    kv("IP", o.get("ip"))
    kv("Tipe", o.get("type"))
    kv("Benua", o.get("continent"))
    kv("Negara", "%s (%s)" % (o.get("country"), o.get("country_code")))
    kv("Wilayah / Kota", "%s / %s" % (o.get("region"), o.get("city")))
    kv("Koordinat (perkiraan)", "%s, %s" % (o.get("latitude"), o.get("longitude")))
    kv("ASN", conn.get("asn"))
    kv("Organisasi / ISP", "%s / %s" % (conn.get("org"), conn.get("isp")))
    kv("Domain ISP", conn.get("domain"))
    kv("Zona waktu", tz.get("id"))
    try:
        kv("Reverse DNS", socket.gethostbyaddr(ip)[0])
    except Exception:
        kv("Reverse DNS", "-")
    if o.get("latitude") is not None:
        kv("Peta", "https://www.google.com/maps?q=%s,%s" % (o.get("latitude"), o.get("longitude")))


def ssl_report(host):
    try:
        ctx = ssl.create_default_context()
        with socket.create_connection((host, 443), timeout=10) as s:
            with ctx.wrap_socket(s, server_hostname=host) as ss:
                c = ss.getpeercert()
                kv("Versi TLS", ss.version())
    except Exception as e:
        p_warn("Sertifikat SSL tidak bisa dibaca: %s" % e)
        return
    sub = dict(x[0] for x in c.get("subject", ()))
    iss = dict(x[0] for x in c.get("issuer", ()))
    kv("Subjek (CN)", sub.get("commonName", "-"))
    kv("Penerbit", "%s / %s" % (iss.get("organizationName", "-"), iss.get("commonName", "-")))
    kv("Berlaku dari", c.get("notBefore"))
    kv("Berlaku sampai", c.get("notAfter"))
    san = [v for k, v in c.get("subjectAltName", ()) if k == "DNS"]
    if san:
        kv("SAN (domain lain)", ", ".join(san[:15]) + (" ..." if len(san) > 15 else ""))


SEC_HEADERS = ["Strict-Transport-Security", "Content-Security-Policy", "X-Frame-Options",
               "X-Content-Type-Options", "Referrer-Policy", "Permissions-Policy"]


def headers_report(host):
    st, hd, _ = http("https://" + host, timeout=15)
    if st == 0:
        st, hd, _ = http("http://" + host, timeout=15)
    if st == 0:
        p_warn("Server tidak merespons.")
        return
    kv("HTTP status", st)
    for k in ("Server", "X-Powered-By", "Via", "Content-Type"):
        if hd.get(k):
            kv(k, hd.get(k))
    for k in SEC_HEADERS:
        kv(k, (G + "ada" + R) if hd.get(k) else (RD + "tidak ada" + R))


def crtsh_subs(domain):
    p_info("Mengambil data sertifikat dari crt.sh (bisa lambat)...")
    st, obj = http_json("https://crt.sh/?q=%25." + q(domain) + "&output=json", timeout=45)
    names = set()
    for row in (obj if isinstance(obj, list) else []):
        if not isinstance(row, dict):
            continue
        for n in str(row.get("name_value", "")).split("\n"):
            n = n.strip().lower()
            if n.startswith("*."):
                n = n[2:]
            if n:
                names.add(n)
    if not names:
        p_warn("Tidak ada subdomain ditemukan / crt.sh sedang sibuk (HTTP %s)." % st)
        return
    p_ok("%d nama unik ditemukan:" % len(names))
    for n in sorted(names)[:150]:
        print("   " + n)
    if len(names) > 150:
        p_info("... dan %d lainnya." % (len(names) - 150))


@module("dom_osint", "Analisis pasif domain/IP: DNS, WHOIS (RDAP), geolokasi IP, SSL, dan header keamanan.",
        "Input: domain (example.com), URL, atau IP. Semua data diambil dari sumber publik, tanpa memindai target.")
def dom_osint():
    t = ask("Masukkan domain / URL / alamat IP (contoh: example.com atau 8.8.8.8)  (0 = batal)")
    if not t or t == "0":
        return
    host = extract_host(t)
    if not host:
        p_err("Input tidak valid.")
        return
    if is_ip(host):
        sec("Informasi IP: " + host)
        ip_info(host)
        return
    sec("Catatan DNS: " + host)
    dns_report(host)
    sec("WHOIS (RDAP)")
    rdap_domain(host)
    a = doh(host, "A")
    if a:
        sec("Geolokasi IP utama: " + a[0])
        ip_info(a[0])
    sec("Sertifikat SSL")
    ssl_report(host)
    sec("Header HTTP & keamanan")
    headers_report(host)
    if yes_no("Cari subdomain lewat sertifikat publik (crt.sh)?"):
        sec("Subdomain (crt.sh)")
        crtsh_subs(host)


@module("ip_osint", "Mencari lokasi perkiraan, ASN, ISP, reverse DNS, dan peta untuk sebuah alamat IP.",
        "Input: alamat IP (IPv4/IPv6) atau domain; domain akan di-resolve ke IP lebih dulu.")
def ip_osint():
    t = ask("Masukkan alamat IP atau domain  (0 = batal)")
    if not t or t == "0":
        return
    host = extract_host(t)
    if not is_ip(host):
        try:
            host = socket.gethostbyname(host)
        except Exception:
            p_err("Domain tidak bisa di-resolve.")
            return
    sec("Informasi IP: " + host)
    ip_info(host)


@module("dom_subs", "Menemukan subdomain dari log sertifikat publik Certificate Transparency (crt.sh).",
        "Input: domain utama, contoh example.com. Proses pasif dan bisa memakan waktu sampai 45 detik.")
def dom_subs():
    t = ask("Masukkan domain utama (contoh: example.com)  (0 = batal)")
    if not t or t == "0":
        return
    crtsh_subs(extract_host(t))


TECH_SIGS = [
    ("WordPress", r"wp-content|wp-includes"), ("Joomla", r"/media/jui/|content=\"Joomla"),
    ("Drupal", r"drupal-settings-json|/sites/default/files"), ("Laravel", r"laravel_session"),
    ("Next.js", r"/_next/"), ("Nuxt.js", r"/_nuxt/"), ("React", r"react(\.|-dom)|data-reactroot"),
    ("Vue.js", r"vue(\.min)?\.js|data-v-"), ("Angular", r"ng-version|angular(\.min)?\.js"),
    ("jQuery", r"jquery[\.-]"), ("Bootstrap", r"bootstrap(\.min)?\.(css|js)"), ("Tailwind CSS", r"tailwind"),
    ("Google Analytics", r"google-analytics\.com|gtag/js"), ("Google Tag Manager", r"googletagmanager\.com"),
    ("Shopify", r"cdn\.shopify\.com"), ("Wix", r"wixstatic\.com"), ("Magento", r"Magento|/static/version"),
    ("Font Awesome", r"font-?awesome"),
]
COOKIE_SIGS = {"PHPSESSID": "PHP", "JSESSIONID": "Java (JSP/Servlet)", "ASP.NET_SessionId": "ASP.NET",
               "laravel_session": "Laravel", "csrftoken": "Django", "_rails": "Ruby on Rails",
               "connect.sid": "Node.js (Express)", "__cfduid": "Cloudflare", "wordpress_": "WordPress"}


def norm_url(u):
    u = u.strip()
    if not re.match(r"^https?://", u, re.I):
        u = "https://" + u
    return u


@module("web_tech", "Mendeteksi teknologi situs: server, framework, CMS, CDN, dan library dari header serta HTML.",
        "Input: URL atau domain (contoh: example.com). Deteksi berbasis tanda-tanda umum, bukan 100% akurat.")
def web_tech():
    t = ask("Masukkan URL / domain situs  (0 = batal)")
    if not t or t == "0":
        return
    url = norm_url(t)
    st, hd, body = http(url, timeout=20)
    if st == 0:
        p_err("Gagal terhubung: " + text_of(body))
        return
    html = text_of(body)
    sec("Hasil deteksi teknologi: " + url)
    kv("HTTP status", st)
    for k in ("Server", "X-Powered-By", "X-Generator", "Via", "X-Served-By"):
        if hd.get(k):
            kv(k, hd.get(k))
    found = set()
    if hd.get("CF-RAY") or "cloudflare" in (hd.get("Server") or "").lower():
        found.add("Cloudflare (CDN/WAF)")
    for name, pat in TECH_SIGS:
        if re.search(pat, html, re.I):
            found.add(name)
    gen = re.search(r'<meta[^>]+name=["\']generator["\'][^>]+content=["\']([^"\']+)', html, re.I)
    if gen:
        found.add("Generator: " + gen.group(1))
    for c in (hd.get_all("Set-Cookie") or []):
        for sig, nm in COOKIE_SIGS.items():
            if c.startswith(sig) or sig in c.split("=")[0]:
                found.add(nm + " (dari cookie)")
    kv("Teknologi terdeteksi", ", ".join(sorted(found)) if found else "tidak ada tanda yang dikenali")
    title = re.search(r"<title[^>]*>(.*?)</title>", html, re.I | re.S)
    if title:
        kv("Judul halaman", re.sub(r"\s+", " ", title.group(1)).strip()[:100])


@module("cookie_analyze", "Menganalisis cookie yang dikirim situs: atribut Secure, HttpOnly, SameSite, domain, dan masa berlaku.",
        "Input: URL atau domain. Cookie yang tidak Secure/HttpOnly akan diberi tanda peringatan.")
def cookie_analyze():
    t = ask("Masukkan URL / domain situs  (0 = batal)")
    if not t or t == "0":
        return
    url = norm_url(t)
    st, hd, _ = http(url, timeout=20)
    if st == 0:
        p_err("Gagal terhubung.")
        return
    cookies = hd.get_all("Set-Cookie") or []
    sec("Analisis cookie: " + url)
    if not cookies:
        p_info("Situs tidak mengirim cookie pada permintaan pertama.")
        return
    for c in cookies:
        parts = [x.strip() for x in c.split(";")]
        name = parts[0].split("=")[0]
        attrs = [x.lower() for x in parts[1:]]
        flags = []
        flags.append(G + "Secure" + R if "secure" in attrs else RD + "tanpa Secure" + R)
        flags.append(G + "HttpOnly" + R if "httponly" in attrs else RD + "tanpa HttpOnly" + R)
        ss = [a for a in attrs if a.startswith("samesite")]
        flags.append(G + ss[0] + R if ss else Y + "SameSite tidak diatur" + R)
        other = [x for x in parts[1:] if x.lower().split("=")[0] in ("domain", "path", "expires", "max-age")]
        print("  %s%s%s  ->  %s" % (Y, name, R, " | ".join(flags)))
        if other:
            print("      %s%s%s" % (D, "; ".join(other), R))


class _Hop(urllib.request.HTTPRedirectHandler):
    def __init__(self):
        super().__init__()
        self.hops = []

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.hops.append((code, req.full_url, newurl))
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@module("redirect_lookup", "Melacak rantai pengalihan (redirect) sebuah tautan sampai tujuan akhir; berguna untuk tautan pendek/phishing.",
        "Input: URL lengkap atau tautan pendek (bit.ly dsb). Tautan tidak dibuka di browser, hanya dilacak.")
def redirect_lookup():
    t = ask("Masukkan URL / tautan pendek  (0 = batal)")
    if not t or t == "0":
        return
    url = norm_url(t)
    h = _Hop()
    opener = urllib.request.build_opener(h)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    sec("Rantai redirect: " + url)
    final, code = url, "?"
    try:
        with opener.open(req, timeout=20) as r:
            final, code = r.geturl(), r.getcode()
    except urllib.error.HTTPError as e:
        final, code = e.url or url, e.code
    except Exception as e:
        p_warn("Pelacakan berhenti: %s" % e)
    for i, (c, src, dst) in enumerate(h.hops, 1):
        print("  %s%d.%s [%s] %s\n      %s-> %s%s" % (Y, i, R, c, src, CY, dst, R))
    if not h.hops:
        p_info("Tidak ada redirect.")
    kv("URL akhir", final)
    kv("Status akhir", code)


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links, self.scripts, self.forms, self._form = set(), set(), [], None

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "a" and a.get("href"):
            self.links.add(a["href"])
        elif tag == "script" and a.get("src"):
            self.scripts.add(a["src"])
        elif tag == "form":
            self._form = {"action": a.get("action", ""), "method": (a.get("method") or "GET").upper(), "inputs": []}
            self.forms.append(self._form)
        elif tag in ("input", "textarea", "select") and self._form is not None:
            self._form["inputs"].append(a.get("name") or a.get("id") or tag)

    def handle_endtag(self, tag):
        if tag == "form":
            self._form = None


def robots_disallow(base):
    st, _, body = http(base + "/robots.txt", timeout=10)
    out, apply = [], False
    if st != 200:
        return out
    for ln in text_of(body).splitlines():
        ln = ln.split("#")[0].strip()
        if ln.lower().startswith("user-agent:"):
            apply = ln.split(":", 1)[1].strip() == "*"
        elif apply and ln.lower().startswith("disallow:"):
            p = ln.split(":", 1)[1].strip()
            if p:
                out.append(p)
    return out


@module("crawl_site", "Crawler pasif satu domain: mengumpulkan link internal/eksternal, email, form, dan file JavaScript.",
        "Input: URL awal, jumlah halaman maks (default 30). Mematuhi robots.txt dan memberi jeda antar permintaan.")
def crawl_site():
    t = ask("Masukkan URL awal (contoh: https://example.com)  (0 = batal)")
    if not t or t == "0":
        return
    start = norm_url(t)
    mx = ask("Jumlah halaman maksimal  [Enter = 30]")
    maxp = int(mx) if mx and mx.isdigit() else 30
    maxp = max(1, min(maxp, 300))
    pu = urllib.parse.urlparse(start)
    base = "%s://%s" % (pu.scheme, pu.netloc)
    dis = robots_disallow(base)
    if dis:
        p_info("robots.txt melarang %d path; path tersebut dilewati." % len(dis))
    queue, seen = [(start, 0)], set()
    internal, external, emails, forms, scripts = set(), set(), set(), [], set()
    sec("Crawling dimulai (maks %d halaman, kedalaman 3)" % maxp)
    while queue and len(seen) < maxp:
        url, depth = queue.pop(0)
        url = url.split("#")[0]
        if url in seen:
            continue
        path = urllib.parse.urlparse(url).path or "/"
        if any(path.startswith(d) for d in dis):
            continue
        seen.add(url)
        st, hd, body = http(url, timeout=15)
        ctype = (hd.get("Content-Type") or "").lower()
        print("  %s[%s]%s %s" % (G if st == 200 else Y, st, R, url))
        if st != 200 or "html" not in ctype:
            continue
        html = text_of(body)
        emails.update(re.findall(r"[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", html))
        lp = _LinkParser()
        try:
            lp.feed(html)
        except Exception:
            pass
        for s in lp.scripts:
            scripts.add(urllib.parse.urljoin(url, s))
        for f in lp.forms:
            forms.append((url, f))
        for href in lp.links:
            full = urllib.parse.urljoin(url, href)
            pp = urllib.parse.urlparse(full)
            if pp.scheme not in ("http", "https"):
                continue
            if pp.netloc == pu.netloc:
                internal.add(full.split("#")[0])
                if depth < 3 and full.split("#")[0] not in seen:
                    queue.append((full, depth + 1))
            else:
                external.add(pp.netloc)
        time.sleep(0.3)
    sec("Ringkasan crawl")
    kv("Halaman dikunjungi", len(seen))
    kv("Link internal unik", len(internal))
    kv("Domain eksternal", len(external))
    if external:
        print("   " + ", ".join(sorted(external)[:30]))
    kv("Email ditemukan", len(emails))
    for e in sorted(emails)[:30]:
        print("   " + e)
    kv("File JavaScript", len(scripts))
    for s in sorted(scripts)[:20]:
        print("   " + s)
    kv("Form ditemukan", len(forms))
    for page, f in forms[:15]:
        print("   %s%s%s %s -> %s  input: %s" % (Y, f["method"], R, page, f["action"] or "(halaman sama)", ", ".join(f["inputs"]) or "-"))
    interesting = [u for u in internal if re.search(r"\.(sql|bak|zip|tar|gz|env|log|conf|ini|xlsx?|docx?|pdf)(\?|$)", u, re.I)]
    if interesting:
        sec("File menarik (periksa manual, hanya jika berizin)")
        for u in sorted(interesting)[:30]:
            print("   " + u)


ENGINES = {"1": ("Google", "https://www.google.com/search?q="), "2": ("Bing", "https://www.bing.com/search?q="),
           "3": ("DuckDuckGo", "https://duckduckgo.com/?q="), "4": ("Yandex", "https://yandex.com/search/?text=")}


def read_items(raw):
    if os.path.isfile(raw):
        with open(raw, "r", encoding="utf-8", errors="replace") as f:
            return [ln.strip() for ln in f if ln.strip()]
    return [x.strip() for x in raw.split(",") if x.strip()]


@module("bulk_search", "Pencarian massal: ubah banyak kata kunci jadi pencarian langsung di terminal, cek status tautan, atau simpan ke file.",
        "Input: kata kunci dipisah koma ATAU path file .txt (satu per baris), lalu pilih mesin dan aksi.")
def bulk_search():
    raw = ask("Masukkan beberapa kata kunci dipisah koma, atau path file .txt  (0 = batal)")
    if not raw or raw == "0":
        return
    items = read_items(raw)
    if not items:
        p_err("Tidak ada kata kunci yang terbaca.")
        return
    pre = ask("Awalan dork opsional, contoh: site:github.com  [Enter = kosong]") or ""
    print("  Pilih mesin untuk tautan (aksi 1 selalu memakai DuckDuckGo/Bing):")
    for k, (n, _) in ENGINES.items():
        print("   %s[%s%s%s]%s %s%s%s" % (W, Y, k, W, R, Y, n, R))
    e = ask("Nomor mesin  [Enter = 1]") or "1"
    name, base = ENGINES.get(e, ENGINES["1"])
    urls = [base + q((pre + " " + it).strip()) for it in items]
    p_ok("%d tautan pencarian %s dibuat." % (len(urls), name))
    act = ask("Aksi: 1=cari langsung di terminal (3 hasil teratas per kata kunci)  2=simpan ke file bulk_hasil.txt  "
              "3=tampilkan tautan  4=cek status tautan")
    if act == "1":
        for it in items[:12]:
            full = (pre + " " + it).strip()
            with Spinner("Mencari: " + full[:40]):
                res, eng = web_search(full, 3)
            sec("%s  (%s)" % (full[:60], eng))
            if not res:
                p_warn("Tidak ada hasil / mesin pencari memblokir permintaan.")
            for title, u, _sn in res:
                print("   %s%s%s\n      %s%s%s" % (W, trunc(title, term_w() - 8), R, BL, trunc(u, term_w() - 9), R))
            time.sleep(1.0)
    elif act == "4":
        batch_status([(it, u) for it, u in zip(items, urls)][:30])
    elif act == "2":
        with open("bulk_hasil.txt", "w", encoding="utf-8") as f:
            f.write("\n".join(urls) + "\n")
        p_ok("Tersimpan: %s" % os.path.abspath("bulk_hasil.txt"))
    else:
        for u in urls:
            print("  " + u)


# =====================================================================
#  MODUL: EMAILHUNTER
# =====================================================================
SMTP_PORT = 25
EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$")
DISPOSABLE = {"mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "temp-mail.org",
              "yopmail.com", "trashmail.com", "sharklasers.com", "getnada.com", "throwawaymail.com",
              "maildrop.cc", "dispostable.com", "fakeinbox.com", "mintemail.com", "moakt.com", "mohmal.com",
              "tempail.com", "burnermail.io", "mailnesia.com", "emailondeck.com"}
FREE_MAIL = {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com", "proton.me", "protonmail.com",
             "aol.com", "zoho.com", "gmx.com", "mail.com", "yandex.com", "live.com", "msn.com"}
ROLE_NAMES = {"admin", "info", "support", "sales", "contact", "noreply", "no-reply", "postmaster", "webmaster",
              "abuse", "hello", "office", "billing", "hr", "security", "root", "help", "marketing"}


def need_email(e=None):
    if e:
        return e
    e = ask("Masukkan email target (contoh: nama@domain.com)  (0 = batal)")
    if not e or e == "0":
        return None
    e = e.strip().lower()
    if not EMAIL_RE.match(e):
        p_err("Format email tidak valid.")
        return None
    return e


@module("email_smtp", "Mengecek apakah kotak surat ada lewat dialog SMTP (RCPT TO) tanpa mengirim email, plus deteksi catch-all.",
        "Input: email lengkap. Port 25 keluar harus terbuka (sering diblokir ISP/hosting/Termux).")
def email_smtp(e=None):
    e = need_email(e)
    if not e:
        return
    dom = e.split("@")[1]
    sec("Verifikasi SMTP: " + e)
    mx = get_mx(dom)
    if not mx:
        p_warn("Domain %s tidak memiliki MX; email kemungkinan tidak bisa menerima surat." % dom)
        return
    kv("Server MX", ", ".join(mx[:3]))
    helo = socket.getfqdn() or "localhost"
    mail_from = "giga@" + helo
    try:
        s = smtplib.SMTP(timeout=12)
        s.connect(mx[0], SMTP_PORT)
        s.ehlo_or_helo_if_needed()
        s.mail(mail_from)
        code, msg = s.rcpt(e)
        rnd = "".join(random.choice(string.ascii_lowercase) for _ in range(14)) + "@" + dom
        c2, _ = s.rcpt(rnd)
        try:
            s.quit()
        except Exception:
            pass
    except (OSError, smtplib.SMTPException) as ex:
        p_err("Koneksi SMTP gagal: %s" % ex)
        p_info("Kemungkinan port 25 diblokir oleh jaringanmu. Coba dari VPS atau jaringan lain.")
        return
    kv("Respons RCPT", "%s %s" % (code, text_of(msg)[:80]))
    if code == 250:
        verdict = G + "Alamat DITERIMA server (kemungkinan ada)" + R
    elif code in (550, 551, 553, 554):
        verdict = RD + "Alamat DITOLAK (kemungkinan tidak ada)" + R
    elif code in (450, 451, 452, 421):
        verdict = Y + "Ditunda/greylisting - hasil belum pasti" + R
    else:
        verdict = Y + "Respons tidak lazim - hasil belum pasti" + R
    kv("Kesimpulan", verdict)
    if c2 == 250:
        p_warn("Domain ini 'catch-all' (menerima alamat acak) sehingga hasil di atas TIDAK bisa dipercaya.")


@module("email_rep", "Mengecek reputasi email lewat EmailRep.io: kebocoran, aktivitas mencurigakan, profil sosial, usia domain.",
        "Input: email lengkap. API gratis dibatasi jumlah permintaan; bila muncul HTTP 429, tunggu beberapa saat.")
def email_rep(e=None):
    e = need_email(e)
    if not e:
        return
    sec("EmailRep.io: " + e)
    st, o = http_json("https://emailrep.io/" + q(e), headers={"Accept": "application/json"}, timeout=20)
    if st == 429:
        p_warn("Batas permintaan EmailRep tercapai (HTTP 429). Coba lagi nanti.")
        return
    if not o or st >= 400:
        p_warn("Tidak ada data dari EmailRep (HTTP %s)." % st)
        return
    kv("Reputasi", o.get("reputation"))
    kv("Mencurigakan", o.get("suspicious"))
    kv("Jumlah referensi", o.get("references"))
    d = o.get("details", {}) or {}
    for k in ("blacklisted", "malicious_activity", "malicious_activity_recent", "credentials_leaked",
              "credentials_leaked_recent", "data_breach", "first_seen", "last_seen", "domain_exists",
              "domain_reputation", "new_domain", "days_since_domain_creation", "suspicious_tld", "spam",
              "free_provider", "disposable", "deliverable", "accept_all", "valid_mx", "spoofable",
              "spf_strict", "dmarc_enforced"):
        if k in d:
            kv(k, d[k])
    if d.get("profiles"):
        kv("Profil terdeteksi", ", ".join(d["profiles"]))


@module("email_hudson", "Mengecek apakah email muncul pada log infostealer (malware pencuri kredensial) lewat HudsonRock Cavalier.",
        "Input: email lengkap. Data sensitif sudah disamarkan oleh HudsonRock; ini hanya indikator paparan.")
def email_hudson(e=None):
    e = need_email(e)
    if not e:
        return
    sec("HudsonRock Cavalier: " + e)
    st, o = http_json("https://cavalier.hudsonrock.com/api/json/v2/osint-tools/search-by-email?email=" + q(e), timeout=25)
    if not o:
        p_warn("Tidak ada respons dari HudsonRock (HTTP %s)." % st)
        return
    st_list = o.get("stealers", []) or []
    kv("Catatan infostealer", len(st_list))
    if o.get("message"):
        kv("Pesan", str(o.get("message"))[:120])
    for i, s in enumerate(st_list[:5], 1):
        print("  %s#%d%s" % (Y, i, R))
        for k in ("date_compromised", "stealer_family", "operating_system", "computer_name", "ip",
                  "total_corporate_services", "total_user_services"):
            if s.get(k) is not None:
                kv("  " + k, s.get(k))
        if s.get("antiviruses"):
            kv("  antivirus", ", ".join(s["antiviruses"]) if isinstance(s["antiviruses"], list) else s["antiviruses"])
    if not st_list:
        p_ok("Tidak ditemukan dalam database infostealer HudsonRock.")


def mask_pw(pw):
    if not MASK_PASSWORD or len(pw) <= 2:
        return pw if not MASK_PASSWORD else "*" * len(pw)
    return pw[:2] + "*" * (len(pw) - 2)


def hibp_check(e):
    key = os.environ.get("HIBP_API_KEY", "").strip()
    if not key:
        key = (ask("API key HaveIBeenPwned (Enter = lewati, akan pakai XposedOrNot)") or "").strip()
    if not key:
        p_info("Tanpa API key HIBP. API HIBP per-email berbayar: https://haveibeenpwned.com/API/Key")
        return False
    st, o = http_json("https://haveibeenpwned.com/api/v3/breachedaccount/%s?truncateResponse=false" % q(e),
                      headers={"hibp-api-key": key, "user-agent": "giga-osint"}, timeout=20)
    if st == 404:
        p_ok("HIBP: email tidak ditemukan pada kebocoran yang diketahui.")
    elif st == 200 and isinstance(o, list):
        p_warn("HIBP: ditemukan pada %d kebocoran:" % len(o))
        for b in o[:25]:
            print("   %s%s%s (%s) - data: %s" % (Y, b.get("Name"), R, b.get("BreachDate"), ", ".join(b.get("DataClasses", [])[:6])))
    elif st in (401, 403):
        p_err("API key HIBP ditolak.")
    else:
        p_warn("HIBP merespons HTTP %s." % st)
    return True


def xon_check(e):
    st, o = http_json("https://api.xposedornot.com/v1/check-email/" + q(e), timeout=20)
    if st == 404 or (o and o.get("Error")):
        p_ok("XposedOrNot: tidak ditemukan pada kebocoran yang diketahui.")
        return
    if not o:
        p_warn("XposedOrNot tidak merespons (HTTP %s)." % st)
        return
    br = o.get("breaches", [])
    names = []
    for item in br:
        names.extend(item if isinstance(item, list) else [item])
    p_warn("XposedOrNot: ditemukan pada %d kebocoran:" % len(names))
    print("   " + ", ".join(names[:40]))


@module("email_proxynova_hibp", "Memeriksa paparan email pada kompilasi kebocoran ProxyNova (COMB) dan Have I Been Pwned.",
        "Input: email. Password hasil kebocoran DISAMARKAN (ubah MASK_PASSWORD di kode bila perlu). HIBP butuh API key.")
def email_proxynova_hibp(e=None):
    e = need_email(e)
    if not e:
        return
    sec("ProxyNova COMB: " + e)
    st, o = http_json("https://api.proxynova.com/comb?query=%s&start=0&limit=15" % q(e), timeout=25)
    if not o:
        p_warn("ProxyNova tidak merespons (HTTP %s)." % st)
    else:
        kv("Total baris ditemukan", o.get("count", 0))
        for ln in (o.get("lines") or [])[:15]:
            user, _, pw = ln.partition(":")
            print("   %s%s%s : %s" % (Y, user, R, mask_pw(pw)))
        if not o.get("count"):
            p_ok("Tidak ada di kompilasi COMB.")
    sec("Have I Been Pwned: " + e)
    if not hibp_check(e):
        sec("XposedOrNot (alternatif gratis)")
        xon_check(e)


@module("email_xon", "Cek kebocoran data email gratis tanpa API key lewat XposedOrNot.",
        "Input: email lengkap. Menampilkan nama layanan/kebocoran tempat email pernah terekspos.")
def email_xon(e=None):
    e = need_email(e)
    if not e:
        return
    sec("XposedOrNot: " + e)
    xon_check(e)


@module("email_gravatar", "Mencari profil Gravatar dari email: foto, nama tampilan, lokasi, dan akun sosial yang terhubung.",
        "Input: email lengkap. Hanya menampilkan data yang pemiliknya buka untuk publik.")
def email_gravatar(e=None):
    e = need_email(e)
    if not e:
        return
    h = hashlib.md5(e.encode()).hexdigest()
    sec("Gravatar: " + e)
    kv("Hash MD5", h)
    st, o = http_json("https://www.gravatar.com/%s.json" % h, timeout=15)
    if st == 404 or not o:
        p_info("Tidak ada profil Gravatar publik untuk email ini.")
        return
    ent = (o.get("entry") or [{}])[0]
    kv("Username", ent.get("preferredUsername"))
    kv("Nama tampilan", ent.get("displayName"))
    kv("Lokasi", ent.get("currentLocation") or "-")
    kv("Tentang", (ent.get("aboutMe") or "-")[:140])
    kv("Foto", "https://www.gravatar.com/avatar/%s?s=400" % h)
    for a in ent.get("accounts", []) or []:
        kv("Akun " + str(a.get("shortname", "")), a.get("url"))
    for u in ent.get("urls", []) or []:
        kv("Tautan", u.get("value"))


def email_dork_list(e):
    user, dom = e.split("@")
    return [('"%s"' % e, "Email persis di seluruh web"),
            ('"%s" filetype:pdf OR filetype:doc OR filetype:xls' % e, "Dalam dokumen"),
            ('site:pastebin.com "%s"' % e, "Paste publik"),
            ('site:github.com "%s"' % e, "Repositori GitHub"),
            ('site:linkedin.com "%s"' % user, "LinkedIn dari username email"),
            ('"%s" -site:%s' % (user, dom), "Username email di tempat lain"),
            ('intext:"%s" "password" OR "kata sandi"' % e, "Dengan konteks password"),
            ('site:facebook.com OR site:instagram.com "%s"' % e, "Media sosial")]


@module("email_dork", "Membuat daftar Google Dork khusus untuk email target agar jejak digitalnya mudah ditelusuri.",
        "Input: email. Pilih nomor dork untuk membuka hasil pencarian Google di browser.")
def email_dork(e=None):
    e = need_email(e)
    if not e:
        return
    sec("Google Dork untuk " + e)
    rows = []
    for dk, desc in email_dork_list(e):
        print("  %s%s%s\n      %s%s%s" % (CY, dk, R, D, desc, R))
        rows.append((desc, "https://www.google.com/search?q=" + q(dk)))
    open_choices(rows)


@module("email_dnswhois", "DNS dan WHOIS dari domain email: MX, SPF/DMARC, nameserver, registrar, dan tanggal pendaftaran.",
        "Input: email (domainnya yang dianalisis) atau langsung nama domain.")
def email_dnswhois(e=None):
    if not e:
        e = ask("Masukkan email atau domain  (0 = batal)")
        if not e or e == "0":
            return
    dom = e.split("@")[-1].strip().lower()
    sec("DNS: " + dom)
    dns_report(dom)
    sec("WHOIS (RDAP): " + dom)
    rdap_domain(dom)


@module("email_format", "Validasi format email, deteksi domain sekali pakai/gratis, akun peran, dan keberadaan MX/SPF/DMARC.",
        "Input: email lengkap. Cepat dan tidak menghubungi server email target.")
def email_format(e=None):
    if not e:
        e = ask("Masukkan email  (0 = batal)")
        if not e or e == "0":
            return
        e = e.strip().lower()
    sec("Cek format & domain: " + e)
    ok = bool(EMAIL_RE.match(e))
    kv("Sintaks valid", (G + "ya" + R) if ok else (RD + "tidak" + R))
    if not ok:
        return
    user, dom = e.split("@")
    kv("Username / Domain", "%s / %s" % (user, dom))
    kv("Domain sekali pakai", (RD + "YA" + R) if dom in DISPOSABLE else "bukan (dari daftar bawaan)")
    kv("Penyedia gratis", "ya" if dom in FREE_MAIL else "tidak / domain sendiri")
    kv("Akun peran (role)", "ya (%s)" % user if user.split("+")[0] in ROLE_NAMES else "tidak")
    mx = get_mx(dom)
    kv("MX valid", (G + ", ".join(mx[:3]) + R) if mx else (RD + "tidak ada" + R))
    txt = doh(dom, "TXT")
    spf = [t for t in txt if "v=spf1" in t]
    kv("SPF", spf[0][:90] if spf else "tidak ada")
    dm = doh("_dmarc." + dom, "TXT")
    kv("DMARC", dm[0][:90] if dm else "tidak ada")


@module("email_permutator", "Membuat daftar kemungkinan pola alamat email perusahaan dari nama depan, nama belakang, dan domain.",
        "Input: nama depan, nama belakang, domain. Hasil bisa diuji dengan Verifikasi SMTP / pemeriksa email.")
def email_permutator():
    f = ask("Nama depan (contoh: budi)  (0 = batal)")
    if not f or f == "0":
        return
    l = ask("Nama belakang (contoh: santoso)") or ""
    d = ask("Domain (contoh: perusahaan.co.id)") or ""
    if not d:
        p_err("Domain wajib diisi.")
        return
    f, l, d = f.lower().strip(), l.lower().strip(), d.lower().strip()
    pats = ["{f}", "{l}", "{f}.{l}", "{f}{l}", "{f}_{l}", "{f}-{l}", "{l}.{f}", "{l}{f}",
            "{f[0]}{l}", "{f[0]}.{l}", "{f}{l[0]}", "{f}.{l[0]}", "{l}{f[0]}", "{l}.{f[0]}", "{f[0]}{l[0]}"]
    out = []
    for p in pats:
        try:
            if not l and "{l" in p:
                continue
            out.append(p.format(f=f, l=l) + "@" + d)
        except Exception:
            pass
    sec("%d kemungkinan alamat email" % len(out))
    for a in out:
        print("   " + a)


@module("pwd_check", "Mengecek apakah sebuah password pernah bocor (Pwned Passwords) dengan k-anonymity: password tidak dikirim utuh.",
        "Input: password (tidak tampil saat diketik). Hanya 5 karakter awal hash SHA-1 yang dikirim ke API.")
def pwd_check():
    try:
        pw = getpass.getpass("Masukkan password yang ingin dicek (tidak terlihat; kosong = batal): ")
    except (EOFError, KeyboardInterrupt):
        return
    if not pw:
        return
    h = hashlib.sha1(pw.encode()).hexdigest().upper()
    pre, suf = h[:5], h[5:]
    st, hd, body = http("https://api.pwnedpasswords.com/range/" + pre, timeout=15)
    if st != 200:
        p_err("API tidak merespons (HTTP %s)." % st)
        return
    for ln in text_of(body).splitlines():
        a, _, n = ln.partition(":")
        if a.strip() == suf:
            p_warn("Password ini PERNAH BOCOR sebanyak %s kali. Jangan dipakai lagi!" % n.strip())
            return
    p_ok("Password tidak ditemukan dalam database kebocoran (tetap gunakan password unik & panjang).")


@module("email_all", "Menjalankan serangkaian pemeriksaan sekaligus untuk satu email: format, reputasi, infostealer, kebocoran, Gravatar, DNS.",
        "Input: satu email; hasil semua modul ditampilkan berurutan. SMTP tidak ikut agar aman dari blokir port.")
def email_all():
    e = need_email()
    if not e:
        return
    email_format(e)
    email_rep(e)
    email_hudson(e)
    sec("Kebocoran data: " + e)
    xon_check(e)
    email_gravatar(e)
    email_dnswhois(e)


# =====================================================================
#  MODUL: TELEPON
# =====================================================================
ID_OPS = {}
for _p, _op, _br in [
        ("0811", "Telkomsel", "Kartu Halo"), ("0812", "Telkomsel", "simPATI"), ("0813", "Telkomsel", "simPATI"),
        ("0821", "Telkomsel", "simPATI"), ("0822", "Telkomsel", "simPATI"), ("0823", "Telkomsel", "Kartu AS"),
        ("0851", "Telkomsel", "by.U"), ("0852", "Telkomsel", "Kartu AS"), ("0853", "Telkomsel", "Kartu AS"),
        ("0814", "Indosat Ooredoo Hutchison", "Matrix / Mentari"), ("0815", "Indosat Ooredoo Hutchison", "Mentari / Matrix"),
        ("0816", "Indosat Ooredoo Hutchison", "Mentari / Matrix"), ("0855", "Indosat Ooredoo Hutchison", "IM3"),
        ("0856", "Indosat Ooredoo Hutchison", "IM3"), ("0857", "Indosat Ooredoo Hutchison", "IM3"),
        ("0858", "Indosat Ooredoo Hutchison", "IM3"), ("0817", "XL Axiata", "XL"), ("0818", "XL Axiata", "XL"),
        ("0819", "XL Axiata", "XL"), ("0859", "XL Axiata", "XL"), ("0877", "XL Axiata", "XL"),
        ("0878", "XL Axiata", "XL"), ("0831", "XL Axiata", "AXIS"), ("0832", "XL Axiata", "AXIS"),
        ("0833", "XL Axiata", "AXIS"), ("0838", "XL Axiata", "AXIS"), ("0895", "Tri (Indosat Ooredoo Hutchison)", "Tri"),
        ("0896", "Tri (Indosat Ooredoo Hutchison)", "Tri"), ("0897", "Tri (Indosat Ooredoo Hutchison)", "Tri"),
        ("0898", "Tri (Indosat Ooredoo Hutchison)", "Tri"), ("0899", "Tri (Indosat Ooredoo Hutchison)", "Tri"),
        ("0881", "Smartfren", "Smartfren"), ("0882", "Smartfren", "Smartfren"), ("0883", "Smartfren", "Smartfren"),
        ("0884", "Smartfren", "Smartfren"), ("0885", "Smartfren", "Smartfren"), ("0886", "Smartfren", "Smartfren"),
        ("0887", "Smartfren", "Smartfren"), ("0888", "Smartfren", "Smartfren"), ("0889", "Smartfren", "Smartfren")]:
    ID_OPS[_p] = (_op, _br)

ID_AREA = {"21": "DKI Jakarta", "22": "Bandung (Jawa Barat)", "24": "Semarang (Jawa Tengah)", "31": "Surabaya (Jawa Timur)",
           "251": "Bogor (Jawa Barat)", "274": "Yogyakarta (DIY)", "361": "Denpasar (Bali)", "61": "Medan (Sumatera Utara)",
           "411": "Makassar (Sulawesi Selatan)", "341": "Malang (Jawa Timur)", "271": "Surakarta/Solo (Jawa Tengah)",
           "711": "Palembang (Sumatera Selatan)", "751": "Padang (Sumatera Barat)", "541": "Samarinda (Kalimantan Timur)",
           "511": "Banjarmasin (Kalimantan Selatan)", "431": "Manado (Sulawesi Utara)", "370": "Mataram (NTB)",
           "380": "Kupang (NTT)", "911": "Ambon (Maluku)", "967": "Jayapura (Papua)", "254": "Serang (Banten)",
           "22": "Bandung (Jawa Barat)", "231": "Cirebon (Jawa Barat)", "761": "Pekanbaru (Riau)", "274": "Yogyakarta (DIY)",
           "561": "Pontianak (Kalimantan Barat)", "778": "Batam (Kepulauan Riau)", "741": "Jambi", "721": "Bandar Lampung"}
PN_TYPES = {0: "Telepon rumah/tetap (FIXED_LINE)", 1: "Seluler (MOBILE)", 2: "Tetap atau seluler (FIXED_LINE_OR_MOBILE)",
            3: "Bebas pulsa (TOLL_FREE)", 4: "Tarif premium (PREMIUM_RATE)", 5: "Biaya ditanggung bersama (SHARED_COST)",
            6: "VoIP", 7: "Nomor personal", 8: "Pager", 9: "UAN", 10: "Voicemail", 99: "Tidak diketahui"}


def id_prefix(raw_digits):
    """Normalisasi nomor Indonesia -> bentuk nasional diawali 0, atau None."""
    d = re.sub(r"\D", "", raw_digits)
    if d.startswith("62"):
        d = "0" + d[2:]
    elif d.startswith("8"):
        d = "0" + d
    return d if d.startswith("0") else None


def phone_parse():
    pn = ensure_pip_module("phonenumbers", "phonenumbers", "analisis nomor telepon")
    if not pn:
        return None, None
    raw = ask("Masukkan nomor telepon. Contoh: +6281234567890 atau 081234567890 (tanpa +, dianggap Indonesia)  (0 = batal)")
    if not raw or raw == "0":
        return None, None
    raw = re.sub(r"[\s\-().]", "", raw)
    try:
        num = pn.parse(raw, None if raw.startswith("+") else "ID")
    except Exception as ex:
        p_err("Nomor tidak bisa dibaca: %s" % ex)
        return None, None
    return pn, num


PHONE_VIEWS = {
    "semua": ("Analisis lengkap nomor telepon: validitas, lokasi, operator, tipe, zona waktu, format, dan prefix.",
              "Input: nomor dengan kode negara (+62...) atau diawali 0 untuk Indonesia."),
    "lokasi": ("Menampilkan lokasi nomor pada tingkat negara/wilayah berdasarkan data libphonenumber.",
               "Input: nomor telepon. Lokasi nomor seluler hanya tingkat negara, bukan posisi pemilik."),
    "operator": ("Mendeteksi operator/carrier nomor (Telkomsel, Indosat, XL, Tri, Smartfren, Airtel, Jio, AT&T, Vodafone, dll).",
                 "Input: nomor telepon. Hasil bisa meleset bila nomor sudah pindah operator (portabilitas)."),
    "tipe": ("Mengenali tipe nomor: Seluler, Telepon rumah (Landline), VoIP, bebas pulsa, premium, dll.",
             "Input: nomor telepon dengan atau tanpa kode negara."),
    "zona": ("Menampilkan zona waktu yang berlaku untuk nomor tersebut.",
             "Input: nomor telepon. Nomor internasional bisa memiliki beberapa zona waktu."),
    "format": ("Mengubah nomor ke format nasional, internasional, E.164, dan RFC3966.",
               "Input: nomor telepon dalam format apa pun."),
    "valid": ("Memeriksa apakah nomor valid dan mungkin (possible) menurut aturan numbering plan negara.",
              "Input: nomor telepon. Valid berarti pola benar, bukan berarti nomor aktif."),
    "prefix": ("Analisis prefix, kode negara, kode area, dan National Destination Code nomor.",
               "Input: nomor telepon. Berguna untuk mengenali wilayah/operator dari awalan nomor."),
    "kota": ("Perkiraan kota/provinsi/wilayah dari pemetaan prefix (kode area telepon rumah Indonesia dan data geokode).",
             "Input: nomor telepon. Nomor seluler tidak terikat kota; hasil hanya perkiraan."),
    "spam": ("[PLACEHOLDER] Bagian laporan spam: belum tersambung ke database; menyediakan tautan pengecekan manual.",
             "Input: nomor telepon. Buka tautan yang ditampilkan untuk melihat laporan pengguna lain."),
    "risk": ("[PLACEHOLDER] Skor risiko indikatif dari heuristik sederhana (bukan hasil layanan reputasi resmi).",
             "Input: nomor telepon. Skor 0-100; makin tinggi makin perlu diwaspadai."),
    "breach": ("[PLACEHOLDER] Bagian info kebocoran data nomor: belum ada sumber terintegrasi; menyediakan tautan manual.",
               "Input: nomor telepon. Untuk email terkait, gunakan kategori EmailHunter."),
}


def phone_osint(view="semua"):
    pn, num = phone_parse()
    if not pn:
        return
    from phonenumbers import geocoder, carrier, timezone
    fmt = pn.PhoneNumberFormat
    e164 = pn.format_number(num, fmt.E164)
    natl_digits = str(num.national_number)
    region = pn.region_code_for_number(num) or "-"
    valid, possible = pn.is_valid_number(num), pn.is_possible_number(num)
    ntype = pn.number_type(num)
    loc = (geocoder.description_for_number(num, "id") or geocoder.description_for_number(num, "en")
           or geocoder.country_name_for_number(num, "id") or "-")
    car = carrier.name_for_number(num, "en") or "-"
    tzs = ", ".join(timezone.time_zones_for_number(num)) or "-"
    opbrand = None
    if region == "ID":
        opbrand = ID_OPS.get("0" + natl_digits[:3])
    allv = view == "semua"
    sec("Hasil: " + e164)
    if allv or view == "valid":
        kv("Valid", (G + "ya" + R) if valid else (RD + "tidak" + R))
        kv("Mungkin (possible)", "ya" if possible else "tidak")
    if allv or view == "format":
        kv("Format nasional", pn.format_number(num, fmt.NATIONAL))
        kv("Format internasional", pn.format_number(num, fmt.INTERNATIONAL))
        kv("E.164", e164)
        kv("RFC3966", pn.format_number(num, fmt.RFC3966))
    if allv or view == "lokasi":
        kv("Negara / wilayah", "%s  (kode %s)" % (loc, region))
    if allv or view == "operator":
        kv("Operator (libphonenumber)", car)
        if opbrand:
            kv("Operator (prefix ID)", "%s - merek: %s" % opbrand)
    if allv or view == "tipe":
        kv("Tipe nomor", PN_TYPES.get(ntype, str(ntype)))
    if allv or view == "zona":
        kv("Zona waktu", tzs)
    if allv or view in ("prefix", "kota"):
        agl = pn.length_of_geographical_area_code(num)
        ndc = pn.length_of_national_destination_code(num)
        if view in ("prefix", "semua"):
            kv("Kode negara", "+%s" % num.country_code)
            kv("Nomor nasional", natl_digits)
            kv("Kode area geografis", natl_digits[:agl] if agl else "- (tidak ada / seluler)")
            kv("NDC (kode tujuan)", natl_digits[:ndc] if ndc else "-")
            if region == "ID":
                kv("Awalan lokal", "0" + natl_digits[:3])
        if view in ("kota", "semua"):
            area = None
            if region == "ID":
                for ln in (3, 2):
                    if natl_digits[:ln] in ID_AREA:
                        area = ID_AREA[natl_digits[:ln]]
                        break
            kv("Perkiraan kota/wilayah", area or loc)
    if view == "spam":
        sec("[PLACEHOLDER] Laporan spam")
        for n, u in [("Who Called Me", "https://whocalledme.com/"), ("Truecaller", "https://www.truecaller.com/"),
                     ("Sync.me", "https://sync.me/")]:
            kv(n, u)
    if view == "risk" or allv:
        score = 10
        if not valid:
            score += 70
        if ntype == 6:
            score += 40
        if ntype == 4:
            score += 50
        if ntype == 99:
            score += 10
        if region not in ("ID", "-"):
            score += 10
        score = min(score, 100)
        label = "rendah" if score < 30 else "sedang" if score < 60 else "tinggi"
        kv("[PLACEHOLDER] Skor risiko", "%d/100 (%s) - indikatif, bukan hasil layanan reputasi" % (score, label))
    if view == "breach":
        sec("[PLACEHOLDER] Info kebocoran data")
        p_info("Belum ada sumber kebocoran nomor yang terintegrasi. Cek manual:")
        for n, u in [("IntelX", "https://intelx.io/"), ("LeakCheck", "https://leakcheck.io/"), ("DeHashed", "https://dehashed.com/")]:
            kv(n, u)
    if allv:
        digits = e164.lstrip("+")
        kv("Cek akun WhatsApp", "https://wa.me/" + digits)
        kv("Cek akun Telegram", "https://t.me/+" + digits)
        kv("[PLACEHOLDER] Spam/Kebocoran", "gunakan menu Spam reports / Data breach info")


for _v, (_a, _h) in PHONE_VIEWS.items():
    MODULES["phone:" + _v] = ((lambda v=_v: phone_osint(v)), _a, _h)


@module("phone_card", "Cek kartu nomor Indonesia: operator, merek kartu, dan validasi panjang nomor dari awalan.",
        "Input: nomor diawali 0, 62, atau +62 (contoh 0812xxxxxxx). Tidak perlu paket tambahan.")
def phone_card():
    raw = ask("Masukkan nomor kartu (contoh: 081234567890)  (0 = batal)")
    if not raw or raw == "0":
        return
    d = id_prefix(raw)
    if not d:
        p_err("Nomor tidak dikenali sebagai nomor Indonesia (gunakan 08xx / 628xx / +628xx).")
        return
    sec("Cek kartu nomor: " + d)
    info = ID_OPS.get(d[:4])
    kv("Awalan", d[:4])
    kv("Operator", info[0] if info else "tidak dikenali dari daftar prefix")
    kv("Merek kartu", info[1] if info else "-")
    kv("Panjang nomor", "%d digit (%s)" % (len(d), "wajar" if 10 <= len(d) <= 13 else "tidak lazim, 10-13 digit"))
    kv("Format internasional", "+62" + d[1:])
    p_info("Catatan: nomor yang sudah pindah operator (MNP) bisa berbeda dari awalan aslinya.")


# =====================================================================
#  MODUL: USERNAME & MEDIA SOSIAL
# =====================================================================
# (nama, url, mode) ; mode "s" = status 200 berarti ada ; "m:teks" = 200 dan teks TIDAK ada di halaman
UCHK = [
    ("GitHub", "https://github.com/{u}", "s"), ("GitLab", "https://gitlab.com/{u}", "s"),
    ("Bitbucket", "https://bitbucket.org/{u}/", "s"), ("Reddit", "https://www.reddit.com/user/{u}/", "s"),
    ("Medium", "https://medium.com/@{u}", "s"), ("DEV.to", "https://dev.to/{u}", "s"),
    ("Keybase", "https://keybase.io/{u}", "s"), ("Pinterest", "https://www.pinterest.com/{u}/", "s"),
    ("YouTube", "https://www.youtube.com/@{u}", "s"), ("Vimeo", "https://vimeo.com/{u}", "s"),
    ("SoundCloud", "https://soundcloud.com/{u}", "s"), ("Flickr", "https://www.flickr.com/people/{u}", "s"),
    ("About.me", "https://about.me/{u}", "s"), ("Gravatar", "https://en.gravatar.com/{u}", "s"),
    ("HackerOne", "https://hackerone.com/{u}", "s"), ("Linktree", "https://linktr.ee/{u}", "s"),
    ("CodePen", "https://codepen.io/{u}", "s"), ("npm", "https://www.npmjs.com/~{u}", "s"),
    ("PyPI", "https://pypi.org/user/{u}/", "s"), ("Docker Hub", "https://hub.docker.com/u/{u}/", "s"),
    ("TryHackMe", "https://tryhackme.com/p/{u}", "s"), ("Lichess", "https://lichess.org/@/{u}", "s"),
    ("Chess.com", "https://www.chess.com/member/{u}", "s"),
    ("Steam", "https://steamcommunity.com/id/{u}", "m:The specified profile could not be found"),
]


def uchk_one(site, user):
    name, tpl, mode = site
    url = tpl.replace("{u}", q(user))
    st, _, body = http(url, timeout=12)
    if st == 0:
        return name, url, "error"
    if mode == "s":
        return name, url, "ada" if st == 200 else "tidak" if st == 404 else "?"
    marker = mode.split(":", 1)[1]
    if st == 200:
        return name, url, "tidak" if marker in text_of(body) else "ada"
    return name, url, "?"


def user_check_run(user):
    with ThreadPoolExecutor(max_workers=8) as ex:
        return list(ex.map(lambda s: uchk_one(s, user), UCHK))


@module("user_check", "Cek username di 24 situs populer secara paralel lewat kode status HTTP (mirip Sherlock versi ringan).",
        "Input: username tanpa @. Hasil bisa meleset (false positive); untuk cakupan lebih luas pakai Sherlock/WhatsMyName.")
def user_check():
    u = ask("Masukkan username (contoh: budi123)  (0 = batal)")
    if not u or u == "0":
        return
    u = u.lstrip("@").strip()
    sec("Mengecek username '%s' di %d situs..." % (u, len(UCHK)))
    res = user_check_run(u)
    found = 0
    for name, url, v in res:
        if v == "ada":
            found += 1
            print("  %s[ADA]%s    %-12s %s" % (G, R, name, url))
        elif v == "tidak":
            print("  %s[TIDAK]%s  %s" % (D, R, name))
        else:
            print("  %s[?]%s      %-12s (diblokir/tidak pasti)" % (Y, R, name))
    p_ok("%d dari %d situs kemungkinan memiliki akun tersebut." % (found, len(UCHK)))


SOC = {
    "instagram": dict(n="Instagram", url="https://www.instagram.com/{u}/", dom="instagram.com",
                      res=[("Storiesig (penampil publik)", "https://storiesig.info/"),
                           ("Imginn (penampil publik)", "https://imginn.com/{u}/")],
                      note="Instagram membatasi akses tanpa login; status 'tidak pasti' itu wajar."),
    "facebook": dict(n="Facebook", url="https://www.facebook.com/{u}", dom="facebook.com",
                     res=[("Lookup-ID (cari ID numerik)", "https://lookup-id.com/"),
                          ("Pencarian Facebook", "https://www.facebook.com/search/top?q={u}")],
                     note="Facebook membatasi data tanpa login; gunakan hanya informasi yang dibuka publik."),
    "youtube": dict(n="YouTube", url="https://www.youtube.com/@{u}", dom="youtube.com",
                    res=[("Social Blade (statistik kanal)", "https://socialblade.com/youtube/handle/{u}"),
                         ("YouTube Data Viewer (Amnesty)", "https://citizenevidence.amnestyusa.org/"),
                         ("YouTube GeoFind", "https://mattw.io/youtube-geofind/location")],
                    note="Masukkan handle kanal (tanpa @). Untuk metadata video pakai YouTube Data Viewer."),
    "pinterest": dict(n="Pinterest", url="https://www.pinterest.com/{u}/", dom="pinterest.com",
                      res=[("Pinterest Search", "https://www.pinterest.com/search/users/?q={u}")],
                      note="Profil publik Pinterest bisa dibuka tanpa login."),
    "shopee": dict(n="Shopee", url="https://shopee.co.id/{u}", dom="shopee.co.id",
                   res=[("Cari produk di Shopee", "https://shopee.co.id/search?keyword={u}")],
                   note="Masukkan username toko. Shopee memakai anti-bot, jadi data otomatis kadang diblokir."),
    "tiktok": dict(n="TikTok", url="https://www.tiktok.com/@{u}", dom="tiktok.com",
                   res=[("Social Blade TikTok", "https://socialblade.com/tiktok/user/{u}"),
                        ("Exolyt (analitik)", "https://exolyt.com/")],
                   note="Gunakan menu 'cek lokasi akun tiktok' untuk membaca region akun dari halaman publik."),
    "twitter": dict(n="Twitter (X)", url="https://x.com/{u}", dom="x.com",
                    res=[("Pencarian Lanjutan X", "https://x.com/search-advanced"),
                         ("Trends24", "https://trends24.in/")],
                    note="X membatasi tanpa login; status akun dicek lewat API FxTwitter di bawah."),
    "wechat": dict(n="WeChat", url=None, dom="weixin.qq.com", res=[("Situs resmi WeChat", "https://www.wechat.com/")],
                   note="WeChat tidak punya halaman profil web publik. ID hanya bisa dicari lewat aplikasi (Add Contacts)."),
    "snapchat": dict(n="Snapchat", url="https://www.snapchat.com/add/{u}", dom="snapchat.com",
                     res=[("Snap Map (cerita publik)", "https://map.snapchat.com/")],
                     note="Halaman /add/<username> terbuka untuk akun publik; akun privat tetap bisa menampilkan kartu."),
}

REGION_NAMES = {"ID": "Indonesia", "US": "Amerika Serikat", "MY": "Malaysia", "SG": "Singapura", "TH": "Thailand",
                "VN": "Vietnam", "PH": "Filipina", "GB": "Inggris", "JP": "Jepang", "KR": "Korea Selatan",
                "BR": "Brasil", "MX": "Meksiko", "AU": "Australia", "DE": "Jerman", "FR": "Prancis", "SA": "Arab Saudi",
                "AE": "Uni Emirat Arab", "TR": "Turki", "RU": "Rusia", "CA": "Kanada", "IT": "Italia", "ES": "Spanyol",
                "EG": "Mesir", "PK": "Pakistan", "BD": "Bangladesh", "TW": "Taiwan", "HK": "Hong Kong", "NL": "Belanda"}


def deep_find(o, key):
    if isinstance(o, dict):
        if key in o:
            return o[key]
        for v in o.values():
            r = deep_find(v, key)
            if r is not None:
                return r
    elif isinstance(o, list):
        for v in o:
            r = deep_find(v, key)
            if r is not None:
                return r
    return None


def fmt_epoch(v):
    try:
        v = float(v)
        if v > 1e11:
            v /= 1000.0
        return datetime.datetime.fromtimestamp(v).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return str(v)


def twitter_status(u=None):
    if not u:
        u = ask("Masukkan username X/Twitter (tanpa @)  (0 = batal)")
        if not u or u == "0":
            return
        u = u.lstrip("@").strip()
    sec("Status akun X/Twitter: @" + u)
    st, o = http_json("https://api.fxtwitter.com/" + q(u), timeout=20)
    usr = (o or {}).get("user") if isinstance(o, dict) else None
    if st == 200 and usr:
        kv("Status", G + "AKTIF / ditemukan" + R)
        kv("Nama", usr.get("name"))
        kv("ID akun", usr.get("id"))
        kv("Bio", (usr.get("description") or "-")[:160])
        kv("Lokasi (isian profil)", usr.get("location") or "-")
        kv("Bergabung", usr.get("joined") or "-")
        kv("Pengikut / Mengikuti", "%s / %s" % (usr.get("followers"), usr.get("following")))
        kv("Jumlah tweet", usr.get("tweets", usr.get("statuses", "-")))
        kv("Terkunci (protected)", usr.get("protected"))
        if usr.get("website") or usr.get("url"):
            kv("Situs", usr.get("website") or usr.get("url"))
    elif st == 404:
        kv("Status", RD + "TIDAK DITEMUKAN" + R)
        p_info("Artinya: username tidak ada, sudah diganti, dihapus, atau akun ditangguhkan (suspended).")
    else:
        kv("Status", Y + "tidak pasti (HTTP %s)" % st + R)
        p_info("API pihak ketiga sedang bermasalah atau membatasi permintaan. Coba lagi nanti.")


def tiktok_loc(u=None):
    if not u:
        u = ask("Masukkan username TikTok (tanpa @)  (0 = batal)")
        if not u or u == "0":
            return
        u = u.lstrip("@").strip()
    sec("Region akun TikTok: @" + u)
    st, hd, body = http("https://www.tiktok.com/@" + q(u), headers={"Accept-Language": "en-US,en;q=0.9"}, timeout=25)
    html = text_of(body)
    if st == 404 or "Couldn't find this account" in html:
        p_err("Akun tidak ditemukan.")
        return
    if st != 200:
        p_warn("TikTok merespons HTTP %s (kemungkinan anti-bot). Coba lagi atau buka manual." % st)
        return
    data = None
    m = re.search(r'<script id="__UNIVERSAL_DATA_FOR_REHYDRATION__"[^>]*>(.*?)</script>', html, re.S)
    if m:
        try:
            data = json.loads(m.group(1))
        except Exception:
            data = None
    ui = deep_find(data, "userInfo") if data else None
    if ui and isinstance(ui, dict) and ui.get("user"):
        us, stt = ui.get("user", {}), ui.get("stats", {}) or {}
        reg = us.get("region")
        kv("Username", us.get("uniqueId"))
        kv("Nama", us.get("nickname"))
        kv("Bio", (us.get("signature") or "-")[:160])
        kv("Terverifikasi", us.get("verified"))
        kv("Region akun", "%s (%s)" % (REGION_NAMES.get(reg, reg or "-"), reg or "-"))
        kv("Bahasa", us.get("language") or "-")
        kv("Akun privat", us.get("privateAccount"))
        if us.get("createTime"):
            kv("Dibuat", fmt_epoch(us["createTime"]))
        kv("Pengikut / Mengikuti", "%s / %s" % (stt.get("followerCount"), stt.get("followingCount")))
        kv("Suka / Video", "%s / %s" % (stt.get("heartCount", stt.get("heart")), stt.get("videoCount")))
    else:
        rg = re.search(r'"region":"([A-Za-z]{2})"', html)
        if rg:
            kv("Region akun (hasil regex)", "%s (%s)" % (REGION_NAMES.get(rg.group(1).upper(), "-"), rg.group(1)))
        else:
            p_warn("Struktur halaman TikTok tidak terbaca (berubah/anti-bot).")
            return
    p_info("Catatan: region = negara tempat akun terdaftar/diatur, BUKAN lokasi GPS pemilik.")


def shopee_api(u):
    sec("Data toko Shopee: " + u)
    st, o = http_json("https://shopee.co.id/api/v4/shop/get_shop_detail?username=" + q(u),
                      headers={"Referer": "https://shopee.co.id/" + u, "X-Requested-With": "XMLHttpRequest",
                               "X-API-SOURCE": "pc"}, timeout=20)
    d = (o or {}).get("data") if isinstance(o, dict) else None
    d = d if isinstance(d, dict) else None
    if not d:
        p_warn("Data otomatis diblokir anti-bot Shopee (HTTP %s). Buka tautan toko secara manual." % st)
        return
    kv("Nama toko", d.get("name"))
    kv("Lokasi toko", d.get("shop_location") or "-")
    kv("Jumlah produk", d.get("item_count"))
    kv("Rating", d.get("rating_star"))
    kv("Pengikut", d.get("follower_count"))
    kv("Tingkat respons", d.get("response_rate"))
    if d.get("ctime"):
        kv("Toko dibuat", fmt_epoch(d["ctime"]))
    kv("Deskripsi", (d.get("description") or "-")[:160])


def soc_profile(key):
    c = SOC[key]
    u = ask("Masukkan username %s (tanpa @)  (0 = batal)" % c["n"])
    if not u or u == "0":
        return
    u = u.lstrip("@").strip()
    sec("%s OSINT: %s" % (c["n"], u))
    rows = []
    if c["url"]:
        url = c["url"].replace("{u}", q(u))
        st, _, _ = http(url, timeout=15)
        verdict = (G + "kemungkinan ada" + R) if st == 200 else (RD + "tidak ditemukan" + R) if st == 404 else \
                  (Y + "tidak pasti (HTTP %s, perlu login/anti-bot)" % st + R)
        kv("Profil", url)
        kv("Status halaman", verdict)
        rows.append(("Buka profil " + c["n"], url))
    p_info(c["note"])
    if key == "twitter":
        twitter_status(u)
    elif key == "tiktok":
        tiktok_loc(u)
    elif key == "shopee":
        shopee_api(u)
    dom = c["dom"]
    sec("Dork pencarian jejak username")
    dorks = ['site:%s "%s"' % (dom, u), '"%s" %s' % (u, c["n"]), 'inurl:%s site:%s' % (u, dom), '"%s" -site:%s' % (u, dom)]
    for dk in dorks:
        print("  " + CY + dk + R)
        rows.append(("Dork: " + dk, "https://www.google.com/search?q=" + q(dk)))
    for n, tpl in c["res"]:
        rows.append((n, tpl.replace("{u}", q(u))))
    sec("Buka di browser")
    open_choices(rows)


for _k in SOC:
    MODULES["soc:" + _k] = ((lambda k=_k: soc_profile(k)),
                            "Analisis profil %s: tautan profil, status halaman, dork username, dan alat bantu publik." % SOC[_k]["n"],
                            "Input: username %s tanpa @. Hanya data yang dibuka publik yang diperiksa." % SOC[_k]["n"])
MODULES["twitter_status"] = (twitter_status, "Mengecek status akun X/Twitter (aktif, tidak ditemukan/suspend) beserta statistik publik.",
                             "Input: username tanpa @. Memakai API publik FxTwitter, bukan login.")
MODULES["tiktok_loc"] = (tiktok_loc, "Membaca region (negara terdaftar) akun TikTok dari halaman profil publik dan statistiknya.",
                         "Input: username TikTok tanpa @. Region bukan posisi GPS; hasil bisa gagal bila TikTok memblokir.")


# =====================================================================
#  MODUL: PAKET, PLAT, SEKOLAH, DOKUMEN
# =====================================================================
COURIERS = [("Shopee Express (SPX)", "https://spx.co.id/track"), ("JNE", "https://www.jne.co.id/tracking-package"),
            ("J&T Express", "https://jet.co.id/track"), ("SiCepat", "https://www.sicepat.com/checkAwb"),
            ("Ninja Xpress", "https://www.ninjaxpress.co/id-id/tracking"), ("AnterAja", "https://anteraja.id/tracking"),
            ("Lazada / LEX", "https://www.lazada.co.id/"), ("TikTok Shop / Tokopedia", "https://www.tokopedia.com/order-list"),
            ("POS Indonesia", "https://www.posindonesia.co.id/id/tracking"), ("TIKI", "https://tiki.id/id/tracking"),
            ("Amazon", "https://www.amazon.com/progress-tracker/package"),
            ("DHL", "https://www.dhl.com/id-en/home/tracking.html?tracking-id={r}"),
            ("FedEx", "https://www.fedex.com/fedextrack/?trknbr={r}"), ("UPS", "https://www.ups.com/track?tracknum={r}")]


def guess_courier(r):
    u = r.upper()
    if u.startswith("SPX"):
        return "Shopee Express (SPX)"
    if u.startswith(("JP", "JD", "JX", "JO")):
        return "J&T Express"
    if u.startswith("NLID"):
        return "Ninja Xpress"
    if u.startswith("1Z"):
        return "UPS"
    if u.isdigit() and len(u) == 12:
        return "SiCepat (atau FedEx)"
    if u.isdigit() and len(u) == 16:
        return "JNE"
    return None


@module("pkg_track", "Melacak paket (Shopee, Lazada/TikTok, JNE, SiCepat, Ninja, Amazon, dll) lewat agregator dan situs kurir resmi.",
        "Input: nomor resi. Nomor otomatis ditebak kurirnya; pilih agregator atau kurir lalu tempel resi bila diminta.")
def pkg_track():
    r = ask("Masukkan nomor resi (contoh: SPXID012345678901)  (0 = batal)")
    if not r or r == "0":
        return
    r = r.strip().replace(" ", "")
    sec("Resi: " + r)
    g = guess_courier(r)
    kv("Tebakan kurir", g or "tidak dikenali dari pola")
    p_info("Salin resi ini bila halaman kurir meminta: " + r)
    rows = [("17TRACK (agregator, otomatis)", "https://t.17track.net/en#nums=" + q(r)),
            ("Parcels (agregator, otomatis)", "https://parcelsapp.com/en/tracking/" + q(r))]
    for n, u in COURIERS:
        rows.append((n + " (situs resmi)", u.replace("{r}", q(r))))
    open_choices(rows)


PLAT = {"A": "Banten (Serang, Cilegon, Pandeglang, Lebak)", "B": "DKI Jakarta, Depok, Tangerang, Bekasi",
        "D": "Bandung, Cimahi, Bandung Barat", "E": "Cirebon, Indramayu, Majalengka, Kuningan",
        "F": "Bogor, Sukabumi, Cianjur", "T": "Purwakarta, Karawang, Subang",
        "Z": "Garut, Tasikmalaya, Sumedang, Ciamis, Banjar", "G": "Pekalongan, Tegal, Brebes, Batang, Pemalang",
        "H": "Semarang, Kendal, Salatiga, Demak", "K": "Pati, Kudus, Jepara, Rembang, Blora",
        "R": "Banyumas, Cilacap, Purbalingga, Banjarnegara", "AA": "Kedu (Magelang, Purworejo, Temanggung, Kebumen)",
        "AB": "DI Yogyakarta", "AD": "Surakarta/Solo, Sukoharjo, Klaten, Boyolali, Karanganyar",
        "AE": "Madiun, Ngawi, Magetan, Ponorogo, Pacitan", "AG": "Kediri, Blitar, Tulungagung, Nganjuk",
        "L": "Surabaya", "M": "Madura (Bangkalan, Sampang, Pamekasan, Sumenep)",
        "N": "Malang, Pasuruan, Probolinggo, Lumajang, Batu", "P": "Besuki (Jember, Banyuwangi, Bondowoso, Situbondo)",
        "S": "Bojonegoro, Lamongan, Tuban, Mojokerto, Jombang", "W": "Sidoarjo, Gresik",
        "DK": "Bali", "DR": "Lombok (NTB)", "EA": "Sumbawa (NTB)", "DH": "Timor / Kupang (NTT)", "EB": "Flores (NTT)",
        "ED": "Sumba (NTT)", "KB": "Kalimantan Barat", "DA": "Kalimantan Selatan", "KH": "Kalimantan Tengah",
        "KT": "Kalimantan Timur & Utara", "DB": "Sulawesi Utara (Manado)", "DL": "Kep. Sangihe/Talaud (Sulut)",
        "DM": "Gorontalo", "DN": "Sulawesi Tengah", "DT": "Sulawesi Tenggara", "DD": "Sulawesi Selatan",
        "DC": "Sulawesi Barat", "BL": "Aceh", "BB": "Sumatera Utara bagian barat (Tapanuli, Sibolga)",
        "BK": "Sumatera Utara (Medan)", "BA": "Sumatera Barat", "BM": "Riau", "BP": "Kepulauan Riau",
        "BG": "Sumatera Selatan", "BN": "Kep. Bangka Belitung", "BE": "Lampung", "BD": "Bengkulu", "BH": "Jambi",
        "DE": "Maluku", "DG": "Maluku Utara", "PA": "Papua", "PB": "Papua Barat",
        "CD": "Korps Diplomatik", "CC": "Korps Konsuler", "RI": "Kendaraan dinas pejabat negara"}


@module("plat_cek", "Mengenali wilayah asal plat nomor Indonesia dari kode huruf depan, serta tautan cek pajak kendaraan resmi.",
        "Input: plat, contoh B 1234 ABC atau AB1234CD. Pajak/identitas pemilik tidak dibuka; gunakan e-Samsat provinsi.")
def plat_cek():
    raw = ask("Masukkan plat nomor (contoh: B 1234 ABC)  (0 = batal)")
    if not raw or raw == "0":
        return
    m = re.match(r"^([A-Za-z]{1,2})\s*(\d{1,4})\s*([A-Za-z]{0,3})$", raw.strip())
    if not m:
        p_err("Format plat tidak dikenali. Contoh yang benar: B 1234 ABC")
        return
    code, num, suf = m.group(1).upper(), m.group(2), m.group(3).upper()
    sec("Plat: %s %s %s" % (code, num, suf))
    kv("Kode wilayah", code)
    kv("Wilayah asal", PLAT.get(code, "tidak ada di daftar bawaan"))
    kv("Nomor urut", num)
    kv("Huruf seri", suf or "-")
    p_info("Warna dasar plat: hitam = pribadi, kuning = angkutan umum, merah = pemerintah.")
    p_info("Huruf seri belakang menandai kewilayahan Samsat di dalam kode wilayah; detailnya berbeda tiap provinsi.")
    rows = [("Cari e-Samsat / cek pajak (Google)", "https://www.google.com/search?q=" + q("cek pajak kendaraan online e-samsat %s %s %s" % (code, num, suf))),
            ("Informasi kode wilayah plat (Google)", "https://www.google.com/search?q=" + q("kode plat nomor " + code + " wilayah"))]
    open_choices(rows)


def stars(v):
    try:
        n = int(round(float(v)))
    except Exception:
        return "-"
    return "*" * n + "." * (5 - n) + " (%s)" % v


@module("school_search", "Mencari sekolah: alamat, koordinat, link Google Maps, serta bintang & ulasan Google (butuh API key opsional).",
        "Input: nama sekolah + kota. Untuk bintang/ulasan, set env GOOGLE_MAPS_API_KEY atau masukkan key saat diminta.")
def school_search():
    n = ask("Masukkan nama sekolah (contoh: SMAN 1 Bogor)  (0 = batal)")
    if not n or n == "0":
        return
    sec("Pencarian sekolah: " + n)
    maps_name = "https://www.google.com/maps/search/?api=1&query=" + q(n)
    kv("Link Google Maps", maps_name)
    key = os.environ.get("GOOGLE_MAPS_API_KEY", "").strip()
    if not key:
        key = (ask("API key Google Maps/Places (Enter = lewati; tanpa key bintang & ulasan tidak tampil)") or "").strip()
    if key:
        st, o = http_json("https://maps.googleapis.com/maps/api/place/textsearch/json?query=%s&language=id&key=%s" % (q(n), q(key)), timeout=20)
        res = (o or {}).get("results") or []
        if not res:
            p_warn("Google Places: tidak ada hasil / key ditolak (%s)." % ((o or {}).get("status") or st))
        for r in res[:3]:
            print()
            kv("Nama", r.get("name"))
            kv("Alamat", r.get("formatted_address"))
            kv("Bintang Google", stars(r.get("rating")))
            kv("Jumlah ulasan", r.get("user_ratings_total"))
            kv("Link peta", "https://www.google.com/maps/place/?q=place_id:" + str(r.get("place_id")))
            st2, d = http_json("https://maps.googleapis.com/maps/api/place/details/json?place_id=%s&fields=reviews,formatted_phone_number,website&language=id&key=%s" % (q(r.get("place_id", "")), q(key)), timeout=20)
            det = (d or {}).get("result") or {}
            if det.get("formatted_phone_number"):
                kv("Telepon", det["formatted_phone_number"])
            if det.get("website"):
                kv("Situs", det["website"])
            for rv in (det.get("reviews") or [])[:3]:
                print("   %s%s%s %s - %s" % (Y, stars(rv.get("rating")), R, rv.get("author_name"), (rv.get("text") or "").replace("\n", " ")[:150]))
    else:
        p_info("Memakai OpenStreetMap (tanpa bintang/ulasan).")
        st, o = http_json("https://nominatim.openstreetmap.org/search?q=%s&format=jsonv2&limit=5&addressdetails=1&countrycodes=id" % q(n),
                          headers={"User-Agent": "GigaOSINT/1.0 (terminal tool)"}, timeout=20)
        if not o:
            p_warn("OpenStreetMap tidak menemukan hasil (HTTP %s)." % st)
        for r in (o or [])[:5]:
            print()
            kv("Nama", (r.get("display_name") or "")[:110])
            kv("Jenis", r.get("type"))
            kv("Koordinat", "%s, %s" % (r.get("lat"), r.get("lon")))
            kv("Link Google Maps", "https://www.google.com/maps?q=%s,%s" % (r.get("lat"), r.get("lon")))
    open_choices([("Buka Google Maps (lihat bintang & ulasan)", maps_name),
                  ("Data Pokok Pendidikan (Kemendikdasmen)", "https://dapo.kemendikdasmen.go.id/"),
                  ("Referensi sekolah (Kemendikdasmen)", "https://referensi.data.kemendikdasmen.go.id/")])


@module("nisn_cek", "Pratinjau status layanan resmi cek NISN (Kemendikdasmen) di terminal; pencarian data siswa butuh captcha di situsnya.",
        "Input di situs: cari berdasarkan nama/tanggal lahir/sekolah lalu isi captcha. Data siswa dikelola pemerintah.")
def nisn_cek():
    sec("Cek NISN")
    p_info("Layanan resmi memakai captcha, sehingga pencarian tidak bisa diotomatisasi dari terminal.")
    p_info("Siapkan: nama lengkap siswa + tanggal lahir atau nama sekolah.")
    open_url("https://nisn.data.kemdikbud.go.id/")


@module("skck_cek", "Pratinjau status portal resmi SKCK Polri di terminal; pengecekan status hanya untuk pemohon yang login.",
        "Input di situs: akun SKCK online milikmu. Tidak ada layanan publik untuk mengecek SKCK orang lain.")
def skck_cek():
    sec("Cek SKCK")
    p_info("Pengecekan status hanya untuk pemohon yang login. Keaslian dokumen diverifikasi lewat QR/Polres penerbit.")
    open_url("https://skck.polri.go.id/")


# =====================================================================
#  MODUL: SAHAM, BERITA, BENCANA
# =====================================================================
TICKERS = {"BBCA": "Bank Central Asia", "BBRI": "Bank Rakyat Indonesia", "BMRI": "Bank Mandiri", "BBNI": "Bank Negara Indonesia",
           "TLKM": "Telkom Indonesia", "ASII": "Astra International", "UNVR": "Unilever Indonesia", "ICBP": "Indofood CBP",
           "INDF": "Indofood Sukses Makmur", "GOTO": "GoTo Gojek Tokopedia", "BUKA": "Bukalapak", "ANTM": "Aneka Tambang",
           "ADRO": "Adaro Energy Indonesia", "PTBA": "Bukit Asam", "BREN": "Barito Renewables Energy",
           "AMMN": "Amman Mineral Internasional", "TMPO": "Tempo Inti Media", "EMTK": "Elang Mahkota Teknologi",
           "MDKA": "Merdeka Copper Gold", "KLBF": "Kalbe Farma", "HMSP": "HM Sampoerna", "GGRM": "Gudang Garam",
           "CPIN": "Charoen Pokphand Indonesia", "SMGR": "Semen Indonesia", "PGAS": "Perusahaan Gas Negara",
           "INCO": "Vale Indonesia", "ITMG": "Indo Tambangraya Megah", "UNTR": "United Tractors", "BRIS": "Bank Syariah Indonesia",
           "ARTO": "Bank Jago", "MAPI": "Mitra Adiperkasa", "BSDE": "Bumi Serpong Damai", "CTRA": "Ciputra Development",
           "SCMA": "Surya Citra Media", "MNCN": "Media Nusantara Citra", "ACES": "Aspirasi Hidup Indonesia",
           "TPIA": "Chandra Asri Pacific", "ESSA": "ESSA Industries Indonesia", "MEDC": "Medco Energi Internasional",
           "EXCL": "XL Axiata", "ISAT": "Indosat Ooredoo Hutchison", "JSMR": "Jasa Marga", "BBTN": "Bank Tabungan Negara"}
TRUSTED = ("kontan", "bisnis", "cnbc", "kompas", "detik", "tempo", "antara", "idx", "bloomberg", "investor",
           "katadata", "emitennews", "liputan6", "cnn", "reuters", "republika", "bbc", "media indonesia")


def parse_feed(body):
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        return []
    items = []
    for el in root.iter():
        if el.tag.split("}")[-1] not in ("item", "entry"):
            continue
        d = {}
        for ch in el:
            t = ch.tag.split("}")[-1]
            if t == "link":
                d.setdefault("link", ch.get("href") or (ch.text or "").strip())
            elif t in ("title", "pubDate", "date", "published", "updated", "source", "description"):
                d.setdefault(t, (ch.text or "").strip())
        items.append(d)
    return items


def parse_date(s):
    if not s:
        return None
    try:
        dt = email.utils.parsedate_to_datetime(s)
    except Exception:
        try:
            dt = datetime.datetime.fromisoformat(s.replace("Z", "+00:00"))
        except Exception:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt


def item_when(it):
    return parse_date(it.get("pubDate") or it.get("published") or it.get("updated") or it.get("date"))


def fresh(dt, hours=24):
    if not dt:
        return False
    age = datetime.datetime.now(datetime.timezone.utc) - dt
    return datetime.timedelta(hours=-1) <= age <= datetime.timedelta(hours=hours)


def gnews(query, when="1d"):
    url = "https://news.google.com/rss/search?q=%s&hl=id&gl=ID&ceid=ID:id" % q(query + " when:" + when)
    st, _, body = http(url, timeout=20)
    return parse_feed(body) if st == 200 else []


def show_items(items, limit=8, mark_trusted=False):
    shown = 0
    for it in items:
        if shown >= limit:
            break
        dt = item_when(it)
        ts = dt.astimezone().strftime("%d/%m %H:%M") if dt else "--/-- --:--"
        src = it.get("source", "")
        tag = ""
        if mark_trusted and any(t in src.lower() for t in TRUSTED):
            tag = G + "  " + GL["dot"] + " sumber tepercaya" + R
        title = re.sub(r"\s+", " ", it.get("title", "")).strip()
        print("  %s%s%s %s%s%s%s" % (D, ts, R, W, title[:120], R, (" [" + src + "]") if src else ""))
        print("      %s%s%s%s" % (BL, it.get("link", ""), R, tag))
        shown += 1
    return shown


NEWS_NAS = [("Antara", "https://www.antaranews.com/rss/terkini.xml"), ("CNN Indonesia", "https://www.cnnindonesia.com/nasional/rss"),
            ("Detik", "https://rss.detik.com/index.php/detikcom"), ("Tempo", "https://rss.tempo.co/nasional")]
NEWS_INT = [("BBC Dunia", "http://feeds.bbci.co.uk/news/world/rss.xml"), ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
            ("DW", "https://rss.dw.com/rdf/rss-en-world"), ("NYT Dunia", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
            ("Google News Dunia", "https://news.google.com/rss/headlines/section/topic/WORLD?hl=id&gl=ID&ceid=ID:id")]


@module("news_today", "Menampilkan berita nasional atau internasional 24 jam terakhir dari kantor berita & media arus utama tepercaya (A1).",
        "Input: pilih 1 (nasional) / 2 (internasional), lalu kata kunci opsional. Memakai RSS resmi media, bukan scraping.")
def news_today():
    c = ask("Pilih berita: 1 = Nasional (Indonesia)   2 = Internasional   (0 = batal)")
    if c not in ("1", "2"):
        return
    kw = ask("Kata kunci opsional (Enter = berita utama hari ini)") or ""
    if kw:
        sec("Berita terbaru tentang '%s' (24 jam terakhir)" % kw)
        items = gnews(kw, "1d")
        items.sort(key=lambda x: (not any(t in x.get("source", "").lower() for t in TRUSTED)))
        if not show_items(items, 12, True):
            p_warn("Tidak ada berita 24 jam terakhir untuk kata kunci itu.")
        return
    feeds = NEWS_NAS if c == "1" else NEWS_INT
    sec("Berita %s hari ini" % ("NASIONAL" if c == "1" else "INTERNASIONAL"))
    total = 0
    for name, url in feeds:
        st, _, body = http(url, timeout=20)
        items = [i for i in parse_feed(body) if fresh(item_when(i))] if st == 200 else []
        items.sort(key=lambda i: item_when(i), reverse=True)
        print("\n  %s%s %s%s%s" % (MG, GL["bullet"], W, name, R))
        n = show_items(items, 5)
        total += n
        if not n:
            p_info("Tidak ada item 24 jam terakhir / feed tidak merespons (HTTP %s)." % st)
    if not total:
        p_warn("Semua feed kosong. Periksa koneksi internet atau coba kata kunci.")


@module("disaster_today", "Peristiwa bencana alam terkini: gempa BMKG, gempa dunia USGS, peringatan GDACS, dan berita bencana tepercaya.",
        "Input: pilih 1 (nasional) / 2 (internasional). Data dari BMKG, USGS, GDACS, dan RSS berita; tanpa API key.")
def disaster_today():
    c = ask("Pilih cakupan: 1 = Nasional (Indonesia)   2 = Internasional   (0 = batal)")
    if c not in ("1", "2"):
        return
    if c == "1":
        sec("Gempa terkini BMKG")
        st, o = http_json("https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json", timeout=20)
        g = ((o or {}).get("Infogempa") or {}).get("gempa")
        if g:
            for k in ("Tanggal", "Jam", "Magnitude", "Kedalaman", "Wilayah", "Coordinates", "Potensi", "Dirasakan"):
                kv(k, g.get(k, "-"))
        else:
            p_warn("Data autogempa BMKG tidak tersedia (HTTP %s)." % st)
        sec("Daftar gempa M5.0+ terbaru (BMKG)")
        st, o = http_json("https://data.bmkg.go.id/DataMKG/TEWS/gempaterkini.json", timeout=20)
        lst = ((o or {}).get("Infogempa") or {}).get("gempa") or []
        for g in lst[:8]:
            print("  %s%s %s%s  M%s  %s  (%s)" % (Y, g.get("Tanggal"), g.get("Jam"), R, g.get("Magnitude"), g.get("Wilayah"), g.get("Kedalaman")))
        sec("Gempa dirasakan (BMKG)")
        st, o = http_json("https://data.bmkg.go.id/DataMKG/TEWS/gempadirasakan.json", timeout=20)
        lst = ((o or {}).get("Infogempa") or {}).get("gempa") or []
        for g in lst[:6]:
            print("  %s%s %s%s  M%s  %s\n      %s%s%s" % (Y, g.get("Tanggal"), g.get("Jam"), R, g.get("Magnitude"), g.get("Wilayah"), D, g.get("Dirasakan", ""), R))
        sec("Berita bencana alam Indonesia hari ini (sumber tepercaya diutamakan)")
        items = gnews("bencana alam Indonesia", "1d")
        items.sort(key=lambda x: (not any(t in x.get("source", "").lower() for t in TRUSTED)))
        if not show_items(items, 8, True):
            p_info("Tidak ada berita bencana 24 jam terakhir.")
        p_info("Peringatan dini cuaca & info resmi: https://www.bmkg.go.id/  |  BNPB: https://bnpb.go.id/")
    else:
        sec("Gempa dunia M4.5+ (24 jam terakhir, USGS)")
        st, o = http_json("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson", timeout=25)
        feats = (o or {}).get("features") or []
        feats.sort(key=lambda f: f["properties"].get("time", 0), reverse=True)
        for f in feats[:10]:
            p = f["properties"]
            print("  %sM%s%s  %s  %s(%s)%s%s" % (Y, p.get("mag"), R, p.get("place"), D, fmt_epoch(p.get("time")), R,
                                                  (RD + "  TSUNAMI-FLAG" + R) if p.get("tsunami") else ""))
            print("      %s%s%s" % (BL, p.get("url"), R))
        if not feats:
            p_warn("Data USGS tidak tersedia (HTTP %s)." % st)
        sec("Peringatan bencana global (GDACS)")
        st, _, body = http("https://www.gdacs.org/xml/rss.xml", timeout=25)
        gi = parse_feed(body) if st == 200 else []
        for it in gi[:8]:
            print("  %s%s%s\n      %s%s%s" % (W, re.sub(r"\s+", " ", it.get("title", ""))[:120], R, BL, it.get("link", ""), R))
        if not gi:
            p_warn("Feed GDACS tidak tersedia.")
        sec("Berita bencana alam dunia hari ini")
        items = gnews("natural disaster earthquake flood storm", "1d")
        items.sort(key=lambda x: (not any(t in x.get("source", "").lower() for t in TRUSTED)))
        if not show_items(items, 8, True):
            p_info("Tidak ada berita 24 jam terakhir.")


def yahoo_chart(sym):
    st, o = http_json("https://query1.finance.yahoo.com/v8/finance/chart/%s?range=5d&interval=1d" % q(sym), timeout=20)
    try:
        res = o["chart"]["result"][0]
        closes = [c for c in res["indicators"]["quote"][0].get("close", []) if c is not None]
        return res["meta"], closes
    except Exception:
        return None, []


@module("emiten", "Cek emiten saham BEI dari kode 4-5 huruf (tmpo -> Tempo): nama perusahaan, harga, dan berita tepercaya hari ini.",
        "Input: kode saham, contoh TMPO / BBCA / GOTO. Data harga bersumber Yahoo Finance (bisa tertunda).")
def emiten():
    code = ask("Masukkan kode emiten 4-5 huruf (contoh: TMPO, BBCA, GOTO)  (0 = batal)")
    if not code or code == "0":
        return
    code = code.strip().upper()
    if not re.fullmatch(r"[A-Z]{4,5}", code):
        p_err("Kode harus 4-5 huruf (contoh: TMPO).")
        return
    sym = code + ".JK"
    name = TICKERS.get(code)
    sec("Emiten: " + code)
    st, o = http_json("https://query2.finance.yahoo.com/v1/finance/search?q=%s&quotesCount=5&newsCount=0&lang=id-ID&region=ID" % q(sym), timeout=20)
    sector = industry = None
    for it in (o or {}).get("quotes", []) or []:
        if it.get("symbol") == sym:
            name = it.get("longname") or it.get("shortname") or name
            sector, industry = it.get("sectorDisp") or it.get("sector"), it.get("industryDisp") or it.get("industry")
            break
    kv("Kode", code)
    kv("Nama perusahaan", name or "tidak ditemukan (periksa kode)")
    if sector:
        kv("Sektor / Industri", "%s / %s" % (sector, industry))
    meta, closes = yahoo_chart(sym)
    if meta:
        price, prev = meta.get("regularMarketPrice"), (closes[-2] if len(closes) >= 2 else meta.get("chartPreviousClose"))
        kv("Bursa", meta.get("fullExchangeName") or meta.get("exchangeName"))
        kv("Harga terakhir", "%s %s" % (price, meta.get("currency", "IDR")))
        if price is not None and prev:
            ch = price - prev
            col = G if ch >= 0 else RD
            kv("Perubahan", "%s%+.2f (%+.2f%%)%s" % (col, ch, ch / prev * 100, R))
        kv("Rentang hari ini", "%s - %s" % (meta.get("regularMarketDayLow"), meta.get("regularMarketDayHigh")))
        kv("Rentang 52 minggu", "%s - %s" % (meta.get("fiftyTwoWeekLow"), meta.get("fiftyTwoWeekHigh")))
        kv("Volume", meta.get("regularMarketVolume"))
    else:
        p_warn("Data harga tidak tersedia (kode salah / Yahoo membatasi akses).")
    if name:
        sec("Berita %s hari ini (sumber tepercaya diutamakan)" % name)
        items = gnews('"%s" OR %s saham' % (name, code), "1d")
        if not items:
            p_info("Tidak ada berita 24 jam terakhir; menampilkan berita 7 hari terakhir.")
            items = gnews('"%s" OR %s saham' % (name, code), "7d")
        items.sort(key=lambda x: (not any(t in x.get("source", "").lower() for t in TRUSTED)))
        if not show_items(items, 8, True):
            p_warn("Tidak ada berita ditemukan.")
    rows = [("TradingView", "https://www.tradingview.com/symbols/IDX-%s/" % code),
            ("Yahoo Finance", "https://finance.yahoo.com/quote/%s" % sym),
            ("Profil resmi BEI", "https://www.idx.co.id/id/perusahaan-tercatat/profil-perusahaan-tercatat/")]
    open_choices(rows)


# =====================================================================
#  MODUL: METADATA, GAMBAR
# =====================================================================
IMG_EXT = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".webp", ".heic", ".gif", ".bmp")


def file_hashes(path):
    md, sh = hashlib.md5(), hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            md.update(chunk)
            sh.update(chunk)
    return md.hexdigest(), sh.hexdigest()


def gps_deg(vals, ref):
    d, m, s = [float(x) for x in vals]
    v = d + m / 60.0 + s / 3600.0
    return -v if str(ref).upper() in ("S", "W") else v


def clean_path(p):
    return (p or "").strip().strip('"').strip("'")


@module("exif_view", "Analisis metadata file: ukuran, hash, EXIF foto (kamera, tanggal, perangkat) dan koordinat GPS bila ada.",
        "Input: path file (contoh /sdcard/DCIM/foto.jpg). Foto dari medsos biasanya sudah bersih dari EXIF.")
def exif_view():
    path = clean_path(ask("Masukkan path file yang akan dianalisis  (0 = batal)"))
    if not path or path == "0":
        return
    if not os.path.isfile(path):
        p_err("File tidak ditemukan: " + path)
        return
    sec("Metadata: " + os.path.basename(path))
    st = os.stat(path)
    md5, sha = file_hashes(path)
    kv("Ukuran", "%d byte" % st.st_size)
    kv("Dimodifikasi", datetime.datetime.fromtimestamp(st.st_mtime).strftime("%Y-%m-%d %H:%M:%S"))
    kv("MD5", md5)
    kv("SHA-256", sha)
    if path.lower().endswith(IMG_EXT):
        pil = ensure_pip_module("PIL", "Pillow", "membaca EXIF gambar")
        if pil:
            try:
                from PIL import Image, ExifTags
                img = Image.open(path)
                kv("Format / Mode", "%s / %s" % (img.format, img.mode))
                kv("Dimensi", "%dx%d" % img.size)
                ex = img.getexif()
                if not ex:
                    p_info("Tidak ada data EXIF pada gambar ini.")
                for tid, val in ex.items():
                    nm = ExifTags.TAGS.get(tid, str(tid))
                    if isinstance(val, bytes):
                        val = val[:40]
                    if nm in ("MakerNote", "UserComment") or tid in (34665, 34853):
                        continue
                    kv(nm, str(val)[:100])
                sub = {}
                try:
                    sub = ex.get_ifd(0x8769)
                except Exception:
                    pass
                for tid, val in sub.items():
                    nm = ExifTags.TAGS.get(tid, str(tid))
                    if nm in ("MakerNote", "UserComment") or isinstance(val, bytes):
                        continue
                    kv(nm, str(val)[:100])
                gps = {}
                try:
                    gps = ex.get_ifd(0x8825)
                except Exception:
                    pass
                if gps.get(2) and gps.get(4):
                    lat, lon = gps_deg(gps[2], gps.get(1, "N")), gps_deg(gps[4], gps.get(3, "E"))
                    sec("KOORDINAT GPS DITEMUKAN")
                    kv("Lintang, Bujur", "%.6f, %.6f" % (lat, lon))
                    kv("Peta", "https://www.google.com/maps?q=%.6f,%.6f" % (lat, lon))
            except Exception as ex2:
                p_warn("Gagal membaca EXIF: %s" % ex2)
    if yes_no("Jalankan ExifTool untuk metadata lengkap semua jenis file?"):
        run_tool("exiftool", {"path": path})


@module("exif_strip", "Menghapus metadata (EXIF/GPS) dari gambar dan menyimpan salinan bersih; file asli tidak diubah.",
        "Input: path gambar. Hasil: file baru dengan akhiran _bersih di folder yang sama (JPEG disimpan ulang, kualitas 95).")
def exif_strip():
    path = clean_path(ask("Masukkan path gambar yang akan dibersihkan  (0 = batal)"))
    if not path or path == "0":
        return
    if not os.path.isfile(path) or not path.lower().endswith(IMG_EXT):
        p_err("File gambar tidak ditemukan / format tidak didukung.")
        return
    pil = ensure_pip_module("PIL", "Pillow", "membersihkan metadata gambar")
    if not pil:
        return
    from PIL import Image
    base, ext = os.path.splitext(path)
    out = base + "_bersih" + ext
    try:
        img = Image.open(path)
        clean = Image.new(img.mode, img.size)
        clean.putdata(list(img.getdata()))
        if ext.lower() in (".jpg", ".jpeg"):
            clean.save(out, quality=95)
        else:
            clean.save(out)
        p_ok("Tersimpan tanpa metadata: " + out)
    except Exception as ex:
        p_err("Gagal membersihkan: %s" % ex)


@module("image_source", "Mencari sumber asli sebuah gambar lewat Google Lens, TinEye, Yandex, dan Bing (pencarian gambar terbalik).",
        "Input: URL gambar langsung (https://...jpg). Untuk file lokal, halaman mesin akan dibuka dan kamu unggah manual.")
def image_source():
    u = ask("Masukkan URL gambar (atau ketik 'file' untuk gambar lokal)  (0 = batal)")
    if not u or u == "0":
        return
    sec("Pencarian gambar terbalik")
    if u.lower() == "file":
        p_info("Buka salah satu mesin berikut, lalu unggah gambarmu secara manual.")
        rows = [("Google Lens", "https://lens.google.com/"), ("TinEye", "https://tineye.com/"),
                ("Yandex Gambar", "https://yandex.com/images/"), ("Bing Visual Search", "https://www.bing.com/visualsearch")]
    else:
        e = q(u)
        rows = [("Google Lens", "https://lens.google.com/uploadbyurl?url=" + e), ("TinEye", "https://tineye.com/search?url=" + e),
                ("Yandex Gambar", "https://yandex.com/images/search?rpt=imageview&url=" + e),
                ("Bing Visual Search", "https://www.bing.com/images/search?view=detailv2&iss=sbi&q=imgurl:" + e)]
    open_choices(rows)


# =====================================================================
#  MODUL: GAME, PRODUK, IMEI
# =====================================================================
DOTA_RANKS = {1: "Herald", 2: "Guardian", 3: "Crusader", 4: "Archon", 5: "Legend", 6: "Ancient", 7: "Divine", 8: "Immortal"}
GENSHIN_SERVER = {"1": "China (CN)", "2": "China (CN)", "5": "China (CN)", "6": "Amerika (NA)", "7": "Eropa (EU)",
                  "8": "Asia (termasuk Indonesia)", "9": "TW/HK/MO"}


def game_minecraft(u):
    st, o = http_json("https://api.mojang.com/users/profiles/minecraft/" + q(u), timeout=15)
    if st != 200 or not o:
        p_warn("Username Minecraft tidak ditemukan (HTTP %s)." % st)
        return
    kv("Nama", o.get("name"))
    kv("UUID", o.get("id"))
    st2, pr = http_json("https://sessionserver.mojang.com/session/minecraft/profile/" + str(o.get("id")), timeout=15)
    for prop in (pr or {}).get("properties", []):
        if prop.get("name") == "textures":
            try:
                tex = json.loads(base64.b64decode(prop["value"]).decode("utf-8"))
                sk = tex.get("textures", {}).get("SKIN", {})
                kv("Skin (file)", sk.get("url", "-"))
                kv("Model skin", (sk.get("metadata") or {}).get("model", "classic"))
                kv("Cape", tex.get("textures", {}).get("CAPE", {}).get("url", "tidak ada"))
            except Exception:
                pass
    kv("Profil NameMC", "https://namemc.com/profile/" + q(o.get("name", u)))
    p_info("Minecraft tidak menyimpan lokasi, rank, atau bio akun.")


def game_roblox(u):
    st, o = http_json("https://users.roblox.com/v1/usernames/users", method="POST",
                      data={"usernames": [u], "excludeBannedUsers": False}, timeout=15)
    d = ((o or {}).get("data") or [])
    if not d:
        p_warn("Username Roblox tidak ditemukan (HTTP %s)." % st)
        return
    uid = d[0].get("id")
    st, pr = http_json("https://users.roblox.com/v1/users/%s" % uid, timeout=15)
    pr = pr or {}
    kv("Nama / Tampilan", "%s / %s" % (pr.get("name"), pr.get("displayName")))
    kv("ID", uid)
    kv("Bio", (pr.get("description") or "-")[:160])
    kv("Dibuat", pr.get("created"))
    kv("Dibanned", pr.get("isBanned"))
    st, fc = http_json("https://friends.roblox.com/v1/users/%s/friends/count" % uid, timeout=15)
    kv("Jumlah teman", (fc or {}).get("count", "-"))
    st, av = http_json("https://thumbnails.roblox.com/v1/users/avatar?userIds=%s&size=420x420&format=Png" % uid, timeout=15)
    try:
        kv("Avatar / skin", av["data"][0]["imageUrl"])
    except Exception:
        pass
    kv("Profil", "https://www.roblox.com/users/%s/profile" % uid)


def game_steam(u):
    path = "profiles/" + u if re.fullmatch(r"\d{17}", u) else "id/" + q(u)
    st, _, body = http("https://steamcommunity.com/%s/?xml=1" % path, timeout=20)
    try:
        root = ET.fromstring(body)
    except ET.ParseError:
        p_warn("Profil Steam tidak terbaca (HTTP %s)." % st)
        return
    if root.find("error") is not None:
        p_warn("Steam: " + (root.find("error").text or "profil tidak ditemukan"))
        return
    for lab, tag in [("SteamID64", "steamID64"), ("Nama", "steamID"), ("Status", "onlineState"), ("Privasi", "privacyState"),
                     ("Nama asli", "realname"), ("Lokasi (isian profil)", "location"), ("Anggota sejak", "memberSince"),
                     ("Headline", "headline"), ("VAC ban", "vacBanned"), ("Avatar", "avatarFull")]:
        el = root.find(tag)
        if el is not None and (el.text or "").strip():
            kv(lab, el.text.strip())
    sm = root.find("summary")
    if sm is not None and sm.text:
        kv("Bio", re.sub(r"<[^>]+>", "", sm.text)[:200])


def game_genshin(uid):
    if not uid.isdigit():
        p_err("UID Genshin berupa angka (9 digit).")
        return
    kv("Server (perkiraan lokasi)", GENSHIN_SERVER.get(uid[0], "tidak diketahui"))
    st, o = http_json("https://enka.network/api/uid/" + uid, headers={"User-Agent": "GigaOSINT/1.0"}, timeout=20)
    pi = (o or {}).get("playerInfo")
    if not pi:
        p_warn("Enka.Network tidak mengembalikan data (HTTP %s). Pastikan UID benar & karakter dipajang di profil game." % st)
        return
    kv("Nama", pi.get("nickname"))
    kv("Bio", pi.get("signature") or "-")
    kv("Adventure Rank", pi.get("level"))
    kv("World Level", pi.get("worldLevel"))
    kv("Achievement", pi.get("finishAchievementNum"))
    if pi.get("towerFloorIndex") is not None:
        kv("Spiral Abyss", "lantai %s-%s" % (pi.get("towerFloorIndex"), pi.get("towerLevelIndex")))
    kv("Karakter dipajang", ", ".join(str(a.get("avatarId")) for a in pi.get("showAvatarInfoList", [])) or "-")


def game_dota(aid):
    st, o = http_json("https://api.opendota.com/api/players/" + q(aid), timeout=20)
    if not o or not o.get("profile"):
        p_warn("Akun Dota 2 tidak ditemukan / profil privat (HTTP %s)." % st)
        return
    p = o["profile"]
    kv("Nama", p.get("personaname"))
    kv("Account ID", p.get("account_id"))
    kv("Negara (isian profil)", p.get("loccountrycode") or "-")
    rt = o.get("rank_tier")
    if rt:
        kv("Rank", "%s %s" % (DOTA_RANKS.get(rt // 10, "?"), rt % 10))
    else:
        kv("Rank", "belum terkalibrasi / tidak publik")
    kv("Login terakhir", p.get("last_login") or "-")
    kv("Profil Steam", p.get("profileurl"))
    kv("Avatar", p.get("avatarfull"))


def game_chesscom(u):
    st, o = http_json("https://api.chess.com/pub/player/" + q(u.lower()), timeout=15)
    if st != 200 or not o:
        p_warn("Akun Chess.com tidak ditemukan (HTTP %s)." % st)
        return
    kv("Username", o.get("username"))
    kv("Nama", o.get("name") or "-")
    kv("Gelar", o.get("title") or "-")
    kv("Negara", str(o.get("country", "-")).rsplit("/", 1)[-1])
    kv("Lokasi (isian profil)", o.get("location") or "-")
    kv("Bergabung / Terakhir online", "%s / %s" % (fmt_epoch(o.get("joined")), fmt_epoch(o.get("last_online"))))
    kv("Pengikut", o.get("followers"))
    st, s = http_json("https://api.chess.com/pub/player/%s/stats" % q(u.lower()), timeout=15)
    for mode in ("chess_rapid", "chess_blitz", "chess_bullet"):
        try:
            kv("Rating " + mode.split("_")[1], s[mode]["last"]["rating"])
        except Exception:
            pass


def game_lichess(u):
    st, o = http_json("https://lichess.org/api/user/" + q(u), timeout=15)
    if st != 200 or not o:
        p_warn("Akun Lichess tidak ditemukan (HTTP %s)." % st)
        return
    pr = o.get("profile", {}) or {}
    kv("Username", o.get("username"))
    kv("Nama", ("%s %s" % (pr.get("firstName", ""), pr.get("lastName", ""))).strip() or "-")
    kv("Negara / Lokasi", "%s / %s" % (pr.get("country", "-"), pr.get("location", "-")))
    kv("Bio", (pr.get("bio") or "-")[:160])
    kv("Dibuat", fmt_epoch(o.get("createdAt")))
    for m in ("bullet", "blitz", "rapid", "classical"):
        if (o.get("perfs", {}).get(m) or {}).get("rating"):
            kv("Rating " + m, o["perfs"][m]["rating"])


GAMES = [
    ("Minecraft (username)", game_minecraft, "Masukkan username Minecraft Java"),
    ("Roblox (username)", game_roblox, "Masukkan username Roblox"),
    ("Steam (ID 17 digit / nama custom URL)", game_steam, "Masukkan SteamID64 atau nama custom URL"),
    ("Genshin Impact (UID)", game_genshin, "Masukkan UID Genshin (9 digit)"),
    ("Dota 2 (Account ID)", game_dota, "Masukkan Account ID Dota 2 (angka)"),
    ("Chess.com (username)", game_chesscom, "Masukkan username Chess.com"),
    ("Lichess (username)", game_lichess, "Masukkan username Lichess"),
]
GAME_LINKS = [("Mobile Legends / Free Fire / PUBG Mobile", None),
              ("Valorant (Tracker.gg)", "https://tracker.gg/valorant"), ("League of Legends (OP.GG)", "https://www.op.gg/"),
              ("Fortnite Tracker", "https://fortnitetracker.com/"), ("Apex Legends Tracker", "https://apex.tracker.gg/")]


@module("game_acc", "Cek akun game dengan ID/username: nama, bio, level/rank, skin, dan lokasi atau server bila datanya publik.",
        "Input: pilih game lalu masukkan ID/username. Game tanpa API publik (ML, FF, PUBGM) hanya diberi tautan tracker.")
def game_acc():
    sec("Pilih game")
    for i, (n, _, _) in enumerate(GAMES, 1):
        print("  %s[%s%d%s]%s %s%s%s" % (W, Y, i, W, R, Y, n, R))
    k = len(GAMES) + 1
    print("  %s[%s%d%s]%s %sGame lain (tautan tracker)%s" % (W, Y, k, W, R, Y, R))
    c = ask("Pilih nomor game  (0 = batal)")
    if not c or not c.isdigit() or int(c) == 0:
        return
    c = int(c)
    if c == k:
        p_info("Mobile Legends, Free Fire, dan PUBG Mobile tidak punya API publik resmi: lokasi, skin, rank, dan bio hanya terlihat di dalam game.")
        open_choices([(n, u) for n, u in GAME_LINKS if u])
        return
    if not 1 <= c <= len(GAMES):
        return
    name, fn, label = GAMES[c - 1]
    v = ask(label + "  (0 = batal)")
    if not v or v == "0":
        return
    sec("%s: %s" % (name, v))
    fn(v.strip())


GS1 = [(0, 139, "Amerika Serikat / Kanada"), (300, 379, "Prancis"), (400, 440, "Jerman"), (450, 459, "Jepang"),
       (460, 469, "Rusia"), (471, 471, "Taiwan"), (480, 480, "Filipina"), (489, 489, "Hong Kong"), (490, 499, "Jepang"),
       (500, 509, "Inggris"), (520, 521, "Yunani"), (539, 539, "Irlandia"), (540, 549, "Belgia / Luksemburg"),
       (560, 560, "Portugal"), (570, 579, "Denmark"), (590, 590, "Polandia"), (600, 601, "Afrika Selatan"),
       (622, 622, "Mesir"), (628, 628, "Arab Saudi"), (629, 629, "Uni Emirat Arab"), (640, 649, "Finlandia"),
       (690, 699, "Tiongkok"), (700, 709, "Norwegia"), (729, 729, "Israel"), (730, 739, "Swedia"), (750, 750, "Meksiko"),
       (760, 769, "Swiss"), (789, 790, "Brasil"), (800, 839, "Italia"), (840, 849, "Spanyol"), (868, 869, "Turki"),
       (870, 879, "Belanda"), (880, 880, "Korea Selatan"), (885, 885, "Thailand"), (888, 888, "Singapura"),
       (890, 890, "India"), (893, 893, "Vietnam"), (896, 896, "Pakistan"), (899, 899, "Indonesia"),
       (900, 919, "Austria"), (930, 939, "Australia"), (940, 949, "Selandia Baru"), (955, 955, "Malaysia")]


def gtin_valid(code):
    if not code.isdigit() or len(code) not in (8, 12, 13, 14):
        return False
    digits = [int(c) for c in code]
    check = digits.pop()
    total = sum(d * (3 if i % 2 == 0 else 1) for i, d in enumerate(reversed(digits)))
    return (10 - total % 10) % 10 == check


def gs1_country(code):
    if len(code) < 13:
        code = code.zfill(13)
    p = int(code[:3])
    for lo, hi, n in GS1:
        if lo <= p <= hi:
            return n
    return None


@module("product_code", "Cek kode produk (barcode EAN/UPC): validitas, negara asal prefix, data produk, harga, dan skor keaslian indikatif.",
        "Input: angka barcode 8/12/13/14 digit di kemasan. Skor hanya indikator; barcode bisa dipalsukan, cek BPOM & segel.")
def product_code():
    code = ask("Masukkan kode barcode produk (contoh: 8991234567890)  (0 = batal)")
    if not code or code == "0":
        return
    code = re.sub(r"\D", "", code)
    sec("Kode produk: " + code)
    score, found_name = 0, None
    valid = gtin_valid(code)
    kv("Checksum valid", (G + "ya" + R) if valid else (RD + "TIDAK (kode kemungkinan salah ketik/palsu)" + R))
    score += 35 if valid else 0
    ctry = gs1_country(code) if code else None
    kv("Prefix GS1 (negara pendaftar)", ctry or "tidak dikenali")
    score += 15 if ctry else 0
    for host, nm in [("world.openfoodfacts.org", "Open Food Facts"), ("world.openbeautyfacts.org", "Open Beauty Facts"),
                     ("world.openproductsfacts.org", "Open Products Facts")]:
        st, o = http_json("https://%s/api/v2/product/%s.json?fields=product_name,brands,quantity,countries,categories" % (host, code), timeout=15)
        p = (o or {}).get("product") if o and o.get("status") == 1 else None
        if p:
            found_name = p.get("product_name") or found_name
            kv(nm, "DITEMUKAN")
            kv("  Nama / Merek", "%s / %s" % (p.get("product_name"), p.get("brands")))
            kv("  Kemasan / Negara jual", "%s / %s" % (p.get("quantity"), p.get("countries")))
            score += 30
            break
    st, o = http_json("https://api.upcitemdb.com/prod/trial/lookup?upc=" + code, timeout=15)
    items = (o or {}).get("items") or []
    if items:
        it = items[0]
        kv("UPCitemdb", "DITEMUKAN")
        kv("  Judul / Merek", "%s / %s" % (it.get("title"), it.get("brand")))
        kv("  Harga tercatat (USD)", "%s - %s" % (it.get("lowest_recorded_price"), it.get("highest_recorded_price")))
        for of in (it.get("offers") or [])[:3]:
            kv("  Penawaran", "%s: %s %s" % (of.get("merchant"), of.get("price"), of.get("currency", "")))
        score += 20
        found_name = found_name or it.get("title")
    score = min(score, 100)
    if not valid:
        score = min(score, 30)   # checksum salah = bukan barcode sah, skor dibatasi
        p_warn("Checksum barcode salah, skor dibatasi maksimal 30%.")
    if score >= 80:
        label = G + "kemungkinan besar produk terdaftar/asli" + R
    elif score >= 50:
        label = Y + "belum pasti - verifikasi lagi" + R
    else:
        label = RD + "mencurigakan / tidak terverifikasi" + R
    sec("Skor keaslian indikatif")
    kv("Skor", "%d%% asli  |  %d%% perlu diwaspadai (KW)" % (score, 100 - score))
    kv("Kesimpulan", label)
    p_warn("Skor ini heuristik dari data terbuka, BUKAN jaminan. Pastikan juga segel, kualitas kemasan, toko resmi, dan nomor BPOM.")
    kw = found_name or code
    open_choices([("Cek BPOM (makanan/obat/kosmetik)", "https://cekbpom.pom.go.id/"),
                  ("Harga di Shopee", "https://shopee.co.id/search?keyword=" + q(kw)),
                  ("Harga di Tokopedia", "https://www.tokopedia.com/search?q=" + q(kw)),
                  ("Harga di Google Shopping", "https://www.google.com/search?tbm=shop&q=" + q(kw))])


def luhn_ok(num):
    total = 0
    for i, ch in enumerate(reversed(num)):
        d = int(ch)
        if i % 2 == 1:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


@module("imei", "Memeriksa IMEI (15 digit): validasi Luhn, TAC/pabrikan, dan tautan cek registrasi IMEI & garansi resmi.",
        "Input: IMEI 15 digit (tekan *#06# di HP). Nomor seri Apple/Samsung dicek lewat tautan garansi resmi.")
def imei():
    n = ask("Masukkan IMEI (15 digit) atau nomor seri  (0 = batal)")
    if not n or n == "0":
        return
    d = re.sub(r"\D", "", n)
    sec("Cek IMEI / nomor seri: " + n)
    if len(d) in (15, 16) and d == n.strip():
        kv("Panjang", "%d digit" % len(d))
        if len(d) == 15:
            kv("Luhn valid", (G + "ya" + R) if luhn_ok(d) else (RD + "tidak (IMEI salah/palsu)" + R))
        kv("TAC (8 digit awal)", d[:8])
        kv("Reporting Body ID", d[:2])
        kv("Nomor seri perangkat", d[8:14])
        p_info("Cari TAC di imei.info untuk melihat merek & model sesuai kode.")
    else:
        p_info("Input bukan IMEI 15/16 digit; dianggap nomor seri perangkat.")
    open_choices([("IMEI.info (model/merek)", "https://www.imei.info/"),
                  ("Cek IMEI Kemenperin (registrasi Indonesia)", "https://imei.kemenperin.go.id/"),
                  ("Garansi Apple (nomor seri)", "https://checkcoverage.apple.com/"),
                  ("Samsung (dukungan & garansi)", "https://www.samsung.com/id/support/")])


# =====================================================================
#  MODUL: KRIPTO, BROKER, DORK
# =====================================================================
WALLET_PATTERNS = [
    ("Bitcoin (BTC)", r"^(bc1[a-z0-9]{25,87}|[13][a-km-zA-HJ-NP-Z1-9]{25,34})$"),
    ("Ethereum / EVM", r"^0x[a-fA-F0-9]{40}$"),
    ("Tron (TRX)", r"^T[1-9A-HJ-NP-Za-km-z]{33}$"),
    ("Litecoin (LTC)", r"^(ltc1[a-z0-9]{25,87}|[LM][a-km-zA-HJ-NP-Z1-9]{26,33})$"),
    ("Dogecoin (DOGE)", r"^D[5-9A-HJ-NP-U][1-9A-HJ-NP-Za-km-z]{32}$"),
    ("Ripple (XRP)", r"^r[1-9A-HJ-NP-Za-km-z]{24,34}$"),
    ("Monero (XMR)", r"^4[0-9AB][1-9A-HJ-NP-Za-km-z]{93}$"),
    ("Bitcoin Cash (BCH)", r"^(bitcoincash:)?[qp][a-z0-9]{41}$"),
    ("Solana (SOL)", r"^[1-9A-HJ-NP-Za-km-z]{32,44}$"),
]
EXPLORERS = {"Bitcoin (BTC)": "https://www.blockchain.com/explorer/addresses/btc/%s", "Ethereum / EVM": "https://etherscan.io/address/%s",
             "Tron (TRX)": "https://tronscan.org/#/address/%s", "Litecoin (LTC)": "https://blockchair.com/litecoin/address/%s",
             "Dogecoin (DOGE)": "https://blockchair.com/dogecoin/address/%s", "Ripple (XRP)": "https://xrpscan.com/account/%s",
             "Monero (XMR)": "https://xmrchain.net/", "Bitcoin Cash (BCH)": "https://blockchair.com/bitcoin-cash/address/%s",
             "Solana (SOL)": "https://solscan.io/account/%s"}


def detect_wallet(a):
    for name, pat in WALLET_PATTERNS:
        if re.match(pat, a):
            return name
    return None


@module("wallet", "Cek kode wallet kripto: deteksi jenis jaringan, saldo & transaksi publik (BTC/ETH), dan tautan block explorer.",
        "Input: alamat wallet (BTC, ETH, TRX, LTC, DOGE, XRP, SOL, dll). Data blockchain bersifat publik dan pseudonim.")
def wallet():
    a = ask("Masukkan alamat wallet kripto  (0 = batal)")
    if not a or a == "0":
        return
    a = a.strip()
    kind = detect_wallet(a)
    sec("Wallet: " + a)
    kv("Jenis terdeteksi", kind or "tidak dikenali")
    if kind == "Bitcoin (BTC)":
        st, o = http_json("https://blockstream.info/api/address/" + q(a), timeout=20)
        if o and "chain_stats" in o:
            cs = o["chain_stats"]
            bal = (cs["funded_txo_sum"] - cs["spent_txo_sum"]) / 1e8
            kv("Saldo", "%.8f BTC" % bal)
            kv("Total transaksi", cs.get("tx_count"))
            kv("Total diterima", "%.8f BTC" % (cs["funded_txo_sum"] / 1e8))
            st2, txs = http_json("https://blockstream.info/api/address/%s/txs" % q(a), timeout=20)
            for t in (txs or [])[:5]:
                bt = (t.get("status") or {}).get("block_time")
                print("   %s%s%s  %s" % (D, fmt_epoch(bt) if bt else "belum terkonfirmasi", R, t.get("txid")))
        else:
            p_warn("Blockstream tidak mengembalikan data (HTTP %s)." % st)
    elif kind == "Ethereum / EVM":
        st, o = http_json("https://ethereum-rpc.publicnode.com", method="POST",
                          data={"jsonrpc": "2.0", "method": "eth_getBalance", "params": [a, "latest"], "id": 1}, timeout=20)
        try:
            kv("Saldo ETH", "%.6f ETH" % (int(o["result"], 16) / 1e18))
        except Exception:
            p_warn("Saldo ETH tidak terbaca.")
        st, o = http_json("https://ethereum-rpc.publicnode.com", method="POST",
                          data={"jsonrpc": "2.0", "method": "eth_getTransactionCount", "params": [a, "latest"], "id": 2}, timeout=20)
        try:
            kv("Transaksi keluar (nonce)", int(o["result"], 16))
        except Exception:
            pass
    rows = []
    if kind and kind in EXPLORERS:
        rows.append(("Block explorer " + kind, EXPLORERS[kind].replace("%s", q(a))))
    rows.append(("OXT / Blockchair pencarian", "https://blockchair.com/search?q=" + q(a)))
    rows.append(("Cek laporan scam (Google)", "https://www.google.com/search?q=" + q('"%s" scam OR fraud OR phishing' % a)))
    open_choices(rows)


@module("nft", "Cek NFT: deteksi alamat kontrak/wallet dan buka NFT, kepemilikan, serta riwayat di marketplace & explorer.",
        "Input: alamat kontrak NFT, alamat wallet (0x...), atau tautan OpenSea. Data NFT berada di blockchain publik.")
def nft():
    a = ask("Masukkan alamat kontrak/wallet NFT (0x...) atau tautan OpenSea  (0 = batal)")
    if not a or a == "0":
        return
    a = a.strip()
    m = re.search(r"0x[a-fA-F0-9]{40}", a)
    sec("Cek NFT")
    if m:
        addr = m.group(0)
        kv("Alamat", addr)
        rows = [("Etherscan - token/NFT", "https://etherscan.io/address/" + addr),
                ("Etherscan - transfer NFT", "https://etherscan.io/nft-transfers?a=" + addr),
                ("OpenSea", "https://opensea.io/" + addr), ("NFTScan", "https://www.nftscan.com/" + addr),
                ("Blockscan (multi-chain)", "https://blockscan.com/address/" + addr)]
    elif re.match(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$", a):
        kv("Jenis", "Alamat Solana")
        rows = [("Solscan", "https://solscan.io/account/" + a), ("Magic Eden", "https://magiceden.io/")]
    else:
        p_warn("Format tidak dikenali; membuka pencarian umum NFT.")
        rows = [("OpenSea pencarian", "https://opensea.io/assets?search[query]=" + q(a)), ("NFTScan", "https://www.nftscan.com/")]
    open_choices(rows)


@module("broker", "Cek legalitas broker/pialang dan entitas investasi lewat daftar regulator (OJK, Bappebti, NFA, FCA, ASIC).",
        "Input: nama broker/perusahaan; halaman regulator dibuka untuk dicari manual. Waspada janji profit pasti.")
def broker():
    n = ask("Masukkan nama broker / platform investasi  (0 = batal)")
    if not n or n == "0":
        return
    sec("Verifikasi legalitas: " + n)
    p_info("Broker legal di Indonesia terdaftar OJK/Bappebti. Daftar entitas ilegal ada di Satgas PASTI (OJK).")
    open_choices([("OJK - Waspada Investasi (entitas ilegal)", "https://sikapiuangmu.ojk.go.id/FrontEnd/AlertPortal/Negative"),
                  ("Bappebti (pialang berjangka)", "https://www.bappebti.go.id/"),
                  ("NFA BASIC (AS)", "https://www.nfa.futures.org/basicnet/"),
                  ("FCA Register (Inggris)", "https://register.fca.org.uk/s/"),
                  ("ASIC (Australia)", "https://asic.gov.au/online-services/search-asics-registers/"),
                  ("Cari laporan penipuan (Google)", "https://www.google.com/search?q=" + q(n + " penipuan OR scam OR ilegal"))])


DORKS_DOMAIN = ['site:{t}', 'site:{t} filetype:pdf', 'site:{t} filetype:xls OR filetype:xlsx OR filetype:csv',
                'site:{t} filetype:doc OR filetype:docx', 'site:{t} inurl:admin OR inurl:login',
                'site:{t} intitle:"index of"', 'site:{t} ext:log OR ext:bak OR ext:sql OR ext:env',
                'site:{t} "confidential" OR "internal use only"', 'site:*.{t} -www',
                'site:pastebin.com "{t}"', 'site:github.com "{t}"', 'site:trello.com "{t}"', '"@{t}" filetype:xls OR filetype:csv']
DORKS_WORD = ['"{t}"', '"{t}" filetype:pdf', 'intitle:"{t}"', 'intext:"{t}"', 'inurl:{t}',
              'site:linkedin.com "{t}"', 'site:facebook.com "{t}"', 'site:instagram.com "{t}"', '"{t}" site:pastebin.com']


@module("dork_builder", "Pembuat Google Dork otomatis untuk domain atau kata kunci: dokumen, login, direktori terbuka, dan jejak paste.",
        "Input: domain (example.com) atau kata kunci/nama. Gunakan hasilnya hanya untuk OSINT dan target berizin.")
def dork_builder():
    t = ask("Masukkan domain atau kata kunci  (0 = batal)")
    if not t or t == "0":
        return
    t = t.strip()
    pool = DORKS_DOMAIN if re.match(r"^[A-Za-z0-9.\-]+\.[A-Za-z]{2,}$", t) else DORKS_WORD
    sec("Dork untuk: " + t)
    rows = []
    for tpl in pool:
        dk = tpl.replace("{t}", t)
        print("  " + CY + dk + R)
        rows.append((dk, "https://www.google.com/search?q=" + q(dk)))
    open_choices(rows)



# =====================================================================
#  v3 - MODUL BARU (1): jaringan, IP, keamanan, arsip, keuangan (API publik)
# =====================================================================
def dd(x):
    """Pastikan dict (balasan API yang formatnya berubah tidak menjatuhkan fitur)."""
    return x if isinstance(x, dict) else {}


def open_choices(rows, ctx=""):
    """rows = [(label, url)]. Nomor = pratinjau di terminal; o<nomor> = buka di browser; a = cek status semua."""
    rows = [(lab, u) for lab, u in rows if u]
    if not rows:
        return
    LAST_URLS[:] = rows
    sec("Tautan resmi / terkait")
    for i, (lab, u) in enumerate(rows, 1):
        print("  %s %s%s%s" % (num_tag(i), W, trunc(lab, max(16, term_w() - 8)), R))
        print("       %s%s%s" % (BL, trunc(u, max(16, term_w() - 10)), R))
    print()
    for ln in hint_bar([("nomor", "pratinjau di terminal"), ("o<nomor>", "buka di browser, contoh o1"), ("a", "cek status semua"), ("0", "selesai")]):
        print(ln)
    while True:
        c = ask("Pilih: nomor / o<nomor> / a / 0")
        if c is None or c == "0":
            return
        cl = c.lower().replace(" ", "")
        if cl == "a":
            batch_status(rows)
            continue
        m = re.fullmatch(r"o(\d*)", cl)
        if m:
            idx = m.group(1)
            if not idx and len(rows) == 1:
                idx = "1"
            if not idx:
                idx = (ask("Nomor tautan yang dibuka di browser (1-%d)" % len(rows)) or "").strip()
            if idx.isdigit() and 1 <= int(idx) <= len(rows):
                open_browser(rows[int(idx) - 1][1])
            else:
                p_warn("Nomor tautan tidak valid.")
            continue
        if cl.isdigit() and 1 <= int(cl) <= len(rows):
            lab, u = rows[int(cl) - 1]
            peek(u, label=lab, ctx=ctx + " " + lab)
        else:
            p_warn("Pilihan tidak valid. Ketik nomor, o1, a, atau 0.")


# ---------- pembantu umum ----------
def ask_val(kind, label, example, allow_empty=False):
    """Tanya input bersih. None = batal (0 / q / Ctrl+C)."""
    while True:
        v = ask("%s  (contoh: %s)  (0 = batal)" % (label, example))
        if v is None or v == "0":
            return None
        if not v and allow_empty:
            return ""
        ok, cl, hint = clean_input(kind, v)
        if ok:
            return cl
        p_warn("Input belum benar: %s" % hint)


def explain_http(st, what="layanan", err=""):
    if st == 0:
        p_err("Tidak bisa terhubung ke %s. %s" % (what, ("(" + err + ")") if err else ""))
        p_info("Penyebab umum: internet mati, DNS diblokir, atau situs sedang down. Coba buka situsnya lewat browser, ganti DNS ke 1.1.1.1, atau matikan VPN/proxy.")
    elif st in (401, 403):
        p_err("%s menolak permintaan (HTTP %s): API key salah/kedaluwarsa atau akses dibatasi untuk jaringanmu." % (what, st))
        p_info("Periksa key di Pengaturan > Kunci API (hapus lalu masukkan ulang), atau pastikan akunmu aktif.")
    elif st == 404:
        p_warn("Data tidak ditemukan di %s (HTTP 404). Periksa ejaan input." % what)
    elif st == 429:
        p_warn("Terlalu banyak permintaan ke %s (HTTP 429). Tunggu sekitar 1 menit lalu coba lagi." % what)
    elif st >= 500:
        p_err("Server %s sedang bermasalah (HTTP %s). Coba lagi beberapa menit lagi." % (what, st))
    else:
        p_warn("%s membalas HTTP %s (tidak terduga)." % (what, st))


def jget(url, what="layanan", headers=None, data=None, method="GET", timeout=20, quiet=False):
    """Ambil JSON dengan penjelasan galat awam. Mengembalikan objek (dict/list) atau None."""
    r = fetch(url, method=method, data=data, headers=headers, timeout=timeout)
    if not (200 <= r.status < 300):
        if not quiet:
            explain_http(r.status, what, r.err)
        return None
    try:
        return json.loads(text_of(r.body))
    except Exception:
        if not quiet:
            p_warn("Balasan %s bukan JSON yang valid (mungkin halaman blokir/penjaga bot)." % what)
        return None


def _flat(obj, prefix="", depth=0, maxdepth=3):
    out = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            key = (prefix + "." + str(k)) if prefix else str(k)
            if isinstance(v, dict) and depth < maxdepth:
                out += _flat(v, key, depth + 1, maxdepth) or [(key, "-")]
            elif isinstance(v, list):
                if not v:
                    out.append((key, "-"))
                elif all(not isinstance(x, (dict, list)) for x in v):
                    out.append((key, ", ".join(str(x) for x in v[:12]) + (" ..." if len(v) > 12 else "")))
                elif depth < maxdepth:
                    for i, x in enumerate(v[:4]):
                        out += _flat(x, "%s[%d]" % (key, i), depth + 1, maxdepth) if isinstance(x, dict) else [("%s[%d]" % (key, i), str(x))]
                else:
                    out.append((key, "(%d item)" % len(v)))
            else:
                out.append((key, "-" if v in (None, "") else str(v)))
    elif obj is not None:
        out.append((prefix or "nilai", str(obj)))
    return out


def show_obj(obj, skip=(), limit=36, w=24):
    rows = [(k, v) for k, v in _flat(obj) if not any(k.startswith(s) for s in skip)]
    for i, (k, v) in enumerate(rows):
        if i >= limit:
            p_info("%d baris lain disembunyikan (batasi tampilan)." % (len(rows) - limit))
            break
        kv(k, v, w)
    return len(rows)


def par(jobs, workers=6):
    """jobs = [(nama, fungsi)] -> dict nama -> hasil atau Exception."""
    out = {}

    def run(j):
        try:
            return j[0], j[1]()
        except Exception as e:      # satu sumber gagal tidak boleh menjatuhkan yang lain
            return j[0], e
    with ThreadPoolExecutor(max_workers=workers) as ex:
        for k, v in ex.map(run, jobs):
            out[k] = v
    return out


def key_peek(name, env=None):
    """Ambil key tersimpan TANPA bertanya (env var atau keys.json); string kosong bila tidak ada."""
    env = env or (re.sub(r"[^A-Z0-9]", "_", name.upper()) + "_API_KEY")
    return os.environ.get(env, "").strip() or _load_keys().get(name, "")


def my_public_ip():
    if SYS.get("pub"):
        return SYS["pub"]
    for u in ("https://api.ipify.org", "https://ifconfig.me/ip", "https://api.ipquery.io/"):
        r = fetch(u, timeout=8)
        t = text_of(r.body).strip()
        try:
            ipaddress.ip_address(t)
            return t
        except ValueError:
            continue
    return ""


def map_links(lat, lon):
    return [("OpenStreetMap", "https://www.openstreetmap.org/?mlat=%s&mlon=%s#map=15/%s/%s" % (lat, lon, lat, lon)),
            ("Google Maps", "https://www.google.com/maps?q=%s,%s" % (lat, lon))]


# ---------- IP lintas sumber ----------
MOD_API["ip_multi"] = "Opsional: sumber ipinfodb dan iplocate lebih lengkap dengan API key gratis (ipinfodb.com / iplocate.io). Tanpa key, 3 sumber lain tetap jalan."


@module("ip_multi", "Lokasi dan kepemilikan sebuah IP dari beberapa sumber gratis sekaligus (ipquery, ip-api, iplocate, RIPEstat, ipinfodb).",
        "Input: alamat IP (Enter = IP publikmu). Tiap sumber tampil terpisah; negara yang berbeda antar sumber ditandai.")
def ip_multi():
    v = ask("Masukkan alamat IP (contoh: 8.8.8.8)  Enter = IP publik saya, 0 = batal")
    if v is None or v == "0":
        return
    ip = v.strip()
    if ip:
        try:
            ip = str(ipaddress.ip_address(ip))
        except ValueError:
            p_err("Itu bukan alamat IP yang valid. Contoh: 8.8.8.8 atau 2001:4860:4860::8888")
            return
    else:
        with Spinner("Mencari IP publikmu"):
            ip = my_public_ip()
        if not ip:
            p_err("IP publik tidak bisa ditemukan (internet mati?). Ketik IP secara manual.")
            return
    if ipaddress.ip_address(ip).is_private:
        p_warn("%s adalah alamat IP pribadi (jaringan lokal): tidak ada data lokasi publik." % ip)
        return
    jobs = [("ipquery.io", lambda: jget("https://api.ipquery.io/" + ip, "ipquery.io", quiet=True)),
            ("ip-api.com", lambda: jget("http://ip-api.com/json/%s?fields=status,message,country,countryCode,regionName,city,zip,lat,lon,timezone,isp,org,as,mobile,proxy,hosting,query" % ip, "ip-api.com", quiet=True)),
            ("iplocate.io", lambda: jget("https://iplocate.io/api/lookup/" + ip + (("?apikey=" + key_peek("iplocate")) if key_peek("iplocate") else ""), "iplocate.io", quiet=True)),
            ("RIPEstat", lambda: jget("https://stat.ripe.net/data/prefix-overview/data.json?resource=" + ip, "RIPEstat", quiet=True))]
    kf = key_peek("ipinfodb")
    if kf:
        jobs.append(("ipinfodb", lambda: jget("https://api.ipinfodb.com/v3/ip-city/?key=%s&ip=%s&format=json" % (kf, ip), "ipinfodb", quiet=True)))
    with Spinner("Menanyakan %d sumber untuk %s" % (len(jobs), ip)):
        res = par(jobs)
    countries = {}
    sec("Hasil untuk IP %s" % ip)
    for name, o in res.items():
        print("\n  %s%s %s%s%s" % (MG, GL["bullet"], W + B, name, R))
        if isinstance(o, Exception) or not o:
            p_warn("Tidak ada jawaban dari %s (gagal, diblokir, atau batas kuota)." % name)
            continue
        if name == "ip-api.com" and o.get("status") != "success":
            p_warn("ip-api.com: %s" % o.get("message", "gagal"))
            continue
        if name == "ipquery.io":
            countries[name] = (o.get("location") or {}).get("country_code")
        elif name == "ip-api.com":
            countries[name] = o.get("countryCode")
        elif name == "iplocate.io":
            countries[name] = o.get("country_code")
        elif name == "ipinfodb":
            countries[name] = o.get("countryCode")
        if name == "RIPEstat":
            d = dd(dd(o).get("data"))
            kv("Blok/prefiks", dd(d.get("block")).get("resource") or d.get("resource"))
            kv("Dijumumkan", d.get("announced"))
            for a in [x for x in (d.get("asns") or []) if isinstance(x, dict)][:4]:
                kv("ASN", "AS%s  %s" % (a.get("asn"), a.get("holder")))
            continue
        show_obj(o, skip=("error",), limit=22)
    cs = set(c for c in countries.values() if c)
    sec("Ringkasan")
    if len(cs) > 1:
        p_warn("Negara berbeda antar sumber: %s. Data lokasi IP bersifat perkiraan; gunakan kepemilikan ASN sebagai pegangan utama." % ", ".join("%s=%s" % (k, v) for k, v in countries.items()))
    elif cs:
        p_ok("Semua sumber sepakat: negara %s." % list(cs)[0])
    else:
        p_warn("Tidak ada sumber yang memberi negara. Periksa internet atau coba lagi nanti.")
    p_info("Catatan: lokasi IP = lokasi penyedia layanan, bukan alamat rumah seseorang.")
    open_choices([("IP lookup (ipinfo.io)", "https://ipinfo.io/" + ip), ("RIPEstat", "https://stat.ripe.net/" + ip),
                  ("AbuseIPDB (reputasi)", "https://www.abuseipdb.com/check/" + ip), ("Shodan", "https://www.shodan.io/host/" + ip)], ctx="ip")


# ---------- ASN / BGP ----------
@module("bgp_asn", "Siapa pemilik sebuah ASN / IP / prefiks, prefiks yang diumumkan, dan profil peering (RIPEstat, BGPView, PeeringDB).",
        "Input: nomor ASN (AS13335 atau 13335), alamat IP, atau prefiks (1.1.1.0/24). Tanpa API key.")
def bgp_asn():
    v = ask("Masukkan ASN / IP / prefiks (contoh: AS13335, 1.1.1.1, 1.1.1.0/24)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = v.strip().upper().replace(" ", "")
    asn = None
    if re.fullmatch(r"(AS)?\d{1,10}", v):
        asn = v.replace("AS", "")
    else:
        try:
            ipaddress.ip_network(v, strict=False)
        except ValueError:
            p_err("Format tidak dikenali. Contoh: AS13335, 8.8.8.8, 8.8.8.0/24")
            return
        with Spinner("Mencari ASN untuk %s" % v):
            o = jget("https://stat.ripe.net/data/prefix-overview/data.json?resource=" + q(v), "RIPEstat", quiet=True)
        d = dd(dd(o).get("data"))
        sec("Prefiks %s" % v)
        kv("Blok", dd(d.get("block")).get("resource") or d.get("resource"))
        kv("Deskripsi blok", dd(d.get("block")).get("desc") or dd(d.get("block")).get("name"))
        kv("Dijumumkan", d.get("announced"))
        asns = [x for x in (d.get("asns") or []) if isinstance(x, dict)]
        for a in asns[:5]:
            kv("ASN pemilik", "AS%s  %s" % (a.get("asn"), a.get("holder")))
        if not asns:
            p_warn("Prefiks ini tidak diumumkan di BGP (atau RIPEstat tidak menjawab).")
            return
        asn = str(asns[0].get("asn"))
    with Spinner("Mengumpulkan data AS%s" % asn):
        res = par([("ov", lambda: jget("https://stat.ripe.net/data/as-overview/data.json?resource=AS" + asn, "RIPEstat", quiet=True)),
                   ("pf", lambda: jget("https://stat.ripe.net/data/announced-prefixes/data.json?resource=AS" + asn, "RIPEstat", quiet=True)),
                   ("ab", lambda: jget("https://stat.ripe.net/data/abuse-contact-finder/data.json?resource=AS" + asn, "RIPEstat", quiet=True)),
                   ("bg", lambda: jget("https://api.bgpview.io/asn/" + asn, "BGPView", quiet=True)),
                   ("pd", lambda: jget("https://www.peeringdb.com/api/net?asn=" + asn, "PeeringDB", quiet=True))])
    sec("AS%s  (RIPEstat)" % asn)
    ov = ((res["ov"] or {}).get("data") or {}) if isinstance(res["ov"], dict) else {}
    if ov:
        kv("Pemegang (holder)", ov.get("holder"))
        kv("Dijumumkan", ov.get("announced"))
        kv("Blok registri", (ov.get("block") or {}).get("desc"))
    else:
        p_warn("RIPEstat tidak memberi data ringkasan untuk AS%s." % asn)
    pf = (((res["pf"] or {}).get("data") or {}).get("prefixes") or []) if isinstance(res["pf"], dict) else []
    kv("Jumlah prefiks", len(pf))
    for p in pf[:12]:
        print("      %s%s%s" % (W, p.get("prefix"), R))
    if len(pf) > 12:
        p_info("%d prefiks lain tidak ditampilkan." % (len(pf) - 12))
    ab = (((res["ab"] or {}).get("data") or {}).get("abuse_contacts") or []) if isinstance(res["ab"], dict) else []
    if ab:
        kv("Kontak abuse", ", ".join(ab[:3]))
    sec("BGPView")
    bg = ((res["bg"] or {}).get("data") or {}) if isinstance(res["bg"], dict) else {}
    if bg:
        for k in ("name", "description_short", "country_code", "website", "email_contacts", "abuse_contacts", "looking_glass", "date_updated"):
            kv(k, bg.get(k) if not isinstance(bg.get(k), list) else ", ".join(bg.get(k)[:3]))
    else:
        p_info("BGPView tidak menjawab (layanan ini kadang tutup/dibatasi). Data RIPEstat di atas tetap valid.")
    sec("PeeringDB")
    pd = ((res["pd"] or {}).get("data") or []) if isinstance(res["pd"], dict) else []
    if pd:
        n = pd[0]
        for k in ("name", "aka", "website", "info_type", "info_scope", "info_traffic", "policy_general", "irr_as_set", "looking_glass", "status"):
            kv(k, n.get(k))
    else:
        p_info("AS%s tidak terdaftar di PeeringDB (wajar untuk jaringan kecil)." % asn)
    open_choices([("RIPEstat AS%s" % asn, "https://stat.ripe.net/AS" + asn), ("BGP.HE.net", "https://bgp.he.net/AS" + asn),
                  ("PeeringDB", "https://www.peeringdb.com/asn/" + asn), ("BGPView", "https://bgpview.io/asn/" + asn)], ctx="bgp")


# ---------- geolokasi WiFi/BSSID ----------
@module("wifi_geo", "Mencari lokasi perkiraan dari alamat MAC/BSSID titik akses WiFi (basis data terbuka Mylnikov).",
        "Input: BSSID, contoh 00:1A:2B:3C:4D:5E. Hasil: lintang, bujur, radius, tanggal data. Data terbuka dan tidak lengkap.")
def wifi_geo():
    v = ask("Masukkan BSSID / MAC WiFi (contoh: 00:1A:2B:3C:4D:5E)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    hexs = re.sub(r"[^0-9A-Fa-f]", "", v)
    if len(hexs) != 12:
        p_err("BSSID harus 12 digit heksadesimal (6 pasang). Contoh: 00:1A:2B:3C:4D:5E")
        return
    mac = ":".join(hexs[i:i + 2] for i in range(0, 12, 2)).upper()
    with Spinner("Mencari %s" % mac):
        o = jget("https://api.mylnikov.org/geolocation/wifi?v=1.1&data=open&bssid=" + mac, "Mylnikov")
    if not o:
        return
    if o.get("result") != 200 or not o.get("data"):
        p_warn("BSSID %s tidak ada di basis data terbuka Mylnikov (kode %s). Itu hal biasa: datanya terbatas." % (mac, o.get("result")))
        return
    d = o["data"]
    sec("Lokasi perkiraan %s" % mac)
    kv("Lintang", d.get("lat"))
    kv("Bujur", d.get("lon"))
    kv("Radius (m)", d.get("range"))
    kv("Data terakhir", fmt_epoch(d.get("time")) if d.get("time") else "-")
    p_info("Titik akses yang dipindahkan atau dimatikan bisa memberi lokasi lama.")
    open_choices(map_links(d.get("lat"), d.get("lon")), ctx="peta")


# ---------- DomainsDB ----------
@module("domainsdb", "Mencari domain terdaftar yang mengandung kata kunci (DomainsDB): tanggal dibuat, negara, IP, status.",
        "Input: kata kunci, contoh 'bank' dan ekstensi opsional (com, id). Berguna untuk mendeteksi domain tiruan (typosquatting).")
def domainsdb():
    kw = ask("Masukkan kata kunci nama domain (contoh: bcaonline)  (0 = batal)")
    if kw is None or kw == "0" or not kw:
        return
    zone = ask("Batasi ekstensi? (contoh: com / id / Enter = semua)") or ""
    kw = re.sub(r"[^a-zA-Z0-9\-]", "", kw)
    if not kw:
        p_err("Kata kunci hanya boleh huruf, angka, dan tanda minus.")
        return
    url = "https://api.domainsdb.info/v1/domains/search?domain=%s&limit=50" % q(kw) + (("&zone=" + q(zone.lstrip("."))) if zone else "")
    with Spinner("Mencari domain berisi '%s'" % kw):
        o = jget(url, "DomainsDB")
    if o is None:
        return
    doms = o.get("domains") or []
    if not doms:
        p_warn("Tidak ada domain yang cocok (atau DomainsDB belum memilikinya).")
        return
    sec("%d domain ditemukan (menampilkan maksimal 25)" % len(doms))
    for d in doms[:25]:
        dead = d.get("isDead")
        a = ", ".join(d.get("A") or [])[:40]
        print("  %s%s%s %s%s  %sdibuat %s  neg %s  %s%s" % (RD if dead == "True" or dead is True else G, GL["dot"], R, W, d.get("domain"), D,
                                                           (d.get("create_date") or "-")[:10], d.get("country") or "-", a or "-", R))
    p_info("Titik merah = domain tidak aktif. Domain baru dengan nama mirip merek terkenal patut dicurigai.")


# ---------- DNS banding resolver ----------
@module("dns_banding", "Membandingkan jawaban DNS dari Google dan Cloudflare (DNS-over-HTTPS) untuk mendeteksi pemblokiran atau pembajakan DNS.",
        "Input: domain. Hasil: catatan A/AAAA/MX/NS/TXT dari dua resolver; perbedaan ditandai. Tanpa API key.")
def dns_banding():
    d = ask_val("domain", "Masukkan domain", "example.com")
    if not d:
        return
    types = ["A", "AAAA", "MX", "NS", "TXT"]

    def one(resolver, typ):
        if resolver == "Google":
            o = jget("https://dns.google/resolve?name=%s&type=%s" % (q(d), typ), "Google DNS", quiet=True)
        else:
            o = jget("https://cloudflare-dns.com/dns-query?name=%s&type=%s" % (q(d), typ), "Cloudflare DNS", headers={"Accept": "application/dns-json"}, quiet=True)
        if not isinstance(o, dict):
            return None
        return o.get("Status"), sorted(set(a.get("data", "") for a in (o.get("Answer") or []) if a.get("type") == RTYPES.get(typ)))
    jobs = [("%s|%s" % (r, t), (lambda r=r, t=t: one(r, t))) for r in ("Google", "Cloudflare") for t in types]
    with Spinner("Menanyakan dua resolver"):
        res = par(jobs, 10)
    diff = 0
    sec("DNS %s" % d)
    for t in types:
        g, c = res.get("Google|" + t), res.get("Cloudflare|" + t)
        print("\n  %s%s%s" % (MG, t, R))
        for nm, x in (("Google", g), ("Cloudflare", c)):
            if not x or isinstance(x, Exception):
                print("   %s%-11s%s %sgagal menjawab%s" % (CY, nm, R, Y, R))
            else:
                st, ans = x
                shown = "; ".join(a[:60] for a in ans[:4]) or ("(kosong)" if st == 0 else "status DNS %s" % st)
                print("   %s%-11s%s %s%s%s" % (CY, nm, R, W, shown, R))
        if g and c and not isinstance(g, Exception) and not isinstance(c, Exception):
            if g[1] != c[1] and t in ("A", "AAAA", "NS", "MX"):
                if g[1] and c[1] and (set(g[1]) & set(c[1])):
                    p_info("Sebagian berbeda: wajar pada layanan dengan banyak IP (CDN, geo-DNS).")
                else:
                    diff += 1
                    p_warn("Jawaban %s berbeda total antar resolver." % t)
            if (g[0] == 3) != (c[0] == 3):
                diff += 1
                p_warn("Satu resolver menjawab NXDOMAIN (domain tidak ada) dan yang lain tidak: kemungkinan pemblokiran/penyaringan DNS.")
    sec("Kesimpulan")
    if diff:
        p_warn("Ada %d perbedaan penting. Bisa karena CDN, penyaringan DNS oleh jaringan/ISP, atau pembajakan DNS." % diff)
    else:
        p_ok("Kedua resolver konsisten untuk domain ini.")


# ---------- arsip web internasional ----------
@module("arsip_multi", "Mencari jejak arsip sebuah halaman di banyak arsip web: Wayback Machine, Arquivo.pt (Portugal), dan Library of Congress (AS).",
        "Input: URL atau domain. Hasil: jumlah/daftar salinan terbaru serta tautan arsip lain (UKWA, Trove, archive.ph).")
def arsip_multi():
    raw = ask("Masukkan URL atau domain (contoh: example.com/berita)  (0 = batal)")
    if raw is None or raw == "0" or not raw:
        return
    u = re.sub(r"^https?://", "", raw.strip())
    if "." not in u:
        p_err("Itu belum terlihat seperti URL/domain. Contoh: example.com")
        return
    full = "http://" + u

    def wb():
        o = jget("https://web.archive.org/cdx/search/cdx?url=%s&output=json&limit=-8&fl=timestamp,statuscode,original&collapse=digest" % q(u), "Wayback", quiet=True)
        return o
    def ar():
        r = fetch("https://arquivo.pt/wayback/cdx?url=%s&output=json&limit=8" % q(u), timeout=25)
        rows = []
        for ln in text_of(r.body).splitlines():
            try:
                rows.append(json.loads(ln))
            except Exception:
                continue
        return rows if r.status == 200 else None

    def loc():
        return jget("https://www.loc.gov/search/?q=%s&fo=json&c=5" % q(u), "Library of Congress", quiet=True)
    with Spinner("Mencari di tiga arsip"):
        res = par([("Wayback Machine", wb), ("Arquivo.pt", ar), ("Library of Congress", loc)])
    sec("Wayback Machine (archive.org)")
    w = res["Wayback Machine"]
    if isinstance(w, list) and len(w) > 1:
        for row in w[1:][-8:]:
            ts = row[0]
            print("  %s%s-%s-%s %s:%s%s  HTTP %s  %shttps://web.archive.org/web/%s/%s%s" % (Y, ts[:4], ts[4:6], ts[6:8], ts[8:10], ts[10:12], R, row[1], BL, ts, row[2][:60], R))
    else:
        p_warn("Wayback tidak punya salinan, atau tidak menjawab sekarang.")
    sec("Arquivo.pt (arsip web Portugal)")
    a = res["Arquivo.pt"]
    if isinstance(a, list) and a:
        for row in a[-8:]:
            ts = str(row.get("timestamp", ""))
            print("  %s%s-%s-%s%s  HTTP %s  %s%s%s" % (Y, ts[:4], ts[4:6], ts[6:8], R, row.get("status"), BL, trunc(str(row.get("url", "")), 70), R))
    else:
        p_info("Arquivo.pt tidak punya salinan untuk alamat ini (arsipnya berfokus pada web Portugal).")
    sec("Library of Congress")
    l = res["Library of Congress"]
    results = (l or {}).get("results") if isinstance(l, dict) else None
    if results:
        for r in results[:5]:
            print("  %s%s%s\n      %s%s%s" % (W, trunc(str(r.get("title")), 90), R, BL, r.get("url") or r.get("id"), R))
    else:
        p_info("Tidak ada hasil di Library of Congress untuk kata ini.")
    open_choices([("Wayback Machine (semua salinan)", "https://web.archive.org/web/*/" + u), ("archive.ph (arsip cepat)", "https://archive.ph/newest/" + full),
                  ("Arquivo.pt", "https://arquivo.pt/"), ("UK Web Archive", "https://www.webarchive.org.uk/"),
                  ("Trove (Australia)", "https://trove.nla.gov.au/"), ("Library of Congress Web Archives", "https://www.loc.gov/web-archives/")], ctx="arsip")


# ---------- VirusTotal ----------
MOD_API["vt_cek"] = "Butuh API key gratis dari https://www.virustotal.com (daftar akun > profil > API key). Batas gratis: 4 permintaan per menit."


def _vt_kind(v):
    if re.fullmatch(r"[0-9a-fA-F]{32}|[0-9a-fA-F]{40}|[0-9a-fA-F]{64}", v):
        return "file", v.lower()
    if re.match(r"^https?://", v, re.I):
        return "url", base64.urlsafe_b64encode(v.encode()).decode().rstrip("=")
    try:
        ipaddress.ip_address(v)
        return "ip", v
    except ValueError:
        pass
    if re.fullmatch(r"[A-Za-z0-9.\-]+\.[A-Za-z]{2,}", v):
        return "domain", v.lower()
    return None, None


@module("vt_cek", "Reputasi IP, domain, URL, atau hash file di VirusTotal (berapa mesin antivirus menandainya berbahaya).",
        "Input: IP, domain, URL (http...), atau hash MD5/SHA1/SHA256. Butuh API key VirusTotal gratis (disimpan lokal).")
def vt_cek():
    v = ask("Masukkan IP / domain / URL / hash file  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = v.strip()
    kind, ident = _vt_kind(v)
    if not kind:
        p_err("Input tidak dikenali. Contoh: 8.8.8.8, example.com, https://example.com/x, atau hash 64 karakter.")
        return
    key = api_key("virustotal", "VirusTotal", "https://www.virustotal.com/gui/my-apikey")
    if not key:
        p_warn("Tanpa API key fitur ini tidak bisa berjalan. Ambil key gratis lalu coba lagi.")
        return
    path = {"ip": "ip_addresses", "domain": "domains", "url": "urls", "file": "files"}[kind]
    with Spinner("Menanyakan VirusTotal"):
        o = jget("https://www.virustotal.com/api/v3/%s/%s" % (path, ident), "VirusTotal", headers={"x-apikey": key})
    if not o:
        return
    at = (o.get("data") or {}).get("attributes") or {}
    st = at.get("last_analysis_stats") or {}
    sec("VirusTotal: %s" % trunc(v, 60))
    mal, sus = st.get("malicious", 0), st.get("suspicious", 0)
    total = sum(st.values()) or 1
    kv("Berbahaya", "%s dari %s mesin" % (mal, total))
    kv("Mencurigakan", sus)
    kv("Bersih", st.get("harmless", 0))
    kv("Tidak terdeteksi", st.get("undetected", 0))
    kv("Reputasi komunitas", at.get("reputation"))
    for k in ("country", "as_owner", "asn", "registrar", "creation_date", "last_analysis_date", "meaningful_name", "type_description", "size", "title", "last_final_url"):
        if k in at:
            val = at[k]
            if k.endswith("_date") and isinstance(val, int):
                val = fmt_epoch(val * 1000)
            kv(k, val)
    if at.get("tags"):
        kv("Tag", ", ".join(at["tags"][:10]))
    if at.get("categories"):
        kv("Kategori", ", ".join(sorted(set(at["categories"].values()))[:6]))
    if mal:
        p_warn("Ada %d mesin yang menandai ini berbahaya. Jangan buka/jalankan tanpa isolasi." % mal)
    elif sus:
        p_warn("Tidak ada vonis berbahaya, tetapi %d mesin menandai mencurigakan." % sus)
    else:
        p_ok("Tidak ada mesin yang menandainya berbahaya (bukan jaminan aman).")
    gui = {"ip": "ip-address", "domain": "domain", "url": "url", "file": "file"}[kind]
    open_choices([("Laporan VirusTotal lengkap", "https://www.virustotal.com/gui/%s/%s" % (gui, ident))], ctx="vt")


# ---------- AbuseIPDB ----------
MOD_API["abuseip_cek"] = "Butuh API key gratis dari https://www.abuseipdb.com/account/api (batas gratis 1000 pemeriksaan per hari)."


@module("abuseip_cek", "Skor penyalahgunaan (spam, serangan, pindai) sebuah alamat IP dari laporan komunitas AbuseIPDB.",
        "Input: alamat IP. Hasil: skor keyakinan 0-100, jumlah laporan 90 hari, ISP, negara, tipe penggunaan. Butuh API key gratis.")
def abuseip_cek():
    ip = ask_val("host", "Masukkan alamat IP", "8.8.8.8")
    if not ip:
        return
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        p_err("AbuseIPDB hanya menerima alamat IP, bukan domain.")
        return
    key = api_key("abuseipdb", "AbuseIPDB", "https://www.abuseipdb.com/account/api")
    if not key:
        p_warn("Tanpa API key fitur ini tidak bisa berjalan.")
        return
    with Spinner("Menanyakan AbuseIPDB"):
        o = jget("https://api.abuseipdb.com/api/v2/check?ipAddress=%s&maxAgeInDays=90" % q(ip), "AbuseIPDB", headers={"Key": key, "Accept": "application/json"})
    if not o:
        return
    d = dd(dd(o).get("data"))
    sec("AbuseIPDB: %s" % ip)
    score = d.get("abuseConfidenceScore", 0)
    kv("Skor penyalahgunaan", "%s dari 100" % score)
    for k in ("totalReports", "numDistinctUsers", "lastReportedAt", "isp", "usageType", "domain", "countryCode", "isTor", "isWhitelisted"):
        kv(k, d.get(k))
    if score >= 75:
        p_err("Skor tinggi: IP ini sering dilaporkan berbahaya. Blokir/waspadai.")
    elif score >= 25:
        p_warn("Skor sedang: ada laporan penyalahgunaan; periksa konteksnya.")
    else:
        p_ok("Skor rendah: sedikit/tidak ada laporan 90 hari terakhir.")
    open_choices([("Laporan lengkap AbuseIPDB", "https://www.abuseipdb.com/check/" + ip)], ctx="abuse")


# ---------- AlienVault OTX ----------
MOD_API["otx_cek"] = "Opsional: API key gratis dari https://otx.alienvault.com (menu profil > OTX Key); sebagian data tidak muncul tanpa key."


@module("otx_cek", "Intelijen ancaman AlienVault OTX untuk IP, domain, URL, atau hash: berapa 'pulse' (laporan komunitas) yang menyebutnya.",
        "Input: IP, domain, URL, atau hash. Hasil: jumlah pulse, reputasi, daftar pulse teratas. Key opsional.")
def otx_cek():
    v = ask("Masukkan IP / domain / URL / hash  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = v.strip()
    kind, _ = _vt_kind(v)
    if kind == "ip":
        typ = "IPv6" if ":" in v else "IPv4"
    elif kind == "domain":
        typ = "domain"
    elif kind == "url":
        typ = "url"
    elif kind == "file":
        typ = "file"
    else:
        p_err("Input tidak dikenali. Contoh: 8.8.8.8, example.com, https://example.com/x, atau hash.")
        return
    key = key_peek("otx")
    hd = {"X-OTX-API-KEY": key} if key else {}
    if not key:
        p_warn("Tanpa API key: dicoba tanpa autentikasi (bisa ditolak). Simpan key lewat Pengaturan > Kunci API.")
    with Spinner("Menanyakan OTX"):
        o = jget("https://otx.alienvault.com/api/v1/indicators/%s/%s/general" % (typ, q(v) if typ == "url" else v), "AlienVault OTX", headers=hd)
    if not o:
        return
    pi = o.get("pulse_info") or {}
    sec("OTX: %s" % trunc(v, 60))
    kv("Jumlah pulse", pi.get("count"))
    kv("Reputasi", o.get("reputation"))
    for k in ("country_name", "city", "asn", "whois", "alexa", "indicator"):
        if o.get(k):
            kv(k, o.get(k))
    for p in (pi.get("pulses") or [])[:6]:
        print("  %s%s%s  %s%s%s" % (Y, GL["bullet"], R, W, trunc(p.get("name", "-"), 80), R))
    if pi.get("count"):
        p_warn("Disebut dalam %s laporan komunitas OTX; cek isinya sebelum menyimpulkan." % pi.get("count"))
    else:
        p_ok("Tidak disebut dalam pulse OTX (bukan jaminan aman).")
    open_choices([("Halaman OTX", "https://otx.alienvault.com/indicator/%s/%s" % ({"IPv4": "ip", "IPv6": "ip", "domain": "domain", "url": "url", "file": "file"}[typ], v))], ctx="otx")


# ---------- urlscan.io ----------
MOD_API["urlscan_cari"] = "Opsional: API key gratis dari https://urlscan.io/user/profile agar kuota pencarian lebih besar."


@module("urlscan_cari", "Mencari hasil pemindaian publik urlscan.io untuk sebuah domain atau IP: kapan dipindai, IP server, negara, tangkapan layar.",
        "Input: domain atau IP. Hasil: 10 pemindaian terbaru dengan tautan laporan. Tanpa key terbatas kuotanya.")
def urlscan_cari():
    t = ask_val("host", "Masukkan domain atau IP", "example.com")
    if not t:
        return
    key = key_peek("urlscan")
    hd = {"API-Key": key} if key else {}
    field = "ip" if re.fullmatch(r"[0-9a-fA-F:.]+", t) and ("." in t and t.replace(".", "").isdigit() or ":" in t) else "domain"
    with Spinner("Mencari di urlscan.io"):
        o = jget("https://urlscan.io/api/v1/search/?q=%s:%s&size=10" % (field, q(t)), "urlscan.io", headers=hd)
    if o is None:
        return
    res = o.get("results") or []
    sec("urlscan.io: %s  (%s hasil total)" % (t, o.get("total")))
    if not res:
        p_warn("Belum ada pemindaian publik untuk '%s'." % t)
    for r in res[:10]:
        tk, pg = r.get("task") or {}, r.get("page") or {}
        print("  %s%s%s  %s%s%s" % (Y, (tk.get("time") or "")[:16].replace("T", " "), R, W, trunc(tk.get("url") or "", 70), R))
        print("      %sIP %s  neg %s  server %s  %s%s%s" % (D, pg.get("ip") or "-", pg.get("country") or "-", pg.get("server") or "-", BL, "https://urlscan.io/result/%s/" % r.get("_id"), R))
    if res:
        open_choices([("Hasil terbaru urlscan", "https://urlscan.io/result/%s/" % res[0].get("_id")), ("Cari ulang di urlscan.io", "https://urlscan.io/search/#" + q(t))], ctx="urlscan")


# ---------- Phisherman ----------
MOD_API["phisherman_cek"] = "Butuh API token gratis dari https://phisherman.gg (daftar lewat Discord, bagian Developer/API)."


@module("phisherman_cek", "Memeriksa apakah sebuah domain terdaftar sebagai situs phishing/penipuan di basis data Phisherman.",
        "Input: domain (tanpa http). Hasil: klasifikasi (aman / berbahaya). Butuh API token Phisherman.")
def phisherman_cek():
    d = ask_val("domain", "Masukkan domain yang dicurigai", "login-bank-palsu.com")
    if not d:
        return
    key = api_key("phisherman", "Phisherman", "https://phisherman.gg")
    if not key:
        p_warn("Tanpa token fitur ini tidak bisa berjalan.")
        return
    with Spinner("Menanyakan Phisherman"):
        o = jget("https://api.phisherman.gg/v2/domains/info/" + q(d), "Phisherman", headers={"Authorization": "Bearer " + key})
    if o is None:
        return
    sec("Phisherman: %s" % d)
    info = o.get(d) if isinstance(o, dict) and isinstance(o.get(d), dict) else o
    show_obj(info, limit=20)
    cls = str((info or {}).get("classification", "")).lower() if isinstance(info, dict) else ""
    if "malicious" in cls or (isinstance(info, dict) and info.get("verifiedPhish")):
        p_err("Domain ini TERDAFTAR sebagai phishing. Jangan masukkan data apa pun di sana.")
    elif cls:
        p_ok("Klasifikasi: %s (tidak terdaftar sebagai phishing saat ini)." % cls)
    else:
        p_info("Respons tidak memuat klasifikasi jelas; lihat rincian di atas.")


# ---------- CVE ----------
MOD_API["cve_cari"] = "Opsional: API key gratis NVD dari https://nvd.nist.gov/developers/request-an-api-key (mempercepat batas permintaan)."


@module("cve_cari", "Mencari kerentanan CVE: deskripsi, skor CVSS, tanggal, dan referensi (NVD, cadangan CVE.org).",
        "Input: ID CVE (CVE-2021-44228) atau kata kunci (log4j). Hasil: ringkasan tiap CVE dan tautan resmi.")
def cve_cari():
    v = ask("Masukkan ID CVE atau kata kunci (contoh: CVE-2021-44228 atau log4j)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = v.strip()
    key = key_peek("nvd")
    hd = {"apiKey": key} if key else {}
    is_id = bool(re.fullmatch(r"CVE-\d{4}-\d{4,}", v, re.I))
    url = "https://services.nvd.nist.gov/rest/json/cves/2.0?" + (("cveId=" + v.upper()) if is_id else ("keywordSearch=%s&resultsPerPage=8" % q(v)))
    with Spinner("Mencari di NVD"):
        o = jget(url, "NVD", headers=hd, quiet=True)
    items = [x.get("cve") or {} for x in (o or {}).get("vulnerabilities", [])] if isinstance(o, dict) else []
    if not items and is_id:
        p_info("NVD tidak menjawab; mencoba CVE.org (cadangan).")
        c = jget("https://cveawg.mitre.org/api/cve/" + v.upper(), "CVE.org")
        if c:
            cna = (c.get("containers") or {}).get("cna") or {}
            sec(v.upper())
            kv("Status", (c.get("cveMetadata") or {}).get("state"))
            kv("Dipublikasikan", (c.get("cveMetadata") or {}).get("datePublished"))
            kv("Deskripsi", next((d.get("value") for d in cna.get("descriptions", []) if d.get("lang", "").startswith("en")), "-"))
            for ref in (cna.get("references") or [])[:6]:
                print("   %s%s%s" % (BL, ref.get("url"), R))
        open_choices([("CVE.org", "https://www.cve.org/CVERecord?id=" + v.upper())], ctx="cve")
        return
    if not items:
        p_warn("Tidak ada CVE yang cocok (atau NVD sedang membatasi permintaan). Coba lagi atau persempit kata kunci.")
        return
    rows = []
    for c in items[:8]:
        cid = c.get("id")
        desc = next((d.get("value") for d in c.get("descriptions", []) if d.get("lang") == "en"), "-")
        met = c.get("metrics") or {}
        cv = None
        for k in ("cvssMetricV40", "cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            if met.get(k):
                cv = (met[k][0].get("cvssData") or {})
                cv["_sev"] = met[k][0].get("baseSeverity") or cv.get("baseSeverity")
                break
        sec(cid)
        kv("Dipublikasikan", (c.get("published") or "")[:10])
        kv("Skor CVSS", ("%s  %s" % (cv.get("baseScore"), cv.get("_sev") or "")) if cv else "-")
        if cv and cv.get("vectorString"):
            kv("Vektor", cv.get("vectorString"))
        kv("Deskripsi", trunc(re.sub(r"\s+", " ", desc), 400))
        for ref in (c.get("references") or [])[:3]:
            print("   %s%s%s" % (BL, ref.get("url"), R))
        rows.append(("%s (NVD)" % cid, "https://nvd.nist.gov/vuln/detail/" + cid))
    open_choices(rows[:6], ctx="cve")


# ---------- kurs & VAT ----------
MOD_API["kurs_mata_uang"] = "Opsional: API key Amdoren (https://www.amdoren.com/currency-api/) untuk sumber kedua; sumber utama (VATcomply) tanpa key."


@module("kurs_mata_uang", "Kurs mata uang terbaru (VATcomply, data Bank Sentral Eropa) dan konversi cepat ke/dari rupiah.",
        "Input: jumlah, mata uang asal, mata uang tujuan (contoh 100 USD ke IDR). Tanpa API key.")
def kurs_mata_uang():
    amt = ask("Jumlah uang (contoh: 100)  (0 = batal)")
    if amt is None or amt == "0" or not amt:
        return
    try:
        amount = float(amt.replace(",", "."))
    except ValueError:
        p_err("Jumlah harus berupa angka. Contoh: 100 atau 2500.50")
        return
    a = (ask("Mata uang asal (kode 3 huruf, contoh: USD)  Enter = USD") or "USD").upper().strip()
    b = (ask("Mata uang tujuan (contoh: IDR)  Enter = IDR") or "IDR").upper().strip()
    if not (re.fullmatch(r"[A-Z]{3}", a) and re.fullmatch(r"[A-Z]{3}", b)):
        p_err("Kode mata uang harus 3 huruf, contoh: USD, IDR, EUR, JPY.")
        return
    with Spinner("Mengambil kurs"):
        o = jget("https://api.vatcomply.com/rates?base=" + a, "VATcomply")
    sec("Kurs %s ke %s" % (a, b))
    if o and (o.get("rates") or {}).get(b):
        rate = o["rates"][b]
        kv("Tanggal data", o.get("date"))
        kv("1 %s" % a, "%s %s" % (rate, b))
        kv("%s %s" % (amount, a), "%s %s" % (format(amount * rate, ",.2f"), b))
    else:
        p_warn("VATcomply tidak punya pasangan %s/%s (daftar dukungan terbatas pada mata uang utama)." % (a, b))
    key = key_peek("amdoren")
    if key:
        with Spinner("Sumber kedua (Amdoren)"):
            o2 = jget("https://www.amdoren.com/api/currency.php?api_key=%s&from=%s&to=%s&amount=%s" % (key, a, b, amount), "Amdoren")
        if o2 and o2.get("error") == 0:
            kv("Amdoren", "%s %s = %s %s" % (amount, a, o2.get("amount"), b))
        elif o2:
            p_warn("Amdoren: %s" % o2.get("error_message", "gagal"))
    else:
        p_info("Sumber kedua Amdoren aktif bila kamu menyimpan key lewat Pengaturan > Kunci API (nama: amdoren).")
    open_choices([("Bank Indonesia: kurs transaksi", "https://www.bi.go.id/id/statistik/informasi-kurs/transaksi-bi/default.aspx"), ("XE Converter", "https://www.xe.com/currencyconverter/")], ctx="kurs")


@module("vat_cek", "Memeriksa nomor VAT/PPN perusahaan Uni Eropa lewat layanan VIES (via VATcomply): valid, nama, dan alamat.",
        "Input: nomor VAT dengan kode negara, contoh NL123456789B01. Cocok untuk memverifikasi pemasok luar negeri.")
def vat_cek():
    v = ask("Masukkan nomor VAT (contoh: DE811128135)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = re.sub(r"[\s.\-]", "", v).upper()
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]{2,14}", v):
        p_err("Format tidak valid. Awali dengan kode negara 2 huruf, contoh: NL123456789B01")
        return
    with Spinner("Memeriksa VIES"):
        o = jget("https://api.vatcomply.com/vat?vat_number=" + q(v), "VATcomply")
    if not o:
        return
    sec("VAT %s" % v)
    kv("Valid", "YA" if o.get("valid") else "TIDAK")
    for k in ("country_code", "name", "address"):
        kv(k, o.get(k))
    if o.get("valid"):
        p_ok("Nomor VAT terdaftar aktif.")
    else:
        p_warn("Nomor tidak terdaftar/aktif. Bisa salah ketik, atau layanan VIES negara itu sedang gangguan.")
    open_choices([("VIES resmi Komisi Eropa", "https://ec.europa.eu/taxation_customs/vies/")], ctx="vat")


# ---------- FDIC (bank Amerika Serikat) ----------
@module("fdic_bank", "Mencari bank terdaftar di Amerika Serikat lewat basis data FDIC: kota, negara bagian, aset, status aktif.",
        "Input: nama bank (contoh: Wells Fargo). Hasil: sampai 8 bank cocok dengan nomor sertifikat FDIC. Tanpa API key.")
def fdic_bank():
    n = ask("Masukkan nama bank (contoh: Wells Fargo)  (0 = batal)")
    if n is None or n == "0" or not n:
        return
    n = re.sub(r'["\\]', "", n).strip()
    url = "https://banks.data.fdic.gov/api/institutions?filters=%s&fields=NAME,CITY,STNAME,ACTIVE,ASSET,CERT,WEBADDR&limit=8&sort_by=ASSET&sort_order=DESC" % q('NAME:"%s"' % n)
    with Spinner("Mencari di FDIC"):
        o = jget(url, "FDIC")
    rows = (o or {}).get("data") or []
    if not rows:
        if o is not None:
            p_warn("Tidak ada bank dengan nama '%s'. FDIC mencari nama persis; coba kata yang lebih pendek." % n)
        return
    sec("%s hasil FDIC" % len(rows))
    for r in rows:
        d = r.get("data") or {}
        print("  %s%s%s %s%s%s  %s%s, %s  aset $%s ribu  CERT %s%s" % (G if d.get("ACTIVE") in (1, "1") else RD, GL["dot"], R, W, d.get("NAME"), R, D,
                                                               d.get("CITY"), d.get("STNAME"), d.get("ASSET"), d.get("CERT"), R))
    open_choices([("FDIC BankFind", "https://banks.fdic.gov/bankfind-suite/bankfind")], ctx="fdic")


# ---------- Alpaca (berita pasar) ----------
MOD_API["alpaca_berita"] = "Butuh DUA key gratis (Key ID dan Secret) dari akun https://alpaca.markets (paper trading, dashboard > API Keys)."


@module("alpaca_berita", "Berita pasar saham/kripto terbaru per simbol dari Alpaca Markets (sumber: Benzinga dan lainnya).",
        "Input: simbol saham (contoh: AAPL, TSLA) atau kosong untuk umum. Butuh Key ID + Secret Alpaca gratis.")
def alpaca_berita():
    sym = (ask("Simbol saham (contoh: AAPL)  Enter = semua berita, 0 = batal") or "").upper().strip()
    if sym == "0":
        return
    if sym and not re.fullmatch(r"[A-Z.,]{1,20}", sym):
        p_err("Simbol hanya huruf, contoh: AAPL atau AAPL,MSFT")
        return
    kid = api_key("alpaca_id", "Alpaca Key ID", "https://app.alpaca.markets/", env="ALPACA_KEY_ID")
    sec_k = api_key("alpaca_secret", "Alpaca Secret", "https://app.alpaca.markets/", env="ALPACA_SECRET_KEY") if kid else ""
    if not (kid and sec_k):
        p_warn("Key ID dan Secret keduanya diperlukan.")
        return
    url = "https://data.alpaca.markets/v1beta1/news?limit=10" + (("&symbols=" + q(sym)) if sym else "")
    with Spinner("Mengambil berita Alpaca"):
        o = jget(url, "Alpaca", headers={"APCA-API-KEY-ID": kid, "APCA-API-SECRET-KEY": sec_k})
    news = (o or {}).get("news") or []
    if not news:
        if o is not None:
            p_warn("Tidak ada berita untuk simbol itu.")
        return
    sec("Berita pasar")
    for n in news:
        print("  %s%s%s  %s%s%s  %s[%s]%s" % (Y, (n.get("created_at") or "")[:16].replace("T", " "), R, W, trunc(n.get("headline", ""), 90), R, D, ",".join((n.get("symbols") or [])[:4]), R))
        print("      %s%s%s" % (BL, n.get("url"), R))


# =====================================================================
#  v3 - MODUL BARU (2): username luas, media sosial, WhatsApp, kartu HP, plat, bioskop, berita cepat, pemantauan
# =====================================================================
import html as _html
from collections import Counter

WMN_URL = "https://raw.githubusercontent.com/WebBreacher/WhatsMyName/main/wmn-data.json"
WMN_CACHE = os.path.join(DATA_DIR, "wmn-data.json")
_STOP = threading.Event()


def wmn_load():
    """Muat basis data WhatsMyName (700 situs): dari cache <7 hari, atau unduh dari GitHub."""
    try:
        if time.time() - os.path.getmtime(WMN_CACHE) < 7 * 86400:
            with open(WMN_CACHE, "r", encoding="utf-8") as f:
                d = json.load(f)
            if d.get("sites"):
                return d
    except Exception:
        pass
    r = fetch(WMN_URL, timeout=40, limit=8000000)
    if r.status == 200:
        try:
            d = json.loads(text_of(r.body))
            if d.get("sites"):
                try:
                    os.makedirs(DATA_DIR, exist_ok=True)
                    with open(WMN_CACHE, "w", encoding="utf-8") as f:
                        json.dump(d, f)
                except OSError:
                    pass
                return d
        except Exception:
            pass
    try:                       # cache lama lebih baik daripada tidak ada
        with open(WMN_CACHE, "r", encoding="utf-8") as f:
            d = json.load(f)
        p_warn("Gagal memperbarui daftar situs; memakai salinan lama di komputermu.")
        return d
    except Exception:
        explain_http(r.status, "GitHub (raw.githubusercontent.com)", r.err)
        return None


def wmn_check(site, user):
    """-> (status, url_tampil). status: ada | tidak | blok | ? | error"""
    acct = user
    for ch in site.get("strip_bad_char", "") or "":
        acct = acct.replace(ch, "")
    enc = urllib.parse.quote(acct, safe="")
    url = site["uri_check"].replace("{account}", enc)
    show = (site.get("uri_pretty") or site["uri_check"]).replace("{account}", enc)
    body = site.get("post_body")
    method = "POST" if body else "GET"
    data = body.replace("{account}", acct.replace('"', "")) if body else None
    r = fetch(url, method=method, data=data, headers=site.get("headers") or None, timeout=10, limit=300000)
    if r.status == 0:
        return "error", show
    txt = text_of(r.body)
    e_ok = r.status == site.get("e_code") and (site.get("e_string") or "") in txt
    m_str = site.get("m_string") or ""
    m_hit = (m_str and m_str in txt) or (r.status == site.get("m_code") and site.get("m_code") != site.get("e_code") and not m_str)
    if e_ok and not m_hit:
        return "ada", show
    if m_hit and not e_ok:
        return "tidak", show
    if r.status in (404, 410) and not e_ok:
        return "tidak", show
    if r.status in (403, 429, 503) or site.get("protection"):
        return "blok", show
    return "?", show


def wmn_scan(user, sites, label):
    """Pindai paralel; tampilkan temuan seketika. Ctrl+C menghentikan dengan rapi."""
    total = len(sites)
    found, unsure, blocked, errors, done = [], 0, 0, 0, [0]
    _STOP.clear()
    lock = threading.Lock()

    def work(s):
        if _STOP.is_set():
            return None
        try:
            return s, wmn_check(s, user)
        except Exception:
            return s, ("error", s.get("uri_check", ""))
    sec("%s: memindai %d situs untuk '%s' (Ctrl+C = berhenti dan tampilkan hasil sejauh ini)" % (label, total, user))
    ex = ThreadPoolExecutor(max_workers=28)
    futs = [ex.submit(work, s) for s in sites]
    try:
        from concurrent.futures import as_completed
        for f in as_completed(futs):
            res = f.result()
            if res is None:
                continue
            s, (st, shown) = res
            with lock:
                done[0] += 1
                if st == "ada":
                    found.append((s["name"], shown, s.get("cat", "")))
                    sys.stdout.write("\r\033[K" if TTY else "")
                    print("  [ADA]  %-22s %s" % (trunc(s["name"], 22), shown))
                elif st == "blok":
                    blocked += 1
                elif st == "?":
                    unsure += 1
                elif st == "error":
                    errors += 1
                if TTY and done[0] % 5 == 0:
                    sys.stdout.write("\r\033[K  %s%d/%d diperiksa  %s%d ditemukan%s" % (D, done[0], total, G, len(found), R))
                    sys.stdout.flush()
    except KeyboardInterrupt:
        _STOP.set()
        print()
        p_warn("Dihentikan oleh pengguna. Menampilkan hasil sejauh ini.")
    finally:
        _STOP.set()
        ex.shutdown(wait=False)
    sys.stdout.write("\r\033[K" if TTY else "")
    sec("Ringkasan")
    kv("Diperiksa", "%d dari %d situs" % (done[0], total))
    kv("Akun kemungkinan ada", len(found))
    kv("Tidak pasti / diblokir", "%d / %d" % (unsure, blocked))
    kv("Gagal terhubung", errors)
    if found:
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
            fp = os.path.join(OUT_DIR, "username_%s_%s.txt" % (re.sub(r"\W", "_", user)[:30], time.strftime("%Y%m%d_%H%M%S")))
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write("Giga OSINT - username '%s' (%s)\n" % (user, time.strftime("%Y-%m-%d %H:%M:%S")))
                for n, u, c in found:
                    fh.write("%s\t%s\t%s\n" % (n, c, u))
            p_ok("Daftar temuan disimpan: %s" % fp)
        except OSError:
            pass
        p_info("Temuan berarti 'ada akun dengan nama itu', belum tentu milik orang yang sama. Cocokkan foto, bio, dan tautan.")
        open_choices([(n, u) for n, u, _ in found[:12]], ctx="username")
    else:
        p_warn("Tidak ada akun ditemukan. Bisa benar-benar tidak ada, atau situs memblokir pemeriksaan otomatis.")
    return found


WMN_CAT_ID = {"social": "Media sosial", "gaming": "Game", "tech": "Teknologi", "hobby": "Hobi", "coding": "Pemrograman",
              "misc": "Lain-lain", "finance": "Keuangan", "business": "Bisnis", "music": "Musik", "shopping": "Belanja",
              "images": "Gambar & foto", "blog": "Blog", "art": "Seni", "dating": "Kencan", "video": "Video",
              "political": "Politik", "news": "Berita", "archived": "Arsip lama", "health": "Kesehatan"}


@module("user_wmn", "Cek username di 600+ situs dari daftar komunitas WhatsMyName (sosial, game, kode, musik, dll.) secara paralel.",
        "Input: username, lalu pilih kategori (Enter = semua kecuali dewasa). Hasil ditampilkan seketika dan disimpan ke folder hasil.")
def user_wmn():
    u = ask_val("user", "Masukkan username (tanpa @)", "budi123")
    if not u:
        return
    with Spinner("Memuat daftar situs WhatsMyName"):
        d = wmn_load()
    if not d:
        return
    sites = [s for s in d["sites"] if s.get("valid", True) and "{account}" in s.get("uri_check", "")]
    cnt = Counter(s.get("cat", "misc") for s in sites)
    cats = [c for c, _ in cnt.most_common() if "nsfw" not in c.lower()]
    sec("Pilih kategori")
    print("  %s %s%s%s  %s(%d situs, tanpa kategori dewasa)%s" % (num_tag(1), W, "Semua kategori", R, D, sum(cnt[c] for c in cats), R))
    for i, c in enumerate(cats, 2):
        print("  %s %s%-16s%s %s%d situs%s" % (num_tag(i), W, WMN_CAT_ID.get(c, c), R, D, cnt[c], R))
    pick = ask("Nomor kategori (boleh beberapa, pisahkan koma; Enter = semua; 0 = batal)")
    if pick is None or pick == "0":
        return
    chosen = set(cats)
    if pick.strip() and pick.strip() != "1":
        chosen = set()
        for tok in re.split(r"[,\s]+", pick.strip()):
            if tok.isdigit() and 2 <= int(tok) <= len(cats) + 1:
                chosen.add(cats[int(tok) - 2])
        if not chosen:
            p_warn("Tidak ada kategori valid dipilih; memakai semua.")
            chosen = set(cats)
    sel = [s for s in sites if s.get("cat") in chosen]
    prot = [s for s in sel if s.get("protection") and any(x in ("cloudflare", "captcha", "ddos-guard", "anubis") for x in s["protection"])]
    if prot and not yes_no("%d situs memakai proteksi anti-bot (hasil kurang pasti). Sertakan juga" % len(prot)):
        sel = [s for s in sel if s not in prot]
    wmn_scan(u, sel, "WhatsMyName")


# ---------- game: pemeriksaan langsung (akurat) + WMN kategori game ----------
def _game_checks(u):
    out = []
    r = fetch("https://api.mojang.com/users/profiles/minecraft/" + q(u), timeout=10)
    out.append(("Minecraft (Mojang)", "ada" if r.status == 200 else "tidak" if r.status in (204, 404) else "?", "https://namemc.com/profile/" + q(u)))
    r = fetch("https://users.roblox.com/v1/usernames/users", method="POST", data={"usernames": [u], "excludeBannedUsers": False}, timeout=10)
    try:
        arr = json.loads(text_of(r.body)).get("data") or []
        out.append(("Roblox", "ada" if arr else "tidak", "https://www.roblox.com/users/%s/profile" % arr[0]["id"] if arr else ""))
    except Exception:
        out.append(("Roblox", "?", ""))
    for name, url, show in (("Chess.com", "https://api.chess.com/pub/player/" + q(u.lower()), "https://www.chess.com/member/" + q(u)),
                            ("Lichess", "https://lichess.org/api/user/" + q(u), "https://lichess.org/@/" + q(u)),
                            ("Speedrun.com", "https://www.speedrun.com/api/v1/users/" + q(u), "https://www.speedrun.com/users/" + q(u))):
        r = fetch(url, timeout=10)
        out.append((name, "ada" if r.status == 200 else "tidak" if r.status == 404 else "?", show))
    return out


MOD_API["user_game"] = "Tanpa API key. Steam/Xbox/PlayStation tidak punya pemeriksaan resmi tanpa login, jadi disediakan tautan pencarian manual."


@module("user_game", "Cek username di platform game: Minecraft, Roblox, Chess, Lichess, Speedrun (langsung ke API) + 69 situs game WhatsMyName.",
        "Input: username/gamertag. Hasil: daftar akun yang ditemukan + tautan pencarian Steam, Xbox, PlayStation, Epic. Disimpan ke folder hasil.")
def user_game():
    u = ask_val("user", "Masukkan username / gamertag", "ProGamer99")
    if not u:
        return
    sec("Pemeriksaan langsung (API platform)")
    with Spinner("Menghubungi platform game"):
        res = _game_checks(u)
    for name, st, url in res:
        if st == "ada":
            print("  [ADA]    %-20s %s" % (name, url))
        elif st == "tidak":
            print("  %s[TIDAK]%s  %-20s" % (D, R, name))
        else:
            print("  %s[?]%s      %-20s (tidak pasti / diblokir)" % (Y, R, name))
    with Spinner("Memuat daftar situs game WhatsMyName"):
        d = wmn_load()
    if d:
        sites = [s for s in d["sites"] if s.get("cat") == "gaming" and s.get("valid", True) and "{account}" in s.get("uri_check", "")]
        wmn_scan(u, sites, "Situs game")
    q_u = q(u)
    open_choices([("Steam: komunitas (cari nama)", "https://steamcommunity.com/search/users/#text=" + q_u), ("Xbox gamertag", "https://xboxgamertag.com/search/" + q_u),
                  ("PlayStation (PSNProfiles)", "https://psnprofiles.com/" + q_u), ("Epic Games / Fortnite tracker", "https://fortnitetracker.com/profile/all/" + q_u),
                  ("Tracker.gg (Valorant, Apex, dll.)", "https://tracker.gg/"), ("NameMC (Minecraft)", "https://namemc.com/profile/" + q_u)], ctx="game")


# ---------- media sosial (X, Snapchat, Spotify, Pinterest, TikTok, Telegram) ----------
def _meta(body):
    t = text_of(body)
    d = {}
    for m in re.finditer(r'<meta\s+[^>]*?>', t, re.I):
        tag = m.group(0)
        k = re.search(r'(?:property|name)\s*=\s*["\']([^"\']+)["\']', tag, re.I)
        c = re.search(r'content\s*=\s*["\']([^"\']*)["\']', tag, re.I)
        if k and c:
            d.setdefault(k.group(1).lower(), _html.unescape(c.group(1)))
    ti = re.search(r"<title[^>]*>(.*?)</title>", t, re.S | re.I)
    d["_title"] = _html.unescape(re.sub(r"\s+", " ", ti.group(1))).strip() if ti else ""
    return d


def _chk_page(url, generic=()):
    r = fetch(url, timeout=14, limit=400000)
    if r.status == 0:
        return "error", {}, r
    m = _meta(r.body)
    if r.status == 200:
        title = (m.get("og:title") or m.get("_title") or "").strip()
        if title and title.lower() not in [g.lower() for g in generic]:
            return "ada", m, r
        return "tidak", m, r
    if r.status in (404, 410):
        return "tidak", m, r
    return "?", m, r


def _show_page(m, keys=("og:title", "og:description", "og:image")):
    for k in keys:
        if m.get(k):
            kv({"og:title": "Judul", "og:description": "Deskripsi", "og:image": "Gambar"}.get(k, k), trunc(m[k], 200))


def plat_telegram(u):
    r = fetch("https://t.me/" + q(u), timeout=14, limit=400000)
    t = text_of(r.body)
    if r.status != 200:
        return ("?" if r.status else "error"), {}
    m = _meta(r.body)
    title = re.search(r'tgme_page_title[^>]*>(?:<span[^>]*>)?([^<]+)', t)
    extra = re.search(r'tgme_page_extra[^>]*>([^<]+)', t)
    if title:
        return "ada", {"Nama": _html.unescape(title.group(1)).strip(), "Info": _html.unescape(extra.group(1)).strip() if extra else "-", "Deskripsi": m.get("og:description", "-")}
    return "tidak", {}


def plat_x(u):
    r = fetch("https://publish.twitter.com/oembed?url=" + q("https://twitter.com/" + u), timeout=14)
    if r.status == 200:
        try:
            o = json.loads(text_of(r.body))
            return "ada", {"Nama": o.get("author_name"), "Profil": o.get("author_url")}
        except Exception:
            return "ada", {}
    return ("tidak" if r.status in (403, 404) else "?" if r.status else "error"), {}


def plat_snap(u):
    st, m, r = _chk_page("https://www.snapchat.com/add/" + q(u), generic=("Snapchat", "Add Friends on Snapchat"))
    return st, {"Judul": m.get("og:title"), "Deskripsi": m.get("og:description")} if st == "ada" else {}


def plat_pin(u):
    st, m, r = _chk_page("https://www.pinterest.com/%s/" % q(u), generic=("Pinterest", "Pinterest - Indonesia", "Pinterest Indonesia"))
    return st, {"Judul": m.get("og:title"), "Deskripsi": m.get("og:description")} if st == "ada" else {}


def plat_tiktok(u):
    st, m, r = _chk_page("https://www.tiktok.com/@" + q(u), generic=("TikTok - Make Your Day", "TikTok"))
    return st, {"Judul": m.get("og:title"), "Deskripsi": m.get("og:description")} if st == "ada" else {}


def plat_spotify(u):
    r = fetch("https://open.spotify.com/oembed?url=" + q("https://open.spotify.com/user/" + u), timeout=14)
    if r.status == 200:
        try:
            o = json.loads(text_of(r.body))
            return "ada", {"Judul": o.get("title"), "Penyedia": o.get("provider_name")}
        except Exception:
            return "ada", {}
    return ("tidak" if r.status in (400, 404) else "?" if r.status else "error"), {}


SOSMED = [("Telegram", plat_telegram, "https://t.me/{u}"), ("X (Twitter)", plat_x, "https://x.com/{u}"),
          ("Snapchat", plat_snap, "https://www.snapchat.com/add/{u}"), ("Pinterest", plat_pin, "https://www.pinterest.com/{u}/"),
          ("TikTok", plat_tiktok, "https://www.tiktok.com/@{u}"), ("Spotify (pengguna)", plat_spotify, "https://open.spotify.com/user/{u}")]


@module("sosmed_cek", "Cek keberadaan akun di Telegram, X (Twitter), Snapchat, Pinterest, TikTok, dan Spotify lewat halaman publik masing-masing.",
        "Input: username (Spotify: ID pengguna). Hasil: ada / tidak / tidak pasti + nama dan deskripsi bila tersedia. WeChat & GetContact: panduan.")
def sosmed_cek():
    u = ask_val("user", "Masukkan username", "budi123")
    if not u:
        return
    with Spinner("Memeriksa 6 platform"):
        res = par([(n, (lambda f=f: f(u))) for n, f, _ in SOSMED], workers=6)
    sec("Hasil untuk '%s'" % u)
    rows = []
    for name, fn, tpl in SOSMED:
        r = res.get(name)
        if isinstance(r, Exception) or r is None:
            st, info = "error", {}
        else:
            st, info = r
        url = tpl.replace("{u}", q(u))
        if st == "ada":
            print("  [ADA]    %-20s %s" % (name, url))
            for k, v in (info or {}).items():
                if v:
                    kv("   " + k, trunc(str(v), 160))
            rows.append((name, url))
        elif st == "tidak":
            print("  %s[TIDAK]%s  %-20s" % (D, R, name))
        elif st == "error":
            print("  %s[GAGAL]%s  %-20s tidak bisa terhubung" % (Y, R, name))
        else:
            print("  %s[?]%s      %-20s tidak pasti (diblokir / wajib login)" % (Y, R, name))
    sec("WeChat dan GetContact")
    p_info("WeChat tidak punya pencarian akun publik di web. Cara resmi: aplikasi WeChat > Kontak > Tambah Teman > ketik WeChat ID atau nomor HP.")
    p_info("GetContact tidak punya API/pencarian web publik; hanya lewat aplikasinya (kontak yang sama dibagikan pengguna lain). Giga OSINT tidak memalsukan hasilnya.")
    p_info("Catatan: halaman publik platform bisa berubah; hasil 'TIDAK' bisa juga berarti akun dikunci atau memblokir pemeriksaan otomatis.")
    if rows:
        open_choices(rows, ctx="sosmed")


# ---------- saluran WhatsApp ----------
@module("wa_channel", "Memeriksa apakah sebuah Saluran (Channel) WhatsApp ada, lewat halaman publiknya: nama, deskripsi, dan gambar.",
        "Input: tautan saluran (whatsapp.com/channel/XXXX) atau kode saluran. Hasil: ada / tidak terdeteksi. Nomor HP tidak bisa diperiksa begini.")
def wa_channel():
    v = ask("Tempel tautan saluran atau kodenya (contoh: https://whatsapp.com/channel/0029Va...)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    m = re.search(r"channel/([A-Za-z0-9_\-]{10,60})", v) or re.fullmatch(r"([A-Za-z0-9_\-]{10,60})", v.strip())
    if not m:
        p_err("Tautan/kode tidak dikenali. Bentuk benar: https://whatsapp.com/channel/<kode>")
        return
    code = m.group(1)
    url = "https://whatsapp.com/channel/" + code
    with Spinner("Membuka halaman saluran"):
        r = fetch(url, timeout=18, limit=400000)
    if r.status == 0:
        explain_http(0, "WhatsApp", r.err)
        return
    meta = _meta(r.body)
    title = (meta.get("og:title") or "").strip()
    sec("Saluran %s" % code)
    kv("HTTP", r.status)
    if r.status == 200 and title and title.lower() not in ("whatsapp", "whatsapp channel", "whatsapp web"):
        p_ok("Saluran TERDETEKSI ADA.")
        kv("Nama", title)
        kv("Deskripsi", trunc(meta.get("og:description", "-"), 220))
        kv("Gambar", meta.get("og:image", "-"))
    elif r.status in (404, 410) or (r.status == 200 and not title):
        p_warn("Saluran tidak terdeteksi (kemungkinan kode salah, saluran dihapus, atau WhatsApp menyembunyikan metadata).")
    else:
        p_warn("Respons tidak pasti (HTTP %s). Coba lagi atau buka tautan di aplikasi WhatsApp." % r.status)
    p_info("Pemeriksaan ini membaca metadata publik halaman; format WhatsApp bisa berubah sewaktu-waktu.")
    open_choices([("Halaman saluran", url)], ctx="whatsapp")


# ---------- Discord ----------
@module("discord_cek", "Membaca undangan server Discord (nama, jumlah anggota, saluran) atau menghitung tanggal pembuatan dari sebuah ID Discord.",
        "Input: kode/URL undangan (discord.gg/xxxx) ATAU ID angka 17-20 digit. Tanpa API key.")
def discord_cek():
    v = ask("Masukkan undangan (discord.gg/xxxx) atau ID angka  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = v.strip()
    if re.fullmatch(r"\d{15,21}", v):
        ms = (int(v) >> 22) + 1420070400000
        try:
            dt = datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc)
        except (OverflowError, OSError, ValueError):
            p_err("ID itu tidak menghasilkan tanggal yang masuk akal.")
            return
        sec("ID Discord %s" % v)
        kv("Dibuat (UTC)", dt.strftime("%Y-%m-%d %H:%M:%S"))
        kv("Dibuat (lokal)", dt.astimezone().strftime("%Y-%m-%d %H:%M:%S"))
        p_info("Berlaku untuk ID pengguna, server, saluran, dan pesan (semuanya memakai format snowflake).")
        return
    code = re.sub(r"^(https?://)?(www\.)?(discord\.gg|discord(app)?\.com/invite)/", "", v).split("?")[0].strip("/")
    if not re.fullmatch(r"[A-Za-z0-9\-]{2,40}", code):
        p_err("Format tidak dikenali. Contoh: discord.gg/abc123 atau ID 18 digit.")
        return
    with Spinner("Membaca undangan"):
        o = jget("https://discord.com/api/v10/invites/%s?with_counts=true&with_expiration=true" % q(code), "Discord", quiet=True)
        r = fetch("https://discord.com/api/v10/invites/%s?with_counts=true" % q(code), timeout=15) if o is None else None
    if o is None:
        if r is not None and r.status == 404:
            p_warn("Undangan tidak ditemukan / sudah kedaluwarsa (HTTP 404).")
        else:
            explain_http(r.status if r else 0, "Discord", r.err if r else "")
        return
    g = o.get("guild") or {}
    sec("Undangan %s" % code)
    kv("Server", g.get("name"))
    kv("ID server", g.get("id"))
    kv("Deskripsi", g.get("description"))
    kv("Anggota (perkiraan)", o.get("approximate_member_count"))
    kv("Sedang online", o.get("approximate_presence_count"))
    kv("Saluran undangan", (o.get("channel") or {}).get("name"))
    kv("Pengundang", (o.get("inviter") or {}).get("username"))
    kv("Kedaluwarsa", o.get("expires_at") or "tidak pernah")
    kv("Fitur", ", ".join((g.get("features") or [])[:8]))
    if g.get("id"):
        ms = (int(g["id"]) >> 22) + 1420070400000
        kv("Server dibuat", datetime.datetime.fromtimestamp(ms / 1000.0, tz=datetime.timezone.utc).strftime("%Y-%m-%d"))


# ---------- Hacker News ----------
@module("hn_user", "Profil pengguna Hacker News (karma, tanggal bergabung, tentang) atau 10 cerita teratas saat ini lewat API resmi.",
        "Input: username HN (contoh: pg), atau Enter untuk cerita teratas. Tanpa API key.")
def hn_user():
    u = ask("Username Hacker News (contoh: pg)  Enter = 10 cerita teratas, 0 = batal")
    if u is None or u == "0":
        return
    base = "https://hacker-news.firebaseio.com/v0/"
    if not u:
        with Spinner("Mengambil cerita teratas"):
            ids = jget(base + "topstories.json", "Hacker News") or []
            items = par([(str(i), (lambda i=i: jget(base + "item/%s.json" % i, "HN", quiet=True))) for i in ids[:10]], 10)
        sec("Cerita teratas Hacker News")
        for i in ids[:10]:
            it = items.get(str(i))
            if isinstance(it, dict):
                print("  %s%4s%s  %s%s%s  %s(%s komentar)%s\n        %s%s%s" % (Y, it.get("score"), R, W, trunc(it.get("title", ""), 90), R, D, it.get("descendants", 0), R, BL, it.get("url") or "https://news.ycombinator.com/item?id=%s" % i, R))
        return
    if not re.fullmatch(r"[A-Za-z0-9_\-]{2,15}", u):
        p_err("Username HN hanya huruf/angka/_/-, 2 sampai 15 karakter.")
        return
    with Spinner("Mencari pengguna"):
        o = jget(base + "user/%s.json" % q(u), "Hacker News", quiet=True)
    if not o:
        p_warn("Pengguna '%s' tidak ditemukan di Hacker News." % u)
        return
    sec("Hacker News: %s" % o.get("id"))
    kv("Bergabung", fmt_epoch(o.get("created")))
    kv("Karma", o.get("karma"))
    kv("Jumlah kiriman", len(o.get("submitted") or []))
    kv("Tentang", trunc(re.sub(r"<[^>]+>", " ", _html.unescape(o.get("about") or "-")), 400))
    subs = (o.get("submitted") or [])[:6]
    items = par([(str(i), (lambda i=i: jget(base + "item/%s.json" % i, "HN", quiet=True))) for i in subs], 6)
    for i in subs:
        it = items.get(str(i))
        if isinstance(it, dict) and (it.get("title") or it.get("text")):
            print("  %s%s%s  %s" % (Y, fmt_epoch(it.get("time")), R, trunc(it.get("title") or re.sub(r"<[^>]+>", " ", _html.unescape(it.get("text", ""))), 100)))
    open_choices([("Profil HN", "https://news.ycombinator.com/user?id=" + q(u))], ctx="hn")


# ---------- Blogger ----------
@module("blogger_cek", "Memeriksa blog Blogger/Blogspot: judul, penulis, jumlah tulisan, dan tulisan terbaru lewat feed resmi.",
        "Input: nama blog (contoh: googleblog) atau URL blogspot. Hasil: info blog dan 5 tulisan terakhir. Tanpa API key.")
def blogger_cek():
    v = ask("Masukkan nama blog atau URL blogspot (contoh: googleblog)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    m = re.search(r"([A-Za-z0-9\-]+)\.blogspot\.", v) or re.fullmatch(r"([A-Za-z0-9\-]+)", v.strip())
    if not m:
        p_err("Bukan nama blogspot yang valid. Contoh: googleblog atau https://googleblog.blogspot.com")
        return
    name = m.group(1)
    with Spinner("Membaca feed blog"):
        r = fetch("https://%s.blogspot.com/feeds/posts/default?alt=json&max-results=5" % name, timeout=18)
    if r.status == 404:
        p_warn("Blog '%s.blogspot.com' tidak ditemukan." % name)
        return
    if r.status != 200:
        explain_http(r.status, "Blogger", r.err)
        return
    try:
        f = json.loads(text_of(r.body)).get("feed") or {}
    except Exception:
        p_warn("Balasan bukan feed JSON (blog mungkin privat atau memakai domain sendiri).")
        return
    sec("Blog %s" % name)
    t = lambda x: (x or {}).get("$t") if isinstance(x, dict) else x
    kv("Judul", t(f.get("title")))
    kv("Penulis", ", ".join(t((a or {}).get("name")) or "-" for a in f.get("author", [])[:3]))
    kv("Diperbarui", t(f.get("updated")))
    kv("Jumlah tulisan", t(f.get("openSearch$totalResults")))
    for e in (f.get("entry") or [])[:5]:
        link = next((l.get("href") for l in e.get("link", []) if l.get("rel") == "alternate"), "")
        print("  %s%s%s  %s%s%s\n      %s%s%s" % (Y, (t(e.get("published")) or "")[:10], R, W, trunc(t(e.get("title")) or "-", 90), R, BL, link, R))
    open_choices([("Buka blog", "https://%s.blogspot.com/" % name)], ctx="blogger")


# ---------- Twitch ----------
MOD_API["twitch_user"] = "Butuh Client ID dan Client Secret gratis dari https://dev.twitch.tv/console (daftarkan aplikasi baru)."


@module("twitch_user", "Profil kanal Twitch: tanggal dibuat, tipe, deskripsi, dan status siaran langsung (API resmi Helix).",
        "Input: nama pengguna Twitch. Butuh Client ID + Secret gratis (disimpan lokal). Hasil: profil dan apakah sedang live.")
def twitch_user():
    u = ask_val("user", "Masukkan nama pengguna Twitch", "ninja")
    if not u:
        return
    cid = api_key("twitch_id", "Twitch Client ID", "https://dev.twitch.tv/console", env="TWITCH_CLIENT_ID")
    sc = api_key("twitch_secret", "Twitch Client Secret", "https://dev.twitch.tv/console", env="TWITCH_CLIENT_SECRET") if cid else ""
    if not (cid and sc):
        p_warn("Client ID dan Secret keduanya diperlukan.")
        return
    with Spinner("Meminta token dan data Twitch"):
        tk = fetch("https://id.twitch.tv/oauth2/token", method="POST", data="client_id=%s&client_secret=%s&grant_type=client_credentials" % (q(cid), q(sc)),
                   headers={"Content-Type": "application/x-www-form-urlencoded"}, timeout=15)
        tok = ""
        try:
            tok = json.loads(text_of(tk.body)).get("access_token", "")
        except Exception:
            pass
        if not tok:
            explain_http(tk.status or 401, "Twitch (token)", tk.err)
            return
        hd = {"Client-Id": cid, "Authorization": "Bearer " + tok}
        us = jget("https://api.twitch.tv/helix/users?login=" + q(u), "Twitch", headers=hd)
        stv = jget("https://api.twitch.tv/helix/streams?user_login=" + q(u), "Twitch", headers=hd, quiet=True)
    d = ((us or {}).get("data") or [None])[0]
    if not d:
        if us is not None:
            p_warn("Kanal '%s' tidak ditemukan di Twitch." % u)
        return
    sec("Twitch: %s" % d.get("display_name"))
    for k in ("id", "login", "type", "broadcaster_type", "created_at", "description"):
        kv(k, d.get(k))
    live = ((stv or {}).get("data") or [None])[0]
    if live:
        p_ok("SEDANG LIVE: %s  (%s penonton, game: %s)" % (live.get("title"), live.get("viewer_count"), live.get("game_name")))
    else:
        p_info("Saat ini tidak sedang siaran langsung.")
    open_choices([("Kanal Twitch", "https://www.twitch.tv/" + q(u))], ctx="twitch")


# ---------- YouTube ----------
MOD_API["youtube_channel"] = "Butuh API key gratis YouTube Data API v3 dari https://console.cloud.google.com/apis/library/youtube.googleapis.com (kuota harian gratis)."


@module("youtube_channel", "Statistik kanal YouTube: pelanggan, total tayangan, jumlah video, negara, tanggal dibuat (API resmi).",
        "Input: @handle, ID kanal (UC...), atau nama kanal. Butuh API key gratis. Hasil: profil dan statistik kanal.")
def youtube_channel():
    v = ask("Masukkan @handle / ID kanal / nama kanal (contoh: @MrBeast)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    v = v.strip()
    key = api_key("youtube", "YouTube Data API", "https://console.cloud.google.com/apis/library/youtube.googleapis.com")
    if not key:
        p_warn("Tanpa API key fitur ini tidak bisa berjalan.")
        return
    base = "https://www.googleapis.com/youtube/v3/"
    part = "snippet,statistics"
    with Spinner("Menanyakan YouTube"):
        if re.fullmatch(r"UC[\w\-]{22}", v):
            o = jget(base + "channels?part=%s&id=%s&key=%s" % (part, v, key), "YouTube")
        elif v.startswith("@"):
            o = jget(base + "channels?part=%s&forHandle=%s&key=%s" % (part, q(v), key), "YouTube")
        else:
            s = jget(base + "search?part=snippet&type=channel&maxResults=1&q=%s&key=%s" % (q(v), key), "YouTube")
            cid = (((s or {}).get("items") or [{}])[0].get("snippet") or {}).get("channelId") if s else None
            o = jget(base + "channels?part=%s&id=%s&key=%s" % (part, cid, key), "YouTube") if cid else None
    items = (o or {}).get("items") or []
    if not items:
        if o is not None:
            p_warn("Kanal tidak ditemukan.")
        return
    c = items[0]
    sn, st = c.get("snippet") or {}, c.get("statistics") or {}
    sec("YouTube: %s" % sn.get("title"))
    kv("ID kanal", c.get("id"))
    kv("Handle", sn.get("customUrl"))
    kv("Dibuat", (sn.get("publishedAt") or "")[:10])
    kv("Negara", sn.get("country"))
    kv("Pelanggan", "disembunyikan" if st.get("hiddenSubscriberCount") else st.get("subscriberCount"))
    kv("Total tayangan", st.get("viewCount"))
    kv("Jumlah video", st.get("videoCount"))
    kv("Deskripsi", trunc(re.sub(r"\s+", " ", sn.get("description") or "-"), 300))
    open_choices([("Kanal YouTube", "https://www.youtube.com/channel/" + c.get("id", ""))], ctx="youtube")


# ---------- pencarian web alternatif ----------
@module("cari_web_bebas", "Pencarian tanpa pelacak: DuckDuckGo Instant Answer (ringkasan fakta) dan Marginalia (situs kecil/independen).",
        "Input: kata kunci. Pilih 1 (DuckDuckGo ringkasan) atau 2 (Marginalia). Tanpa API key.")
def cari_web_bebas():
    kw = ask("Masukkan kata kunci  (0 = batal)")
    if kw is None or kw == "0" or not kw:
        return
    c = ask("Pilih sumber: 1 = DuckDuckGo ringkasan   2 = Marginalia (situs independen)   Enter = keduanya")
    if c == "0" or c is None:
        return
    if c in ("", "1"):
        with Spinner("DuckDuckGo"):
            o = jget("https://api.duckduckgo.com/?q=%s&format=json&no_html=1&skip_disambig=1" % q(kw), "DuckDuckGo", quiet=True)
        sec("DuckDuckGo: ringkasan")
        if o and (o.get("AbstractText") or o.get("RelatedTopics")):
            kv("Judul", o.get("Heading"))
            kv("Ringkasan", trunc(o.get("AbstractText") or "-", 500))
            kv("Sumber", o.get("AbstractURL"))
            for t in (o.get("RelatedTopics") or [])[:6]:
                if isinstance(t, dict) and t.get("Text"):
                    print("  %s%s%s %s\n      %s%s%s" % (MG, GL["bullet"], R, trunc(t["Text"], 110), BL, t.get("FirstURL", ""), R))
        else:
            p_info("DuckDuckGo tidak punya ringkasan instan untuk kata ini (normal untuk pencarian umum).")
    if c in ("", "2"):
        with Spinner("Marginalia"):
            o = jget("https://api.marginalia.nu/public/search/%s?count=8" % q(kw), "Marginalia", quiet=True)
        sec("Marginalia: situs independen")
        res = (o or {}).get("results") or []
        if res:
            for r in res[:8]:
                print("  %s%s%s\n      %s%s%s  %s%s%s" % (W, trunc(re.sub(r"<[^>]+>", "", r.get("title", "")), 90), R, BL, r.get("url"), R, D, trunc(re.sub(r"<[^>]+>", "", r.get("description", "")), 90), R))
        else:
            p_info("Marginalia tidak menjawab lewat API; gunakan tautan di bawah.")
    open_choices([("DuckDuckGo", "https://duckduckgo.com/?q=" + q(kw)), ("Marginalia Search", "https://search.marginalia.nu/search?query=" + q(kw)),
                  ("Brave Search", "https://search.brave.com/search?q=" + q(kw))], ctx="cari")


# ---------- pajak kendaraan (plat -> situs resmi) ----------
PAJAK_SITES = {
    "DKI Jakarta": "https://samsat-pkb2.jakarta.go.id/", "Jawa Barat": "https://bapenda.jabarprov.go.id/e-samsat-jabar", "Banten": "https://infopkb.bantenprov.go.id/",
    "Jawa Tengah": None, "DI Yogyakarta": "https://samsatsleman.jogjaprov.go.id/cek/pajak", "Jawa Timur": "https://bapenda.jatimprov.go.id/info/pkb",
    "Bali": "https://portal.bpdbali.id/infosamsat/", "NTB": None, "NTT": "https://samsat.bpdntt.co.id/", "Aceh": "https://esamsat.acehprov.go.id/",
    "Sumatera Utara": "https://bapenda.sumutprov.go.id/website/pajak#/pkb/info-pkb", "Sumatera Barat": "https://bapenda.sumbarprov.go.id/content/info_pajak_kendaraan",
    "Riau": "https://bapenda.riau.go.id/dashboard/layanan/infopajak", "Kepulauan Riau": None, "Jambi": "https://jambisamsat.net/infopkb.html",
    "Sumatera Selatan": None, "Bangka Belitung": "https://samsat-sungailiat.babelprov.go.id/layanan", "Bengkulu": "https://pusako.bengkuluprov.go.id/infopajak",
    "Lampung": None, "Kalimantan Barat": "https://jipp.kalbarprov.go.id/inovasi/view/173", "Kalimantan Tengah": "https://pajak.samsatkalteng.com/",
    "Kalimantan Selatan": "https://bapenda.kalselprov.go.id/", "Kalimantan Timur": None, "Kalimantan Utara": "https://dkisp.tarakankota.go.id/esamsat-kalimantan-utara/",
    "Sulawesi Utara": "https://bapenda.sulutprov.go.id/cekpajak", "Gorontalo": "https://gorontaloprov.go.id/esamsat", "Sulawesi Tengah": "https://bapenda.sultengprov.go.id/pkb",
    "Sulawesi Selatan": "https://bapenda.sulselprov.go.id/", "Sulawesi Tenggara": "https://sultraprov.go.id/esamsat", "Sulawesi Barat": "https://web.bpkpd.sulbarprov.go.id/",
    "Maluku": "https://esamsat.malukuprov.go.id/kiosk/kiosk.aspx", "Maluku Utara": "https://esamsat.malutprov.go.id/", "Papua": "http://180.250.219.60:81/cekpajak/",
    "Papua Barat": "https://samsatdigital.id/"}
PLAT_PROV = {"B": "DKI Jakarta", "A": "Banten", "D": "Jawa Barat", "E": "Jawa Barat", "F": "Jawa Barat", "T": "Jawa Barat", "Z": "Jawa Barat",
             "G": "Jawa Tengah", "H": "Jawa Tengah", "K": "Jawa Tengah", "R": "Jawa Tengah", "AA": "Jawa Tengah", "AD": "Jawa Tengah", "AB": "DI Yogyakarta",
             "L": "Jawa Timur", "M": "Jawa Timur", "N": "Jawa Timur", "P": "Jawa Timur", "S": "Jawa Timur", "W": "Jawa Timur", "AE": "Jawa Timur", "AG": "Jawa Timur",
             "DK": "Bali", "DR": "NTB", "EA": "NTB", "DH": "NTT", "EB": "NTT", "ED": "NTT", "BL": "Aceh", "BB": "Sumatera Utara", "BK": "Sumatera Utara",
             "BA": "Sumatera Barat", "BM": "Riau", "BP": "Kepulauan Riau", "BH": "Jambi", "BG": "Sumatera Selatan", "BN": "Bangka Belitung", "BD": "Bengkulu",
             "BE": "Lampung", "KB": "Kalimantan Barat", "KH": "Kalimantan Tengah", "DA": "Kalimantan Selatan", "KT": "Kalimantan Timur", "KU": "Kalimantan Utara",
             "DB": "Sulawesi Utara", "DL": "Sulawesi Utara", "DM": "Gorontalo", "DN": "Sulawesi Tengah", "DT": "Sulawesi Tenggara", "DD": "Sulawesi Selatan",
             "DC": "Sulawesi Barat", "DE": "Maluku", "DG": "Maluku Utara", "PA": "Papua", "PB": "Papua Barat"}
PLAT_EXTRA = {"B": "Plat B juga dipakai di Depok, Bekasi, dan Tangerang: pajak mengikuti provinsi tempat kendaraan terdaftar (lihat STNK).",
              "PA": "Papua kini dimekarkan; sebagian daerah memakai Samsat Digital (samsatdigital.id).",
              "PB": "Provinsi pemekaran di Papua memakai Samsat Digital (samsatdigital.id)."}
SAMSAT_APP = ("Samsat Digital Nasional (aplikasi SIGNAL)", "https://play.google.com/store/search?q=SIGNAL%20Samsat%20Digital%20Nasional&c=apps")


@module("pajak_kendaraan", "Dari nomor plat: provinsi asal, lalu situs resmi Samsat/Bapenda provinsi untuk cek status pajak. Tekan o untuk membuka di browser.",
        "Input: plat, contoh B 1234 ABC. Hasil: provinsi, situs resmi cek pajak, dan tips. o1 = buka situs resmi di browser.")
def pajak_kendaraan():
    raw = ask("Masukkan plat nomor (contoh: B 1234 ABC atau AB1234CD)  (0 = batal)")
    if raw is None or raw == "0" or not raw:
        return
    m = re.match(r"^([A-Za-z]{1,2})\s*(\d{1,4})\s*([A-Za-z]{0,3})$", raw.strip())
    if not m:
        p_err("Format plat tidak dikenali. Contoh yang benar: B 1234 ABC atau AB 1234 CD")
        return
    code, num, suf = m.group(1).upper(), m.group(2), m.group(3).upper()
    prov = PLAT_PROV.get(code)
    sec("Plat %s %s %s" % (code, num, suf))
    kv("Kode wilayah", code)
    kv("Wilayah asal", PLAT.get(code, "tidak ada di daftar bawaan"))
    kv("Provinsi pajak", prov or "tidak diketahui")
    if code in ("CD", "CC", "RI"):
        p_warn("Kode %s untuk kendaraan korps diplomatik/konsuler/dinas pejabat: tidak ada cek pajak publik." % code)
        return
    rows = []
    url = PAJAK_SITES.get(prov) if prov else None
    if url:
        p_ok("Situs resmi cek pajak %s ditemukan." % prov)
        rows.append(("Situs resmi pajak kendaraan %s" % prov, url))
    else:
        p_warn("Alamat khusus untuk %s belum ada di daftar bawaan; gunakan pencarian situs resmi (domain .go.id) di bawah." % (prov or "kode ini"))
    if code in PLAT_EXTRA:
        p_info(PLAT_EXTRA[code])
    qs = "cek pajak kendaraan %s e-samsat resmi go.id" % (prov or code)
    rows.append(("Cari situs resmi %s lewat DuckDuckGo (pilih yang berakhiran .go.id)" % (prov or code), "https://duckduckgo.com/?q=" + q(qs)))
    rows.append(SAMSAT_APP)
    p_info("Biasanya diminta nomor plat penuh dan beberapa digit terakhir nomor rangka (lihat STNK/BPKB). Pajak hanya bisa dibayar di kanal resmi.")
    p_warn("Hati-hati situs tiruan: pastikan alamat berakhiran .go.id (atau aplikasi resmi SIGNAL). Daftar alamat dapat berubah; periksa kembali di situs Bapenda provinsi.")
    print()
    for ln in hint_bar([("o1", "buka situs resmi di browser"), ("1", "pratinjau di terminal"), ("0", "selesai")]):
        print(ln)
    open_choices(rows, ctx="pajak")


# ---------- kartu HP / SIM ----------
IMSI_MNC = {"01": "Indosat Ooredoo", "08": "AXIS (kini XL Axiata)", "09": "Smartfren", "10": "Telkomsel", "11": "XL Axiata", "21": "Indosat Ooredoo", "28": "Fren (Smartfren)", "89": "Tri (Indosat Ooredoo Hutchison)"}
ICCID_CC = {"62": "Indonesia", "60": "Malaysia", "65": "Singapura", "66": "Thailand", "84": "Vietnam", "63": "Filipina", "91": "India", "81": "Jepang", "82": "Korea Selatan",
            "86": "Tiongkok", "61": "Australia", "44": "Inggris", "49": "Jerman", "33": "Prancis", "1": "AS/Kanada", "7": "Rusia", "971": "UEA", "966": "Arab Saudi"}


def sim_decode():
    v = ask("Masukkan ICCID (19-20 digit, tercetak di kartu SIM) atau IMSI (15 digit)  (0 = batal)")
    if v is None or v == "0" or not v:
        return
    d = re.sub(r"[\s\-]", "", v)
    if not d.isdigit():
        p_err("Hanya angka yang diperbolehkan (tanpa huruf).")
        return
    if len(d) in (19, 20):
        sec("ICCID %s" % d)
        kv("Awalan industri (MII)", d[:2] + ("  (benar: 89 = telekomunikasi)" if d[:2] == "89" else "  (bukan 89: tidak lazim)"), 30)
        cc = next((c for c in (d[2:5], d[2:4], d[2:3]) if c in ICCID_CC), None)
        kv("Kode negara", "%s  %s" % (cc, ICCID_CC[cc]) if cc else d[2:4] + "  (tidak ada di daftar)", 30)
        if cc == "62":
            iss = d[4:6]
            kv("Penerbit (perkiraan)", IMSI_MNC.get(iss, "tidak dikenal (%s)" % iss), 30)
        kv("Digit periksa Luhn", "VALID" if luhn_ok(d) else "TIDAK VALID (ada angka salah ketik)", 30)
        p_info("ICCID adalah nomor seri fisik kartu SIM, bukan nomor telepon dan bukan IMSI.")
    elif len(d) == 15:
        sec("IMSI %s" % d)
        mcc, mnc2 = d[:3], d[3:5]
        kv("MCC (kode negara seluler)", mcc + ("  Indonesia" if mcc == "510" else ""), 30)
        kv("MNC (jaringan)", "%s  %s" % (mnc2, IMSI_MNC.get(mnc2, "tidak dikenal")) if mcc == "510" else d[3:6], 30)
        kv("MSIN (nomor pelanggan)", d[5:] + "  (rahasia; jangan dibagikan)", 30)
        p_warn("IMSI = identitas pelanggan di jaringan. Jangan dibagikan ke pihak yang tidak dikenal.")
    else:
        p_err("Panjang tidak cocok: ICCID 19-20 digit, IMSI 15 digit (kamu memasukkan %d)." % len(d))


@module("kartu_hp_lengkap", "Cek kartu HP: operator dari prefiks nomor, format nasional/internasional, tipe nomor, pembaca ICCID/IMSI kartu SIM, dan cara cek registrasi resmi.",
        "Pilih 1 analisis nomor, 2 baca ICCID/IMSI, 3 cara cek NIK terdaftar. Nomor contoh: 0812... atau +62812... Tanpa API key.")
def kartu_hp_lengkap():
    c = ask("Pilih: 1 = Analisis nomor HP   2 = Baca ICCID/IMSI kartu SIM   3 = Cara cek registrasi/NIK resmi   (0 = batal)")
    if c is None or c == "0":
        return
    if c == "2":
        sim_decode()
        return
    if c == "3":
        sec("Cek registrasi kartu dan NIK (jalur resmi)")
        p_info("Giga OSINT tidak punya akses ke data registrasi (itu data pribadi milik operator dan Dukcapil), jadi tidak bisa menampilkan nama pemilik nomor.")
        for step in ("Buka aplikasi resmi operatormu: MyTelkomsel, myIM3 / Bima+, myXL, atau aplikasi AXIS / by.U / Smartfren.",
                     "Cari menu profil atau 'Registrasi / Cek Nomor' untuk melihat NIK terdaftar (sebagian disensor).",
                     "Bila ada nomor yang tidak kamu kenal memakai NIK-mu, ajukan blokir lewat Layanan Pelanggan operator atau layanan pengaduan resmi pemerintah.",
                     "Waspada SMS/telepon yang meminta kode OTP atau foto KTP: itu modus penipuan."):
            p_info(step)
        open_choices([("Cari cara resmi cek NIK terdaftar (DuckDuckGo)", "https://duckduckgo.com/?q=" + q("cara cek NIK terdaftar di nomor HP resmi operator")),
                      ("Komdigi (Kementerian Komunikasi dan Digital)", "https://www.komdigi.go.id/"), ("Aduan konten / penipuan (aduannomor)", "https://aduannomor.id/")], ctx="sim")
        return
    p = ask_val("phone", "Masukkan nomor HP", "081234567890 atau +6281234567890")
    if not p:
        return
    d = re.sub(r"\D", "", p)
    nat = id_prefix(d) if p.startswith("+62") or d.startswith("62") or d.startswith("0") else None
    sec("Nomor %s" % p)
    kv("Format E.164", p, 30)
    if nat:
        kv("Format nasional", nat, 30)
        op = ID_OPS.get(nat[:4])
        kv("Operator (menurut prefiks)", ("%s  (merek %s)" % op) if op else "prefiks %s tidak ada di daftar bawaan" % nat[:4], 30)
        if nat[:2] == "08":
            kv("Tipe", "Seluler", 30)
        else:
            area = next((ID_AREA[k] for k in sorted(ID_AREA, key=len, reverse=True) if nat[1:].startswith(k)), None)
            kv("Tipe", "Telepon rumah/kantor (tetap)" if area else "tidak diketahui", 30)
            kv("Area", area or "-", 30)
        p_info("Prefiks hanya menunjukkan operator PENERBIT awal. Nomor bisa pindah operator (MNP), jadi operator sekarang bisa berbeda.")
    pn = None
    try:
        import phonenumbers as pn
        from phonenumbers import carrier, geocoder, timezone as pntz
        num = pn.parse(p, None)
        kv("Valid (pustaka libphonenumber)", "YA" if pn.is_valid_number(num) else "TIDAK", 30)
        kv("Mungkin (panjang cocok)", "YA" if pn.is_possible_number(num) else "TIDAK", 30)
        kv("Jenis", PN_TYPES.get(pn.number_type(num), "tidak diketahui"), 30)
        kv("Operator (data penerbit)", carrier.name_for_number(num, "id") or "-", 30)
        kv("Wilayah", geocoder.description_for_number(num, "id") or "-", 30)
        kv("Zona waktu", ", ".join(pntz.time_zones_for_number(num)) or "-", 30)
    except ImportError:
        p_info("Pustaka 'phonenumbers' belum terpasang: pasang dengan '%s -m pip install phonenumbers' untuk validasi, wilayah, dan zona waktu." % sys.executable)
    except Exception as e:
        p_warn("Pustaka phonenumbers tidak bisa menguraikan nomor ini: %s" % e)
    e164 = re.sub(r"\D", "", p)
    sec("Jejak publik nomor ini")
    p_info("WhatsApp: tautan wa.me terbuka untuk nomor apa pun, jadi TIDAK bisa membuktikan akun itu ada. Hanya aplikasi WhatsApp yang bisa memastikan.")
    p_info("GetContact / Truecaller: data dari buku kontak pengguna lain, hanya lewat aplikasinya masing-masing.")
    nat_q = (nat or "")
    open_choices([("WhatsApp (wa.me)", "https://wa.me/" + e164), ("Cari nomor di Google (tanda kutip)", 'https://www.google.com/search?q=' + q('"%s" OR "+%s"' % (nat_q or e164, e164))),
                  ("Truecaller", "https://www.truecaller.com/search/id/" + e164), ("Sync.ME", "https://sync.me/search/?number=" + q("+" + e164)),
                  ("Cek data bocor (Have I Been Pwned - email)", "https://haveibeenpwned.com/")], ctx="telepon")


# ---------- bioskop ----------
MOD_API["bioskop_jadwal"] = "Opsional: API key gratis TMDB (https://www.themoviedb.org/settings/api) untuk daftar film yang sedang tayang di Indonesia."
BIOSKOP = [("XXI (Cinema 21)", "https://www.cinema21.co.id/"), ("CGV Indonesia", "https://www.cgv.id/"), ("Cinepolis Indonesia", "https://www.cinepolis.co.id/"),
           ("TIX ID (beli tiket & jadwal)", "https://www.tix.id/")]


@module("bioskop_jadwal", "Jadwal bioskop: film yang sedang tayang di Indonesia (TMDB) dan tautan resmi jaringan bioskop (XXI, CGV, Cinepolis, TIX ID).",
        "Input: nama kota (contoh: Bandung). Hasil: film tayang saat ini + tautan jadwal resmi + pencarian jadwal kotamu. Tekan o1 untuk membuka.")
def bioskop_jadwal():
    kota = ask("Nama kota (contoh: Bandung)  Enter = lewati, 0 = batal")
    if kota is None or kota == "0":
        return
    kota = kota.strip()
    key = key_peek("tmdb")
    if key:
        with Spinner("Mengambil film yang sedang tayang"):
            o = jget("https://api.themoviedb.org/3/movie/now_playing?region=ID&language=id-ID&page=1&api_key=" + q(key), "TMDB")
        res = (o or {}).get("results") or []
        if res:
            sec("Sedang tayang di Indonesia (TMDB)")
            for i, f in enumerate(res[:15], 1):
                print("  %s %s%s%s  %s%s  nilai %s%s" % (num_tag(i), W, trunc(f.get("title", ""), 50), R, D, f.get("release_date", "-"), f.get("vote_average", "-"), R))
        elif o is not None:
            p_warn("TMDB tidak mengembalikan daftar film.")
    else:
        p_info("Daftar film otomatis aktif bila kamu menyimpan key TMDB gratis (Pengaturan > Kunci API, nama: tmdb). Jadwal per bioskop tetap lewat tautan resmi di bawah.")
    where = (" " + kota) if kota else ""
    rows = list(BIOSKOP) + [("Cari jadwal bioskop%s (DuckDuckGo)" % where, "https://duckduckgo.com/?q=" + q("jadwal bioskop" + where + " hari ini")),
                            ("Cari film sedang tayang (Google)", "https://www.google.com/search?q=" + q("film bioskop sedang tayang" + where))]
    p_info("Jadwal dan harga tiket berubah tiap hari dan per cabang; sumber paling akurat adalah situs/aplikasi resmi bioskop.")
    open_choices(rows, ctx="bioskop")


# ---------- berita OSINT ultra cepat ----------
NEWS_SRC = {
    "Indonesia": [("Antara", "https://www.antaranews.com/rss/terkini.xml"), ("CNN Indonesia", "https://www.cnnindonesia.com/nasional/rss"),
                  ("Detik", "https://rss.detik.com/index.php/detikcom"), ("Tempo", "https://rss.tempo.co/nasional"),
                  ("Kompas (Google News)", "https://news.google.com/rss/search?q=site:kompas.com+when:1d&hl=id&gl=ID&ceid=ID:id"),
                  ("CNBC Indonesia", "https://www.cnbcindonesia.com/news/rss"), ("Republika", "https://www.republika.co.id/rss"),
                  ("Liputan6", "https://feed.liputan6.com/rss/news"), ("Suara", "https://www.suara.com/rss/news")],
    "Dunia": [("BBC Dunia", "http://feeds.bbci.co.uk/news/world/rss.xml"), ("Al Jazeera", "https://www.aljazeera.com/xml/rss/all.xml"),
              ("DW", "https://rss.dw.com/rdf/rss-en-world"), ("NYT Dunia", "https://rss.nytimes.com/services/xml/rss/nyt/World.xml"),
              ("The Guardian", "https://www.theguardian.com/world/rss"), ("France 24", "https://www.france24.com/en/rss"),
              ("NPR", "https://feeds.npr.org/1004/rss.xml"), ("NHK World", "https://www3.nhk.or.jp/rss/news/cat0.xml")],
    "Siber & OSINT": [("Krebs on Security", "https://krebsonsecurity.com/feed/"), ("BleepingComputer", "https://www.bleepingcomputer.com/feed/"),
                      ("The Hacker News", "https://feeds.feedburner.com/TheHackersNews"), ("CISA Advisories", "https://www.cisa.gov/cybersecurity-advisories/all.xml"),
                      ("Bellingcat", "https://www.bellingcat.com/feed/"), ("SANS ISC", "https://isc.sans.edu/rssfeed.xml"), ("The Record", "https://therecord.media/feed")],
}


def _age(dt):
    if not dt:
        return "  ?  "
    s = (datetime.datetime.now(datetime.timezone.utc) - dt).total_seconds()
    if s < 0:
        s = 0
    if s < 3600:
        return "%2d mnt" % (s // 60)
    if s < 86400:
        return "%2d jam" % (s // 3600)
    return "%2d hr " % (s // 86400)


def news_collect(groups, kw=""):
    feeds = []
    for g in groups:
        feeds += [(n, u, g) for n, u in NEWS_SRC[g]]
    if kw:
        feeds.append(("Google News: " + kw, "https://news.google.com/rss/search?q=%s+when:1d&hl=id&gl=ID&ceid=ID:id" % q(kw), "Kata kunci"))
        feeds.append(("Google News (EN): " + kw, "https://news.google.com/rss/search?q=%s+when:1d&hl=en&gl=US&ceid=US:en" % q(kw), "Kata kunci"))
    t0 = time.time()

    def one(f):
        r = fetch(f[1], timeout=8, limit=600000)
        return f, r.status, (parse_feed(r.body) if r.status == 200 else [])
    with ThreadPoolExecutor(max_workers=20) as ex:
        res = list(ex.map(one, feeds))
    items, ok, bad = [], 0, []
    for f, st, its in res:
        if st == 200 and its:
            ok += 1
            for it in its[:25]:
                it["_src"] = f[0]
                it["_when"] = item_when(it)
                items.append(it)
        else:
            bad.append("%s (%s)" % (f[0], st or "gagal"))
    mk = os.environ.get("MEDIASTACK_API_KEY", "") or key_peek("mediastack")
    if mk:
        o = jget("http://api.mediastack.com/v1/news?access_key=%s&languages=id,en&limit=25&sort=published_desc%s" % (q(mk), ("&keywords=" + q(kw)) if kw else ""), "mediastack", quiet=True)
        for a in ((o or {}).get("data") or []):
            items.append({"title": a.get("title", ""), "link": a.get("url", ""), "_src": "mediastack/" + str(a.get("source", "")), "_when": parse_date(a.get("published_at"))})
    now = datetime.datetime.now(datetime.timezone.utc)
    items = [i for i in items if i.get("title") and (i["_when"] is None or (now - i["_when"]).days < 3)]
    seen, uniq = set(), []
    for i in sorted(items, key=lambda x: x["_when"] or datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc), reverse=True):
        k = norm(i["title"])[:60]
        if kw and kw.lower() not in (i["title"] + " " + (i.get("description") or "")).lower() and i["_src"] and not i["_src"].startswith(("Google", "mediastack")):
            continue
        if k in seen:
            continue
        seen.add(k)
        uniq.append(i)
    return uniq, ok, len(feeds), bad, time.time() - t0


MOD_API["news_cepat"] = "Opsional: API key gratis mediastack (https://mediastack.com) menambah satu sumber lagi; tanpa key semua RSS tetap jalan."


@module("news_cepat", "Berita terbaru dari puluhan sumber sekaligus (RSS paralel): Indonesia, dunia, dan siber/OSINT, terurut dari yang paling baru.",
        "Pilih grup (1-4), kata kunci opsional. Hasil: judul + umur berita + sumber; ketik nomor untuk pratinjau, o<nomor> browser, r muat ulang.")
def news_cepat():
    c = ask("Pilih sumber: 1 = Indonesia   2 = Dunia   3 = Siber & OSINT   4 = Semua   (0 = batal)")
    if c is None or c == "0":
        return
    groups = {"1": ["Indonesia"], "2": ["Dunia"], "3": ["Siber & OSINT"], "4": ["Indonesia", "Dunia", "Siber & OSINT"]}.get(c)
    if not groups:
        p_warn("Pilihan tidak valid. Ketik 1, 2, 3, atau 4.")
        return
    kw = ask("Kata kunci (Enter = semua berita; contoh: banjir, ransomware)") or ""
    if kw == "0":
        return
    while True:
        with Spinner("Mengambil berita dari banyak sumber sekaligus"):
            items, ok, total, bad, secs = news_collect(groups, kw)
        sec("%d berita unik  %s  %d dari %d sumber menjawab dalam %.1f detik" % (len(items), GL["sep"], ok, total, secs))
        top = items[:25]
        for i, it in enumerate(top, 1):
            print("  %s %s%s%s %s%s%s  %s[%s]%s" % (num_tag(i), Y, _age(it["_when"]), R, W, trunc(re.sub(r"\s+", " ", it["title"]), max(20, term_w() - 36)), R, D, trunc(it["_src"], 18), R))
        if not top:
            p_warn("Tidak ada berita yang cocok. Kurangi kata kunci atau periksa internet.")
        if bad:
            p_info("Sumber yang tidak menjawab: %s" % ", ".join(bad[:6]) + (" ..." if len(bad) > 6 else ""))
        for ln in hint_bar([("nomor", "pratinjau di terminal"), ("o<nomor>", "buka di browser"), ("r", "muat ulang"), ("k", "ganti kata kunci"), ("0", "selesai")]):
            print(ln)
        a = ask("Pilih: nomor / o<nomor> / r / k / 0")
        if a is None or a == "0":
            return
        al = a.lower().replace(" ", "")
        if al == "r":
            continue
        if al == "k":
            kw = ask("Kata kunci baru (Enter = semua)") or ""
            continue
        m = re.fullmatch(r"o(\d+)", al)
        if m and 1 <= int(m.group(1)) <= len(top):
            open_browser(top[int(m.group(1)) - 1].get("link", ""))
        elif al.isdigit() and 1 <= int(al) <= len(top):
            peek(top[int(al) - 1].get("link", ""), label=top[int(al) - 1]["_src"], ctx="berita")
        else:
            p_warn("Pilihan tidak valid.")


# ---------- pemantauan internasional ----------
MON_LINKS = [("osirisai.live (pemantauan OSINT)", "https://osirisai.live"), ("Liveuamap (peta konflik)", "https://liveuamap.com/"), ("ADS-B Exchange (penerbangan)", "https://globe.adsbexchange.com/"),
             ("FlightRadar24", "https://www.flightradar24.com/"), ("MarineTraffic (kapal)", "https://www.marinetraffic.com/"), ("VesselFinder", "https://www.vesselfinder.com/"),
             ("NASA FIRMS (titik api)", "https://firms.modaps.eosdis.nasa.gov/map/"), ("Copernicus Browser (satelit)", "https://browser.dataspace.copernicus.eu/"),
             ("Windy (cuaca)", "https://www.windy.com/"), ("GDELT Project (peristiwa dunia)", "https://www.gdeltproject.org/"), ("ACLED (data konflik)", "https://acleddata.com/"),
             ("OONI Explorer (sensor internet)", "https://explorer.ooni.org/"), ("IODA (gangguan internet)", "https://ioda.inetintel.cc.gatech.edu/"),
             ("Cloudflare Radar (trafik internet)", "https://radar.cloudflare.com/"), ("Downdetector Indonesia", "https://downdetector.id/"),
             ("BMKG (gempa & cuaca RI)", "https://www.bmkg.go.id/"), ("USGS Gempa", "https://earthquake.usgs.gov/earthquakes/map/"), ("GDACS (peringatan bencana)", "https://www.gdacs.org/")]


def mon_flights():
    with Spinner("Mengambil pesawat di atas wilayah Indonesia (OpenSky)"):
        o = jget("https://opensky-network.org/api/states/all?lamin=-11&lomin=95&lamax=6&lomax=141", "OpenSky", quiet=True)
    st = (o or {}).get("states") if isinstance(o, dict) else None
    if st is None:
        p_warn("OpenSky tidak menjawab (kuota anonim habis atau layanan sibuk). Coba lagi 1-2 menit lagi atau pakai tautan ADS-B Exchange.")
        return
    sec("%d pesawat terdeteksi di atas Indonesia (data OpenSky, anonim)" % len(st))
    cnt = Counter(s[2] for s in st if s and len(s) > 2)
    kv("Negara asal teratas", ", ".join("%s (%d)" % (k, v) for k, v in cnt.most_common(6)))
    air = [s for s in st if s and len(s) > 9 and not s[8]]
    for s in sorted(air, key=lambda x: -(x[7] or 0))[:10]:
        print("  %s%-8s%s %s%-22s%s %s%6s m  %5s km/j  %s,%s%s" % (Y, (s[1] or "-").strip(), R, W, trunc(s[2] or "-", 22), R, D, int(s[7] or 0), int((s[9] or 0) * 3.6), round(s[6] or 0, 2), round(s[5] or 0, 2), R))
    p_info("Pesawat tanpa transponder atau di luar jangkauan penerima tidak tampil. Untuk peta, buka ADS-B Exchange (pilihan 5).")


def mon_quake():
    with Spinner("Mengambil gempa"):
        res = par([("bmkg", lambda: jget("https://data.bmkg.go.id/DataMKG/TEWS/autogempa.json", "BMKG", quiet=True)),
                   ("usgs", lambda: jget("https://earthquake.usgs.gov/earthquakes/feed/v1.0/summary/4.5_day.geojson", "USGS", quiet=True))])
    g = (((res["bmkg"] or {}).get("Infogempa") or {}).get("gempa")) if isinstance(res["bmkg"], dict) else None
    sec("Gempa terakhir Indonesia (BMKG)")
    if g:
        for k in ("Tanggal", "Jam", "Magnitude", "Kedalaman", "Wilayah", "Potensi", "Dirasakan"):
            kv(k, g.get(k))
    else:
        p_warn("BMKG tidak menjawab.")
    sec("Gempa dunia M4.5+ (24 jam, USGS)")
    feats = ((res["usgs"] or {}).get("features") or []) if isinstance(res["usgs"], dict) else []
    feats.sort(key=lambda f: f["properties"].get("time", 0), reverse=True)
    for f in feats[:10]:
        p = f["properties"]
        print("  %sM%s%s  %s  %s(%s)%s" % (Y, p.get("mag"), R, p.get("place"), D, fmt_epoch(p.get("time")), R))
    if not feats:
        p_warn("USGS tidak menjawab atau tidak ada gempa M4.5+ dalam 24 jam.")


def mon_eonet():
    with Spinner("Mengambil kejadian alam aktif (NASA EONET)"):
        o = jget("https://eonet.gsfc.nasa.gov/api/v3/events?status=open&limit=15", "NASA EONET")
    ev = (o or {}).get("events") or []
    sec("%d kejadian alam sedang aktif (NASA EONET)" % len(ev))
    for e in ev[:15]:
        cat = ", ".join(c.get("title", "") for c in e.get("categories", []))
        last = (e.get("geometry") or [{}])[-1]
        print("  %s%s%s  %s[%s]%s  %s%s%s" % (W, trunc(e.get("title", ""), 56), R, MG, cat, R, D, (last.get("date") or "")[:10], R))
    if not ev:
        p_warn("Tidak ada data kejadian dari EONET.")


def mon_news():
    kw = ask("Kata kunci / negara / topik (contoh: Indonesia, Taiwan, ransomware)  (0 = batal)")
    if kw is None or kw == "0" or not kw:
        return
    with Spinner("Mencari berita dunia (GDELT)"):
        o = jget("https://api.gdeltproject.org/api/v2/doc/doc?query=%s&mode=artlist&maxrecords=15&format=json&sort=datedesc" % q(kw), "GDELT", quiet=True)
    arts = (o or {}).get("articles") if isinstance(o, dict) else None
    if not arts:
        p_warn("GDELT tidak memberi hasil (batasnya 1 permintaan per 5 detik; tunggu sebentar) atau kata kunci terlalu umum/pendek.")
        return
    sec("Berita dunia terbaru: %s" % kw)
    for a in arts[:15]:
        sd = a.get("seendate", "")
        ts = "%s-%s-%s %s:%s" % (sd[:4], sd[4:6], sd[6:8], sd[9:11], sd[11:13]) if len(sd) >= 13 else "-"
        print("  %s%s%s  %s%s%s\n      %s%s%s  %s%s | %s%s" % (Y, ts, R, W, trunc(a.get("title", ""), 100), R, BL, trunc(a.get("url", ""), 90), R, D, a.get("domain"), a.get("sourcecountry"), R))


@module("monitor_intl", "Pemantauan internasional: gempa dunia, kejadian alam aktif (NASA), pesawat di atas Indonesia, berita dunia (GDELT), dan 18 tautan pemantau.",
        "Pilih menu 1-5 di dalam. Semua sumber gratis tanpa API key. Hasil tampil di terminal; tautan peta bisa dibuka dengan o<nomor>.")
def monitor_intl():
    while True:
        sec("Pemantauan Internasional")
        for n, t in (("1", "Gempa: BMKG terakhir + USGS dunia"), ("2", "Kejadian alam aktif (NASA EONET: badai, api, gunung berapi)"),
                     ("3", "Pesawat di atas wilayah Indonesia (OpenSky)"), ("4", "Berita dunia per kata kunci/negara (GDELT)"), ("5", "Tautan pemantau resmi (peta kapal, pesawat, internet, konflik)")):
            print("  %s %s%s%s" % (num_tag(int(n)), W, t, R))
        print("  %s %sKembali%s" % (num_tag(0), W, R))
        c = ask("Pilih 1-5, 0 = kembali")
        if c is None or c == "0":
            return
        if c == "1":
            mon_quake()
        elif c == "2":
            mon_eonet()
        elif c == "3":
            mon_flights()
        elif c == "4":
            mon_news()
        elif c == "5":
            open_choices(MON_LINKS, ctx="pemantauan")
        else:
            p_warn("Pilihan tidak valid.")
            continue
        pause()


# ---------- Kunci API & Pusat Bantuan ----------
def mask_key(v):
    return (v[:3] + "*" * max(3, len(v) - 6) + v[-3:]) if len(v) > 8 else "*" * len(v)


def kunci_api_menu():
    while True:
        keys = _load_keys()
        sec("Kunci API tersimpan di %s" % KEYS_FILE)
        names = sorted(keys)
        if not names:
            p_info("Belum ada key tersimpan. Key diminta otomatis saat fitur yang membutuhkannya dijalankan.")
        for i, n in enumerate(names, 1):
            print("  %s %s%-18s%s %s%s%s" % (num_tag(i), W, n, R, D, mask_key(str(keys[n])), R))
        c = ask("Pilih: nomor = hapus key itu, t = tambah key baru, 0 = kembali")
        if c is None or c == "0":
            return
        if c.lower() == "t":
            nm = (ask("Nama key (contoh: virustotal, abuseipdb, otx, urlscan, nvd, tmdb, mediastack, ipinfodb, iplocate, amdoren)") or "").strip().lower()
            if not re.fullmatch(r"[a-z0-9_]{2,30}", nm):
                p_warn("Nama hanya huruf kecil/angka/garis bawah.")
                continue
            val = (ask("Tempel key untuk '%s'" % nm) or "").strip()
            if len(val) < 6 or re.search(r"\s", val):
                p_warn("Key tidak valid (terlalu pendek atau berisi spasi).")
                continue
            keys[nm] = val
        elif c.isdigit() and 1 <= int(c) <= len(names):
            if yes_no("Hapus key '%s'" % names[int(c) - 1]):
                keys.pop(names[int(c) - 1], None)
            else:
                continue
        else:
            p_warn("Pilihan tidak valid.")
            continue
        try:
            os.makedirs(DATA_DIR, exist_ok=True)
            with open(KEYS_FILE, "w", encoding="utf-8") as f:
                json.dump(keys, f, indent=2)
            try:
                os.chmod(KEYS_FILE, 0o600)
            except OSError:
                pass
            p_ok("Perubahan disimpan.")
        except OSError as e:
            p_err("Gagal menyimpan: %s" % e)


def _diag_checks():
    rows = []        # (ok True/False/None, judul, detail, perbaikan)
    v = sys.version_info
    rows.append((v >= (3, 8), "Versi Python %d.%d.%d" % v[:3], "Giga OSINT butuh 3.8+. Beberapa tool butuh 3.10-3.12.", "Perbarui Python: https://www.python.org/downloads/ (Termux: pkg upgrade python)."))
    rows.append((True, "Sistem: %s" % SYS.get("dev", platform.system()), "Terminal %dx%d, warna %s." % (term_w(), term_h(), {3: "24-bit", 2: "256", 1: "16", 0: "mati"}[COLOR_LVL]),
                 ""))
    if term_w() < 60:
        rows.append((False, "Terminal terlalu sempit (%d kolom)" % term_w(), "Tampilan bisa terpotong.", "Perlebar jendela atau kecilkan huruf; atau jalankan: python3 giga_osint.py --ascii --cepat"))
    t0 = time.time()
    r = fetch("https://pypi.org/simple/pip/", timeout=10, limit=2000)
    rows.append((r.status == 200, "Internet & PyPI (pemasangan paket)", "HTTP %s dalam %d ms" % (r.status or "-", int((time.time() - t0) * 1000)),
                 "Periksa koneksi, matikan VPN/proxy, atau ganti DNS ke 1.1.1.1. Galat: %s" % (r.err or "-")))
    r = fetch("https://github.com/", timeout=10, limit=2000)
    rows.append((r.status in (200, 301, 302), "Akses GitHub (unduh tool)", "HTTP %s" % (r.status or "-"), "Tanpa GitHub banyak tool tidak bisa dipasang. Coba jaringan lain / VPN."))
    try:
        free = shutil.disk_usage(DATA_DIR if os.path.isdir(DATA_DIR) else HOME).free / 1e9
        rows.append((free > 1.0, "Ruang disk kosong %.1f GB" % free, "Tool besar (whisper, crawl4ai) butuh beberapa GB.", "Kosongkan ruang: hapus folder %s yang tidak dipakai." % TOOLS_DIR))
    except Exception:
        pass
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        probe = os.path.join(DATA_DIR, ".tulis")
        open(probe, "w").close()
        os.remove(probe)
        rows.append((True, "Folder data bisa ditulis", DATA_DIR, ""))
    except OSError as e:
        rows.append((False, "Folder data TIDAK bisa ditulis", str(e), "Periksa izin folder %s atau jalankan dari akun biasa (bukan root)." % DATA_DIR))
    for name, fix_key in (("git", "git"), ("go", "go"), ("node", "node"), ("docker", "docker"), ("java", "java")):
        ok = prereq_ok(fix_key)
        cmd = prereq_cmd(fix_key) if not ok else ""
        rows.append((ok if fix_key == "git" else (True if ok else None), "%s %s" % (PREREQ[fix_key]["label"], "terpasang" if ok else "belum terpasang"),
                     "Dibutuhkan hanya oleh tool tertentu." if not ok else "", ("Pasang: " + cmd) if cmd else ""))
    try:
        if os.path.exists(os.path.join(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED")):
            rows.append((None, "pip diblokir sistem (externally-managed-environment)", "Python ini dikelola paket sistem.",
                         "Giga OSINT otomatis memakai --user/--break-system-packages bila perlu; alternatif: python3 -m venv ~/.venv && source ~/.venv/bin/activate"))
    except Exception:
        pass
    paths = os.environ.get("PATH", "").split(os.pathsep)
    for d, why in ((os.path.join(HOME, ".local", "bin"), "tool Python (pipx/--user)"), (os.path.join(HOME, "go", "bin"), "tool Go"), (BIN_DIR, "biner tool Giga OSINT")):
        if os.path.isdir(d) and d not in paths:
            rows.append((None, "%s belum ada di PATH" % d, "Perintah untuk %s mungkin 'command not found'." % why, "Tambahkan: export PATH=\"$PATH:%s\"  (simpan di ~/.bashrc)" % d))
    px = [k for k in ("HTTP_PROXY", "HTTPS_PROXY", "http_proxy", "https_proxy") if os.environ.get(k)]
    if px:
        rows.append((None, "Proxy terdeteksi (%s)" % ", ".join(px), "Semua permintaan lewat proxy.", "Bila koneksi gagal, coba: unset HTTP_PROXY HTTPS_PROXY http_proxy https_proxy"))
    rows.append((True, "Kunci API tersimpan: %d" % len(_load_keys()), "", ""))
    return rows


def diagnosa():
    with Spinner("Memeriksa sistem dan koneksi"):
        rows = _diag_checks()
    sec("Hasil diagnosa")
    bad = 0
    lines = []
    for ok, title, det, fix in rows:
        if ok is True:
            mark = G + GL["dot"] + R
        elif ok is None:
            mark = Y + GL["warn"] + R
        else:
            mark = RD + GL["cross"] + R
            bad += 1
        print("  %s %s%s%s" % (mark, W, title, R))
        if det:
            print("      %s%s%s" % (D, det, R))
        if fix and ok is not True:
            print("      %sSolusi:%s %s" % (Y, R, fix))
        lines.append("%s | %s | %s | %s" % ({True: "OK", None: "PERHATIAN", False: "MASALAH"}[ok], title, det, fix))
    print()
    if bad:
        p_warn("%d masalah penting ditemukan. Ikuti 'Solusi' di atas, lalu jalankan diagnosa lagi." % bad)
    else:
        p_ok("Tidak ada masalah penting. Bila sebuah tool tetap gagal, buka 'Masalah umum' di Pusat Bantuan.")
    if yes_no("Simpan laporan diagnosa ke berkas (untuk ditunjukkan ke orang yang membantu)"):
        try:
            os.makedirs(OUT_DIR, exist_ok=True)
            fp = os.path.join(OUT_DIR, "diagnosa_%s.txt" % time.strftime("%Y%m%d_%H%M%S"))
            with open(fp, "w", encoding="utf-8") as fh:
                fh.write("Giga OSINT %s - diagnosa %s\n" % (VERSION, time.strftime("%Y-%m-%d %H:%M:%S")))
                fh.write("\n".join(lines) + "\n")
            p_ok("Tersimpan: %s" % fp)
        except OSError as e:
            p_err("Gagal menyimpan: %s" % e)


FAQ = [
    ("Tool bilang 'command not found' setelah dipasang",
     "Tool terpasang tetapi folder programnya belum ada di PATH terminalmu.",
     ["Tutup terminal lalu buka lagi (PATH dibaca ulang).", "Atau jalankan: export PATH=\"$PATH:$HOME/.local/bin:$HOME/go/bin\"", "Giga OSINT juga mencari tool di %s sehingga biasanya tetap bisa dijalankan dari menu." % BIN_DIR]),
    ("pip: error: externally-managed-environment",
     "Linux modern melarang pip memasang ke Python milik sistem.",
     ["Giga OSINT otomatis mencoba --user dan --break-system-packages.", "Cara bersih: python3 -m venv ~/.venv lalu source ~/.venv/bin/activate lalu jalankan Giga OSINT dari sana.", "Debian/Ubuntu: sudo apt install python3-pip python3-venv"]),
    ("Permission denied / butuh sudo",
     "Perintah memasang paket sistem butuh hak admin.",
     ["Linux: ketik sudo di depan perintah yang ditampilkan.", "Termux tidak memakai sudo: gunakan pkg install nama_paket.", "Jangan menjalankan Giga OSINT sebagai root kecuali terpaksa."]),
    ("git clone gagal",
     "Internet putus, GitHub diblokir, atau folder tujuan sudah ada.",
     ["Tes: git ls-remote https://github.com/git/git.git HEAD", "Hapus folder lama di %s lalu coba lagi." % TOOLS_DIR, "Bila diblokir, ganti DNS ke 1.1.1.1 atau pakai jaringan lain."]),
    ("Go belum terpasang / go install gagal",
     "Tool bertanda Go dipasang lewat Go atau biner rilis GitHub.",
     ["Pasang Go: Debian/Ubuntu sudo apt install golang; macOS brew install go; Termux pkg install golang.", "Tutup dan buka lagi terminal, lalu ulangi pemasangan.", "Giga OSINT mencoba biner rilis GitHub lebih dulu bila tersedia."]),
    ("Versi Python terlalu lama untuk sebuah tool",
     "Beberapa tool baru butuh Python 3.10-3.13.",
     ["Lihat 'Python' di kartu tool: Giga OSINT memberi peringatan kuning.", "Pasang Python baru berdampingan (pyenv / deadsnakes / python.org) lalu jalankan: python3.12 giga_osint.py", "Atau pakai tool lain yang sejenis (lihat daftar alternatif)."]),
    ("Tool berjalan tetapi tidak mengeluarkan apa-apa",
     "Tool butuh argumen, atau hasilnya kosong, atau menunggu input yang tidak dikirim.",
     ["Giga OSINT menandai 'TANPA keluaran' dan menjelaskan penyebabnya.", "Jalankan lagi dengan input yang benar (lihat contoh di tanda kurung).", "Buka menu penutup: u = ulangi, b = bantuan, Enter = kembali."]),
    ("Saya terjebak di dalam tool, bagaimana keluar?",
     "Beberapa tool interaktif mengambil alih layar.",
     ["Coba berurutan: q lalu Enter, exit, quit, :q, lalu Ctrl+C, lalu Ctrl+D, lalu Ctrl+Z.", "Giga OSINT menampilkan petunjuk keluar sebelum tool dijalankan.", "Terminal macet total: tutup tab/jendela terminal; data tool tidak rusak."]),
    ("Saya lupa memasang / tool belum terpasang",
     "Memilih tool yang belum ada tidak merusak apa pun.",
     ["Giga OSINT menampilkan rencana perintah lalu bertanya y/n.", "Jawab y = pasang otomatis, n = batal tanpa perubahan.", "Pusat Tool (tombol t) menandai yang belum terpasang dan bisa memasang semuanya (a)."]),
    ("Saya lupa mengisi / salah mengisi input",
     "Setiap input diperiksa sebelum dijalankan.",
     ["Bila salah format, muncul contoh yang benar dan kamu bisa mengetik ulang.", "Ketik 0 atau q kapan saja untuk membatalkan dan kembali.", "Tool yang butuh input memberi contoh dalam tanda kurung."]),
    ("API key ditolak (401/403) atau habis kuota (429)",
     "Key salah, kedaluwarsa, atau melewati batas gratis.",
     ["Hapus lalu masukkan ulang key: Pengaturan > Kunci API.", "Cek dashboard penyedia (kuota harian/menit).", "Tunggu 1 menit untuk batas per menit; untuk batas harian tunggu keesokan hari."]),
    ("Situs menolak (403) / 'You have been blocked'",
     "Situs memblokir permintaan otomatis dari jaringan atau VPN-mu.",
     ["Itu bukan galat Giga OSINT. Coba jaringan lain atau matikan VPN.", "Gunakan arsip (tombol 2 di pratinjau) atau tool GitHub sejenis.", "Jangan memaksa berulang kali: bisa memperpanjang blokir."]),
    ("Khusus Termux (Android)",
     "Termux dari Play Store sudah usang.",
     ["Pasang Termux dari F-Droid.", "Jalankan: pkg update && pkg upgrade -y && pkg install python git -y", "Akses galeri/file: termux-setup-storage, lalu path /sdcard/..."]),
    ("Khusus Windows",
     "Beberapa tool Linux tidak jalan langsung di Windows.",
     ["Pakai Windows Terminal (bukan cmd lama) agar warna tampil.", "Untuk tool Linux, pasang Ubuntu WSL: wsl --install", "Gunakan: python giga_osint.py (bukan python3)."]),
    ("Tampilan berantakan / warna aneh",
     "Terminal tidak mendukung simbol atau warna 24-bit.",
     ["Jalankan: python3 giga_osint.py --ascii --cepat", "Matikan warna sepenuhnya: --polos", "Pengaturan > Animasi untuk mematikan efek."]),
    ("SSL: CERTIFICATE_VERIFY_FAILED",
     "Jam perangkat salah atau sertifikat sistem usang.",
     ["Perbaiki tanggal dan jam perangkat.", "macOS: jalankan 'Install Certificates.command' di folder Python.", "Linux: sudo apt install ca-certificates && sudo update-ca-certificates"]),
    ("Docker: permission denied",
     "Akunmu belum boleh memakai Docker.",
     ["Tambahkan ke grup: sudo usermod -aG docker $USER lalu login ulang.", "Atau jalankan perintah dengan sudo.", "Pastikan layanan aktif: sudo systemctl start docker"]),
    ("Tool 'tidak aktif' atau 'usang'",
     "Repo lama bisa tidak cocok dengan layanan/versi sekarang.",
     ["Lihat catatan kuning pada kartu tool dan tanggal commit terakhir.", "Pakai alternatif yang aktif di sub-kategori yang sama.", "Boleh tetap dicoba: tidak ada yang rusak bila gagal."]),
]


def faq_menu():
    while True:
        sec("Masalah umum dan solusinya")
        for i, (t, _, _) in enumerate(FAQ, 1):
            print("  %s %s%s%s" % (num_tag(i), W, trunc(t, max(20, term_w() - 10)), R))
        c = ask("Nomor masalah, 0 = kembali")
        if c is None or c == "0":
            return
        if c.isdigit() and 1 <= int(c) <= len(FAQ):
            t, why, steps = FAQ[int(c) - 1]
            sec(t)
            kv("Penyebab", why, 10)
            for j, st in enumerate(steps, 1):
                print("  %s%d.%s %s%s%s" % (Y, j, R, W, st, R))
            pause()
        else:
            p_warn("Pilihan tidak valid.")


@module("pusat_bantuan", "Pusat Bantuan: diagnosa otomatis, solusi masalah umum (gagal pasang, lupa pasang, lupa isi input), cara keluar dari tool, dan kunci API.",
        "Pilih 1 diagnosa, 2 masalah umum, 3 kunci API, 4 pengantar singkat. Bahasa sederhana; tidak ada yang diubah tanpa izinmu.")
def pusat_bantuan():
    while True:
        sec("PUSAT BANTUAN")
        for n, t in (("1", "Diagnosa otomatis (cek internet, Git, Python, PATH, disk, izin)"), ("2", "Masalah umum dan solusinya (gagal pasang, lupa pasang, lupa isi, terjebak)"),
                     ("3", "Kunci API: lihat (disamarkan), tambah, hapus"), ("4", "Pengantar singkat: apa arti tanda di menu dan cara keluar")):
            for j, ln in enumerate(wrap_ansi(t, max(16, term_w() - 10))):
                print("  %s %s%s%s" % (num_tag(int(n)) if j == 0 else "    ", W, ln, R))
        print("  %s %sKembali%s" % (num_tag(0), W, R))
        c = ask("Pilih 1-4, 0 = kembali")
        if c is None or c == "0":
            return
        if c == "1":
            diagnosa()
            pause()
        elif c == "2":
            faq_menu()
        elif c == "3":
            kunci_api_menu()
        elif c == "4":
            sec("Pengantar singkat")
            for ln in ("Tanda [modul] = fitur yang berjalan langsung di dalam Giga OSINT. [repo] = tool dari GitHub (dipasang otomatis setelah kamu menjawab y).",
                       "Tanda [web] = tautan yang dibuka sebagai pratinjau di terminal. Ketik o<nomor> (contoh o1) bila ingin membukanya di browser.",
                       "Keluar dari fitur kapan saja: ketik 0 atau q di kolom input, atau tekan Ctrl+C. Tidak ada yang rusak karena keluar.",
                       "Setelah fitur selesai tampil menu penutup: Enter = kembali, u = ulangi, b = bantuan, m = menu utama.",
                       "Tulisan merah = keluaran tool. Kuning = peringatan (misalnya butuh API key). Hijau = berhasil.",
                       "Pemindai aktif hanya untuk sistem milik sendiri atau yang kamu punya izin tertulis. Jangan Disalah Gunakan!"):
                p_info(ln)
            pause()
        else:
            p_warn("Pilihan tidak valid.")


@module("kunci_api", "Kelola kunci API yang tersimpan (lihat disamarkan, tambah, hapus). Dipakai fitur VirusTotal, AbuseIPDB, urlscan, NVD, TMDB, dll.",
        "Pilih nomor untuk menghapus, t untuk menambah. Berkas kunci disimpan di komputermu dengan izin 600 dan tidak pernah dikirim ke tempat lain.")
def kunci_api():
    kunci_api_menu()


# =====================================================================
#  KATALOG FITUR  (@Kategori|tentang|cara input   #Sub|tentang   Nama|url / @modul / !tool)
#  {q} dalam URL = tool meminta kata kunci/domain/username. URL kosong = dicari lewat pencarian terminal.
# =====================================================================
CATALOG = r"""
@EmailHunter|Pusat investigasi alamat email: verifikasi, reputasi, kebocoran data, profil publik, DNS & WHOIS.|Masukkan email lengkap (contoh: nama@domain.com) saat diminta; modul membutuhkan koneksi internet.
#Modul Utama EmailHunter|Pemeriksaan email langsung dari terminal memakai API publik.
Verifikasi SMTP|@email_smtp
EmailRep.io|@email_rep
HudsonRock|@email_hudson
ProxyNova + HIBP|@email_proxynova_hibp
Gravatar|@email_gravatar
Google Dork|@email_dork
DNS + WHOIS|@email_dnswhois
#Fitur Lainnya EmailHunter|Pelengkap: validasi format, kebocoran gratis, pola email, dan cek password.
Cek Format, Disposable & MX|@email_format
XposedOrNot (Cek Kebocoran Gratis)|@email_xon
Email Permutator (Tebak Pola Email)|@email_permutator
Cek Kebocoran Password (k-Anonymity)|@pwd_check
Jalankan Semua Sekaligus|@email_all
#Tool Repo GitHub (Email)|Tool dari GitHub: dipasang otomatis (y/n) lalu berjalan langsung di terminal.
Holehe (Cek Email Terdaftar di Situs)|!holehe
#Email Search / Email Check|Situs eksternal untuk mencari, memverifikasi, dan memeriksa alamat email.
Email Hunter|https://hunter.io/
hacked-emails|https://hacked-emails.com/
Public Email Records|
Find That Lead|https://findthatlead.com/
BriteVerify Email Verification|
Email Address Validator|
Email Format|https://www.email-format.com/
EmailHippo|https://www.emailhippo.com/
Email Permutator+|https://metricsparrow.com/toolkit/email-permutator/
Email Validator|https://www.email-validator.net/
Email Validator Tool|
Have I Been Pwned (ihavebeenpwned)|https://haveibeenpwned.com/
Have I Been Sold|https://haveibeensold.app/
MailTester|https://mailtester.com/
TCIPUTILS.com Email Test|https://www.tcpiputils.com/
ThatsThem|https://thatsthem.com/
Toofr|https://www.toofr.com/
Verify Email|https://www.verifyemailaddress.org/
sync me|https://sync.me/

@Telepon & Nomor|Analisis nomor telepon: validitas, operator, tipe, lokasi, zona waktu, format, serta layanan pencari nomor.|Masukkan nomor dengan kode negara (+62...) atau diawali 0 untuk Indonesia. Paket 'phonenumbers' dipasang otomatis (y/n).
#Analisis Nomor Telepon (Mandiri)|Analisis nomor langsung di terminal memakai pustaka libphonenumber.
OSINT dari nomor telepon|@phone:semua
Get the location (state/region level) of the phone number|@phone:lokasi
Detect carrier/operator name (Airtel, Jio, AT&T, Vodafone, etc.)|@phone:operator
Identify phone type (Mobile, Landline, VoIP)|@phone:tipe
Time zone of the number|@phone:zona
National & International formats|@phone:format
Validity check of the number|@phone:valid
Prefix and area code analysis|@phone:prefix
City/State/Region (approximate via prefix mapping)|@phone:kota
Cek kartu nomor|@phone_card
#Placeholder Sections (Spam, Risiko, Kebocoran)|Bagian placeholder: spam, skor risiko, dan info kebocoran data nomor.
Spam reports|@phone:spam
Risk score|@phone:risk
Data breach info|@phone:breach
#Tool Repo GitHub (Telepon)|Tool dari GitHub: dipasang otomatis (y/n) lalu berjalan langsung di terminal.
PhoneInfoga (Pemindai Nomor Internasional)|!phoneinfoga
#Phone Number Research|Situs eksternal pencari dan pemeriksa nomor telepon.
Spy Dialer|https://www.spydialer.com/
Rep Digger|
True Caller|https://www.truecaller.com/
Free Carrier Lookup|https://freecarrierlookup.com/
bmobile.in (India)|
Phone Validator (US)|https://www.phonevalidator.com/
That's Them|https://thatsthem.com/
Next Caller|https://www.nextcaller.com/
fone finder|https://www.fonefinder.net/
Open Cnam|https://www.opencnam.com/
Who Called Me|https://whocalledme.com/
Nuwber|https://nuwber.com/

@Domain, IP & Website|Riset domain, alamat IP, DNS, teknologi situs, riwayat web, dan lalu lintas situs.|Masukkan domain (example.com) atau IP. Layanan eksternal berbasis {q} meminta domain/IP lalu menampilkan pratinjau hasilnya di terminal.
#Analisis Domain & IP (Mandiri)|Analisis pasif langsung di terminal tanpa menyentuh server target secara agresif.
OSINT dari domain dan IP|@dom_osint
Lookup IP (Geolokasi, ASN, rDNS)|@ip_osint
Subdomain via Sertifikat (crt.sh)|@dom_subs
Website technology look up|@web_tech
cookies analyze|@cookie_analyze
redirect lookup|@redirect_lookup
#Tool Repo GitHub (Domain & Jaringan)|Tool dari GitHub: dipasang otomatis (y/n) lalu berjalan langsung di terminal.
DNSRecon (Enumerasi DNS)|!dnsrecon
dnstwist (Deteksi Domain Tiruan)|!dnstwist
WhatWeb (Teknologi Situs)|!whatweb
#Domain and IP Research|Layanan eksternal riset domain & IP: WHOIS, DNS, BGP, port terbuka, dan reputasi.
ViewDNS.info|https://viewdns.info/
Who.is|https://who.is/whois/{q}
DomainTools Whois|https://whois.domaintools.com/{q}
SecurityTrails|https://securitytrails.com/domain/{q}/dns
DNSdumpster|https://dnsdumpster.com/
crt.sh|https://crt.sh/?q={q}
Shodan|https://www.shodan.io/search?query={q}
Censys|https://search.censys.io/search?q={q}
BGPView|https://bgpview.io/search/{q}
Hurricane Electric BGP Toolkit|https://bgp.he.net/search?search%5Bsearch%5D={q}
Robtex|https://www.robtex.com/dns-lookup/{q}
Netcraft Site Report|https://sitereport.netcraft.com/?url={q}
IPinfo|https://ipinfo.io/{q}
AbuseIPDB|https://www.abuseipdb.com/check/{q}
URLScan.io|https://urlscan.io/search/#{q}
VirusTotal|https://www.virustotal.com/gui/search/{q}
#DNS|Alat pemeriksa DNS, propagasi, email DNS, dan DNSSEC.
DNSChecker|https://dnschecker.org/#A/{q}
MXToolbox|https://mxtoolbox.com/SuperTool.aspx?action=mx%3a{q}
Google Public DNS|https://dns.google/query?name={q}
DNSViz|https://dnsviz.net/d/{q}/dnssec/
IntoDNS|https://intodns.com/{q}
#Website traffic look up (Lalu Lintas Situs)|Estimasi trafik, peringkat, dan sumber pengunjung situs.
SimilarWeb|https://www.similarweb.com/website/{q}/
Semrush Analytics|https://www.semrush.com/analytics/overview/?q={q}
Cloudflare Radar Domain|https://radar.cloudflare.com/domains/domain/{q}
Tranco List|https://tranco-list.eu/query
#Website technology look up (Layanan Eksternal)|Deteksi CMS, framework, dan teknologi situs lewat layanan online.
Wappalyzer|https://www.wappalyzer.com/lookup/{q}/
BuiltWith|https://builtwith.com/{q}
WhatCMS|https://whatcms.org/?s={q}
#Web History and Website Capture|Arsip dan tangkapan layar halaman web lama atau yang sudah dihapus.
Internet Archive|https://web.archive.org/web/*/{q}
Archive.fo|https://archive.ph/{q}
webcitation|http://www.webcitation.org/
Memento Time Travel|https://timetravel.mementoweb.org/
Perma.cc|https://perma.cc/
Riwayat Arsip Situs (Wayback CDX)|@wayback_cdx
gau (URL Lama dari Arsip)|!gau
waybackurls (URL Arsip Wayback)|!waybackurls
#Analytics & Affiliate ID's|Menghubungkan situs lewat ID Google Analytics, AdSense, dan afiliasi yang sama.
SpyOnWeb|https://spyonweb.com/{q}
BuiltWith Relationships|https://builtwith.com/relationships/{q}
DNSlytics Reverse Analytics|https://dnslytics.com/reverse-analytics

@Media Sosial Utama|Profil OSINT berbagai platform, daftar jejaring sosial besar, pencarian real-time, dan forum.|Pilih modul OSINT lalu masukkan username tanpa @. Gunakan hanya informasi yang bersifat publik.
#Profil Platform (OSINT Mandiri)|Pemeriksaan profil publik: tautan, status halaman, dork username, dan alat bantu.
Instagram OSINT|@soc:instagram
Facebook OSINT|@soc:facebook
Youtube OSINT|@soc:youtube
Pinterest OSINT|@soc:pinterest
Shopee OSINT|@soc:shopee
Tiktok OSINT|@soc:tiktok
Twitter (X) OSINT|@soc:twitter
wechat osint|@soc:wechat
snapchat osint|@soc:snapchat
cek lokasi akun tiktok pake username|@tiktok_loc
twitter status|@twitter_status
#Major Social Networks (social networks)|Jejaring sosial besar dunia dan regional.
Draugiem (Latvia) (.lv)|https://www.draugiem.lv/
Facebook|https://www.facebook.com/
Badoo|https://badoo.com/
Facenama (IR)|https://facenama.com/
Google+|
Instagram|https://www.instagram.com/
Linkedin|https://www.linkedin.com/
Mixi (JP)|https://mixi.jp/
Odnoklassniki (.ru)|https://ok.ru/
Pinterest|https://www.pinterest.com/
Qzone (CN)|https://qzone.qq.com/
Reddit|https://www.reddit.com/
Taringa (Latin America)|https://www.taringa.net/
Tinder|https://tinder.com/
Tumblr|https://www.tumblr.com/
Twitter|https://x.com/
Weibo (China)|https://weibo.com/
VKontakte|https://vk.com/
Care2|https://www.care2.com/
Nextdoor|https://nextdoor.com/
#Real-Time Search, Social Media Search, and General Social Media Tools|Pencarian real-time dan agregator percakapan di banyak platform.
Addict-o-matic|
Social Searcher|https://www.social-searcher.com/
Social Mention|http://socialmention.com/
Geofeedia|
HowSociable|
Hashtatit|
OpinionCrawl|http://opinioncrawl.com/
#Social Media Tools|Alat analitik, pemantauan, dan manajemen media sosial.
Buzz sumo|https://buzzsumo.com/
Cyfe|https://www.cyfe.com/
Gaddr|
Asian Ave|https://www.asianave.com/
Hootsuite|https://hootsuite.com/
Klear|https://klear.com/
Klout|
SociaBlade|https://socialblade.com/
yachudo (UA)|
#Imageboards & Forum Anonim|Papan gambar dan forum anonim beserta arsip pencariannya.
4chansearch|
4chan|https://www.4chan.org/
4plebs|https://archive.4plebs.org/
7chan|https://7chan.org/
imagechan|
raddle.me|https://raddle.me/
Hispachan|https://www.hispachan.org/
Phuks|
Warez BB|https://www.warez-bb.org/
voat|
tbpchan|
#Blog Search|Pencarian blog dan agregator pembaca feed RSS.
Feedly|https://feedly.com/i/search/{q}
Inoreader|https://www.inoreader.com/
Bloglovin|https://www.bloglovin.com/
Medium Search|https://medium.com/search?q={q}
Substack Search|https://substack.com/search/{q}
#Forums and Discussion Boards Search|Pencarian forum, grup diskusi, dan papan percakapan.
Boardreader|https://boardreader.com/
Facebook Groups|https://www.facebook.com/groups/
Google Groups|https://groups.google.com/
Linkedin Groups|https://www.linkedin.com/groups/
Omgili|https://omgili.com/
Yahoo Groups|
Kaskus|https://www.kaskus.co.id/search?q={q}

@Twitter / X|Kumpulan alat analisis akun, tweet, tagar, peta, dan tren di Twitter/X.|Beberapa layanan lama sudah tutup; bila tautan tidak bisa dibuka, pratinjau terminal menawarkan arsip Wayback dan tool GitHub terkait.
#Twitter|Alat pihak ketiga untuk Twitter/X.
qrt tweets|
Twipu|
onemilliontweetmap|https://onemilliontweetmap.com/
Twitter Fall|
Mapd Tweet Map|
AllMyTweets|
Bioischanged|
doesfollow|
ExportData|
Fake Follower Check|
First Tweet|
Foller.me|https://foller.me/
Followerwonk|https://followerwonk.com/
Geochirp|
GeoSocial Footprint|
GetTwitterID|https://gettwitterid.com/
Gigatweeter|
Harvard TweetMap|https://worldmap.harvard.edu/tweetmap/
Hashtagify|https://hashtagify.me/
Hashtags.org|
introduce|
Mentionmapp|https://mentionmapp.com/
ManageFlitter|
My Top Tweet|
Queryfeed|
RiteTag|
Sentiment140|
SnapBird|https://snapbird.org/
Sleeping Time|https://sleepingtime.org/
Social Bearing|https://socialbearing.com/
Social Rank First Follower|
Tagdef|
Trends24|https://trends24.in/
TrendsMap|https://www.trendsmap.com/
Twazzup|
twbirthday|
TwChat|
tweepsect|
Tweet4me|
TweetArchivist|https://www.tweetarchivist.com/
TweetMap|
Tweetpaths|
TweetPsych|
Tweetreach|
TweetStats|
Tweet Tag|
TweetTunnel|
Twellow|
Tweriod|
Twiangulate|
Twicsy|
Twipho|
Twitonomy|https://www.twitonomy.com/
TwitRSS|
Twitter Advanced Search|https://x.com/search-advanced
Twitter Audit|https://www.twitteraudit.com/
Twitter Chat Schedule|
Twitter Counter|
Twitter Search|https://x.com/search?q={q}
TWUBS Twitter Chat|
Schedule Warble|
Block Together|https://blocktogether.org/

@Facebook, Instagram & TikTok|Alat bantu analisis halaman, grup, ID, story, dan profil pada Facebook, Instagram, dan TikTok.|Banyak alat pihak ketiga sering berubah; tautan kosong dicari otomatis lewat pencarian di terminal.
#Facebook|Alat pencarian dan analisis Facebook (hanya data publik).
ExtractFace|
Fanpage Karma|https://www.fanpagekarma.com/
Facebook Search|https://www.facebook.com/search/top?q={q}
Facebook Search Tool|
FaceLIVE|
LikeAlyzer|https://likealyzer.com/
Lookup-ID.com|https://lookup-id.com/
SearchIsBack|https://searchisback.com/
Wallfux|
Stalkscan|
Find My Facebook ID API|
Wolfram Alpha Facebook Report|https://www.wolframalpha.com/facebook
Zesty Facebook Search|
Facebook Intersect Search Tool|
#Instagram|Penampil dan penganalisis profil serta story Instagram yang bersifat publik.
Tofo|
Buzzweb|
The Insta Stalker|
imgtoon|
Storiesig|https://storiesig.info/
loadingram|
Instagram Profil Publik (Instaloader)|@insta_profile
#TikTok|Analitik dan pemantauan akun serta tren TikTok.
Exolyt|https://exolyt.com/
Tokboard|https://tokboard.com/
Social Blade TikTok|https://socialblade.com/tiktok/

@Platform Sosial Lainnya|Pinterest, Reddit, VK, Tumblr, LinkedIn, Telegram, Discord, Snapchat, Steam, dan GitHub.|Pilih platform lalu alat yang sesuai; sebagian alat meminta username atau kata kunci.
#Pinterest|Pencarian dan analitik Pinterest.
socialab|
pingroupie (Pinterest)|https://pingroupie.com/
Pinterest Search|https://www.pinterest.com/search/pins/?q={q}
#Reddit|Pencarian arsip, metrik, dan investigasi akun Reddit.
Reddit Archive|
Reddit Investigator|
Reddit Metrics|https://frontpagemetrics.com/
SnoopSnoo|
Redective|
Redditlist|http://redditlist.com/
Reddit Search|https://www.reddit.com/search/?q={q}
#VKontakte|Pencarian di jejaring sosial Rusia VKontakte.
VK Search|https://vk.com/search?c%5Bq%5D={q}
#Tumblr|Pencarian dan arsip konten Tumblr.
Tumblr Search|https://www.tumblr.com/search/{q}
Tumblr OriginalsResavr|
Imgur|https://imgur.com/
#LinkedIn|Pencarian profil dan perusahaan di LinkedIn.
LinkedIn Search|https://www.linkedin.com/search/results/all/?keywords={q}
#Telegram|Direktori dan statistik channel serta grup Telegram publik.
tchannels|https://tchannels.me/
Buzz.im|
Google CSE (Telegram)|
Tgstat|https://tgstat.com/
Telesco|https://telesco.pe/
GroupFinder|
Info Channel/Grup Telegram Publik|@telegram_channel
#Discord & Snapchat|Alat bantu pencarian ID Discord dan akun Snapchat.
Dis.cool|
discord.id|https://discord.id/
Find my snap|
PlusFeed|
whopostedwhat|https://whopostedwhat.com/
#Steam|Pencarian pengguna dan ID Steam.
Steam Community Search|https://steamcommunity.com/search/users/#text={q}
SteamID Lookup|https://steamid.io/lookup/{q}
#GitHub|Pencarian pengguna dan repositori GitHub.
GitHub User Search|https://github.com/search?q={q}&type=users
GitHub Repo Search|https://github.com/search?q={q}&type=repositories
GitHub OSINT (Profil, Repo, Email Commit)|@github_osint

@Mesin Pencari|Mesin pencari umum, nasional, meta, privasi, dokumen, file, kode, paste, dan alat dork.|Pilih tool; bila ada {q} masukkan kata kunci lalu hasilnya tampil sebagai pratinjau di terminal.
#General Search|Mesin pencari umum untuk pencarian awal.
Google|https://www.google.com/search?q={q}
Bing|https://www.bing.com/search?q={q}
DuckDuckGo|https://duckduckgo.com/?q={q}
Yandex|https://yandex.com/search/?text={q}
Brave Search|https://search.brave.com/search?q={q}
Yahoo Search|https://search.yahoo.com/search?p={q}
Baidu|https://www.baidu.com/s?wd={q}
#Google Dorks|Operator pencarian lanjutan Google untuk menemukan informasi spesifik.
Pembuat Google Dork (Otomatis)|@dork_builder
Google Hacking Database (Exploit-DB)|https://www.exploit-db.com/google-hacking-database
Dorksearch|https://dorksearch.com/
#Main National Search Engines|Mesin pencari utama berbagai negara.
Google Indonesia|https://www.google.co.id/search?q={q}
Naver (Korea)|https://search.naver.com/search.naver?query={q}
Seznam (Ceko)|https://search.seznam.cz/?q={q}
Daum (Korea)|https://search.daum.net/search?q={q}
Yahoo Japan|https://search.yahoo.co.jp/search?p={q}
Sogou (Tiongkok)|https://www.sogou.com/web?query={q}
#International Search Engines|Pencarian lintas bahasa dan wilayah.
2lingual Search|
#Meta Search|Meta-search: satu kueri dikirim ke banyak mesin pencari sekaligus.
All-in-One|
AllTheInternet|
Dogpile|https://www.dogpile.com/serp?q={q}
Etools|https://www.etools.ch/
Excite|
FaganFinder|https://www.faganfinder.com/
Glearch|
Goofram|
iZito|
Nextaris|
Metabear|
Myallsearch|
Qrobe|
Qwant|https://www.qwant.com/?q={q}
Sputtr|
Trovando|
WebCrawler|https://www.webcrawler.com/serp?q={q}
WiinkZ|
Zapmeta|https://www.zapmeta.com/
#Privacy Focused Search Engines|Mesin pencari yang tidak melacak penggunanya.
Startpage|https://www.startpage.com/do/search?q={q}
Mojeek|https://www.mojeek.com/search?q={q}
MetaGer|https://metager.org/meta/meta.ger3?eingabe={q}
Ecosia|https://www.ecosia.org/search?q={q}
SearX Instances|https://searx.space/
#Specialty Search Engines|Mesin pencari khusus: bisnis, ilmiah, simbol, dan arsip.
Biznar|
CiteSeerX|https://citeseerx.ist.psu.edu/search?q={q}
Digle|
Google Custom Search|https://cse.google.com/cse
Harmari (Unified Listings Search)|
Million Short|https://millionshort.com/search?keywords={q}
WorldWideScience.org|https://worldwidescience.org/
Zanran|
Swiss Cows|
bvsg.org|
Symbol Hound|https://symbolhound.com/?q={q}
#Similar Sites Search|Menemukan situs serupa atau alternatif dari sebuah situs.
SimilarSites|https://www.similarsites.com/site/{q}
AlternativeTo|https://alternativeto.net/browse/search/?q={q}
Similar Site Search|https://www.similarsitesearch.com/
#Visual Search and Clustering Search Engines|Pencarian visual dan pengelompokan (cluster) hasil.
Carrot2|https://search.carrot2.org/#/search/web/{q}/treemap
#Document and Slides Search|Pencarian dokumen PDF, presentasi, dan arsip dokumen.
Authorstream|https://www.authorstream.com/
Find-pdf-doc|https://www.find-pdf-doc.com/
Free Full PDF|https://www.freefullpdf.com/
PDF Search Engine|
PDFgive|https://www.pdfgive.com/
PDFSB|https://www.pdfsb.com/
PDFSR|https://www.pdfsr.com/
PPTHunter|
RECAP|https://www.courtlistener.com/recap/
Scribd|https://www.scribd.com/search?query={q}
SlideSearchEngine|
SlideShare|https://www.slideshare.net/search?q={q}
Slideworld|
soPDF.com|https://www.sopdf.com/
Document Cloud|https://www.documentcloud.org/
#File Search|Pencarian file dan direktori berkas publik.
file-search.info|https://www.file-search.info/
filesearching|https://www.filesearching.com/
filesloop|https://www.filesloop.com/
Search Shared|https://www.searchshared.com/
mmnt.net|https://www.mmnt.net/
File Chef|https://www.filechef.com/
Palined|
PDF Search|
#Open directories search engines|Mencari direktori terbuka (open directory / index of).
FilePursuit|https://filepursuit.com/
ODCrawler|https://odcrawler.xyz/
Google Index-of Dork|https://www.google.com/search?q=intitle:%22index+of%22+{q}
#Universal search tools|Alat pencarian serba guna lintas sumber untuk investigator.
IntelligenceX|https://intelx.io/?s={q}
IntelTechniques Search Tools|https://inteltechniques.com/tools/
OSINT Framework|https://osintframework.com/
Cari di Web (Hasil di Terminal)|@web_search
Pratinjau & Cek Status URL|@peek_url
#Tools for DuckDuckGo|Fitur dan operator khusus DuckDuckGo.
DuckDuckGo Bangs|https://duckduckgo.com/bangs
DuckDuckGo Operator Help|https://duckduckgo.com/duckduckgo-help-pages/results/syntax/
DuckDuckGo Images|https://duckduckgo.com/?q={q}&iax=images&ia=images
#Tools for Google|Fitur lanjutan Google untuk riset OSINT.
Google Advanced Search|https://www.google.com/advanced_search
Google Alerts|https://www.google.com/alerts
Google Operators Help|https://support.google.com/websearch/answer/2466433
Google Books|https://www.google.com/search?tbm=bks&q={q}
#Filesharing Search Engines|Mencari berkas yang dibagikan publik di layanan penyimpanan awan.
Google Drive Publik (dork)|https://www.google.com/search?q=site:drive.google.com+{q}
Dropbox Publik (dork)|https://www.google.com/search?q=site:dropbox.com/s+{q}
MEGA Publik (dork)|https://www.google.com/search?q=site:mega.nz+{q}
OneDrive Publik (dork)|https://www.google.com/search?q=site:onedrive.live.com+{q}
#Pastebins|Situs paste publik tempat teks dan data sering dibagikan.
justpastit|
PasteLert|
Pastebin|https://pastebin.com/
Psbdmp|https://psbdmp.ws/
GitHub Gist|https://gist.github.com/
#Code Search|Pencarian kode sumber dan jejak teknologi di seluruh web.
NerdyData|https://www.nerdydata.com/
SearchCode|https://searchcode.com/?q={q}
Publicwww|https://publicwww.com/
Spyse|
Grep.app|https://grep.app/search?q={q}
GitHub Code Search|https://github.com/search?q={q}&type=code

@Dark Web & Data Bocor|Pencarian dark web, database kebocoran data, dan arsip dokumen bocor.|Gunakan hanya untuk riset, jurnalisme, dan keamanan; jangan memakai data bocor milik orang lain.
#Dark Web Search Engines|Mesin pencari untuk jaringan Tor (.onion).
Ahmia|https://ahmia.fi/search/?q={q}
Dark Search|https://darksearch.io/
#Darknet/deepweb search tools|Alat bantu riset darknet dan deep web.
OnionSearch (tool GitHub)|https://github.com/megadose/OnionSearch
Hunchly Dark Web Reports|https://darkweb.hunch.ly/
#Data Breach Search Engines|Layanan pemeriksa dan pencari kebocoran data.
DeHashed|https://dehashed.com/
LeakCheck|https://leakcheck.io/
BreachDirectory|https://breachdirectory.org/
Snusbase|https://snusbase.com/
Leak-Lookup|https://leak-lookup.com/
XposedOrNot (Situs)|https://xposedornot.com/
Firefox Monitor|https://monitor.firefox.com/
#Arsip Kebocoran & Dokumen Bocor|Arsip publik dokumen bocor, peretasan besar, dan investigasi jurnalistik.
Wiki Leaks|https://wikileaks.org/
Database Today|
DataBreaches|https://databreaches.net/
Gawker Hack|
Ashley Madison|
Leaked Source|
Offshore Leak Database|https://offshoreleaks.icij.org/
Crytome (Cryptome)|https://cryptome.org/

@Threat Intelligence & Keamanan|Intelijen ancaman siber, peta serangan, pelaku ancaman, kerentanan, dan analisis file.|Pilih sub-kategori; pratinjau tampil di terminal dan menu aksi menawarkan tool GitHub terkait.
#Threat Actor Search|Profil kelompok peretas dan pelaku ancaman siber.
MITRE ATT&CK Groups|https://attack.mitre.org/groups/
ETDA Threat Group Cards|https://apt.etda.or.th/cgi-bin/listgroups.cgi
Malpedia|https://malpedia.caad.fkie.fraunhofer.de/
Ransomware.live|https://www.ransomware.live/
#Live Cyber Threat Maps|Peta serangan siber secara langsung (real-time).
Kaspersky Cybermap|https://cybermap.kaspersky.com/
Fortinet Threat Map|https://threatmap.fortiguard.com/
Check Point ThreatCloud Live|https://threatmap.checkpoint.com/
Radware Live Threat Map|https://livethreatmap.radware.com/
Digital Attack Map|https://www.digitalattackmap.com/
Bitdefender Threat Map|https://threatmap.bitdefender.com/
#Threat Intelligence|Reputasi IP, domain, URL, dan malware.
AlienVault OTX|https://otx.alienvault.com/browse/global/pulses?q={q}
VirusTotal Intelligence|https://www.virustotal.com/
URLhaus|https://urlhaus.abuse.ch/browse.php?search={q}
GreyNoise|https://viz.greynoise.io/query/{q}
MalwareBazaar|https://bazaar.abuse.ch/browse.php?search={q}
Any.Run|https://any.run/
Hybrid Analysis|https://www.hybrid-analysis.com/
Pulsedive|https://pulsedive.com/
Shodan CLI (Info Host & Port)|!shodan
#Bugbounty/vulnerabilities search tools|Database CVE, exploit publik, dan platform bug bounty.
NVD CVE Search|https://nvd.nist.gov/vuln/search/results?query={q}
Exploit-DB|https://www.exploit-db.com/search?q={q}
Vulners|https://vulners.com/search?query={q}
CVE Details|https://www.cvedetails.com/
CISA KEV Catalog|https://www.cisa.gov/known-exploited-vulnerabilities-catalog
HackerOne Hacktivity|https://hackerone.com/hacktivity
Bugcrowd|https://bugcrowd.com/
Intigriti|https://www.intigriti.com/
YesWeHack|https://yeswehack.com/
#Public buckets search tools|Mencari bucket penyimpanan awan yang terbuka ke publik.
GrayhatWarfare|https://buckets.grayhatwarfare.com/
S3Scanner (tool GitHub)|https://github.com/sa7mon/S3Scanner
#Files (Analisis File)|Analisis file mencurigakan, tanda tangan file, dan decoding data.
Jotti Malware Scan|https://virusscan.jotti.org/
CyberChef|https://gchq.github.io/CyberChef/
File Signatures (Gary Kessler)|https://www.garykessler.net/library/file_sigs.html
FileInfo.com|https://fileinfo.com/

@Offensive Security & Recon (Izin Sah Saja)|Tool pentest/bug bounty. Hanya untuk sistem sendiri atau target berizin tertulis dan sesuai scope program.|Tool yang belum terpasang akan memunculkan rencana instalasi otomatis dan pertanyaan y/n. Pemindai aktif meminta konfirmasi izin.
#Offensive Security (Authorized Testing Only)|Tool recon & pengujian keamanan; instalasi otomatis (y/n) lalu dijalankan dengan input arahan.
harvester|!harvester
maltego|!maltego
nmap|!nmap
dirsearch|!dirsearch
nuclei|!nuclei
dalfox|!dalfox
katana|!katana
subfinder|!subfinder
paramspider|!paramspider
photon|!photon
wafw00f (Deteksi WAF)|!wafw00f
#Recon & Otomasi (Pasif)|Crawler dan pencarian massal yang berjalan langsung dari Giga OSINT.
crawl website|@crawl_site
bulk search|@bulk_search
SpiderFoot (Otomasi OSINT Pasif)|!spiderfoot
Recon-ng (Framework Recon)|!reconng

@Investigasi Orang & Username|Pelacakan username, penelusuran orang, dokumen peradilan, dan pembelajaran rekayasa sosial untuk pertahanan.|Cari informasi hanya dari sumber publik dan hormati privasi orang lain.
#Username Check|Cek ketersediaan dan keberadaan username di banyak platform.
Username Check (Built-in 24 Situs)|@user_check
sherlok (Sherlock)|!sherlock
mr holmes|!mrholmes
Check User Names|https://checkusernames.com/
Knowem|https://knowem.com/
Name Chk|https://namechk.com/
Name Checkr|https://www.namecheckr.com/
User Sherlock|
Whatsmyname|https://whatsmyname.app/
Name Combiner|
huntel.io|https://huntel.io/
Maigret (Dossier Username)|!maigret
Socialscan (Username & Email)|!socialscan
Blackbird (Pencari Akun)|!blackbird
#People Investigations|Pencarian orang dari data publik dan silsilah.
Family Search|https://www.familysearch.org/search/
PeekYou|https://www.peekyou.com/
PeopleSearch.net|
snitch.name|https://snitch.name/
The Knot|https://www.theknot.com/
Pipl|https://pipl.com/
Spokeo|https://www.spokeo.com/
#Expert Search|Mencari pakar dan peneliti pada bidang tertentu.
ResearchGate|https://www.researchgate.net/search?q={q}
ORCID|https://orcid.org/orcid-search/search?searchQuery={q}
Semantic Scholar|https://www.semanticscholar.org/search?q={q}
#Arrests, Inmate & Court Search|Catatan penangkapan, narapidana, dan putusan pengadilan.
VINELink|https://www.vinelink.com/
Federal Bureau of Prisons Inmate Locator|https://www.bop.gov/inmateloc/
PACER|https://pacer.uscourts.gov/
CourtListener|https://www.courtlistener.com/?q={q}
Putusan Mahkamah Agung (Indonesia)|https://putusan3.mahkamahagung.go.id/search.html?q={q}
#Social Engineering (Edukasi & Pertahanan)|Materi untuk memahami dan mencegah rekayasa sosial (phishing, pretexting).
Social-Engineer.org|https://www.social-engineer.org/
Google Phishing Quiz|https://phishingquiz.withgoogle.com/
KnowBe4 Phishing Security Test|https://www.knowbe4.com/phishing-security-test-offer

@Kendaraan|Cek plat nomor Indonesia, VIN, riwayat kendaraan, dan lelang.|Masukkan plat (B 1234 ABC) untuk fitur plat; situs VIN/lelang eksternal memakai nomor VIN atau plat sesuai negaranya.
#Cek Plat Kendaraan (Indonesia)|Pengenalan wilayah plat dan akses pengecekan pajak resmi.
Cek Plat Kendaraan|@plat_cek
#Vehicle / Automobile Research (Vehicle)|Riset kendaraan: pencarian plat dan VIN lintas negara.
Poctra (US / EU)|https://poctra.com/
nomerogram (RU)|https://nomerogram.ru/
Reverse Genie (License Plate Search)|https://www.reversegenie.com/
Autowini (Vin Search International)|https://www.autowini.com/
thatsthem (Vin Search)|https://thatsthem.com/
All Vehicle Data|
Vin Place|
Check That (Vin Search)|
Vin decoderz (Vin Search)|https://www.vindecoderz.com/
National Insurance Crime Bureau(Vin Search)|https://www.nicb.org/vincheck
Vehicle History (Make/Model & Vin Search)|
Vehicle History (Plate Search)|
auto bid master (auction)|
copart (auction)|https://www.copart.com/
Check That Vin|
Vin-Info (UK)|
Carnet AI|https://carnet.ai/

@Penerbangan & Drone|Pelacakan pesawat, bandara, registri, dan informasi penerbangan dunia.|Pakai modul pelacak live di terminal, atau pratinjau situs pelacak untuk nomor penerbangan, registrasi, dan bandara.
#Flight Tracking|Pelacak penerbangan real-time dan historis.
Open Flights|https://openflights.org/
Plane Finder|https://planefinder.net/
Plane Spotter|
Flight Aware|https://www.flightaware.com/
Flight Stats|https://www.flightstats.com/
Plane Flight Tracker|https://www.planeflighttracker.com/
Flight Aware(Historical)|https://www.flightaware.com/
Flight Radar 24|https://www.flightradar24.com/
Flightwise|https://www.flightwise.com/
Airport Webcams|https://airportwebcams.net/
Live ATC|https://www.liveatc.net/
Radar Box|https://www.radarbox.com/
Airfield Search|
Virtual Radar|
FAA Registry|https://registry.faa.gov/aircraftinquiry/
US Air Space Map|
Pelacak Penerbangan Live (OpenSky)|@flight_track
#Aviation|Data penerbangan terbuka dan keselamatan penerbangan.
OpenSky Network|https://opensky-network.org/
ADS-B Exchange|https://globe.adsbexchange.com/
AirNav Radar|https://www.airnavradar.com/
Aviation Safety Network|https://aviation-safety.net/
JetPhotos|https://www.jetphotos.com/
#Drones|Informasi dan regulasi drone.
Travel By Drone|https://travelbydrone.com/
DJI FlySafe|https://fly-safe.dji.com/

@Maritim, Kargo & Kereta|Pelacakan kapal, kargo, kontainer, kapal pesiar, paket pos, dan kereta api.|Masukkan nama kapal, IMO/MMSI, nomor kontainer, atau nomor resi langsung di situs tujuan.
#Marine & Cargo Tracking|Pelacak kapal dan kargo dunia.
Fleetmon|https://www.fleetmon.com/
Marine Traffic|https://www.marinetraffic.com/
Vessel Tracker|https://www.vesseltracker.com/
Vessel Finder|https://www.vesselfinder.com/
Boat Info World|https://boatinfoworld.com/
My Ship Tracking|https://www.myshiptracking.com/
Ship Spotting|https://www.shipspotting.com/
eships.net|
Crusin|
Live Cruise Ship Tracker|
Cruise Mapper|https://www.cruisemapper.com/
Track Trace (Cargo)|https://www.track-trace.com/
Track Trace (Lading)|https://www.track-trace.com/bol
container-tracking (Cargo)|https://www.container-tracking.org/
Panjiva (Cargo)|https://panjiva.com/
Import Genius (Cargo)|https://www.importgenius.com/
Track Trace Post|https://www.track-trace.com/post
#Maritime|Data kapal, perikanan, dan pelayaran terbuka.
AISHub|https://www.aishub.net/
Global Fishing Watch|https://globalfishingwatch.org/map
Equasis|https://www.equasis.org/
#Railway|Peta dan jadwal jalur kereta api.
OpenRailwayMap|https://www.openrailwaymap.org/
Realtime Trains (UK)|https://www.realtimetrains.co.uk/
KAI Access (Indonesia)|https://kai.id/

@Geospasial, Peta & Satelit|Peta, citra satelit, street view, webcam dunia, rute, alam, transportasi, dan infrastruktur komunikasi.|Pratinjau tautan peta di terminal, lalu cari koordinat atau nama tempat. Cocok untuk verifikasi lokasi foto/video (geolocation).
#Geospatial Research and Mapping Tools|Peta digital dan alat riset geospasial.
Google Earth|https://earth.google.com/web/
Google Maps|https://www.google.com/maps/search/{q}
OpenStreetMap|https://www.openstreetmap.org/search?query={q}
Overpass Turbo|https://overpass-turbo.eu/
Wikimapia|https://wikimapia.org/
#Street View|Foto jalan 360 derajat dari berbagai penyedia.
Mapillary|https://www.mapillary.com/app
KartaView|https://kartaview.org/
Bing Maps Streetside|https://www.bing.com/maps
Yandex Panoramas|https://yandex.com/maps
#Satellite/aerial imagery|Citra satelit dan udara, termasuk arsip historis.
Sentinel Hub EO Browser|https://apps.sentinel-hub.com/eo-browser/
NASA Worldview|https://worldview.earthdata.nasa.gov/
Zoom Earth|https://zoom.earth/
USGS EarthExplorer|https://earthexplorer.usgs.gov/
Google Earth Timelapse|https://earthengine.google.com/timelapse/
Tanah Air Indonesia (BIG)|https://tanahair.indonesia.go.id/
#Routes|Perencanaan rute dan jejak perjalanan.
OpenRouteService|https://maps.openrouteservice.org/
Wikiloc|https://www.wikiloc.com/
Strava Global Heatmap|https://www.strava.com/maps/global-heatmap
Rome2Rio|https://www.rome2rio.com/
#Worldwide street webcams|Webcam publik di jalan dan kota dunia.
Windy Webcams|https://www.windy.com/webcams
EarthCam|https://www.earthcam.com/
WebcamTaxi|https://www.webcamtaxi.com/
Skyline Webcams|https://www.skylinewebcams.com/
#Social media and photos|Foto dan konten sosial berbasis lokasi.
Flickr Map|https://www.flickr.com/map
Snap Map|https://map.snapchat.com/
#Nature|Data alam: satwa, hutan, kebakaran, dan cuaca.
iNaturalist|https://www.inaturalist.org/
eBird|https://ebird.org/
GBIF|https://www.gbif.org/
Global Forest Watch|https://www.globalforestwatch.org/map/
NASA FIRMS|https://firms.modaps.eosdis.nasa.gov/map/
Windy|https://www.windy.com/
#Tools (Geospasial)|Alat bantu koordinat dan nama tempat.
GeoNames|https://www.geonames.org/
GPS Coordinates|https://www.gps-coordinates.net/
what3words|https://what3words.com/
#Transport|Informasi transportasi umum.
Moovit|https://moovit.com/
Citymapper|https://citymapper.com/
Transitland|https://www.transit.land/
TransJakarta|https://transjakarta.co.id/
#Communications, Internet, Technologies|Infrastruktur komunikasi, gangguan internet, dan jaringan nirkabel.
Submarine Cable Map|https://www.submarinecablemap.com/
Cloudflare Radar|https://radar.cloudflare.com/
OpenCelliD|https://opencellid.org/
WiGLE|https://wigle.net/
NetBlocks|https://netblocks.org/
Downdetector|https://downdetector.com/
#Anomalies and Lost Places|Tempat misterius, terbengkalai, dan anomali lokasi.
Atlas Obscura|https://www.atlasobscura.com/

@Militer & Konflik|Pelacakan aktivitas militer terbuka dan visualisasi peta konflik.|Sumber terbuka saja; verifikasi informasi dengan beberapa sumber sebelum menyimpulkan.
#Military tracking|Pelacak penerbangan dan sumber militer terbuka.
ADS-B Exchange (Filter Militer)|https://globe.adsbexchange.com/?mil
Liveuamap|https://liveuamap.com/
GlobalSecurity.org|https://www.globalsecurity.org/
Global Firepower|https://www.globalfirepower.com/
#Military visalisation (Visualisasi Militer)|Peta dan visualisasi konflik bersenjata.
ACLED|https://acleddata.com/
DeepStateMap|https://deepstatemap.live/
Institute for the Study of War|https://www.understandingwar.org/

@Astronomi (Matahari & Bulan)|Posisi matahari dan bulan, jadwal terbit/terbenam, dan gerhana untuk analisis bayangan foto.|Berguna untuk memverifikasi waktu dan lokasi foto lewat arah bayangan (chronolocation).
#Sun and lunar Tools|Perhitungan matahari dan bulan.
Sun rise, noon, and set time and direction.|https://www.suncalc.org/
SunEarthTools.com|https://www.sunearthtools.com/
Astronomy - Sun - Moon - Eclipses|https://www.timeanddate.com/astronomy/
3D Sun Path|https://andrewmarsh.com/apps/staging/sunpath3d.html
Hitung Matahari, Bayangan & Waktu Foto|@sun_calc

@Gambar, Wajah & Metadata|Pencarian gambar terbalik, analisis forensik foto, EXIF, pengenalan wajah, font, dan metadata.|Masukkan path file atau URL gambar. Pengenalan wajah hanya dengan dasar hukum/izin; hargai privasi.
#Image Search|Mesin pencari gambar umum.
Google Images|https://www.google.com/search?tbm=isch&q={q}
Bing Images|https://www.bing.com/images/search?q={q}
Yandex Images|https://yandex.com/images/search?text={q}
Flickr|https://www.flickr.com/search/?text={q}
#Image Search and Identification|Mengenali isi gambar dan mencari sumber aslinya.
cek sumber gambar|@image_source
Google Lens|https://lens.google.com/
#Reverse Image Search Engines and automation tools|Pencarian gambar terbalik dan otomatisasinya.
TinEye|https://tineye.com/
Bing Visual Search|https://www.bing.com/visualsearch
Search by Image (Ekstensi Browser)|https://github.com/dessant/search-by-image
Karma Decay (Reddit)|https://karmadecay.com/
#Other Image Search Engines|Mesin pencari gambar tambahan.
Baidu Image Search|https://image.baidu.com/
Sogou Image Search|https://pic.sogou.com/
Pexels|https://www.pexels.com/search/{q}/
#Image Analysis|Analisis forensik dan keaslian gambar.
FotoForensics|https://fotoforensics.com/
Forensically|https://29a.ch/photo-forensics/
Jeffrey's Image Metadata Viewer|http://exif.regex.info/exif.cgi
Aperisolve|https://www.aperisolve.com/
#Image Analyze|Analisis lanjutan isi gambar dan steganografi.
Stegonline|https://stegonline.georgeom.net/
#Exif Analyze and editing|Membaca dan menghapus metadata EXIF.
metadata|@exif_view
Hapus Metadata (EXIF Strip)|@exif_strip
ExifTool (Situs Resmi)|https://exiftool.org/
Meta Shield|
Get-Metadata|https://www.get-metadata.com/
ExifTool (Metadata Lengkap Semua File)|!exiftool
#Face recognition and search|Pencarian wajah (gunakan hanya dengan izin dan dasar hukum yang jelas).
PimEyes|https://pimeyes.com/
Search4faces|https://search4faces.com/
#Font Indenfication (Identifikasi Font)|Mengenali jenis huruf dari gambar.
WhatTheFont|https://www.myfonts.com/pages/whatthefont
Font Squirrel Matcherator|https://www.fontsquirrel.com/matcherator
Identifont|https://www.identifont.com/
WhatFontIs|https://www.whatfontis.com/

@Video, Suara & Musik|Pencarian video, verifikasi video, identifikasi lagu/suara, analisis audio, dan layanan musik.|Gunakan tautan video atau judul lagu; beberapa alat meminta kata kunci.
#Video Search and Other Video Tools|Mesin pencari video dan alat verifikasi video.
YouTube Search|https://www.youtube.com/results?search_query={q}
YouTube Data Viewer|https://citizenevidence.amnestyusa.org/
Youtube GeoFinder|https://mattw.io/youtube-geofind/location
Startpage Video Search|https://www.startpage.com/do/search?cat=video&q={q}
invidio (Invidious)|https://invidious.io/
Aol Videos|
Mefeedia|
Bing Videos|https://www.bing.com/videos/search?q={q}
Blinkx|
Crowd Tangle|
Clip Blast|
DailyMotion|https://www.dailymotion.com/search/{q}
Internet Archive: Open Source Videos|https://archive.org/details/opensource_movies
LiveLeak|
Metacafe|
Metatube|
Archive TV News|https://archive.org/details/tv
Vimeo|https://vimeo.com/search?q={q}
Yahoo Video Search|https://video.search.yahoo.com/search/video?p={q}
yt-dlp (Metadata Video)|!ytdlp
#Video editing and analyze|Analisis dan pengeditan video untuk verifikasi.
InVID-WeVerify Plugin|https://www.invid-project.eu/tools-and-services/invid-verification-plugin/
FFmpeg|https://ffmpeg.org/
MediaInfo|https://mediaarea.net/en/MediaInfo
Watch Frame by Frame|https://www.watchframebyframe.com/
FFprobe (Analisis Video/Audio)|!ffprobe
#Sound indefication and analyze (Identifikasi Suara)|Mengenali lagu dan suara dari rekaman.
Shazam|https://www.shazam.com/
SoundHound|https://www.soundhound.com/
AudD|https://audd.io/
ACRCloud|https://www.acrcloud.com/
Musipedia|https://www.musipedia.org/
#Sound search and analyze|Pencarian efek suara dan analisis spektrum audio.
Freesound|https://freesound.org/search/?q={q}
Audacity|https://www.audacityteam.org/
Sonic Visualiser|https://www.sonicvisualiser.org/
Praat|https://www.fon.hum.uva.nl/praat/
#Music Streaming Services|Layanan musik streaming untuk pencarian lagu dan artis.
Spotify|https://open.spotify.com/search/{q}
Apple Music|https://music.apple.com/
YouTube Music|https://music.youtube.com/search?q={q}
SoundCloud|https://soundcloud.com/search?q={q}
Deezer|https://www.deezer.com/
Tidal|https://tidal.com/
Bandcamp|https://bandcamp.com/search?q={q}
Last.fm|https://www.last.fm/search?q={q}

@Berita & Fakta|Berita nasional/internasional terkini dari sumber tepercaya, agregator, dan pemeriksa fakta.|Pilih 'cek berita' untuk ringkasan berita 24 jam terakhir, atau pratinjau portal berita dan pemeriksa fakta.
#News|Berita terkini dan portal media utama.
cek berita internasional / nasional hari ini (a1)|@news_today
Reuters|https://www.reuters.com/
AP News|https://apnews.com/
BBC News|https://www.bbc.com/news
Al Jazeera|https://www.aljazeera.com/
Antara News|https://www.antaranews.com/
Kompas|https://www.kompas.com/
Tempo|https://www.tempo.co/
detikcom|https://www.detik.com/
CNN Indonesia|https://www.cnnindonesia.com/
CNBC Indonesia|https://www.cnbcindonesia.com/
Kontan|https://www.kontan.co.id/
Bisnis.com|https://www.bisnis.com/
#News Digest and Discovery Tools|Agregator dan penemu berita lintas sumber.
Google News|https://news.google.com/search?q={q}
AllSides|https://www.allsides.com/
Ground News|https://ground.news/
Newsmap|https://newsmap.jp/
GDELT Project|https://www.gdeltproject.org/
Event Registry|https://eventregistry.org/
Media Cloud|https://search.mediacloud.org/
#Fact Checking|Pemeriksa fakta untuk melawan hoaks dan disinformasi.
Snopes|https://www.snopes.com/
Google Fact Check Explorer|https://toolbox.google.com/factcheck/explorer
TurnBackHoax (MAFINDO)|https://turnbackhoax.id/
Cek Fakta Tempo|https://www.tempo.co/cek-fakta
PolitiFact|https://www.politifact.com/
FactCheck.org|https://www.factcheck.org/
Full Fact|https://fullfact.org/

@Bencana Alam|Peristiwa bencana alam nasional & internasional: gempa, peringatan global, dan berita bencana tepercaya.|Pilih 'cek peristiwa bencana alam' lalu pilih cakupan (1 nasional / 2 internasional). Info resmi: BMKG, BNPB, USGS.
#Pemantauan Bencana Terkini|Ringkasan otomatis dari BMKG, USGS, GDACS, dan berita.
cek peristiwa bencana alam internasional/nasional hari ini (a1)|@disaster_today
#Sumber Resmi Bencana|Portal resmi pemantauan dan peringatan dini bencana.
BMKG|https://www.bmkg.go.id/
BNPB|https://bnpb.go.id/
InaRISK|https://inarisk.bnpb.go.id/
USGS Earthquakes|https://earthquake.usgs.gov/earthquakes/map/
GDACS|https://www.gdacs.org/
Tsunami.gov (NOAA)|https://www.tsunami.gov/

@Keuangan, Saham & Kripto|Cek emiten saham, wallet kripto, NFT, broker, bank, dan penyelidikan kripto.|Input kode saham 4-5 huruf (mis. TMPO), alamat wallet, atau nama broker. Bukan saran investasi.
#Saham & Broker (Mandiri)|Fitur cek langsung: emiten BEI, akun broker, dan sumber data pasar.
Cek emiten|@emiten
cek akun broker|@broker
IDX (Bursa Efek Indonesia)|https://www.idx.co.id/
TradingView|https://www.tradingview.com/
#Kripto & NFT (Mandiri)|Pemeriksaan alamat wallet dan NFT di blockchain publik.
cek kode wallet crypto|@wallet
cek NFT|@nft
#Cryptocurrency Investigations|Block explorer dan alat penelusuran transaksi kripto.
Bitcoinwhoswho|https://www.bitcoinwhoswho.com/
Blockchain Info|https://www.blockchain.com/explorer
Block Explorer|https://blockexplorer.com/
Blockonomics|https://www.blockonomics.co/
Wallet Explorer|https://www.walletexplorer.com/
Block Trail|
Ether Chain|https://www.etherchain.org/
EtherScan|https://etherscan.io/
Token View|https://tokenview.io/
Explore Bitcoin|
Block Chair|https://blockchair.com/
Mblocks|
Chain Radar|
Xmrchain|https://xmrchain.net/
Monero Wallet Hunter|
Bitref|https://bitref.com/
Live Coin Watch|https://www.livecoinwatch.com/
Blockpath|
#Bank information search|Informasi bank, kode SWIFT/IBAN, dan regulator perbankan.
Bank Indonesia|https://www.bi.go.id/
OJK|https://www.ojk.go.id/
BIC / SWIFT Code Lookup (Wise)|https://wise.com/gb/swift-codes
IBAN calculator|https://www.iban.com/calculate-iban
IBAN checker|https://www.iban.com/iban-checker

@Perusahaan, Properti & Pekerjaan|Riset perusahaan, merek dagang, tender, properti, dan lowongan kerja (termasuk khusus Indonesia).|Masukkan nama perusahaan, merek, atau kata kunci pekerjaan pada kolom {q}.
#Company Research|Data perusahaan dan registrasi badan usaha.
OpenCorporates|https://opencorporates.com/companies?q={q}
Crunchbase|https://www.crunchbase.com/textsearch?q={q}
SEC EDGAR|https://www.sec.gov/edgar/search/
AHU Online (Kemenkumham)|https://ahu.go.id/
OSS RBA (NIB Indonesia)|https://oss.go.id/
Companies House (Inggris)|https://find-and-update.company-information.service.gov.uk/search?q={q}
#Company information search|Pemilik manfaat, sanksi, dan identitas hukum perusahaan.
OCCRP Aleph|https://aleph.occrp.org/search?q={q}
OpenOwnership Register|https://register.openownership.org/
GLEIF LEI Search|https://search.gleif.org/
OpenSanctions|https://www.opensanctions.org/search/?q={q}
#Brand/trademark information search|Pencarian merek dagang dan paten.
WIPO Global Brand Database|https://branddb.wipo.int/
USPTO Trademark Search|https://tmsearch.uspto.gov/
EUIPO TMview|https://www.tmdn.org/tmview/
PDKI DJKI (Indonesia)|https://pdki-indonesia.dgip.go.id/
Google Patents|https://patents.google.com/?q={q}
#Tender/shipment information search|Informasi tender pemerintah dan data pengiriman/impor.
INAPROC (LPSE Indonesia)|https://inaproc.id/
TED Tenders (Eropa)|https://ted.europa.eu/
UN Global Marketplace|https://www.ungm.org/
Volza|https://www.volza.com/
Zauba|https://www.zauba.com/
SAM.gov|https://sam.gov/
#Real estate|Pencarian properti dan harga pasar.
Rumah123|https://www.rumah123.com/
99.co Indonesia|https://www.99.co/id
Lamudi Indonesia|https://www.lamudi.co.id/
Zillow|https://www.zillow.com/homes/{q}_rb/
#Job Search Resources|Portal lowongan kerja internasional.
LinkedIn Jobs|https://www.linkedin.com/jobs/search/?keywords={q}
Indeed|https://www.indeed.com/jobs?q={q}
Glassdoor|https://www.glassdoor.com/
#Job Search (yang diindonesia aja)|Portal lowongan kerja khusus Indonesia.
JobStreet Indonesia|https://www.jobstreet.co.id/id/job-search/{q}-jobs
Kalibrr|https://www.kalibrr.com/
Glints|https://glints.com/id/opportunities/jobs/explore?keyword={q}
Karir.com|https://karir.com/
Loker.id|https://www.loker.id/
Indeed Indonesia|https://id.indeed.com/jobs?q={q}
SIAPKerja (Kemnaker)|https://siapkerja.kemnaker.go.id/

@Pendidikan & Dokumen Resmi|Pencarian sekolah, NISN, SKCK, sumber akademik, dan situs tanya-jawab.|Masukkan nama sekolah/kota; layanan resmi pemerintah memakai captcha sehingga data siswa hanya bisa dicari di situs resminya.
#Sekolah & Dokumen Resmi (Mandiri)|Pencarian sekolah beserta peta/ulasan dan tautan layanan resmi NISN & SKCK.
Cari Nama Sekolah|@school_search
Cek nisn|@nisn_cek
Cek skck|@skck_cek
#Academic Resources and Grey Literature|Jurnal, preprint, dan literatur abu-abu.
Google Scholar|https://scholar.google.com/scholar?q={q}
BASE (Bielefeld)|https://www.base-search.net/Search/Results?lookfor={q}
CORE|https://core.ac.uk/search?q={q}
arXiv|https://arxiv.org/search/?query={q}
SSRN|https://www.ssrn.com/
OpenAlex|https://openalex.org/
Garuda (Indonesia)|https://garuda.kemdikbud.go.id/
Neliti|https://www.neliti.com/
#Q&A Sites|Situs tanya-jawab untuk mencari jawaban dan pakar.
Quora|https://www.quora.com/search?q={q}
StackExchange|https://stackexchange.com/search?q={q}
Stack Overflow|https://stackoverflow.com/search?q={q}
Brainly Indonesia|https://brainly.co.id/

@Belanja, Paket & Perangkat|Lacak resi paket, cek keaslian produk (kode barcode), IMEI, dan cari harga di marketplace.|Masukkan nomor resi, kode barcode, atau IMEI sesuai fitur. Skor keaslian bersifat indikatif, bukan jaminan.
#Paket, Produk & Perangkat (Mandiri)|Fitur cek langsung dari terminal.
Cek Resi Paket (Shopee, Lazada/Tiktok, Jne, Sicepatxpress, Ninja, Amazon, dll)|@pkg_track
Cek kode produk (yg keluar data dan persentase asli/kw beserta harga)|@product_code
cek IMEI and serial numbers|@imei
#Marketplace & Cek Keamanan Transaksi|Pencarian produk dan pemeriksa penipuan.
Shopee|https://shopee.co.id/search?keyword={q}
Tokopedia|https://www.tokopedia.com/search?q={q}
Lazada|https://www.lazada.co.id/catalog/?q={q}
Bukalapak|https://www.bukalapak.com/products?search%5Bkeywords%5D={q}
Blibli|https://www.blibli.com/cari/{q}
Amazon|https://www.amazon.com/s?k={q}
eBay|https://www.ebay.com/sch/i.html?_nkw={q}
AliExpress|https://www.aliexpress.com/wholesale?SearchText={q}
Cek Rekening (Komdigi)|https://cekrekening.id/
Cek BPOM|https://cekbpom.pom.go.id/
Cek IMEI Kemenperin|https://imei.kemenperin.go.id/

@Game & Hiburan|Cek akun game, platform gaming, dan budaya internet (meme).|Pilih game lalu masukkan ID/username; hanya data profil publik yang tampil.
#Gaming Platforms|Platform game dan pemeriksa akun.
cek akun game dengan id atau username|@game_acc
Steam Store|https://store.steampowered.com/search/?term={q}
Xbox|https://www.xbox.com/
PlayStation|https://www.playstation.com/
Epic Games Store|https://store.epicgames.com/
Roblox|https://www.roblox.com/
Tracker.gg|https://tracker.gg/
OP.GG|https://www.op.gg/
Twitch|https://www.twitch.tv/search?term={q}
Discord|https://discord.com/
#Meme|Penelusuran asal-usul dan penyebaran meme.
Know Your Meme|https://knowyourmeme.com/search?q={q}
Meme Center|https://www.memecenter.com/
9gag|https://9gag.com/
Meme Droid|
Me.Me|https://me.me/
Img Flip|https://imgflip.com/
Patriot Minear (Right-Wing)|

@Privasi & Keamanan Pribadi|Browser, VPN, enkripsi, penjelajahan offline, dan analisis jejak browser.|Pilih alat sesuai kebutuhan privasi; unduh hanya dari situs resmi pengembangnya.
#Browsers|Browser yang berfokus pada privasi.
Tor Browser|https://www.torproject.org/
Brave|https://brave.com/
Firefox|https://www.mozilla.org/firefox/
LibreWolf|https://librewolf.net/
Mullvad Browser|https://mullvad.net/en/browser
#Browser analyze|Menguji sidik jari (fingerprint) dan kebocoran data browser.
BrowserLeaks|https://browserleaks.com/
Cover Your Tracks (EFF)|https://coveryourtracks.eff.org/
AmIUnique|https://amiunique.org/fingerprint
#Offline Browsing|Menyimpan situs untuk dibaca atau dianalisis tanpa internet.
HTTrack|https://www.httrack.com/
SingleFile|https://github.com/gildas-lormeau/SingleFile
GNU Wget|https://www.gnu.org/software/wget/
Hunchly|https://www.hunch.ly/
#VPN Services|Layanan VPN dengan reputasi privasi yang baik.
Proton VPN|https://protonvpn.com/
Mullvad VPN|https://mullvad.net/
IVPN|https://www.ivpn.net/
Windscribe|https://windscribe.com/
Cloudflare WARP|https://one.one.one.one/
#Privacy and Encryption Tools|Aplikasi enkripsi, pesan aman, dan pengelola password.
Signal|https://signal.org/
GnuPG|https://gnupg.org/
VeraCrypt|https://www.veracrypt.fr/
Bitwarden|https://bitwarden.com/
KeePassXC|https://keepassxc.org/
Tails|https://tails.net/
Cryptomator|https://cryptomator.org/

@Kata Kunci, Data & Pemantauan|Riset kata kunci, tren, statistik, pemantauan perubahan web, dan alat bahasa.|Masukkan kata kunci atau topik pada kolom {q}; hasil tampil sebagai pratinjau di terminal.
#Keywords Discovery and Research|Menemukan kata kunci dan minat pencarian.
Google Trends|https://trends.google.com/trends/explore?q={q}
KeywordTool|https://keywordtool.io/
Keyword Spy|https://www.keywordspy.com/
One Look Reverse Dictionary|https://www.onelook.com/reverse-dictionary.shtml
Word Tracker|https://www.wordtracker.com/
Soovle|https://soovle.com/
Ubersuggest|https://neilpatel.com/ubersuggest/
AnswerThePublic|https://answerthepublic.com/
#Keywords, trends, news analytics|Analitik tren dan topik populer.
Exploding Topics|https://explodingtopics.com/
Wikipedia Pageviews|https://pageviews.wmcloud.org/
#Data and Statistics|Sumber data statistik resmi dan dataset terbuka.
BPS (Badan Pusat Statistik)|https://www.bps.go.id/
Satu Data Indonesia|https://data.go.id/
World Bank Data|https://data.worldbank.org/
Our World in Data|https://ourworldindata.org/
Statista|https://www.statista.com/
Kaggle Datasets|https://www.kaggle.com/datasets?search={q}
Google Dataset Search|https://datasetsearch.research.google.com/
#Web Monitoring|Memantau perubahan halaman web secara otomatis.
Visualping|https://visualping.io/
Distill|https://distill.io/
changedetection.io|https://changedetection.io/
Talkwalker Alerts|https://www.talkwalker.com/alerts
#Language Tools|Penerjemah dan kamus untuk riset lintas bahasa.
Google Translate|https://translate.google.com/?sl=auto&tl=id&text={q}
DeepL|https://www.deepl.com/translator
Linguee|https://www.linguee.com/
Omniglot|https://omniglot.com/
KBBI|https://kbbi.kemdikbud.go.id/

@Visualisasi & Otomasi|Infografis, analisis jaringan sosial, visualisasi data, otomasi ekstraksi data, dan aplikasi OSINT.|Alat bantu analisis lanjutan; sebagian membutuhkan pemasangan di perangkatmu.
#Infographics and Data Visualization|Membuat infografis dan grafik interaktif.
Flourish|https://flourish.studio/
Datawrapper|https://www.datawrapper.de/
Tableau Public|https://public.tableau.com/
RAWGraphs|https://www.rawgraphs.io/
Canva Infografis|https://www.canva.com/graphs/infographics/
#Social Network Analysis|Memetakan relasi antar akun dan entitas.
Gephi|https://gephi.org/
NodeXL|https://nodexl.com/
Cytoscape|https://cytoscape.org/
sixdefreeofwikipedia (Six Degrees of Wikipedia)|https://www.sixdegreesofwikipedia.com/
#Visualization tools|Diagram dan peta konsep untuk investigasi.
Kumu|https://kumu.io/
yEd|https://www.yworks.com/products/yed
Mermaid Live Editor|https://mermaid.live/
diagrams.net|https://app.diagrams.net/
#Routine/Data Extraction Automation|Otomasi pengumpulan data dan alur kerja rutin.
Scrapy|https://scrapy.org/
n8n|https://n8n.io/
Apify|https://apify.com/
Huginn|https://github.com/huginn/huginn
Zapier|https://zapier.com/
#NOOSINT tools|Kumpulan alat OSINT NOOSINT.
NOOSINT tools|
#Apps and programs|Aplikasi dan program OSINT yang dipasang di komputer.
SpiderFoot|https://www.spiderfoot.net/
Recon-ng|https://github.com/lanmaster53/recon-ng
Amass|https://github.com/owasp-amass/amass

@Sumber Belajar OSINT|Video, blog, panduan, dan daftar sumber (awesome lists) untuk belajar OSINT.|Pilih tautan untuk dipratinjau di terminal; pilih sumber terkini karena banyak situs OSINT sering berubah.
#OSINT Videos|Kanal video pembelajaran OSINT.
OSINT Dojo (YouTube)|https://www.youtube.com/@OSINTDojo
Bellingcat (YouTube)|https://www.youtube.com/@bellingcat
OSINT Curious (YouTube)|https://www.youtube.com/@OSINTCurious
The Cyber Mentor (YouTube)|https://www.youtube.com/@TheCyberMentor
#OSINT Blogs|Blog dan buletin OSINT.
Bellingcat|https://www.bellingcat.com/
OSINT Curious Project|https://osintcurio.us/
Sector035 Week in OSINT|https://sector035.nl/
IntelTechniques Blog|https://inteltechniques.com/blog/
#Other Resources|Sumber dan komunitas OSINT lainnya.
Trace Labs|https://www.tracelabs.org/
OSINT Techniques|https://www.osinttechniques.com/
start.me OSINT Dashboards|https://start.me/
#Related Awesome Lists|Daftar sumber OSINT terkurasi di GitHub.
awesome-osint|https://github.com/jivoi/awesome-osint
osint_stuff_tool_collection|https://github.com/cipher387/osint_stuff_tool_collection
#Other Tools|Alat lain-lain untuk investigasi.
TBG 5|
DMI Tools|
Black Book Online|https://www.blackbookonline.info/
Melissa Data|https://www.melissa.com/
"""


# =====================================================================
#  v3 - KATALOG TAMBAHAN (digabung ke kategori lama; duplikat nama/tautan otomatis dibuang, yang lama menang)
# =====================================================================
OLD_GROUP_SUB = {"Email & Kebocoran": SUB_E, "Username & Sosial": SUB_U, "Telepon": SUB_U, "Domain & Jaringan": SUB_D, "Intelijen Ancaman": SUB_T,
                 "Gambar, Video & Metadata": SUB_I, "Kerangka Kerja OSINT": SUB_K, "Pemindaian (Izin Sah)": SUB_S}
STATUS_ORD = {"aktif": 0, "jarang": 1, "usang": 2, "arsip": 3, "tidakrelevan": 4, "mati": 5}


def tool_sub(t):
    return t.get("sub") or OLD_GROUP_SUB.get(t.get("group"), SUB_K)


_OLD_KEYS = set(re.findall(r"\|!([A-Za-z0-9_]+)", CATALOG))
_THEME = [
    (SUB_U, "Investigasi Orang & Username", "", "", "Tool GitHub: Username & Akun Sosial"),
    (SUB_E, "EmailHunter", "", "", "Tool GitHub: Email & Kebocoran"),
    (SUB_D, "Recon & Pemetaan Target", "Penemuan subdomain, DNS, dan permukaan serangan sebuah domain (recon). Hanya untuk target milik sendiri atau berizin.",
     "Pilih tool, jawab y/n untuk pasang, lalu ketik domain saat diminta. Pemindai aktif meminta konfirmasi izin.", "Tool GitHub: Recon"),
    (SUB_N, "Analisis Jaringan", "Pemindaian jaringan, analisis lalu lintas, BGP, TLS, dan infrastruktur server.",
     "Pilih tool; tool berat (Wireshark, Zeek, ntopng) tampil sebagai panduan langkah demi langkah.", "Tool GitHub: Jaringan & Infrastruktur"),
    (SUB_C, "Crawler, Scraper & Arsip Web", "Perayap web, scraper, dan pengarsip halaman agar bukti tidak hilang.",
     "Pilih tool; pustaka Python dites dengan satu URL contoh dan hasilnya tampil di terminal.", "Tool GitHub: Crawler & Arsip"),
    (SUB_V, "Video, Suara & Musik", "", "", "Tool GitHub: Video, Audio & Streaming"),
    (SUB_I, "Gambar, Wajah & Metadata", "", "", "Tool GitHub: OCR & Metadata"),
    (SUB_G, "Geospasial, Peta & Satelit", "", "", "Tool GitHub: Geospasial"),
    (SUB_A, "Analisis Data & NLP", "Olah dataset investigasi, graf hubungan, dan teks: pandas, DuckDB, NetworkX, spaCy, dan lainnya.",
     "Beri path berkas data (CSV/GeoJSON/teks); ringkasan tampil di terminal.", "Tool GitHub: Data & NLP"),
    (SUB_T, "Threat Intelligence & Keamanan", "", "", "Tool GitHub: Threat Intel & Kerentanan"),
    (SUB_F, "Forensik Digital & Malware", "Forensik memori/disk, analisis malware, YARA, dan rekayasa balik. Gunakan di lingkungan terisolasi.",
     "Beri path berkas yang diperiksa; hasil tampil di terminal. Jangan menjalankan sampel malware di komputer utama.", "Tool GitHub: Forensik & Malware"),
    (SUB_M, "Mobile & Aplikasi", "Analisis aplikasi Android/iOS: dekompilasi APK, privasi, instrumentasi, dan verifikasi ponsel.",
     "Pilih tool; beberapa butuh Java/Docker (diperiksa otomatis).", "Tool GitHub: Android & iOS"),
    (SUB_K, "Kerangka OSINT & Investigasi", "Platform investigasi lengkap (OpenCTI, Aleph, Datashare) dan daftar sumber OSINT terkurasi.",
     "Platform berat tampil sebagai panduan pemasangan; daftar sumber bisa dibaca langsung di terminal.", "Tool GitHub: Kerangka & Daftar"),
    (SUB_ID, "Pendidikan & Dokumen Resmi", "", "", "Tool GitHub: Data & Layanan Indonesia"),
    (SUB_P, "Platform Sosial Lainnya", "", "", "Tool GitHub: Komunitas, Feed & Pesan"),
    (SUB_S, "Pentesting & Keamanan Cloud", "Pemindai kerentanan, SBOM, kode, cloud, dan kontainer: Trivy, Semgrep, OSV-Scanner, dan lainnya.",
     "Pilih tool; pemindai aktif hanya untuk sistem milik sendiri/berizin.", "Tool GitHub: Pemindai Keamanan"),
]


def _thematic_text():
    out = []
    for sub, cat, about, how, subname in _THEME:
        ks = [(k, t) for k, t in TOOLS.items() if k not in _OLD_KEYS and tool_sub(t) == sub and t.get("status") in ("aktif", "jarang")]
        if not ks:
            continue
        out.append("@%s|%s|%s" % (cat, about, how))
        ks.sort(key=lambda x: (STATUS_ORD.get(x[1].get("status"), 3), x[1]["title"].lower()))
        out.append("#%s|Tool dari GitHub/PyPI; aktif di atas. Belum terpasang? Instalasi ditawarkan otomatis (y/n)." % subname)
        for k, t in ks:
            out.append("%s|!%s" % (t["title"], k))
    return "\n".join(out)


CATALOG_EXTRA = """
@Domain, IP & Website
#Modul Baru: IP, DNS & Arsip|IP multi-sumber, ASN/BGP, DNS banding, domain terdaftar, dan arsip web dunia.
IP Multi-Sumber (Lokasi & Pemilik)|@ip_multi
ASN, BGP & PeeringDB|@bgp_asn
Geolokasi WiFi dari BSSID|@wifi_geo
Cari Domain Terdaftar (DomainsDB)|@domainsdb
Bandingkan DNS Google vs Cloudflare|@dns_banding
Arsip Web Internasional (Wayback, Arquivo, LoC)|@arsip_multi

@Threat Intelligence & Keamanan
#Reputasi & Kerentanan (API)|Reputasi IP/domain/URL/hash dan pencarian CVE lewat API publik. Sebagian butuh API key gratis (peringatan kuning).
VirusTotal: Reputasi IP/Domain/URL/Hash|@vt_cek
AbuseIPDB: Skor Penyalahgunaan IP|@abuseip_cek
AlienVault OTX: Intel Ancaman|@otx_cek
urlscan.io: Riwayat Pemindaian|@urlscan_cari
Phisherman: Cek Domain Phishing|@phisherman_cek
Cari Kerentanan CVE (NVD)|@cve_cari

@Keuangan, Saham & Kripto
#Kurs, VAT & Bank Dunia|Kurs mata uang, verifikasi nomor VAT Eropa, bank Amerika, dan berita pasar.
Kurs Mata Uang Terbaru|@kurs_mata_uang
Cek Nomor VAT Uni Eropa|@vat_cek
Cari Bank Amerika (FDIC)|@fdic_bank
Berita Pasar Alpaca|@alpaca_berita

@Telepon & Nomor
#Kartu HP & SIM|Cek kartu HP: operator, ICCID/IMSI, dan cara cek registrasi resmi.
Cek Kartu HP Lengkap (Operator, SIM, Registrasi)|@kartu_hp_lengkap

@Platform Sosial Lainnya
#Akun, Saluran & Komunitas|Cek akun dan saluran di berbagai platform lewat halaman publik atau API resmi.
Cek Akun Telegram, X, Snapchat, Pinterest, TikTok, Spotify|@sosmed_cek
Cek Saluran WhatsApp|@wa_channel
Server dan ID Discord|@discord_cek
Profil Hacker News|@hn_user
Blog Blogger / Blogspot|@blogger_cek
Kanal Twitch (API Resmi)|@twitch_user
Kanal YouTube (API Resmi)|@youtube_channel

@Investigasi Orang & Username
#Username Sangat Luas|Satu username diperiksa di 600+ situs sekaligus.
Cek Username di 600+ Situs (WhatsMyName)|@user_wmn

@Game & Hiburan
#Username Game & Bioskop|Cek username game di puluhan platform dan lihat jadwal bioskop.
Cek Username Game (Sangat Luas)|@user_game
Jadwal Bioskop Indonesia|@bioskop_jadwal

@Kendaraan
#Pajak Kendaraan Resmi|Dari plat nomor ke situs resmi cek pajak provinsi. Tekan o untuk membuka di browser.
Cek Pajak Kendaraan per Provinsi (Situs Resmi)|@pajak_kendaraan

@Berita & Fakta
Berita Terkini Multi-Sumber Paralel|@news_cepat

@Mesin Pencari
Pencarian DuckDuckGo & Marginalia|@cari_web_bebas

@Pemantauan Internasional & Berita Cepat|Pemantauan dunia: gempa, bencana, penerbangan, berita global, dan tautan pemantau resmi (peta kapal, internet, konflik).|Buka Pemantauan Internasional lalu pilih 1-5; Berita Ultra Cepat mengambil puluhan RSS sekaligus dalam hitungan detik.
Pemantauan Internasional (Gempa, Bencana, Pesawat)|@monitor_intl
Berita OSINT Ultra Cepat (Fiber Optik)|@news_cepat
osirisai.live (Pemantauan OSINT)|https://osirisai.live
GDELT: Peristiwa Dunia Real-Time|https://www.gdeltproject.org/
Peta Peringatan Bencana Global (GDACS)|https://www.gdacs.org/
Gangguan Internet Dunia (IODA)|https://ioda.inetintel.cc.gatech.edu/
Sensor Internet Dunia (OONI Explorer)|https://explorer.ooni.org/
Trafik Internet Dunia (Cloudflare Radar)|https://radar.cloudflare.com/
Status Layanan Down? (Downdetector)|https://downdetector.id/

@Pusat Bantuan & Troubleshooting|Satu tempat untuk diagnosa otomatis, solusi gagal pasang, lupa pasang/isi input, cara keluar dari tool, dan kunci API. Bahasa sederhana.|Buka Pusat Bantuan lalu pilih 1-4. Bisa juga ditekan b kapan saja di menu.
Pusat Bantuan Lengkap (Diagnosa & Solusi)|@pusat_bantuan
Kelola Kunci API|@kunci_api

@OSINT Browser Gratis (Tanpa Bayar)|Situs OSINT yang bisa dipakai gratis di browser (tanpa langganan wajib). Dibuka sebagai pratinjau di terminal; o<nomor> membukanya di browser.|Pilih sub-kategori lalu situs. Sebagian situs punya paket berbayar tambahan, tetapi fitur dasarnya gratis.
#Pilihan Baru: Pemantauan Langsung|Peta dan pelacak real-time yang gratis.
Pemantauan OSINT osirisai.live|https://osirisai.live
Liveuamap Peta Konflik Langsung|https://liveuamap.com/
ADS-B Exchange Pesawat Tanpa Sensor|https://globe.adsbexchange.com/
VesselFinder Kapal Dunia|https://www.vesselfinder.com/
NASA FIRMS Titik Api Dunia|https://firms.modaps.eosdis.nasa.gov/map/
Copernicus Browser Citra Satelit|https://browser.dataspace.copernicus.eu/
Windy Cuaca dan Angin|https://www.windy.com/
ACLED Data Konflik|https://acleddata.com/
#Pilihan Baru: API, IP & Jaringan|Layanan IP dan jaringan dengan tingkat gratis.
IPQuery Lokasi dan Risiko IP|https://ipquery.io/
IPLocate Data IP|https://iplocate.io/
ip-api Geolokasi IP|https://ip-api.com/
PeeringDB Profil Jaringan|https://www.peeringdb.com/
BGPView Data ASN|https://bgpview.io/
DNSCheck Alat DNS|https://dnscheck.tools/
DomainsDB Cari Domain|https://domainsdb.info/
PacketTotal Analisis PCAP|https://packettotal.com/
IPinfoDB Geolokasi|https://www.ipinfodb.com/
#Pilihan Baru: Keamanan & Reputasi|Periksa reputasi dan kerentanan secara gratis.
VirusTotal Tingkat Gratis|https://www.virustotal.com/
AbuseIPDB Laporan IP|https://www.abuseipdb.com/
AlienVault OTX Komunitas|https://otx.alienvault.com/
urlscan.io Pindai URL|https://urlscan.io/
NVD Basis Data Kerentanan|https://nvd.nist.gov/vuln/search
OpenCVE Pantau CVE|https://www.opencve.io/
Phisherman Basis Phishing|https://phisherman.gg/
#Pilihan Baru: Arsip & Perpustakaan Digital|Arsip web dan koleksi sejarah dunia.
Wayback Machine Arsip Web|https://web.archive.org/
Arquivo.pt Arsip Web Portugal|https://arquivo.pt/
UK Web Archive|https://www.webarchive.org.uk/
Trove Arsip Australia|https://trove.nla.gov.au/
Library of Congress Arsip Web|https://www.loc.gov/web-archives/
#Pilihan Baru: Username, Sosial & Komunitas|Cari jejak akun dan komunitas.
WhatsMyName Web|https://whatsmyname.app/
Namechk Cek Username|https://namechk.com/
TGStat Direktori Telegram|https://tgstat.com/
Hacker News Pencarian (Algolia)|https://hn.algolia.com/
Marginalia Mesin Pencari Independen|https://search.marginalia.nu/
#Pilihan Baru: Layanan Lokal & Hiburan|Layanan publik Indonesia dan hiburan.
XXI Jadwal Bioskop|https://www.cinema21.co.id/
CGV Indonesia|https://www.cgv.id/
Cinepolis Indonesia|https://www.cinepolis.co.id/
TIX ID Tiket Film|https://www.tix.id/
BMKG Gempa dan Cuaca|https://www.bmkg.go.id/
Tracker.gg Statistik Game|https://tracker.gg/
NameMC Profil Minecraft|https://namemc.com/
""" + "\n" + _thematic_text() + "\n"
# =====================================================================
#  v3 - PARSER KATALOG & MESIN MENU (rata tengah, kartu, chip status, jam hidup, menu penutup)
# =====================================================================
class GoHome(Exception):
    pass


class JumpTo(Exception):
    def __init__(self, node):
        Exception.__init__(self)
        self.node = node


class Node:
    def __init__(self, kind, name, info=None, target=""):
        self.kind = kind          # root | cat | sub | link | mod | tool
        self.name = name
        self.info = info or []
        self.target = target
        self.children = []
        self.parent = None
        self.ref = False          # True = tampilan silang (entri aslinya ada di kategori lain)


def norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _url_key(u):
    return re.sub(r"^https?://(www\.)?", "", u.strip().lower()).rstrip("/")


def new_state():
    return {"names": set(), "tools": set(), "urls": set()}


def parse_catalog(text, root=None, st=None, dedupe_url=False):
    """Urai teks katalog. Kategori/sub bernama sama DIGABUNG. Entri duplikat dibuang (yang lama menang):
    nama sama, kunci tool sama, dan (bila dedupe_url) tautan web yang sama."""
    root = root or Node("root", "Menu Utama")
    st = st if st is not None else new_state()
    cat = sub = None
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith(";"):
            continue
        if line[0] == "@":
            parts = line[1:].split("|")
            if parts and parts[0] and not parts[0][0].isalnum():
                parts = parts[1:]          # kompatibel dengan katalog lama yang berisi emoji
            name = parts[0].strip()
            found = next((c for c in root.children if c.kind == "cat" and norm(c.name) == norm(name)), None)
            if found is None:
                found = Node("cat", name, [p.strip() for p in parts[1:3]])
                found.parent = root
                root.children.append(found)
            elif not found.info:
                found.info = [p.strip() for p in parts[1:3]]
            cat, sub = found, None
        elif line[0] == "#" and cat is not None:
            parts = line[1:].split("|")
            name = parts[0].strip()
            found = next((c for c in cat.children if c.kind == "sub" and norm(c.name) == norm(name)), None)
            if found is None:
                found = Node("sub", name, [p.strip() for p in parts[1:2]])
                found.parent = cat
                cat.children.append(found)
            sub = found
        elif cat is not None:
            parts = line.split("|", 1)
            name = parts[0].strip()
            target = parts[1].strip() if len(parts) > 1 else ""
            key = norm(name)
            if not key or key in st["names"]:
                continue
            if target.startswith("@"):
                node = Node("mod", name, target=target[1:])
            elif target.startswith("!"):
                node = Node("tool", name, target=target[1:])
                if node.target in st["tools"]:
                    continue
                st["tools"].add(node.target)
            else:
                node = Node("link", name, target=target)
                if target and "{q}" not in target:
                    uk = _url_key(target)
                    if dedupe_url and uk in st["urls"]:
                        continue
                    st["urls"].add(uk)
            st["names"].add(key)
            holder = sub if sub is not None else cat
            node.parent = holder
            holder.children.append(node)
    return root


def prune(n):
    n.children = [c for c in n.children if c.kind not in ("cat", "sub") or (prune(c) or c.children)]
    return n


# ---------- kategori khusus: Github Tools (semua repo) & OSINT Browser Gratis ----------
GH_CAT = "Github Tools"
FREE_CAT = "OSINT Browser Gratis (Tanpa Bayar)"
PAID_HOSTS = ("maltego.com", "pipl.com", "spokeo.com", "lexisnexis", "clearview.ai", "socialcatfish.com", "truthfinder.com", "beenverified.com", "intelligencex")
def add_github_category(root, placed, names):
    cat = Node("cat", GH_CAT, ["Semua tool dari GitHub dalam satu tempat, dipisah per fungsi. Tool yang aktif di atas; yang lama/tidak relevan dipisah di sub-kategori terakhir.",
                               "Pilih sub-kategori lalu tool. Bila belum terpasang, Giga OSINT menawarkan pasang otomatis (y/n). Tekan x untuk memeriksa keamanan sebuah repo GitHub."])
    cat.parent = root
    order = [SUB_X] + [n for n, _ in GH_SUBS if n not in (SUB_X, SUB_Z)] + [SUB_Z]
    about = dict(GH_SUBS)
    subs = {}
    for name in order:
        s = Node("sub", name, [about.get(name, "")])
        s.parent = cat
        subs[name] = s
        cat.children.append(s)
    for key, t in TOOLS.items():
        s = subs.get(tool_sub(t)) or subs[SUB_K]
        n = Node("tool", t["title"], target=key)
        n.parent = s
        n.ref = key in placed
        if not n.ref and norm(n.name) in names:
            n.name += " (repo)"
        s.children.append(n)
    for s in subs.values():
        s.children.sort(key=lambda n: (STATUS_ORD.get(TOOLS[n.target].get("status"), 3), TOOLS[n.target]["title"].lower()))
    cat.children = [s for s in cat.children if s.children]
    root.children.insert(0, cat)
    return cat


def leaves(n):
    out = []
    for c in n.children:
        out += [c] if c.kind in ("link", "mod", "tool") else leaves(c)
    return out


def clone_ref(n):
    holder = n.parent
    about = n.info[0] if n.info else (holder.info[0] if holder is not None and holder.info else "")
    c = Node(n.kind, n.name, [about] if about else [], n.target)
    c.ref = True
    return c


def add_free_category(root):
    cat = next((c for c in root.children if norm(c.name) == norm(FREE_CAT)), None)
    if cat is None:
        cat = Node("cat", FREE_CAT, [], "")
        cat.parent = root
        root.children.append(cat)
    cat.info = cat.info or ["Situs OSINT yang bisa dipakai gratis di browser (tanpa langganan wajib). Dibuka sebagai pratinjau di terminal; o<nomor> membukanya di browser.",
                            "Pilih sub-kategori lalu situs. Sebagian situs punya paket berbayar tambahan, tetapi fitur dasarnya gratis."]
    for c in list(root.children):
        if c is cat or c.name == GH_CAT:
            continue
        links = [n for n in leaves(c) if n.kind == "link" and not any(h in (n.target or "").lower() for h in PAID_HOSTS)]
        if not links:
            continue
        s = Node("sub", c.name, [c.info[0] if c.info else ""])
        s.parent = cat
        for n in links:
            r = clone_ref(n)
            r.parent = s
            s.children.append(r)
        cat.children.append(s)
    return cat


SUB_ID_NAMES = {
    "Email Search / Email Check": "Cari & Cek Email", "Placeholder Sections (Spam, Risiko, Kebocoran)": "Spam, Risiko & Kebocoran Nomor",
    "Phone Number Research": "Riset Nomor Telepon", "Domain and IP Research": "Riset Domain & IP", "Website traffic look up (Lalu Lintas Situs)": "Lalu Lintas Situs",
    "Website technology look up (Layanan Eksternal)": "Teknologi Situs (Layanan Eksternal)", "Web History and Website Capture": "Riwayat Web & Tangkapan Situs",
    "Analytics & Affiliate ID's": "ID Analitik & Afiliasi", "Major Social Networks (social networks)": "Jejaring Sosial Besar",
    "Real-Time Search, Social Media Search, and General Social Media Tools": "Pencarian Waktu Nyata & Alat Media Sosial Umum", "Social Media Tools": "Alat Media Sosial",
    "Blog Search": "Pencarian Blog", "Forums and Discussion Boards Search": "Pencarian Forum & Diskusi", "General Search": "Pencarian Umum",
    "Main National Search Engines": "Mesin Pencari Nasional Utama", "International Search Engines": "Mesin Pencari Internasional", "Meta Search": "Meta Pencarian",
    "Privacy Focused Search Engines": "Mesin Pencari Fokus Privasi", "Specialty Search Engines": "Mesin Pencari Khusus", "Similar Sites Search": "Cari Situs Serupa",
    "Visual Search and Clustering Search Engines": "Pencarian Visual & Pengelompokan", "Document and Slides Search": "Cari Dokumen & Slide", "File Search": "Cari Berkas",
    "Open directories search engines": "Direktori Terbuka", "Universal search tools": "Alat Pencarian Universal", "Tools for DuckDuckGo": "Alat untuk DuckDuckGo",
    "Tools for Google": "Alat untuk Google", "Filesharing Search Engines": "Cari Berbagi Berkas", "Code Search": "Cari Kode",
    "Dark Web Search Engines": "Mesin Pencari Dark Web", "Darknet/deepweb search tools": "Alat Pencarian Darknet/Deep Web", "Data Breach Search Engines": "Cari Data Bocor",
    "Threat Actor Search": "Cari Pelaku Ancaman", "Live Cyber Threat Maps": "Peta Ancaman Siber Langsung", "Bugbounty/vulnerabilities search tools": "Bug Bounty & Pencarian Kerentanan",
    "Public buckets search tools": "Cari Bucket Cloud Publik", "Offensive Security (Authorized Testing Only)": "Keamanan Ofensif (Pengujian Berizin Saja)",
    "People Investigations": "Investigasi Orang", "Expert Search": "Cari Ahli", "Arrests, Inmate & Court Search": "Penangkapan, Narapidana & Pengadilan",
    "Vehicle / Automobile Research (Vehicle)": "Riset Kendaraan", "Flight Tracking": "Pelacakan Penerbangan", "Aviation": "Penerbangan", "Drones": "Drone",
    "Marine & Cargo Tracking": "Pelacakan Kapal & Kargo", "Maritime": "Maritim", "Railway": "Kereta Api", "Geospatial Research and Mapping Tools": "Riset Geospasial & Pemetaan",
    "Street View": "Street View", "Satellite/aerial imagery": "Citra Satelit & Udara", "Routes": "Rute", "Worldwide street webcams": "Webcam Jalan Dunia",
    "Social media and photos": "Media Sosial & Foto", "Nature": "Alam", "Transport": "Transportasi", "Communications, Internet, Technologies": "Komunikasi, Internet & Teknologi",
    "Anomalies and Lost Places": "Anomali & Tempat Terlupakan", "Military tracking": "Pelacakan Militer", "Military visalisation (Visualisasi Militer)": "Visualisasi Militer",
    "Sun and lunar Tools": "Alat Matahari & Bulan", "Image Search": "Cari Gambar", "Image Search and Identification": "Cari & Kenali Gambar",
    "Reverse Image Search Engines and automation tools": "Cari Gambar Terbalik & Otomasi", "Other Image Search Engines": "Mesin Cari Gambar Lain", "Image Analysis": "Analisis Gambar",
    "Image Analyze": "Analisis Citra", "Exif Analyze and editing": "Analisis & Edit EXIF", "Face recognition and search": "Pengenalan & Pencarian Wajah",
    "Font Indenfication (Identifikasi Font)": "Identifikasi Font", "Video Search and Other Video Tools": "Cari Video & Alat Video", "Video editing and analyze": "Edit & Analisis Video",
    "Sound indefication and analyze (Identifikasi Suara)": "Identifikasi & Analisis Suara", "Sound search and analyze": "Cari & Analisis Suara", "Music Streaming Services": "Layanan Musik Streaming",
    "News": "Berita", "News Digest and Discovery Tools": "Ringkasan & Penemuan Berita", "Fact Checking": "Cek Fakta", "Cryptocurrency Investigations": "Investigasi Kripto",
    "Bank information search": "Informasi Bank", "Company Research": "Riset Perusahaan", "Company information search": "Informasi Perusahaan",
    "Brand/trademark information search": "Merek Dagang", "Tender/shipment information search": "Tender & Pengiriman", "Real estate": "Properti",
    "Job Search Resources": "Sumber Lowongan Kerja", "Job Search (yang diindonesia aja)": "Lowongan Kerja Indonesia", "Academic Resources and Grey Literature": "Sumber Akademik & Literatur Abu-abu",
    "Q&A Sites": "Situs Tanya Jawab", "Gaming Platforms": "Platform Game", "Meme": "Meme", "Browsers": "Peramban", "Browser analyze": "Analisis Peramban",
    "Offline Browsing": "Penjelajahan Offline", "VPN Services": "Layanan VPN", "Privacy and Encryption Tools": "Alat Privasi & Enkripsi",
    "Keywords Discovery and Research": "Riset Kata Kunci", "Keywords, trends, news analytics": "Kata Kunci, Tren & Analitik Berita", "Data and Statistics": "Data & Statistik",
    "Web Monitoring": "Pemantauan Web", "Language Tools": "Alat Bahasa", "Infographics and Data Visualization": "Infografis & Visualisasi Data",
    "Social Network Analysis": "Analisis Jaringan Sosial", "Visualization tools": "Alat Visualisasi", "Routine/Data Extraction Automation": "Otomasi Ekstraksi Data",
    "Apps and programs": "Aplikasi & Program", "OSINT Videos": "Video OSINT", "OSINT Blogs": "Blog OSINT", "Other Resources": "Sumber Lain",
    "Related Awesome Lists": "Daftar Awesome Terkait", "Other Tools": "Alat Lain", "Tools (Geospasial)": "Alat Geospasial", "Files (Analisis File)": "Analisis Berkas",
    "Imageboards & Forum Anonim": "Imageboard & Forum Anonim", "Threat Intelligence": "Intelijen Ancaman", "Username Check": "Cek Username",
}


def rename_subs(n):
    for c in n.children:
        if c.kind == "sub":
            c.name = SUB_ID_NAMES.get(c.name, c.name)
        if c.kind in ("cat", "sub"):
            rename_subs(c)


def build_root():
    st = new_state()
    root = parse_catalog(CATALOG, None, st)
    parse_catalog(CATALOG_EXTRA, root, st, dedupe_url=True)
    placed = set(st["tools"])
    add_free_category(root)
    add_github_category(root, placed, st["names"])
    prune(root)
    rename_subs(root)
    head = [c for c in root.children if c.name in (GH_CAT, FREE_CAT)]
    tail = [c for c in root.children if c.name.startswith("Pusat Bantuan")]
    mid = [c for c in root.children if c not in head and c not in tail]
    head.sort(key=lambda c: 0 if c.name == GH_CAT else 1)
    root.children = head + mid + tail
    for c in root.children:
        c.parent = root
    return root


ROOT = build_root()
LEAF = ("link", "mod", "tool")


def node_path(n):
    out = []
    p = n.parent
    while p is not None and p.kind != "root":
        out.append(p.name)
        p = p.parent
    return list(reversed(out))


def in_github(n):
    while n is not None:
        if n.kind == "cat" and n.name == GH_CAT:
            return True
        n = n.parent
    return False


def all_entries():
    out = []

    def rec(n):
        for ch in n.children:
            if ch.kind in LEAF:
                if not ch.ref:
                    out.append((ch, node_path(ch)))
            else:
                rec(ch)
    rec(ROOT)
    return out


ALL = all_entries()


def count_entries(n):
    if n.kind in LEAF:
        return 1
    return sum(count_entries(c) for c in n.children)


def catalog_stats():
    k = {"link": 0, "mod": 0, "tool": 0}
    for n, _ in ALL:
        k[n.kind] += 1
    return k


_tool_counts_raw = tool_counts
_TC = {"t": 0.0, "v": (0, 0)}


def tool_counts():
    if time.time() - _TC["t"] > 6:
        _TC["v"] = _tool_counts_raw()
        _TC["t"] = time.time()
    return _TC["v"]


def entry_texts(n):
    if n.kind == "mod":
        _, a, h = MODULES[n.target]
        return a, h
    if n.kind == "tool":
        t = TOOLS[n.target]
        return t["about"], t["how"]
    holder = n.parent
    a = n.info[0] if n.info else (holder.info[0] if holder is not None and holder.info else "Tautan eksternal OSINT.")
    if "{q}" in n.target:
        h = "Masukkan kata kunci / domain / username saat diminta; hasilnya tampil sebagai pratinjau di terminal."
    elif not n.target:
        h = "Tautan resmi tidak tetap, jadi dicari lewat pencarian di terminal; pilih hasilnya untuk pratinjau."
    else:
        h = "Tekan Enter: pratinjau di terminal (status, deteksi blokir, ringkasan isi, arsip, tool GitHub terkait). o = buka di browser."
    return a, h


# ---------- tampilan baris (kartu) ----------
STAT_CHIP = {"aktif": ("aktif", G), "jarang": ("jarang", Y), "usang": ("usang", Y), "arsip": ("arsip", RD), "mati": ("mati", RD), "tidakrelevan": ("kurang relevan", Y)}
KIND_LABEL = {"cli": "repo", "lib": "pustaka", "platform": "panduan", "data": "data", "dead": "info"}


def chips(n):
    """-> (teks_polos, teks_berwarna) bagian kanan baris."""
    if n.kind in ("cat", "sub"):
        s = "(%d)" % count_entries(n)
        return s, D + s + R
    plain, col = [], []
    if n.kind == "mod":
        plain.append("modul")
        col.append(G + "modul" + R)
        if MOD_API.get(n.target):
            plain.append("API")
            col.append(Y + "API" + R)
    elif n.kind == "tool":
        t = TOOLS.get(n.target)
        if t is None:
            return "?", D + "?" + R
        ok = bool(find_tool(t)) if t.get("kind") not in ("dead",) else False
        lab = KIND_LABEL.get(t.get("kind", "cli"), "repo")
        plain.append(GL["dot"] + " " + lab)
        col.append(((G + GL["dot"]) if ok else (D + GL["ring"])) + R + " " + MG + lab + R)
        sl, sc = STAT_CHIP.get(t.get("status", "aktif"), ("aktif", G))
        plain.append(sl)
        col.append(sc + sl + R)
        if t.get("api"):
            plain.append("API")
            col.append(Y + "API" + R)
    else:
        plain.append("web")
        col.append(D + "web" + R)
    return "  ".join(plain), "  ".join(col)


def short_about(n):
    if n.kind in ("cat", "sub"):
        return n.info[0] if n.info else ""
    try:
        return entry_texts(n)[0]
    except KeyError:
        return ""


def card_rows(i, n, inner, two):
    tag = num_tag(i)
    tw = vlen(tag)
    plain, col = chips(n)
    name_w = max(8, inner - tw - 2 - len(plain))
    name = trunc(n.name, name_w)
    pad = " " * max(1, inner - tw - 1 - vlen(name) - len(plain))
    star = ""
    if n.kind == "cat" and n.name in (GH_CAT, FREE_CAT):
        star = Y + GL["info"] + R + " "
        pad = pad[:-2] if len(pad) > 3 else pad
    nm = (W + B + name + R) if n.kind in ("cat", "sub") else (W + name + R)
    out = ["%s %s%s%s%s" % (tag, star, nm, pad, col)]
    if two:
        d = short_about(n)
        if d:
            out.append("%s%s%s" % (" " * (tw + 1), D, trunc(d, inner - tw - 1)) + R)
        else:
            out.append("")
    return out


def hint_c(pairs):
    return [center(l.strip()) for l in hint_bar(pairs)]


def hints_for(node):
    base = [("n/p", "halaman"), ("/kata", "cari"), ("g", "Github Tools"), ("f", "Browser Gratis"), ("b", "bantuan"), ("t", "Pusat Tool"), ("s", "setelan"), ("h", "panduan")]
    if node.kind != "root":
        base.insert(0, ("m", "menu utama"))
    if in_github(node):
        base.insert(0, ("x", "periksa repo"))
    return base


def render_screen(node, trail, page, fresh):
    """Susun satu layar penuh (rata tengah) lalu tampilkan. -> (page, pages, items, posisi_jam)."""
    LIVE.stop()
    h = term_h()
    PM[0] = mg()
    head = []
    if node.kind == "root":
        head += [""] + banner_static() + subtitle_lines() + [rule_line()] + hud_block() + [""]
    else:
        head += brand_header([t.name for t in trail[1:]] + [node.name])
        about = [CY + "Tentang     " + R + W + (node.info[0] if node.info else "") + R]
        how = node.info[1] if len(node.info) > 1 else (node.parent.info[1] if node.parent is not None and len(node.parent.info) > 1 else "")
        if how:
            about.append(CY + "Cara input " + R + W + how + R)
        head += pad_lines(panel(None, about))
        if in_github(node):
            head += pad_lines(panel(None, ["%s[%sx%s]%s  %sPERIKSA REPO GITHUB (Genetic)%s  %stempel URL atau owner/repo untuk melihat persentase risiko sebelum memasang.%s" % (W, Y, W, R, W + B, R, D, R),
                                           "%s%s aktif   %s%s jarang diperbarui   %s%s tidak aktif%s   %sAPI%s = butuh API key   %s%s%s = terpasang" % (
                                               G, GL["dot"], Y, GL["dot"], Y, GL["dot"], R, Y, R + D, G, GL["dot"], R)]))
    items = node.children
    inner = content_w() - 4
    foot = 3 + len(hint_c(hints_for(node)))
    avail = max(4, h - len(head) - foot - 3)
    two = avail >= 18
    per = 2 if two else 1
    rows_pp = max(3, avail // per)
    pages = max(1, (len(items) + rows_pp - 1) // rows_pp)
    page = max(0, min(page, pages - 1))
    start = page * rows_pp
    chunk = items[start:start + rows_pp]
    body = []
    for k, it in enumerate(chunk):
        body += card_rows(start + k + 1, it, inner, two)
        if two and k < len(chunk) - 1:
            pass
    ft = "hal %d/%d  %s  %d %s" % (page + 1, pages, GL["sep"], len(items), "kategori" if node.kind == "root" else "item")
    title = "MENU UTAMA" if node.kind == "root" else node.name.upper()
    lines = head + pad_lines(panel(title, body, footer=ft))
    zero = "Keluar dari Giga OSINT" if node.kind == "root" else "Kembali"
    lines.append(" " * mg() + "  %s %s%s%s" % (num_tag(0), W, zero, R))
    lines += hint_c(hints_for(node))
    clear()
    emit(lines, 0.003 if fresh else 0.0)
    clock = None
    pos = find_clock(lines)
    if pos and len(lines) + 2 <= h:
        clock = (pos[0] + 1, pos[1])
        LIVE.start(*clock)
    return page, pages, items, clock


def show_guide(first=False):
    steps = [
        ("1", "Ketik %sNOMOR%s menu lalu tekan %sEnter%s. Contoh: ketik 1 untuk membuka kategori pertama."),
        ("2", "Ketik %s0%s untuk kembali. Di Menu Utama, 0 = KELUAR. Di dalam fitur, %s0%s atau %sq%s membatalkan; %sCtrl+C%s menghentikan."),
        ("3", "Ketik %sn%s / %sp%s untuk halaman berikut / sebelumnya bila daftar panjang."),
        ("4", "Ketik %s/kata%s untuk mencari fitur di semua kategori, contoh /plat atau /nmap. %sm%s = ke Menu Utama."),
        ("5", "%sg%s = Github Tools (semua repo), %sf%s = OSINT Browser Gratis, %sb%s = Pusat Bantuan, %sx%s (di Github Tools) = periksa repo."),
        ("6", "%st%s = Pusat Tool (deteksi yang belum terpasang lalu pasang sekaligus dengan satu y/n), %ss%s = setelan."),
        ("7", "Tool repo yang belum terpasang menampilkan rencana perintah lalu bertanya %sy/n%s. Panduan masalah ada di Pusat Bantuan."),
        ("8", "Setelah fitur selesai: %sEnter%s kembali, %su%s ulangi, %so%s buka tautan di browser, %sb%s bantuan."),
        ("9", "Pemindai aktif hanya untuk sistem milik sendiri atau berizin. Jangan Disalah Gunakan!"),
    ]
    lines = []
    for n, txt in steps:
        cnt = txt.count("%s")
        txt = txt % tuple((Y if i % 2 == 0 else R + W) for i in range(cnt)) if cnt else txt
        wrapped = wrap_ansi(W + txt + R, max(20, content_w() - 4 - 5))
        lines.append("%s[%s%s%s]%s %s" % (W, Y, n, W, R, wrapped[0]))
        lines.extend("    " + x for x in wrapped[1:])
    lines.append("")
    lines.append("%sLencana%s  %smodul%s = jalan di terminal   %srepo%s = tool GitHub   %sweb%s = tautan   %sAPI%s = butuh API key (peringatan kuning)" % (CY, R, G, W, MG, W, D, W, Y, W) + R)
    lines.append("%sWarna%s  %smerah%s = keluaran tool   %skuning%s = peringatan   %shijau%s = berhasil" % (CY, R, OUT_TINT, W, Y, W, G, W) + R)
    PM[0] = mg()
    if first:
        sys.stdout.write("\n" + "\n".join(pad_lines(panel("PANDUAN SINGKAT  " + GL["sep"] + "  CARA MENGGUNAKAN GIGA OSINT", lines))) + "\n")
        try:
            input(rl(D + "\n" + " " * max(2, mg()) + "Tekan Enter untuk masuk ke menu utama..." + R))
        except (EOFError, KeyboardInterrupt):
            pass
        return
    clear()
    emit(brand_header(["Panduan"]) + pad_lines(panel("PANDUAN SINGKAT", lines)))
    pause()


def do_exit():
    LIVE.stop()
    if ANIM and COLOR_LVL:
        try:
            hide_cursor()
            for i in range(0, 21):
                sys.stdout.write("\r\033[K" + center("%s  %sMenutup sesi Giga OSINT...%s" % (bar(1.0 - i / 20.0, 24), W, R)))
                sys.stdout.flush()
                nap(0.012)
        except KeyboardInterrupt:
            pass
    show_cursor()
    clear(full=True)
    sys.stdout.write("%sGiga OSINT ditutup. Jalankan lagi dengan:%s %spython3 giga_osint.py%s\n" % (G, R, W, R))
    sys.stdout.flush()
    sys.exit(0)


# ---------- menjalankan entri ----------
def entry_footer(n):
    """Menu penutup setelah fitur selesai: pengguna tidak pernah buntu. Mengembalikan 'u' bila diminta ulang."""
    url = None
    if n.kind == "tool" and n.target in TOOLS and TOOLS[n.target].get("repo"):
        url = "https://github.com/" + TOOLS[n.target]["repo"]
    elif n.kind == "link" and n.target and "{q}" not in n.target:
        url = n.target
    while True:
        opts = [("Enter", "kembali"), ("u", "ulangi fitur ini"), ("b", "bantuan")]
        if LAST_URLS or url:
            opts.append(("o", "buka tautan di browser"))
        opts.append(("m", "menu utama"))
        print()
        for ln in hint_bar(opts):
            print(ln)
        c = ask("Selesai. Pilih (Enter = kembali)")
        if c is None or c.strip().lower() in ("", "0", "q"):
            return ""
        cl = c.strip().lower()
        if cl == "u":
            return "u"
        if cl == "m":
            raise GoHome()
        if cl == "b":
            with entry_mode():
                try:
                    MODULES["pusat_bantuan"][0]()
                except KeyboardInterrupt:
                    p_warn("Dihentikan.")
            continue
        if cl == "o" and (LAST_URLS or url):
            if LAST_URLS:
                open_choices(list(LAST_URLS), ctx="hasil")
            else:
                open_browser(url)
            continue
        p_warn("Pilihan tidak valid. Ketik Enter, u, b, o, atau m.")


def run_entry(n):
    LIVE.stop()
    PM[0] = 0
    try:
        a, h = entry_texts(n)
    except KeyError:
        p_err("Entri '%s' belum tersedia di versi ini." % n.target)
        pause()
        return
    path = node_path(n)
    while True:
        LAST_URLS[:] = []
        clear()
        emit(brand_header(path[-2:] + [n.name[:44]]))
        info = [CY + "Tentang     " + R + W + a + R, CY + "Cara input " + R + W + h + R]
        if n.kind == "mod" and MOD_API.get(n.target):
            info.append(Y + GL["warn"] + " PERINGATAN API  " + MOD_API[n.target] + R)
        with entry_mode():
            try:
                if n.kind == "mod":
                    sys.stdout.write("\n".join(pad_lines(panel(n.name, info))) + "\n")
                    exit_notice()
                    MODULES[n.target][0]()
                elif n.kind == "tool":
                    run_tool(n.target)
                else:
                    sys.stdout.write("\n".join(pad_lines(panel(n.name, info))) + "\n")
                    exit_notice()
                    url = n.target
                    ctx = " ".join(path) + " " + n.name
                    if not url:
                        search_and_pick(n.name, ctx)
                    else:
                        go = True
                        if "{q}" in url:
                            v = ask("Masukkan kata kunci / domain / username  (0 = batal)")
                            if not v or v == "0":
                                go = False
                            else:
                                url = url.replace("{q}", q(v))
                        else:
                            c = ask("Tekan Enter untuk pratinjau di terminal, o = buka di browser  (0 = batal)")
                            if c is None or c == "0":
                                go = False
                            elif c.lower() == "o":
                                open_browser(url)
                                go = False
                        if go:
                            LAST_URLS[:] = [(n.name, url)]
                            peek(url, label=n.name, ctx=ctx)
            except KeyboardInterrupt:
                print()
                p_warn("Dihentikan oleh pengguna (Ctrl+C). Tidak ada yang rusak; kamu bisa mengulang atau kembali.")
            except GoHome:
                raise
            except JumpTo:
                raise
            except Exception as e:
                p_err("Terjadi kesalahan: %s: %s" % (e.__class__.__name__, e))
                p_info("Buka Pusat Bantuan (tombol b di bawah) untuk diagnosa. Fitur lain tetap aman dipakai.")
        if entry_footer(n) != "u":
            break


# ---------- pencarian ----------
def search_menu(term):
    t = term.strip().lower()
    if not t:
        p_warn("Ketik kata kunci setelah tanda '/'. Contoh: /plat")
        time.sleep(1.2)
        return
    nt = norm(t)
    hits = []
    for n, path in ALL:
        hay = n.name.lower()
        words = re.split(r"[^a-z0-9]+", hay)
        try:
            desc = entry_texts(n)[0].lower()
        except KeyError:
            desc = ""
        if nt and norm(n.name) == nt:
            rank = 0
        elif hay.startswith(t):
            rank = 1
        elif t in words:
            rank = 2
        elif t in hay:
            rank = 3
        elif nt and nt in norm(n.name):
            rank = 4
        elif nt and nt in norm(" ".join(path)):
            rank = 5
        elif t in desc:
            rank = 6
        else:
            continue
        hits.append((rank, n, path))
    hits.sort(key=lambda x: x[0])
    hits = [(n, path) for _, n, path in hits]
    while True:
        LIVE.stop()
        PM[0] = mg()
        clear()
        emit(brand_header(["Pencarian", "'" + term + "'"]))
        if not hits:
            p_warn("Tidak ada fitur yang cocok dengan '%s'. Coba kata lebih pendek, atau lihat Github Tools (g)." % term)
            pause()
            return
        shown = hits[:min(40, max(8, term_h() - 12))]
        rows = []
        inner = content_w() - 4
        for i, (n, path) in enumerate(shown, 1):
            plain, col = chips(n)
            loc = trunc(" > ".join(path[-2:]), max(10, inner // 3))
            nm = trunc(n.name, max(10, inner - vlen(num_tag(i)) - len(plain) - len(loc) - 6))
            pad = " " * max(2, inner - vlen(num_tag(i)) - 1 - vlen(nm) - len(plain) - len(loc) - 2)
            rows.append("%s %s%s%s%s%s%s  %s%s%s" % (num_tag(i), W, nm, R, pad, col, R, D, loc, R))
        sys.stdout.write("\n".join(pad_lines(panel("%d HASIL" % len(hits), rows))) + "\n")
        if len(hits) > len(shown):
            p_info("%d hasil lain tidak ditampilkan; perkecil kata kunci." % (len(hits) - len(shown)))
        c = ask("Pilih nomor untuk membuka, atau 0 untuk kembali")
        if c is None or c == "0":
            return
        if c.isdigit() and 1 <= int(c) <= len(shown):
            run_entry(shown[int(c) - 1][0])
        else:
            p_warn("Pilihan tidak valid.")
            time.sleep(1)


# ---------- Pusat Tool GitHub ----------
def pasang_semua_belum():
    """Deteksi tool yang belum terpasang; satu pertanyaan y/n; pasang berurutan; laporkan yang gagal."""
    cand = [k for k, t in TOOLS.items() if t.get("kind", "cli") in ("cli", "lib") and t.get("status") in ("aktif", "jarang") and not find_tool(t)]
    ok_n, total = tool_counts()
    sec("Hasil deteksi")
    kv("Total tool terdaftar", total)
    kv("Sudah terpasang", ok_n)
    kv("Bisa dipasang otomatis", len(cand))
    kv("Panduan / data (manual)", sum(1 for t in TOOLS.values() if t.get("kind") in ("platform", "data")))
    if not cand:
        p_ok("Semua tool yang bisa dipasang otomatis sudah terpasang.")
        return
    print()
    for k in cand[:12]:
        print("  %s%s%s %s" % (D, GL["ring"], R, TOOLS[k]["title"]))
    if len(cand) > 12:
        p_info("... dan %d tool lain." % (len(cand) - 12))
    p_warn("Memasang semuanya bisa memakan banyak waktu dan ruang disk. Aman dihentikan dengan Ctrl+C.")
    if not yes_no("Pasang %d tool yang belum terpasang sekarang" % len(cand)):
        p_info("Dibatalkan. Kamu tetap bisa memasang satu per satu dari daftar.")
        return
    gagal = []
    for i, k in enumerate(cand, 1):
        print()
        p_info("[%d/%d] %s" % (i, len(cand), TOOLS[k]["title"]))
        try:
            if not install_tool(TOOLS[k]):
                gagal.append(k)
        except KeyboardInterrupt:
            p_warn("Dihentikan oleh pengguna.")
            break
    _TC["t"] = 0
    sec("Ringkasan pemasangan")
    p_ok("Berhasil: %d" % (len(cand) - len(gagal)) if len(cand) > len(gagal) else "Tidak ada yang berhasil.")
    if gagal:
        p_warn("Gagal: %s" % ", ".join(TOOLS[k]["title"] for k in gagal[:15]))
        p_info("Buka Pusat Bantuan (b) > Masalah umum untuk solusi, atau pasang manual lewat kartu tool.")


def tool_hub():
    page = 0
    while True:
        LIVE.stop()
        PM[0] = mg()
        groups = {}
        for k, t in TOOLS.items():
            groups.setdefault(tool_sub(t), []).append(k)
        order = [g for g, _ in GH_SUBS if g in groups] + [g for g in groups if g not in dict(GH_SUBS)]
        ok, total = tool_counts()
        head = brand_header(["Pusat Tool GitHub"])
        head += pad_lines(panel(None, [CY + "Tentang     " + R + W + "Semua tool GitHub/PyPI: lihat status, pasang, atau baca panduan. Belum terpasang? Instalasi ditawarkan (y/n)." + R,
                                       CY + "Cara input " + R + W + "Nomor = buka tool, d = deteksi yang belum terpasang, x = periksa repo, n/p = halaman, 0 = kembali." + R,
                                       CY + "Terpasang   " + R + bar(ok / float(max(1, total)), 20) + "  " + W + "%d dari %d" % (ok, total) + R]))
        order_keys = []
        entries = []
        for g in order:
            ks = sorted(groups[g], key=lambda k: (STATUS_ORD.get(TOOLS[k].get("status"), 3), TOOLS[k]["title"].lower()))
            entries.append(("hdr", g, 0))
            for k in ks:
                order_keys.append(k)
                entries.append(("tool", k, len(order_keys)))
        cap = max(8, term_h() - len(head) - 8)
        pages = max(1, (len(entries) + cap - 1) // cap)
        page = max(0, min(page, pages - 1))
        chunk = entries[page * cap:(page + 1) * cap]
        if chunk and chunk[0][0] == "tool":
            chunk = [("hdr", tool_sub(TOOLS[chunk[0][1]]), 0)] + chunk
        inner = content_w() - 4
        body = []
        for kind, val, num in chunk:
            if kind == "hdr":
                body.append("%s%s%s %s%s%s" % (gc(0.0), GL["info"], R, W + B, val, R))
            else:
                nd = Node("tool", TOOLS[val]["title"], target=val)
                body += card_rows(num, nd, inner, False)
        lines = head + pad_lines(panel("PUSAT TOOL", body, footer="hal %d/%d" % (page + 1, pages)))
        lines.append(" " * mg() + "  %s %sKembali%s" % (num_tag(0), W, R))
        lines += hint_c([("nomor", "buka tool"), ("d", "deteksi & pasang yang belum"), ("x", "periksa repo"), ("n/p", "halaman"), ("0", "kembali")])
        clear()
        emit(lines, 0.001)
        c = ask("Pilih nomor tool / d / x / n / p / 0")
        if c is None or c == "0":
            return
        cl = c.lower()
        PM[0] = 0
        if cl == "n":
            page = min(page + 1, pages - 1)
        elif cl == "p":
            page = max(page - 1, 0)
        elif cl == "d":
            with entry_mode():
                pasang_semua_belum()
            pause()
        elif cl == "x":
            run_entry(Node("tool", "Genetic", target="genetic"))
        elif c.isdigit() and 1 <= int(c) <= len(order_keys):
            run_entry(Node("tool", TOOLS[order_keys[int(c) - 1]]["title"], target=order_keys[int(c) - 1]))
        else:
            p_warn("Pilihan tidak valid.")
            time.sleep(0.9)


# ---------- Pengaturan ----------
def refresh_anim():
    global ANIM
    ANIM = bool(CFG.get("anim", True)) and TTY and "--cepat" not in ARGS and not os.environ.get("GIGA_NO_ANIM")


def view_results():
    try:
        files = sorted((os.path.join(OUT_DIR, f) for f in os.listdir(OUT_DIR)), key=os.path.getmtime, reverse=True)
        files = [f for f in files if os.path.isfile(f)][:12]
    except OSError:
        files = []
    sec("Folder hasil: " + OUT_DIR)
    if not files:
        p_info("Belum ada hasil tersimpan. Hasil tool GitHub dan pemindaian username otomatis disimpan di sini.")
        return
    for i, f in enumerate(files, 1):
        print("  %s %s%s%s  %s%.1f KB  %s%s" % (num_tag(i), W, trunc(os.path.basename(f), term_w() - 36), R, D,
                                              os.path.getsize(f) / 1024.0, time.strftime("%d/%m %H:%M", time.localtime(os.path.getmtime(f))), R))
    c = ask("Nomor file untuk dibaca (60 baris pertama), 0 = kembali")
    if c and c.isdigit() and 1 <= int(c) <= len(files):
        try:
            with open(files[int(c) - 1], "r", encoding="utf-8", errors="replace") as fh:
                for ln in fh.read().splitlines()[:60]:
                    print("  " + trunc(ln, term_w() - 4))
        except OSError as e:
            p_err("Gagal membaca file: %s" % e)


def settings_menu():
    global MASK_PASSWORD
    while True:
        LIVE.stop()
        PM[0] = mg()
        clear()
        on, off = G + "AKTIF" + R, RD + "MATI" + R
        rows = [("Animasi antarmuka", on if CFG["anim"] else off),
                ("Kecepatan animasi", W + CFG["speed"] + R),
                ("Samarkan password hasil kebocoran", on if CFG["mask"] else off),
                ("Tema warna banner", W + THEME_LABEL.get(CFG["theme"], CFG["theme"]) + R),
                ("Keluaran tool berwarna merah", on if CFG.get("outred", True) else off),
                ("Jam bergerak di layar", on if CFG.get("clock", True) else off),
                ("Tampilkan IP publik (minta ke ipquery.io)", on if CFG.get("pubip", True) else off),
                ("Kunci API tersimpan", D + "lihat / tambah / hapus" + R),
                ("Lihat folder hasil tool", D + OUT_DIR + R),
                ("Atur ulang semua pengaturan", D + "kembali ke bawaan" + R)]
        lines = brand_header(["Pengaturan"])
        lines += pad_lines(panel(None, [CY + "Tentang     " + R + W + "Atur tampilan dan perilaku Giga OSINT. Tersimpan otomatis di %s." % CONF_FILE + R,
                                        CY + "Cara input " + R + W + "Ketik nomor pengaturan untuk mengubahnya (1-%d), 0 = kembali." % len(rows) + R]))
        body = ["%s %s%s%s  %s" % (num_tag(i), W, padr(lab, 42), R, val) for i, (lab, val) in enumerate(rows, 1)]
        lines += pad_lines(panel("PENGATURAN", body))
        lines.append(" " * mg() + "  %s %sKembali%s" % (num_tag(0), W, R))
        emit(lines)
        c = ask("Pilih nomor pengaturan")
        if c is None or c == "0":
            return
        if c == "1":
            CFG["anim"] = not CFG["anim"]
        elif c == "2":
            CFG["speed"] = {"normal": "cepat", "cepat": "lambat", "lambat": "normal"}.get(CFG["speed"], "normal")
        elif c == "3":
            CFG["mask"] = not CFG["mask"]
            MASK_PASSWORD = CFG["mask"]
        elif c == "4":
            names = list(THEMES)
            keep = CFG["theme"]
            print()
            for i, nm in enumerate(names, 1):
                CFG["theme"] = nm
                print("  %s %s%s  %s" % (num_tag(i), W, padr(THEME_LABEL[nm], 16), hline(34, 0, 1, GL["rule"])))
            CFG["theme"] = keep
            t = ask("Pilih tema 1-%d, 0 = batal" % len(names))
            if t and t.isdigit() and 1 <= int(t) <= len(names):
                CFG["theme"] = names[int(t) - 1]
        elif c == "5":
            CFG["outred"] = not CFG.get("outred", True)
        elif c == "6":
            CFG["clock"] = not CFG.get("clock", True)
        elif c == "7":
            CFG["pubip"] = not CFG.get("pubip", True)
            SYS["pub_state"] = "off" if not CFG["pubip"] else SYS.get("pub_state", "idle")
            if CFG["pubip"] and not SYS.get("pub"):
                start_sysinfo()
        elif c == "8":
            PM[0] = 0
            kunci_api_menu()
            pause()
            continue
        elif c == "9":
            PM[0] = 0
            view_results()
            pause()
            continue
        elif c == "10":
            if yes_no("Kembalikan semua pengaturan ke bawaan"):
                CFG.clear()
                CFG.update(DEFAULT_CFG)
                MASK_PASSWORD = CFG["mask"]
        else:
            p_warn("Pilihan tidak valid.")
            time.sleep(0.8)
            continue
        refresh_anim()
        save_cfg()


# ---------- menu utama / navigasi ----------
def find_cat(name):
    return next((c for c in ROOT.children if c.name == name), None)


def run_help():
    LIVE.stop()
    PM[0] = 0
    clear()
    emit(brand_header(["Pusat Bantuan"]))
    with entry_mode():
        try:
            exit_notice()
            MODULES["pusat_bantuan"][0]()
        except KeyboardInterrupt:
            p_warn("Dihentikan.")


def browse(node, trail):
    page, fresh = 0, True
    while True:
        page, pages, items, _ = render_screen(node, trail, page, fresh)
        fresh = False
        c = ask("Pilih nomor menu")
        LIVE.stop()
        if c is None:
            if node.kind == "root":
                do_exit()
            return
        cl = c.lower()
        if cl == "0":
            if node.kind == "root":
                do_exit()
            return
        if cl == "n":
            page = min(page + 1, pages - 1)
        elif cl == "p":
            page = max(page - 1, 0)
        elif cl in ("h", "?"):
            show_guide()
            fresh = True
        elif cl == "t":
            tool_hub()
            fresh = True
        elif cl == "s":
            settings_menu()
            fresh = True
        elif cl == "b":
            run_help()
            fresh = True
        elif cl in ("g", "f"):
            target = find_cat(GH_CAT if cl == "g" else FREE_CAT)
            if target is not None and target is not node:
                if node.kind == "root":
                    try:
                        browse(target, [node])
                    except (GoHome, JumpTo):
                        pass
                else:
                    raise JumpTo(target)
            fresh = True
        elif cl == "x" and in_github(node):
            run_entry(Node("tool", "Genetic", target="genetic"))
            fresh = True
        elif cl == "m":
            if node.kind != "root":
                raise GoHome()
        elif c.startswith("/"):
            search_menu(c[1:])
            fresh = True
        elif c.isdigit() and 1 <= int(c) <= len(items):
            ch = items[int(c) - 1]
            fresh = True
            try:
                if ch.kind in ("cat", "sub"):
                    browse(ch, trail + [node])
                else:
                    run_entry(ch)
            except GoHome:
                if node.kind != "root":
                    raise
            except JumpTo as j:
                if node.kind != "root":
                    raise
                try:
                    browse(j.node, [node])
                except (GoHome, JumpTo):
                    pass
        else:
            p_warn("Pilihan tidak valid. Ketik nomor yang tampil, 0, n, p, g, f, b, t, s, h, atau /kata.")
            time.sleep(1.1)


# ---------- boot ----------
def boot_stage(label, fn, m=""):
    result = fn()
    if not (ANIM and COLOR_LVL):
        print("%s  %s%s%s %s%s%s  %s%s%s" % (m, G, GL["dot"], R, W, label, R, D, result, R))
        return
    steps = 14
    for i in range(steps + 1):
        sys.stdout.write("\r\033[K%s  %s %s%s%s %s%s%s" % (m, bar(i / float(steps), 16), W, label, R, gc(i / float(steps)), SPIN[i % len(SPIN)], R))
        sys.stdout.flush()
        nap(0.014)
    sys.stdout.write("\r\033[K%s  %s%s%s %s%s%s  %s%s%s\n" % (m, G, GL["dot"], R, W, label, R, D, result, R))
    sys.stdout.flush()


def boot():
    clear()
    rows = banner_rows()
    print()
    banner_play(rows)
    for sl in ([SUBTITLE] if term_w() >= len(SUBTITLE) + 2 else SUBTITLE.rsplit(" | ", 1)):
        sys.stdout.write(" " * max(0, (term_w() - len(sl)) // 2))
        typewrite(sl, 0.007, W)
    print(rule_line())
    print()
    st = catalog_stats()
    cats = len(ROOT.children)
    bw = max(len("Mendeteksi lingkungan"), len("Memuat katalog fitur"), len("Memeriksa modul terminal"),
             len("Memindai tool terpasang"), len("Menyiapkan antarmuka")) + 34
    bm = " " * max(0, (term_w() - bw) // 2)
    boot_stage("Mendeteksi lingkungan", lambda: "%s  Python %s  %dx%d  warna %s" % (
        platform.system(), platform.python_version(), term_w(), term_h(), {3: "24-bit", 2: "256", 1: "16", 0: "mati"}[COLOR_LVL]), bm)
    boot_stage("Memuat katalog fitur", lambda: "%d kategori  %d fitur" % (cats, len(ALL)), bm)
    boot_stage("Memeriksa modul terminal", lambda: "%d modul  %d tool GitHub siap" % (st["mod"], len(TOOLS)), bm)
    boot_stage("Memindai tool terpasang", lambda: "%d dari %d terpasang" % tool_counts(), bm)
    boot_stage("Menyiapkan antarmuka", lambda: "siap  %s  %s" % (GL["sep"], "animasi aktif" if ANIM else "animasi mati"), bm)
    print()
    print(bm + "  %s%s%s %sSISTEM ONLINE%s" % (G, GL["dot"], R, G, R))
    print()


def main():
    if sys.version_info < (3, 8):
        print("Giga OSINT membutuhkan Python 3.8 atau lebih baru.")
        sys.exit(1)
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
    except OSError:
        pass
    try:
        start_sysinfo()
        try:
            boot()
        except KeyboardInterrupt:
            show_cursor()
        show_guide(first=True)
        browse(ROOT, [])
    except KeyboardInterrupt:
        do_exit()


if __name__ == "__main__":
    main()
