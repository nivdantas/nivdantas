"""Builds the animated SVGs used in the profile README.

The look follows nivdantas.com: ink on paper, Instrument Serif headlines,
Geist body copy and Geist Mono labels. Every SVG is written twice, once for
GitHub's light theme and once for its dark theme.

Usage: python scripts/build_assets.py   (needs: pip install fonttools brotli)
"""

import base64
import io
import math
from pathlib import Path
from xml.sax.saxutils import escape

from fontTools import subset
from fontTools.ttLib import TTFont
from fontTools.varLib import instancer

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "scripts" / "fonts"
OUT = ROOT / "assets"

THEMES = {
    "light": {
        "bg": "#fbfbfb",
        "quiet": "#ededed",
        "surface": "#d7d7d7",
        "text": "#0d0d0d",
        "secondary": "#454545",
        "muted": "#646464",
        "line": "#b9b9b9",
        "control": "#646464",
    },
    "dark": {
        "bg": "#0d0d0d",
        "quiet": "#191919",
        "surface": "#2c2c2c",
        "text": "#fbfbfb",
        "secondary": "#b9b9b9",
        "muted": "#9c9c9c",
        "line": "#454545",
        "control": "#9c9c9c",
    },
}

INK = "cubic-bezier(0.65, 0, 0.35, 1)"
EXPO = "cubic-bezier(0.16, 1, 0.3, 1)"
SPRING = "cubic-bezier(0.34, 1.56, 0.64, 1)"


# ---------------------------------------------------------------- fonts


class Font:
    def __init__(self, file, family, style="normal"):
        font = TTFont(FONTS / file)
        if "fvar" in font:
            font = instancer.instantiateVariableFont(font, {"wght": 400})
        self.font = font
        self.family = family
        self.style = style
        self.cmap = font.getBestCmap()
        self.hmtx = font["hmtx"]
        self.upm = font["head"].unitsPerEm
        self.used = set()

    def width(self, text, size, tracking=0.0):
        units = 0
        for char in text:
            glyph = self.cmap.get(ord(char)) or self.cmap.get(ord("?"))
            units += self.hmtx[glyph][0]
        return units / self.upm * size + tracking * size * len(text)

    def face(self):
        """An @font-face rule embedding only the characters this SVG uses."""
        options = subset.Options()
        options.flavor = "woff2"
        options.layout_features = ["kern", "liga"]
        options.name_IDs = []
        options.notdef_outline = True
        subsetter = subset.Subsetter(options)
        font = TTFont(io.BytesIO(self._bytes()))
        subsetter.populate(text="".join(sorted(self.used)) + " ")
        subsetter.subset(font)
        buffer = io.BytesIO()
        font.flavor = "woff2"
        font.save(buffer)
        data = base64.b64encode(buffer.getvalue()).decode()
        return (
            f"@font-face{{font-family:'{self.family}';font-style:{self.style};"
            f"src:url(data:font/woff2;base64,{data}) format('woff2')}}"
        )

    def _bytes(self):
        buffer = io.BytesIO()
        self.font.flavor = None
        self.font.save(buffer)
        return buffer.getvalue()


SANS = Font("Geist.woff2", "Geist")
MONO = Font("GeistMono.woff2", "Geist Mono")
SERIF = Font("InstrumentSerif.woff2", "Instrument Serif")
ITALIC = Font("InstrumentSerif-Italic.woff2", "Instrument Serif", "italic")

STYLES = {
    # class: (font, size, tracking, uppercase, fill)
    "label": (MONO, 11, 0.06, True, "muted"),
    "label-ink": (MONO, 11, 0.06, True, "text"),
    "label-lg": (MONO, 12, 0.06, True, "muted"),
    "tag": (MONO, 11, 0.06, True, "secondary"),
    "button": (SANS, 14, 0, False, "bg"),
    "body": (SANS, 20, -0.015, False, "text"),
    "intro": (SANS, 23, -0.015, False, "secondary"),
    "small": (SANS, 14, 0, False, "secondary"),
    "card": (SANS, 17, -0.015, False, "text"),
    "row": (SANS, 13, 0, False, "text"),
}


