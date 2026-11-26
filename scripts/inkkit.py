"""Shared pieces for the profile's Tako Ink SVGs.

The tako sprite, its choreography and the dithered glow are a Python port of
NV-CODE's scripts/nv-tako-ink.ts (MIT): Tako-streak's tako as pixel art, shaded
with a 16x16 ordered dither in the NV-CODE home-glow blue.
"""

import base64
import io
import math
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

FONTS = Path(__file__).resolve().parent / "fonts"

# ---------------------------------------------------------------- palette

BLUE = {"light": "#7f9ef0", "mid": "#3c6dec", "dark": "#1842b4"}
INK = "#0b1a52"
WHITE = "#ffffff"
CHEEK = "#ffc6e4"
SPARK = "#a8c4ff"
WATER = "#6fd3ff"

THEMES = {
    "dark": {
        "canvas": "#0b1124",
        "card": "#0f1730",
        "raised": "#141e3d",
        "border": "#223062",
        "text": "#eef1ff",
        "muted": "#8d98c4",
        "accent": "#3c6dec",
        "accent_text": "#7f9ef0",
        "on_accent": "#ffffff",
        "grain": 0.94,
    },
    "light": {
        "canvas": "#f0eeec",
        "card": "#f7f6f4",
        "raised": "#ffffff",
        "border": "#d9d5d0",
        "text": "#0b1124",
        "muted": "#5e6582",
        "accent": "#2d5cd7",
        "accent_text": "#2d5cd7",
        "on_accent": "#ffffff",
        "grain": 0.3,
    },
}

EXPO = "cubic-bezier(0.16, 1, 0.3, 1)"

# ---------------------------------------------------------------- fonts


class Font:
    def __init__(self, file, family, weight=400):
        font = TTFont(FONTS / file, recalcTimestamp=False)
        if "fvar" in font:
            font = instancer.instantiateVariableFont(font, {"wght": weight})
        buffer = io.BytesIO()
        font.flavor = None
        font.save(buffer)
        self.raw = buffer.getvalue()
        self.family, self.weight = family, weight
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm
        self.used = set()

    def width(self, text, size, tracking=0.0):
        units = sum(self.hmtx[self.cmap.get(ord(ch)) or self.cmap[ord("?")]][0] for ch in text)
        return units / self.upm * size + tracking * size * len(text)

    def face(self):
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga", "tnum"]
        options.name_IDs = []
        subsetter = subset.Subsetter(options)
        font = TTFont(io.BytesIO(self.raw), recalcTimestamp=False)
        subsetter.populate(text="".join(sorted(self.used)) + " ")
        subsetter.subset(font)
        out = io.BytesIO()
        font.flavor = "woff2"
        font.save(out)
        data = base64.b64encode(out.getvalue()).decode()
        return (
            f"@font-face{{font-family:'{self.family}';font-weight:{self.weight};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )


SANS = Font("Geist.woff2", "Geist", 400)
SEMI = Font("Geist.woff2", "Geist", 600)
HEAVY = Font("Geist.woff2", "Geist", 900)
MONO = Font("GeistMono.woff2", "Geist Mono", 400)
ALL_FONTS = (SANS, SEMI, HEAVY, MONO)

STYLES = {
    # name: (font, size, tracking, uppercase, color key)
    "label": (MONO, 11, 0.06, True, "muted"),
    "label-accent": (MONO, 11, 0.06, True, "accent_text"),
    "chip": (SANS, 13, 0, False, "text"),
    "tag": (MONO, 11, 0.04, False, "accent_text"),
    "body": (SANS, 15, 0, False, "muted"),
    "lead": (SANS, 20, -0.01, False, "muted"),
    "title": (SEMI, 22, -0.01, False, "text"),
    "strong": (SEMI, 14, 0, False, "text"),
    "small": (SANS, 13, 0, False, "muted"),
    "button": (SEMI, 14, 0, False, "on_accent"),
    "composer": (SANS, 16, 0, False, "text"),
}


class Svg:
    def __init__(self, width, height, theme, title):
        self.w, self.h = width, height
        self.theme = theme
        self.c = THEMES[theme]
        self.title = title
        self.css, self.defs, self.body = [], [], []

    def add(self, markup):
        self.body.append(markup)

    def text(self, x, y, value, style=None, *, font=None, size=None, fill=None,
             anchor="start", extra="", tracking=0.0, cls=""):
        if style:
            font, size, tracking, upper, color = STYLES[style]
            value = value.upper() if upper else value
            fill = fill or self.c[color]
        fill = fill or self.c["text"]
        font.used.update(value)
        ls = f' letter-spacing="{tracking * size:.2f}"' if tracking else ""
        klass = f' class="{cls}"' if cls else ""
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font.family}" font-weight="{font.weight}" '
            f'font-size="{size}"{ls} fill="{fill}" text-anchor="{anchor}"{klass}{extra}>'
            f"{escape(value)}</text>"
        )

    @staticmethod
    def width(value, style):
        font, size, tracking, upper, _ = STYLES[style]
        return font.width(value.upper() if upper else value, size, tracking)

    def pill(self, x, y, value, style="tag", *, stroke=None, fill="none", pad=9, height=22):
        w = self.width(value, style) + pad * 2
        markup = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{height}" rx="{height / 2}" '
            f'fill="{fill}" stroke="{stroke or self.c["border"]}"/>'
            + self.text(x + pad, y + height / 2 + 4, value, style)
        )
        return markup, w

    def render(self):
        faces = "".join(f.face() for f in ALL_FONTS if f.used)
        css = faces + "".join(self.css) + (
            "@media (prefers-reduced-motion: reduce){*{animation:none!important}.motion-only{display:none}}"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" '
            f'viewBox="0 0 {self.w} {self.h}" role="img" aria-label="{escape(self.title)}">'
            f"<title>{escape(self.title)}</title><defs><style>{css}</style>{''.join(self.defs)}</defs>"
            f"{''.join(self.body)}</svg>"
        )