class Svg:
    def __init__(self, width, height, theme, title):
        self.w, self.h = width, height
        self.c = THEMES[theme]
        self.title = title
        self.fonts = set()
        self.css = []
        self.defs = []
        self.body = []

    def add(self, markup):
        self.body.append(markup)

    def text(self, x, y, value, style=None, *, font=None, size=None, fill=None,
             anchor="start", cls="", extra="", tracking=0.0):
        if style:
            font, size, tracking, upper, color = STYLES[style]
            value = value.upper() if upper else value
            fill = fill or self.c[color]
        fill = fill or self.c["text"]
        font.used.update(value)
        self.fonts.add(font)
        ls = f' letter-spacing="{tracking * size:.2f}"' if tracking else ""
        style_attr = ' font-style="italic"' if font.style == "italic" else ""
        klass = f' class="{cls}"' if cls else ""
        return (
            f'<text x="{x:.1f}" y="{y:.1f}" font-family="{font.family}" '
            f'font-size="{size}"{style_attr}{ls} fill="{fill}" '
            f'text-anchor="{anchor}"{klass}{extra}>{escape(value)}</text>'
        )

    def width(self, value, style):
        font, size, tracking, upper, _ = STYLES[style]
        return font.width(value.upper() if upper else value, size, tracking)

    def pill(self, x, y, value, style="tag", *, stroke=None, fill="none", pad=10,
             height=22):
        w = self.width(value, style) + pad * 2
        stroke = stroke or self.c["line"]
        markup = (
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{height}" '
            f'rx="{height / 2}" fill="{fill}" stroke="{stroke}"/>'
            + self.text(x + pad, y + height / 2 + 4, value, style)
        )
        return markup, w

    def render(self):
        faces = "".join(font.face() for font in self.fonts)
        css = faces + "".join(self.css) + (
            "@media (prefers-reduced-motion: reduce){*{animation:none!important}"
            ".motion-only{display:none}}"
        )
        return (
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" '
            f'height="{self.h}" viewBox="0 0 {self.w} {self.h}" role="img" '
            f'aria-label="{escape(self.title)}"><title>{escape(self.title)}</title>'
            f"<defs><style>{css}</style>{''.join(self.defs)}</defs>"
            f"{''.join(self.body)}</svg>"
        )


def wrap(text, style, max_width, svg):
    lines, line = [], ""
    for word in text.split():
        trial = f"{line} {word}".strip()
        if line and svg.width(trial, style) > max_width:
            lines.append(line)
            line = word
        else:
            line = trial
    return lines + [line]


def rounded(x, y, w, h, tl, tr, br, bl):
    return (
        f"M{x + tl} {y}H{x + w - tr}A{tr} {tr} 0 0 1 {x + w} {y + tr}"
        f"V{y + h - br}A{br} {br} 0 0 1 {x + w - br} {y + h}"
        f"H{x + bl}A{bl} {bl} 0 0 1 {x} {y + h - bl}V{y + tl}"
        f"A{tl} {tl} 0 0 1 {x + tl} {y}Z"
    )


def arrow(x, y, color, diagonal=True, size=10):
    """The portfolio's arrow, drawn as a path so no glyph is needed."""
    s = size
    if diagonal:
        d = f"M{x} {y + s}L{x + s} {y}M{x + 3} {y}H{x + s}V{y + s - 3}"
    else:
        d = f"M{x + s / 2} {y}V{y + s}M{x + 1} {y + s - 4.5}L{x + s / 2} {y + s}L{x + s - 1} {y + s - 4.5}"
    return (
        f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.4" '
        'stroke-linecap="round" stroke-linejoin="round"/>'
    )


def frame(svg, radius=6):
    svg.add(
        f'<rect x="0.5" y="0.5" width="{svg.w - 1}" height="{svg.h - 1}" '
        f'rx="{radius}" fill="{svg.c["bg"]}" stroke="{svg.c["line"]}"/>'
    )


# ---------------------------------------------------------------- header

# One pen stroke, written three slightly different ways: no two signatures match.
STROKES = [
    "M76 252C82 190 92 120 106 68c4-12 12-10 18 0 30 58 68 130 100 180 6 10 14 6 14-6 2-62 8-122 22-182",
    "M80 256C80 196 88 126 100 72c2-14 12-14 18-2 34 56 72 124 106 172 8 10 16 4 16-8-2-58 2-118 12-176",
    "M72 248C82 184 96 116 112 64c4-10 10-8 16 2 26 60 60 134 92 186 6 8 14 4 14-8 4-64 12-124 30-178",
]


def header(theme):
    svg = Svg(1200, 440, theme, "Nivaldo Dantas, software engineer. Thoughtful code. A personal touch.")
    c = svg.c
    cycle = 15  # seconds; each signature gets five
    svg.css.append(
        f"""
.rule{{transform-box:fill-box;transform-origin:left;animation:rule 1.2s {EXPO} .1s both}}
@keyframes rule{{from{{transform:scaleX(0)}}}}
.rise{{transform-box:fill-box;transform-origin:left bottom;animation:rise 1.1s {EXPO} both}}
@keyframes rise{{from{{transform:translateY(118px) rotate(3deg)}}}}
.fade{{animation:fade .9s {EXPO} both}}
@keyframes fade{{from{{opacity:0;transform:translateY(14px)}}}}
.sig{{fill:none;stroke:{c['text']};stroke-width:17;stroke-linecap:round;stroke-linejoin:round;
stroke-dasharray:1;stroke-dashoffset:1;animation:sign {cycle}s {INK} infinite backwards}}
@keyframes sign{{0%{{stroke-dashoffset:1}}7.3%,28%{{stroke-dashoffset:0}}32%,100%{{stroke-dashoffset:1}}}}
.dot{{fill:{c['text']};transform-box:fill-box;transform-origin:center;transform:scale(0);
animation:dot {cycle}s {EXPO} infinite backwards}}
@keyframes dot{{0%,7.3%{{transform:scale(0)}}9.4%,28%{{transform:scale(1)}}30%,100%{{transform:scale(0)}}}}
.v2{{animation-delay:{cycle / 3}s}}.v3{{animation-delay:{cycle * 2 / 3}s}}
.bob{{animation:bob 2.4s ease-in-out infinite}}
@keyframes bob{{50%{{transform:translateY(4px)}}}}
@media (prefers-reduced-motion: reduce){{.v1 .sig{{stroke-dashoffset:0}}.v1.dot,.v1 .dot{{transform:none}}.v2,.v3{{display:none}}}}
"""
    )
    for seed in range(3):
        svg.defs.append(
            f'<filter id="ink{seed}" x="-10%" y="-10%" width="120%" height="120%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.035" numOctaves="2" seed="{seed}"/>'
            '<feDisplacementMap in="SourceGraphic" scale="6"/></filter>'
        )
    svg.defs.append('<clipPath id="h1"><rect x="0" y="70" width="840" height="143"/></clipPath>')
    svg.defs.append('<clipPath id="h2"><rect x="0" y="213" width="840" height="110"/></clipPath>')
    frame(svg)

    svg.add(f'<g class="fade" style="animation-delay:.05s">'
            + svg.text(48, 46, "Nivaldo Dantas · Software engineer", "label-lg")
            + svg.text(1152, 46, "Brazil / Web, mobile & AI", "label-lg", anchor="end")
            + "</g>")
    svg.add(f'<line class="rule" x1="48" y1="66" x2="1152" y2="66" stroke="{c["line"]}"/>')

    svg.add('<g clip-path="url(#h1)"><g class="rise" style="animation-delay:.25s">'
            + svg.text(44, 186, "Thoughtful code.", font=SERIF, size=104, tracking=-0.02)
            + "</g></g>")
    svg.add('<g clip-path="url(#h2)"><g class="rise" style="animation-delay:.4s">'
            + svg.text(44, 292, "A personal touch.", font=ITALIC, size=104, tracking=-0.02,
                       fill=c["secondary"])
            + "</g></g>")

    intro = svg.text(48, 352, "", "intro").replace("></text>", ">")
    SANS.used.update("I'm Niv. I build the interface, the API, and the connections between them.")
    svg.add(
        '<g class="fade" style="animation-delay:.7s">'
        + intro
        + f'I’m <tspan fill="{c["text"]}">Niv</tspan>. I build the interface, the API,</text>'
        + svg.text(48, 382, "and the connections between them.", "intro")
        + "</g>"
    )
    SANS.used.add("’")

    svg.add(
        '<g class="fade" style="animation-delay:1s">'
        + svg.text(48, 414, "Scroll to explore", "label")
        + f'<g class="bob">{arrow(180, 404, c["muted"], diagonal=False)}</g></g>'
    )

    # The signed N, about 300px square, on the right.
    svg.add('<g transform="translate(852 74) scale(0.94)">')
    for i, stroke in enumerate(STROKES):
        v = f"v{i + 1}"
        svg.add(
            f'<g class="{v}" filter="url(#ink{i})">'
            f'<path class="sig {v}" pathLength="1" d="{stroke}"/>'
            f'<circle class="dot {v}" cx="286" cy="246" r="10"/></g>'
        )
    svg.add("</g>")
    svg.add('<g class="fade" style="animation-delay:1.2s">'
            + svg.text(1002, 414, "Different pieces. One connected system.", "label", anchor="middle")
            + "</g>")
    return svg.render()