def reset_fonts():
    for font in ALL_FONTS:
        font.used = set()


def window(svg, radius=16, fill=None):
    svg.add(f'<rect x="0.5" y="0.5" width="{svg.w - 1}" height="{svg.h - 1}" rx="{radius}" '
            f'fill="{fill or svg.c["canvas"]}" stroke="{svg.c["border"]}"/>')
    svg.defs.append(f'<clipPath id="window"><rect x="1" y="1" width="{svg.w - 2}" '
                    f'height="{svg.h - 2}" rx="{radius - 1}"/></clipPath>')


def arrow(x, y, color, size=9):
    return (f'<path d="M{x} {y + size}L{x + size} {y}M{x + 2.5} {y}H{x + size}V{y + size - 2.5}" '
            f'fill="none" stroke="{color}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>')


def grain_pattern(svg, pid="grain", alpha=0.48):
    """NV-CODE's grain fill: a 2px checker of shade over the fill colour."""
    svg.defs.append(
        f'<pattern id="{pid}" width="4" height="4" patternUnits="userSpaceOnUse">'
        f'<rect width="2" height="2" fill="#000" fill-opacity="{alpha}"/>'
        f'<rect x="2" y="2" width="2" height="2" fill="#000" fill-opacity="{alpha}"/></pattern>'
    )


# ---------------------------------------------------------------- dither


def bayer_matrix(size):
    m = [[0]]
    while len(m) < size:
        n = len(m)
        nxt = [[0] * (n * 2) for _ in range(n * 2)]
        for y in range(n):
            for x in range(n):
                v = m[y][x] * 4
                nxt[y][x] = v
                nxt[y][x + n] = v + 2
                nxt[y + n][x] = v + 3
                nxt[y + n][x + n] = v + 1
        m = nxt
    return m


B16 = bayer_matrix(16)


def bayer(x, y):
    return (B16[y & 15][x & 15] + 0.5) / 256


def glow(svg, gid, cx, cy, scale, alpha=None, breathe=True):
    """The NV-CODE home glow: an 8x8 Bayer threshold against an elliptical
    coverage gradient, binarised by a filter. 384x224 dots, `scale` px each."""
    alpha = svg.c["grain"] if alpha is None else alpha
    b8 = bayer_matrix(8)
    pattern = "".join(
        f"<path fill='#00{round((b8[y][x] + 0.5) / 64 * 255):02x}00' d='M{x} {y}h1v1h-1z'/>"
        for y in range(8) for x in range(8)
    )
    w, h = 384, 224
    edge = [v / 255 for v in (0x18, 0x42, 0xB4)]
    centre = [v / 255 for v in (0x77, 0x97, 0xE3)]
    channel = lambda i: f"{(centre[i] - edge[i]) / 0.55:.3f} 0 0 0 {edge[i]:.3f}"
    matrix = " ".join([channel(0), channel(1), channel(2), "60 -60 0 0 0.5"])
    stops = [("0", "#9a0000"), (".45", "#620000"), (".78", "#1c0000"), ("1", "#000000")]
    # A slow breath: the inner stops swell and settle, so dots appear and fade.
    stop_markup = ""
    for i, (offset, color) in enumerate(stops):
        anim = ""
        if breathe and i in (1, 2):
            to = {1: ".55", 2: ".9"}[i]
            anim = (f'<animate attributeName="offset" values="{offset};{to};{offset}" dur="7s" '
                    'repeatCount="indefinite" calcMode="spline" keySplines=".45 0 .55 1;.45 0 .55 1"/>')
        stop_markup += f'<stop offset="{offset}" stop-color="{color}">{anim}</stop>'
    svg.defs.append(
        f'<radialGradient id="{gid}g">{stop_markup}</radialGradient>'
        f'<pattern id="{gid}b" width="8" height="8" patternUnits="userSpaceOnUse">{pattern}</pattern>'
        f'<filter id="{gid}d" x="0" y="0" width="1" height="1" color-interpolation-filters="sRGB">'
        f'<feColorMatrix type="matrix" values="{matrix}"/>'
        f'<feComponentTransfer><feFuncA type="discrete" tableValues="0 {alpha}"/></feComponentTransfer></filter>'
    )
    x, y = cx - w * scale / 2, cy - h * scale / 2
    svg.add(
        f'<svg x="{x:.1f}" y="{y:.1f}" width="{w * scale:.1f}" height="{h * scale:.1f}" viewBox="0 0 {w} {h}" '
        f'shape-rendering="crispEdges" style="image-rendering:pixelated">'
        f'<clipPath id="{gid}c"><rect x="4" y="4" width="{w - 8}" height="{h - 8}"/></clipPath>'
        f'<g clip-path="url(#{gid}c)"><g filter="url(#{gid}d)"><rect width="{w}" height="{h}" fill="url(#{gid}g)"/>'
        f'<rect width="{w}" height="{h}" fill="url(#{gid}b)" style="mix-blend-mode:screen"/></g></g></svg>'
    )


# ---------------------------------------------------------------- tako sprites

CELL, X0, Y0, COLS, ROWS = 4, 16, 16, 42, 28
N4 = [(1, 0), (-1, 0), (0, 1), (0, -1)]


def cx(c):
    return X0 + (c + 0.5) * CELL


def cy(r):
    return Y0 + (r + 0.5) * CELL


def col(x):
    return math.floor((x - X0) / CELL)


def row(y):
    return math.floor((y - Y0) / CELL)


def cubic(p0, p1, p2, p3, n=40):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        u = 1 - t
        at = lambda k: u ** 3 * p0[k] + 3 * u * u * t * p1[k] + 3 * u * t * t * p2[k] + t ** 3 * p3[k]
        pts.append((at(0), at(1)))
    return pts