# ---------------------------------------------------------------- connections

GROUPS = [
    ("01", "Interfaces", ["React", "Svelte", "React Native", "TypeScript"]),
    ("02", "Systems", ["Express", "REST", "SQL", "Laravel", "PHP"]),
    ("03", "Automation", ["n8n", "Webhooks", "REST"]),
    ("04", "AI integrations", ["Gemini", "SQLite", "Docker"]),
]


def connections(theme):
    svg = Svg(1200, 430, theme, "How the pieces fit: interfaces, systems, automation and AI integrations, connected.")
    c = svg.c
    travel = 6.0
    x0, box_w, gap, top, box_h, wire_y = 48, 258, 24, 156, 158, 372
    length = 1104
    svg.css.append(
        f"""
.packet{{animation:packet {travel}s linear infinite}}
@keyframes packet{{0%{{transform:translateX(0);opacity:0}}4%,96%{{opacity:1}}100%{{transform:translateX({length}px);opacity:0}}}}
.node{{transform-box:fill-box;transform-origin:center;animation:node {travel}s {EXPO} infinite}}
@keyframes node{{0%,100%{{transform:scale(1)}}2%{{transform:scale(2.1)}}8%{{transform:scale(1)}}}}
.box{{animation:box {travel}s ease-out infinite}}
@keyframes box{{0%,100%{{stroke:{c['line']}}}2%{{stroke:{c['text']}}}14%{{stroke:{c['line']}}}}}
.fade{{animation:fade .9s {EXPO} both}}
@keyframes fade{{from{{opacity:0;transform:translateY(14px)}}}}
"""
    )
    frame(svg)
    svg.add(svg.text(48, 46, "How the pieces fit", "label-lg"))
    svg.add(svg.text(1152, 46, "Tools make sense in context", "label-lg", anchor="end"))
    svg.add(f'<line x1="48" y1="66" x2="1152" y2="66" stroke="{c["line"]}"/>')
    title = svg.text(48, 124, "From the screen. ", font=SERIF, size=56, tracking=-0.02)
    title_w = SERIF.width("From the screen. ", 56, -0.02)
    svg.add('<g class="fade">' + title
            + svg.text(48 + title_w, 124, "To the system.", font=ITALIC, size=56,
                       tracking=-0.02, fill=c["secondary"]) + "</g>")

    svg.add(f'<line x1="48" y1="{wire_y}" x2="1152" y2="{wire_y}" stroke="{c["line"]}"/>')
    for i, (number, name, tags) in enumerate(GROUPS):
        x = x0 + i * (box_w + gap)
        cx = x + box_w / 2
        delay = (cx - 48) / length * travel
        sync = f'style="animation-delay:{delay - travel:.2f}s"'
        svg.add(f'<g class="fade" style="animation-delay:{0.15 + i * 0.1:.2f}s">')
        svg.add(f'<rect class="box" {sync} x="{x}.5" y="{top}.5" width="{box_w - 1}" '
                f'height="{box_h}" rx="4" fill="{c["bg"]}" stroke="{c["line"]}"/>')
        svg.add(svg.text(x + 18, top + 30, f"{number} /", "label"))
        svg.add(svg.text(x + 18, top + 70, name, font=SERIF, size=32, tracking=-0.01))
        tx, ty = x + 18, top + 92
        for tag in tags:
            w = svg.width(tag, "tag") + 20
            if tx + w > x + box_w - 18:
                tx, ty = x + 18, ty + 30
            markup, w = svg.pill(tx, ty, tag)
            svg.add(markup)
            tx += w + 6
        svg.add(f'<line x1="{cx}" y1="{top + box_h + 1}" x2="{cx}" y2="{wire_y}" '
                f'stroke="{c["line"]}" stroke-dasharray="2 4"/>')
        svg.add(f'<circle class="node" {sync} cx="{cx}" cy="{wire_y}" r="4" fill="{c["text"]}"/>')
        svg.add("</g>")
    svg.add(f'<circle class="packet motion-only" cx="48" cy="{wire_y}" r="5" fill="{c["text"]}"/>')
    svg.add(svg.text(48, 410, "The interface someone uses. The API behind it. The data that makes it useful.",
                     "label"))
    return svg.render()


# ---------------------------------------------------------------- project cards

PROJECTS = [
    {
        "slug": "bolota",
        "number": "01",
        "name": "Bolota",
        "category": "AI & conversation",
        "description": "A veterinary assistant that connects natural language to the information a pet shop actually needs.",
        "detail": "Gemini handles the conversation while an Express API connects to a local SQLite database of prices, inventory, and medications.",
        "tags": ["Gemini", "TypeScript", "Express", "SQLite"],
        "development": False,
    },
    {
        "slug": "n-store",
        "number": "02",
        "name": "n-store",
        "category": "Commerce & systems",
        "description": "An e-commerce platform in progress, exploring the pieces behind a complete shopping experience.",
        "detail": "Built on Laravel 12 and PHP with Blade templates. A space to develop the structure and interfaces of a commerce platform.",
        "tags": ["Laravel", "PHP", "Blade"],
        "development": True,
    },
    {
        "slug": "takostreak",
        "number": "03",
        "name": "TakoStreak",
        "category": "Small tools, daily habits",
        "description": "Fluffy streaks for everyone. A small, playful project about showing up, one day at a time.",
        "detail": "Built with React, TanStack, Express, and TypeScript. An experiment in making a simple daily interaction feel a little more personal.",
        "tags": ["React", "TanStack", "Express", "TypeScript"],
        "development": True,
    },
]


def study_bolota(svg):
    c = svg.c
    svg.css.append(
        f"""
.q{{transform-box:fill-box;transform-origin:center;animation:q 6s ease-in-out infinite}}
@keyframes q{{50%{{transform:translateX(-6px) rotate(-1deg)}}}}
.a{{transform-box:fill-box;transform-origin:center;animation:a 6s ease-in-out infinite}}
@keyframes a{{50%{{transform:translateX(6px) rotate(1deg)}}}}
.drop{{animation:drop 2.4s {INK} infinite}}
@keyframes drop{{0%{{transform:none;opacity:0}}15%,85%{{opacity:1}}100%{{transform:translateY(57px);opacity:0}}}}
.typing circle{{animation:typing 1.4s ease-in-out infinite}}
@keyframes typing{{0%,60%,100%{{opacity:.25}}30%{{opacity:1}}}}
.row{{animation:row 4.8s ease-in-out infinite}}
@keyframes row{{0%,100%{{opacity:.55}}20%,45%{{opacity:1}}}}
"""
    )
    x, y, w = 120, 108, 281
    svg.add(f'<g class="q"><path d="{rounded(x, y, w, 86, 4, 14, 14, 14)}" '
            f'fill="{c["bg"]}" stroke="{c["text"]}"/>'
            + svg.text(x + 16, y + 26, "01 / Input", "label")
            + svg.text(x + 16, y + 54, "A question from a customer.", "card")
            + '<g class="typing">'
            + "".join(f'<circle cx="{x + 20 + k * 9}" cy="{y + 70}" r="2.4" fill="{c["text"]}" '
                      f'style="animation-delay:{k * 0.18:.2f}s"/>' for k in range(3))
            + "</g></g>")
    svg.add(f'<line x1="300.5" y1="194" x2="300.5" y2="252" stroke="{c["control"]}"/>')
    svg.add(f'<circle class="drop motion-only" cx="300.5" cy="196" r="3.5" fill="{c["text"]}"/>')
    x2, y2 = 199, 252
    rows = ""
    for k, (left, right) in enumerate([("Inventory & prices", "SQLite"), ("Conversation", "Gemini")]):
        ry = y2 + 44 + k * 34
        rows += (
            f'<g class="row" style="animation-delay:{k * 2.4:.1f}s">'
            f'<line x1="{x2 + 16}" y1="{ry}" x2="{x2 + w - 16}" y2="{ry}" stroke="{c["bg"]}" stroke-opacity=".25"/>'
            + svg.text(x2 + 16, ry + 22, left, "row", fill=c["bg"])
            + svg.text(x2 + w - 16, ry + 22, right, "label", fill=c["bg"], anchor="end")
            + "</g>"
        )
    svg.add(f'<g class="a"><path d="{rounded(x2, y2, w, 120, 14, 14, 4, 14)}" fill="{c["text"]}"/>'
            + svg.text(x2 + 16, y2 + 26, "02 / Context", "label", fill=c["bg"],
                       extra=' fill-opacity=".6"')
            + rows + "</g>")