def body_cells(lifts=(0, 0, 0, 0, 0, 0), sway=0):
    poly = [(22, 104), *cubic((22, 104), (22, 18), (178, 18), (178, 104))]
    x = 178
    for i in range(5, -1, -1):
        lift = lifts[i]
        poly += cubic((x, 104), (x + sway, 134 - lift), (x - 26 + sway, 126 - lift), (x - 26, 104))
        x -= 26

    def inside(px, py):
        c = False
        j = len(poly) - 1
        for i in range(len(poly)):
            xi, yi = poly[i]
            xj, yj = poly[j]
            if (yi > py) != (yj > py) and px < (xj - xi) * (py - yi) / (yj - yi) + xi:
                c = not c
            j = i
        return c

    body = {(c, r) for r in range(ROWS) for c in range(COLS) if inside(cx(c), cy(r))}
    edge = {(c, r) for (c, r) in body if any((c + dx, r + dy) not in body for dx, dy in N4)}
    return body, edge


class Layers(dict):
    def put(self, color, cell):
        for cells in self.values():
            cells.discard(cell)
        self.setdefault(color, set()).add(cell)


def pixels(layers, height=ROWS):
    """Pixel layers as run-length paths in sprite pixels."""
    out = ""
    for color, cells in layers.items():
        rows = {}
        for c, r in cells:
            if 0 <= c < COLS and 0 <= r < height:
                rows.setdefault(r, []).append(c)
        d = ""
        for r in sorted(rows):
            xs = sorted(rows[r])
            a = 0
            while a < len(xs):
                b = a
                while b + 1 < len(xs) and xs[b + 1] == xs[b] + 1:
                    b += 1
                d += f"M{xs[a]} {r}h{b - a + 1}v1h-{b - a + 1}z"
                a = b + 1
        if d:
            out += f'<path fill="{color}" d="{d}"/>'
    return out


def body_sprite(lifts=(0, 0, 0, 0, 0, 0), sway=0):
    body, edge = body_cells(lifts, sway)
    layers = Layers()
    bx0, bx1, by0, by1 = col(22), col(178), row(40), row(124)
    stops = [BLUE["light"], BLUE["mid"], BLUE["dark"]]
    for c, r in sorted(body, key=lambda k: (k[1], k[0])):
        if (c, r) in edge:
            layers.put(INK, (c, r))
            continue
        u = (c - bx0 + 0.5) / (bx1 - bx0 + 1) - 0.34
        v = ((r - by0 + 0.5) / (by1 - by0 + 1) - 0.22) * ((by1 - by0) / (bx1 - bx0))
        t = max(0, min(1, math.hypot(u, v) / 0.62))
        s = t * 2
        band = min(1, math.floor(s))
        layers.put(stops[band + 1 if s - band > bayer(c, r) else band], (c, r))
    for ex, ey in ((58, 94), (142, 94)):
        for c, r in body - edge:
            q = ((cx(c) - ex) / 11) ** 2 + ((cy(r) - ey) / 7) ** 2
            if q <= 0.5 or (q <= 1 and (c + r) % 2 == 0):
                layers.put(CHEEK, (c, r))
    return pixels(layers)


EYE_L, EYE_R, EYE_TOP, EW, EH = col(76) - 2, col(124) - 1, row(78) - 2, 4, 5
MOUTH_C, MOUTH_R = col(100) - 1, row(95)


def eye_glyph(glyph):
    cells = []

    def pill(top, rows, cut_top=True):
        for dy in range(rows):
            for dx in range(EW):
                edge_row = (cut_top and dy == 0) or dy == rows - 1
                if edge_row and dx in (0, EW - 1):
                    continue
                cells.append((dx, top + dy))

    if glyph == "closed":
        cells += [(dx, EH - 2) for dx in range(EW)]
    elif glyph == "lidded":
        pill(2, EH - 2, False)
    elif glyph == "wide":
        pill(-1, EH + 1)
    elif glyph == "happy":
        cells += [(0, 2), (0, 3), (1, 1), (2, 1), (3, 2), (3, 3)]
    else:
        pill(0, EH)
    return cells


MOUTHS = {
    "smile": [(-2, 0), (2, 0), (-1, 1), (0, 1), (1, 1)],
    "open": [(-2, 0), (-1, 0), (0, 0), (1, 0), (2, 0), (-1, 1), (1, 1), (0, 2)],
    "tongue": [(0, 1)],
    "oh": [(0, 0), (-1, 1), (1, 1), (0, 2)],
    "flat": [(-1, 1), (0, 1), (1, 1)],
    "chew": [(-1, 0), (0, 1), (1, 0)],
    "sip": [(0, 0), (0, 1)],
    "snore": [(0, 1)],
}
PROP_COLORS = {"o": INK, "w": "#f4f6ff", "n": "#1e3b34", "g": "#dfe8ff", "a": WATER, "z": WHITE}
PROPS = {
    "onigiri": ["....o....", "...owo...", "..owwwo..", ".owwwwwo.", "owwwwwwwo", "ownnnnnwo", "onnnnnnno"],
    "bitten": [".........", ".........", ".........", ".o.o.o.o.", "owwwwwwwo", "ownnnnnwo", "onnnnnnno"],
    "lastBite": [".........", ".........", ".........", ".........", ".........", ".o.o.o.o.", "onnnnnnno"],
    "crumbs": ["w.......w", ".........", "...w....."],
    "glassFull": ["g...g", "gaaag", "gaaag", "gaaag", "gaaag", ".ggg."],
    "glassHalf": ["g...g", "g...g", "g...g", "gaaag", "gaaag", ".ggg."],
    "glassEmpty": ["g...g", "g...g", "g...g", "g...g", "g...g", ".ggg."],
    "z1": [".........", ".........", "zzzz.....", "..z......", ".z.......", "zzzz....."],
    "z2": [".....zzzz", ".......z.", "zzzz..z..", "..z..zzzz", ".z.......", "zzzz....."],
}
SPARKS = [(col(30), row(34)), (col(172), row(28)), (col(100), row(20))]
PLUS = [(0, -1), (-1, 0), (0, 0), (1, 0), (0, 1)]


def face_sprite(eyes, mouth, sparks=False, *props):
    layers = Layers()
    white = {(x0 + dx, EYE_TOP + dy) for x0 in (EYE_L, EYE_R) for dx, dy in eye_glyph(eyes)}
    ring = {(c + dx, r + dy) for c, r in white for dx, dy in N4 if (c + dx, r + dy) not in white}
    layers[INK] = set(ring)
    layers[WHITE] = set(white)
    for dx, dy in MOUTHS[mouth]:
        layers.put(INK, (MOUTH_C + dx, MOUTH_R + dy))
    if mouth == "open":
        for dx, dy in MOUTHS["tongue"]:
            layers.put(CHEEK, (MOUTH_C + dx, MOUTH_R + dy))
    if sparks:
        for sc, sr in SPARKS:
            for dx, dy in PLUS:
                layers.put(SPARK, (sc + dx, sr + dy))
    for prop in props:
        rows = PROPS[prop]
        sleeping = prop in ("z1", "z2")
        top = 0 if sleeping else MOUTH_R + 2
        left = col(140) if sleeping else MOUTH_C - len(rows[0]) // 2
        for dy, line in enumerate(rows):
            for dx, ch in enumerate(line):
                if ch in PROP_COLORS:
                    layers.put(PROP_COLORS[ch], (left + dx, top + dy))
    return pixels(layers)


def shadow_sprite():
    layers = Layers()
    for r in range(3):
        for c in range(COLS):
            q = ((c + 0.5 - COLS / 2) / 17) ** 2 + ((r + 0.5 - 1.5) / 1.6) ** 2
            if q <= 1 and bayer(c, r) < 0.85 - q * 0.7:
                layers.put(BLUE["dark"] if q < 0.35 else INK, (c, r))
    return pixels(layers, 3)