def study_store(svg):
    c = svg.c
    svg.css.append(
        f"""
.lift{{transform-box:fill-box;animation:lift 4s {SPRING} infinite}}
@keyframes lift{{0%,30%,100%{{transform:none}}12%{{transform:translateY(-12px)}}}}
.receipt{{transform-box:fill-box;transform-origin:center;transform:rotate(-4deg);animation:receipt 6s ease-in-out infinite}}
@keyframes receipt{{50%{{transform:rotate(0) translateY(-4px)}}}}
.print{{animation:print 6s ease-out infinite}}
@keyframes print{{0%{{opacity:0;transform:translateY(-4px)}}8%,88%{{opacity:1;transform:none}}96%,100%{{opacity:0}}}}
"""
    )
    svg.defs.append(
        f'<pattern id="hatch" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
        f'<line x1="0" y1="0" x2="0" y2="7" stroke="{c["text"]}"/></pattern>'
    )
    base = 312
    svg.add(f'<line x1="84" y1="{base}.5" x2="416" y2="{base}.5" stroke="{c["text"]}"/>')
    svg.add(f'<circle class="lift" cx="140" cy="{base - 42}" r="42" fill="{c["text"]}"/>')
    svg.add(f'<path class="lift" style="animation-delay:.25s" d="M200.5 {base}V{base - 96}a36 36 0 0 1 72 0V{base}" '
            f'fill="{c["surface"]}" stroke="{c["text"]}"/>')
    svg.add(f'<path class="lift" style="animation-delay:.5s" d="M290.5 {base}V{base - 92}h92V{base}" '
            f'fill="url(#hatch)" stroke="{c["text"]}"/>')
    rx, ry, rw = 352, 222, 176
    lines = ""
    for k, item in enumerate(["Catalog", "Interface", "Data"]):
        ly = ry + 40 + k * 30
        lines += (
            f'<g class="print" style="animation-delay:{0.3 + k * 0.35:.2f}s">'
            f'<line x1="{rx + 14}" y1="{ly}" x2="{rx + rw - 14}" y2="{ly}" stroke="{c["text"]}" stroke-opacity=".25"/>'
            + svg.text(rx + 14, ly + 20, f"0{k + 1}", "label")
            + svg.text(rx + rw - 14, ly + 20, item, "row", anchor="end")
            + "</g>"
        )
    bars = ""
    bx = rx + 14
    pattern = [2, 1, 3, 1, 1, 2, 1, 3, 2, 1, 1, 2, 3, 1, 2, 1, 1, 3, 1, 2, 2, 1, 3, 1, 2, 1]
    k = 0
    while bx < rx + rw - 16:
        bw = pattern[k % len(pattern)]
        bars += f'<rect x="{bx}" y="{ry + 136}" width="{bw}" height="18" fill="{c["text"]}"/>'
        bx += bw + 3 + (k % 3)
        k += 1
    svg.add(f'<g class="receipt"><rect x="{rx}.5" y="{ry}.5" width="{rw}" height="168" rx="4" '
            f'fill="{c["bg"]}" stroke="{c["text"]}"/>'
            + svg.text(rx + 14, ry + 26, "A commerce study", "label")
            + lines + f'<g class="print" style="animation-delay:1.4s">{bars}</g></g>')