WALK_A, WALK_B = (6, 0, 6, 0, 6, 0), (0, 6, 0, 6, 0, 6)
RUN_A, RUN_B = (10, 0, 10, 0, 10, 0), (0, 10, 0, 10, 0, 10)
BODIES = {
    "stand": lambda: body_sprite(),
    "stepA": lambda: body_sprite(WALK_A),
    "stepB": lambda: body_sprite(WALK_B),
    "runRA": lambda: body_sprite(RUN_A, -4),
    "runRB": lambda: body_sprite(RUN_B, -4),
    "runLA": lambda: body_sprite(RUN_A, 4),
    "runLB": lambda: body_sprite(RUN_B, 4),
}
FACES = {
    "open": ("open", "smile"),
    "blink": ("closed", "smile"),
    "happy": ("happy", "open", True),
    "wide": ("wide", "oh"),
    "sleepy": ("lidded", "flat"),
    "eat": ("wide", "open", False, "onigiri"),
    "chomp": ("happy", "chew", False, "bitten"),
    "chew": ("happy", "smile", False, "bitten"),
    "chompLast": ("happy", "chew", False, "lastBite"),
    "chewLast": ("happy", "chew", False, "crumbs"),
    "drink": ("open", "sip", False, "glassFull"),
    "gulp": ("closed", "sip", False, "glassHalf"),
    "gulpLast": ("closed", "sip", False, "glassEmpty"),
    "ahh": ("happy", "open", True, "glassEmpty"),
    "doze": ("closed", "snore", False, "z1"),
    "snooze": ("closed", "snore", False, "z2"),
}


def cycle(frames, step, start, until):
    out, i, t = [], 0, start
    while t < until - 1e-6:
        out.append((t, frames[i % len(frames)]))
        i += 1
        t += step
    return out


STILL = [(0, (0, 0))]
# Choreography from NV-CODE's Tako Ink: one loop on the ground.
SCRIPT = [
    dict(d=1.4, x=0, gait="stand", face=[(0, "open"), (0.9, "blink"), (1.05, "open")], look=[(0, (0, 0))]),
    dict(d=4.2, x=55, gait="walk", face=[(0, "open"), (2.6, "blink"), (2.75, "open")], look=[(0, (2, 0))]),
    dict(d=0.8, gait="stand", face=[(0, "open")], look=[(0, (2, -1))]),
    dict(d=0.8, gait="stand", face=[(0, "open")], look=[(0, (-2, -1))]),
    dict(d=1.5, gait="stand", face=[(0, "wide"), (1.0, "happy")], look=[(0, (0, 0))]),
    dict(d=3.6, gait="stand", face=[(0, "eat"), *cycle(["chomp", "chew"], 0.3, 0.7, 2.2),
                                    *cycle(["chompLast", "chewLast"], 0.3, 2.2, 3.1), (3.1, "happy")], look=STILL),
    dict(d=1.0, gait="jump", h=16, face=[(0, "happy")], look=[(0, (0, 0))]),
    dict(d=1.4, x=100, gait="runR", face=[(0, "open")], look=[(0, (2, 0))]),
    dict(d=0.35, gait="skid", face=[(0, "wide")], look=[(0, (2, 0))]),
    dict(d=1.4, gait="stand", face=[(0, "wide")], look=[(0, (2, -1)), (0.7, (0, -1))]),
    dict(d=0.8, gait="stand", face=[(0, "open"), (0.4, "blink"), (0.55, "open")], look=[(0, (0, 0))]),
    dict(d=3.0, gait="stand", face=[(0, "drink"), (0.5, "gulp"), (1.3, "drink"), (1.5, "gulp"),
                                    (2.1, "gulpLast"), (2.5, "ahh")], look=STILL),
    dict(d=2.4, x=10, gait="runL", face=[(0, "open")], look=[(0, (-2, 0))]),
    dict(d=0.35, gait="skid", face=[(0, "wide")], look=[(0, (-2, 0))]),
    dict(d=0.9, gait="stand", face=[(0, "wide"), (0.5, "open")], look=[(0, (0, -1)), (0.5, (0, 0))]),
    dict(d=0.6, gait="jump", h=7, face=[(0, "happy")], look=[(0, (0, 0))]),
    dict(d=1.0, x=0, gait="walk", face=[(0, "open")], look=[(0, (-2, 0))]),
    dict(d=1.6, gait="stand", face=[(0, "sleepy"), (0.8, "blink"), (1.0, "sleepy")], look=STILL),
    dict(d=6.0, gait="sleep", face=cycle(["doze", "snooze"], 1.0, 0, 6.0), look=STILL),
    dict(d=1.2, gait="stand", face=[(0, "sleepy"), (0.5, "blink"), (0.7, "open")], look=STILL),
]