def study_streak(svg):
    c = svg.c
    svg.css.append(
        f"""
.creature{{animation:bob 4.5s ease-in-out infinite}}
@keyframes bob{{50%{{transform:translateY(-8px) rotate(-1.5deg)}}}}
.eye{{transform-box:fill-box;transform-origin:center;animation:blink 5s infinite}}
@keyframes blink{{0%,92%,100%{{transform:none}}96%{{transform:scaleY(.1)}}}}
.day{{transform-box:fill-box;transform-origin:bottom;transform:scaleY(0);animation:day 7s {SPRING} infinite}}
@keyframes day{{0%{{transform:scaleY(0)}}6%,90%{{transform:scaleY(1)}}96%,100%{{transform:scaleY(0)}}}}
.today{{animation:today 1.6s ease-in-out infinite}}
@keyframes today{{50%{{stroke-opacity:.3}}}}
@media (prefers-reduced-motion: reduce){{.day{{transform:none}}}}
"""
    )
    svg.add(
        '<g transform="translate(205 100) scale(1.055)"><g class="creature">'
        f'<path d="M12 70C12 5 168 5 168 70M12 70c0 24 26 16 26 0 0 24 26 16 26 0 0 24 26 16 26 0 0 24 26 16 26 0 0 24 26 16 26 0 0 24 26 16 26 0" '
        f'fill="{c["bg"]}" stroke="{c["text"]}" stroke-width="1.5" stroke-linejoin="round"/>'
        f'<circle class="eye" cx="70" cy="50" r="5" fill="{c["text"]}"/>'
        f'<circle class="eye" cx="110" cy="50" r="5" fill="{c["text"]}"/></g></g>'
    )
    svg.add(svg.text(300, 256, "One day at a time", "label", anchor="middle"))
    x0 = 300 - (7 * 22 + 6 * 5) / 2
    for i in range(7):
        x = x0 + i * 27
        if i < 5:
            svg.add(f'<rect class="day" style="animation-delay:{0.2 + i * 0.35:.2f}s" x="{x}" y="270" '
                    f'width="22" height="52" rx="3" fill="{c["text"]}"/>')
        klass = ' class="today"' if i == 5 else ""
        svg.add(f'<rect{klass} x="{x + 0.5}" y="270.5" width="21" height="51" rx="3" fill="none" '
                f'stroke="{c["text"]}"/>')
    svg.add(svg.text(300, 348, "An illustrative week", "label", anchor="middle"))


STUDIES = {"bolota": study_bolota, "n-store": study_store, "takostreak": study_streak}


def project(theme, p):
    svg = Svg(1200, 420, theme, f"{p['name']}: {p['description']}")
    c = svg.c
    svg.css.append(
        f"""
.pulse{{animation:pulse 2.4s ease-in-out infinite}}
@keyframes pulse{{50%{{opacity:.25}}}}
.fade{{animation:fade .9s {EXPO} both}}
@keyframes fade{{from{{opacity:0;transform:translateY(14px)}}}}
.nudge{{animation:nudge 2.4s ease-in-out infinite}}
@keyframes nudge{{50%{{transform:translate(2px,-2px)}}}}
"""
    )
    svg.defs.append(f'<clipPath id="art"><rect x="1" y="1" width="599" height="418" rx="5"/></clipPath>')
    frame(svg)
    svg.add(f'<rect x="1" y="1" width="600" height="418" fill="{c["quiet"]}" clip-path="url(#art)"/>')
    svg.add(f'<line x1="600.5" y1="1" x2="600.5" y2="419" stroke="{c["line"]}"/>')
    svg.add(svg.text(24, 38, f"{p['number']} / Selected work", "label"))
    svg.add(svg.text(576, 38, "Visual study", "label", anchor="end"))
    STUDIES[p["slug"]](svg)

    x, right = 648, 1152
    y = 72
    svg.add('<g class="fade">')
    svg.add(svg.text(x, y, p["category"], "label"))
    if p["development"]:
        px = x + svg.width(p["category"], "label") + 14
        w = svg.width("In development", "label-ink") + 34
        svg.add(f'<rect x="{px}" y="{y - 15.5}" width="{w}" height="22" rx="11" fill="none" stroke="{c["control"]}"/>'
                f'<circle class="pulse" cx="{px + 14}" cy="{y - 4.5}" r="3" fill="{c["text"]}"/>'
                + svg.text(px + 24, y, "In development", "label-ink"))
    y += 70
    svg.add(svg.text(x - 3, y, p["name"], font=SERIF, size=68, tracking=-0.02))
    y += 40
    for line in wrap(p["description"], "body", right - x, svg):
        svg.add(svg.text(x, y, line, "body"))
        y += 27
    y += 8
    for line in wrap(p["detail"], "small", right - x, svg):
        svg.add(svg.text(x, y, line, "small"))
        y += 21
    y += 8
    tx = x
    for tag in p["tags"]:
        markup, w = svg.pill(tx, y, tag)
        svg.add(markup)
        tx += w + 6
    by = 350
    label = "Explore the source"
    bw = svg.width(label, "button") + 62
    svg.add(f'<rect x="{x}" y="{by}" width="{bw}" height="44" rx="22" fill="{c["text"]}"/>'
            + svg.text(x + 22, by + 27, label, "button")
            + f'<g class="nudge">{arrow(x + bw - 32, by + 17, c["bg"])}</g>')
    svg.add("</g>")
    return svg.render()


# ---------------------------------------------------------------- footer


def footer(theme):
    svg = Svg(1200, 300, theme, "Let's connect the next idea. Interfaces, APIs, and everything in between.")
    c = svg.c
    svg.css.append(
        f"""
.link{{stroke-dasharray:1;stroke-dashoffset:1;animation:link 5s {INK} infinite}}
@keyframes link{{0%{{stroke-dashoffset:1}}30%,80%{{stroke-dashoffset:0}}95%,100%{{stroke-dashoffset:-1}}}}
.end{{transform-box:fill-box;transform-origin:center;animation:end 5s {SPRING} infinite}}
@keyframes end{{0%,26%{{transform:scale(0)}}34%,82%{{transform:scale(1)}}92%,100%{{transform:scale(0)}}}}
.nudge{{animation:nudge 2.4s ease-in-out infinite}}
@keyframes nudge{{50%{{transform:translate(2px,-2px)}}}}
@media (prefers-reduced-motion: reduce){{.link{{stroke-dashoffset:0}}.end{{transform:none}}}}
"""
    )
    frame(svg)
    svg.add(svg.text(48, 46, "One more connection", "label-lg"))
    svg.add(svg.text(1152, 46, "nivdantas.com", "label-lg", anchor="end"))
    svg.add(f'<line x1="48" y1="66" x2="1152" y2="66" stroke="{c["line"]}"/>')
    first = "Let’s connect "
    w = SERIF.width(first, 80, -0.02)
    svg.add(svg.text(44, 160, first, font=SERIF, size=80, tracking=-0.02)
            + svg.text(44 + w, 160, "the next idea.", font=ITALIC, size=80, tracking=-0.02,
                       fill=c["secondary"]))
    # Two pieces, joined by a single hand-drawn line.
    svg.add(f'<circle cx="902" cy="196" r="7" fill="{c["text"]}"/>'
            f'<path class="link" pathLength="1" d="M902 196C952 120 1010 250 1060 170S1120 120 1136 130" '
            f'fill="none" stroke="{c["text"]}" stroke-width="2" stroke-linecap="round"/>'
            f'<circle class="end" cx="1136" cy="130" r="7" fill="{c["text"]}"/>')
    svg.add(svg.text(48, 210, "Interfaces, APIs, and everything in between.", "intro"))
    label = "nivdantas@icloud.com"
    bw = svg.width(label, "button") + 62
    svg.add(f'<rect x="48" y="234" width="{bw}" height="44" rx="22" fill="{c["text"]}"/>'
            + svg.text(70, 261, label, "button")
            + f'<g class="nudge">{arrow(48 + bw - 32, 251, c["bg"])}</g>')
    return svg.render()


# ---------------------------------------------------------------- build


def main():
    OUT.mkdir(exist_ok=True)
    builders = {"header": header, "connections": connections, "footer": footer}
    for p in PROJECTS:
        builders[f"project-{p['slug']}"] = lambda theme, p=p: project(theme, p)
    for name, build in builders.items():
        for theme in THEMES:
            for font in (SANS, MONO, SERIF, ITALIC):
                font.used = set()
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(build(theme), encoding="utf-8")
            print(f"{path.relative_to(ROOT)}  {path.stat().st_size / 1024:.1f} KB")


if __name__ == "__main__":
    main()