NAP = [
    dict(d=1.6, gait="stand", face=[(0, "sleepy"), (0.8, "blink"), (1.0, "sleepy")], look=STILL),
    dict(d=8.0, gait="sleep", face=cycle(["doze", "snooze"], 1.0, 0, 8.0), look=STILL),
    dict(d=1.4, gait="stand", face=[(0, "sleepy"), (0.5, "blink"), (0.7, "open"), (1.1, "blink")], look=STILL),
    dict(d=1.0, gait="stand", face=[(0, "sleepy")], look=STILL),
]


def compile_script(script):
    loop = sum(b["d"] for b in script)
    kf = {"x": [], "gait": [], "hop": [], "face": [], "look": []}
    t = x = 0
    for beat in script:
        t1 = t + beat["d"]
        kf["x"].append((t, x))
        if "x" in beat:
            x = beat["x"]
        kf["x"].append((t1, x))
        kf["face"] += [(t + at, f) for at, f in beat["face"]]
        kf["look"] += [(t + at, xy) for at, xy in beat["look"]]
        start = t

        def hop(at, jump, sx=1, sy=1):
            kf["hop"].append((start + at, (jump, sx, sy)))

        gait = beat["gait"]
        if gait == "stand":
            kf["gait"].append((t, "stand"))
            hop(0, 0)
        elif gait in ("walk", "runR", "runL"):
            run = gait != "walk"
            beat_len = 0.09 if run else 0.15
            frames = ["stand", f"{gait}A", "stand", f"{gait}B"] if run else ["stand", "stepA", "stand", "stepB"]
            n = max(4, round(beat["d"] / beat_len / 4) * 4)
            step = beat["d"] / n
            for i in range(n):
                frame = frames[i % 4]
                kf["gait"].append((t + i * step, frame))
                hop(i * step, 0 if frame == "stand" else 1)
            kf["gait"].append((t1 - 0.001, "stand"))
            hop(beat["d"], 0)
        elif gait == "sleep":
            kf["gait"].append((t, "stand"))
            at = 0.0
            while at < beat["d"] - 1e-6:
                hop(at, 0)
                hop(at + 1, 0, 1.04, 0.94)
                at += 2
            hop(beat["d"], 0)
        elif gait == "skid":
            kf["gait"].append((t, "stand"))
            hop(0, 0, 1.05, 0.95)
            hop(beat["d"], 0)
        elif gait == "jump":
            h, d = beat.get("h", 10), beat["d"]
            kf["gait"] += [(t, "stand"), (t + d * 0.25, "stepA"), (t + d * 0.7, "stand")]
            for at, jump, sx, sy in [(0, 0, 1, 1), (0.15, 0, 1.14, 0.8), (0.32, round(h * 0.8), 0.9, 1.14),
                                     (0.45, h, 1, 1), (0.62, round(h * 0.25), 0.94, 1.08),
                                     (0.7, 0, 1.16, 0.8), (0.85, 0, 0.97, 1.04), (1, 0, 1, 1)]:
                hop(d * at, jump, sx, sy)
        t = t1
    return loop, kf


def _keyframes(name, frames, loop, rest, fmt):
    by_pct = {}
    for t, v in sorted(frames, key=lambda f: f[0]):
        by_pct[f"{min(t, loop) / loop * 100:.3f}".rstrip("0").rstrip(".") + "%"] = v
    by_pct.setdefault("0%", rest)
    by_pct.setdefault("100%", rest)
    ordered = sorted(by_pct.items(), key=lambda kv: float(kv[0][:-1]))
    # Drop keyframes that repeat the previous value (fine for step-end tracks).
    return f"@keyframes {name}{{" + "".join(f"{p}{{{fmt(v)}}}" for p, v in ordered) + "}"


def _visibility_track(name, frames, loop, rest):
    by_pct = {}
    for t, v in sorted(frames, key=lambda f: f[0]):
        by_pct[min(t, loop) / loop * 100] = v
    by_pct.setdefault(0.0, rest)
    by_pct.setdefault(100.0, rest)
    tracks = {}
    for frame in sorted(set(by_pct.values())):
        out, last = [], None
        for p in sorted(by_pct):
            on = by_pct[p] == frame
            if on != last or p in (0.0, 100.0):
                out.append(f"{p:.3f}".rstrip("0").rstrip(".") + f"%{{opacity:{1 if on else 0}}}")
                last = on
        tracks[frame] = f"@keyframes {name}-{frame}{{{''.join(out)}}}"
    return tracks


def tako(svg, prefix, x, ground, walkway, px=3, script=None, delay=0.0, still_face="open"):
    """Draws the tako with its whole loop. `walkway` is how far it may travel in px."""
    loop, kf = compile_script(script or SCRIPT)
    w, h = COLS * px, ROWS * px
    span = max(0, walkway - w)
    dur = f"{loop:.2f}s"
    anim = lambda name, timing: f"animation:{prefix}-{name} {dur} {timing} {-delay:.2f}s infinite"
    svg.css.append(
        _keyframes(f"{prefix}-x", kf["x"], loop, 0, lambda v: f"transform:translateX({v / 100 * span:.1f}px)")
        + _keyframes(f"{prefix}-hop", kf["hop"], loop, (0, 1, 1),
                     lambda v: f"transform:translateY({-v[0] * px}px) scale({v[1]},{v[2]})")
        + _keyframes(f"{prefix}-sh", kf["hop"], loop, (0, 1, 1), lambda v: f"transform:scaleX({v[1]})")
        + _keyframes(f"{prefix}-look", kf["look"], loop, (0, 0),
                     lambda v: f"transform:translate({v[0]}px,{v[1]}px)")
        + f".{prefix}-x{{{anim('x', 'linear')}}}"
        + f".{prefix}-hop{{transform-box:fill-box;transform-origin:50% 100%;{anim('hop', 'ease-in-out')}}}"
        + f".{prefix}-sh{{transform-box:fill-box;transform-origin:50% 50%;{anim('sh', 'ease-in-out')}}}"
        + f".{prefix}-look{{{anim('look', 'step-end')}}}"
    )
    gait_tracks = _visibility_track(f"{prefix}-g", kf["gait"], loop, "stand")
    face_tracks = _visibility_track(f"{prefix}-f", kf["face"], loop, "open")
    for frame, rule in {**gait_tracks, **face_tracks}.items():
        svg.css.append(rule)
    for frame in gait_tracks:
        svg.css.append(f".{prefix}-g-{frame}{{opacity:0;animation:{prefix}-g-{frame} {dur} step-end {-delay:.2f}s infinite}}")
    for frame in face_tracks:
        svg.css.append(f".{prefix}-f-{frame}{{opacity:0;animation:{prefix}-f-{frame} {dur} step-end {-delay:.2f}s infinite}}")
    # Without motion it simply stands and smiles.
    svg.css.append(
        f"@media (prefers-reduced-motion: reduce){{.{prefix}-g-stand,.{prefix}-f-{still_face}{{opacity:1}}}}"
    )
    bodies = "".join(f'<g class="{prefix}-g-{f}">{BODIES[f]()}</g>' for f in gait_tracks)
    faces = "".join(f'<g class="{prefix}-f-{f}">{face_sprite(*FACES[f])}</g>' for f in face_tracks)
    top = ground + px - h  # tentacle tips sit one pixel into the ground, as in NV-CODE
    svg.add(
        f'<g transform="translate({x} 0)"><g class="{prefix}-x">'
        f'<g transform="translate(0 {ground - 3 * px}) scale({px})"><g class="{prefix}-sh" shape-rendering="crispEdges">{shadow_sprite()}</g></g>'
        f'<g class="{prefix}-hop"><g transform="translate(0 {top}) scale({px})" shape-rendering="crispEdges">'
        f'{bodies}<g class="{prefix}-look">{faces}</g></g></g></g></g>'
    )
    return loop
