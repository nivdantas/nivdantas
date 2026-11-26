"""Builds the profile README's animated SVGs in NV-CODE's Tako Ink look.

Usage: python scripts/build_assets.py   (needs: pip install fonttools brotli)
Each SVG is written for GitHub's dark and light themes.
"""

import math
from pathlib import Path

from inkkit import (BLUE, CHEEK, EXPO, HEAVY, INK, NAP, SEMI, THEMES, WATER, WHITE, Svg, arrow,
                    bayer, body_sprite, face_sprite, glow, grain_pattern, reset_fonts, tako, window)

OUT = Path(__file__).resolve().parent.parent / "assets"

FADE = (f".fade{{animation:fade .9s {EXPO} both}}"
        "@keyframes fade{from{opacity:0;transform:translateY(10px)}}")
NUDGE = ".go{animation:go 2.4s ease-in-out infinite}@keyframes go{50%{transform:translate(2px,-2px)}}"


def nv_icon(svg, x, y, size):
    """The NV-CODE icon: a navy tile with a dithered dash grid and a white NV."""
    dashes = ""
    for r in range(11):
        for c in range(12):
            level = bayer(c * 3, r * 5)
            if level < 0.55:
                w = 2 if level < 0.3 else 1.4
                dashes += (f'<rect x="{9 + c * 7.2:.1f}" y="{8 + r * 8:.1f}" width="{w}" height="3.6" '
                           f'fill="{BLUE["mid"]}" fill-opacity="{0.35 + (1 - level) * 0.6:.2f}"/>')
    svg.defs.append(
        '<linearGradient id="nvbg" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0" stop-color="#16348c"/><stop offset="1" stop-color="#0a1847"/></linearGradient>'
        '<clipPath id="nvclip"><rect x="2" y="2" width="96" height="96" rx="20"/></clipPath>'
    )
    svg.add(
        f'<g transform="translate({x} {y}) scale({size / 100})">'
        '<rect x="2" y="2" width="96" height="96" rx="20" fill="url(#nvbg)" stroke="#2a4bb0" stroke-width="1.2"/>'
        f'<g clip-path="url(#nvclip)">{dashes}</g>'
        + svg.text(50, 68, "NV", font=HEAVY, size=50, fill=WHITE, anchor="middle", tracking=-0.02)
        + "</g>"
    )


def ground_line(svg, x0, x1, y):
    d = "".join(f"M{x} {y}h2v2h-2z" for i, x in enumerate(range(x0, x1, 3)) if bayer(i, 3) < 0.5)
    svg.add(f'<path d="{d}" fill="{svg.c["border"]}"/>')


# ---------------------------------------------------------------- header

CHIPS = [("Bellus", BLUE["light"]), ("Worktables", BLUE["mid"]), ("Independent", CHEEK), ("Brazil", WATER)]
PHRASE = "Build the interface, the API, and everything in between."


def header(theme):
    svg = Svg(1200, 556, theme, "Nivaldo Dantas, software engineer. I build the interface, the API, "
                                "and the connections between them.")
    c = svg.c
    svg.css.append(FADE)
    window(svg)
    svg.add('<g clip-path="url(#window)">')
    glow(svg, "hg", 600, 392, 2.5, alpha=0.8 if theme == "dark" else None)
    svg.add("</g>")

    # Title bar.
    svg.add(f'<line x1="1" y1="44.5" x2="1199" y2="44.5" stroke="{c["border"]}"/>')
    for i in range(3):
        svg.add(f'<circle cx="{24 + i * 18}" cy="22" r="5.5" fill="none" stroke="{c["border"]}" stroke-width="1.5"/>')
    svg.add(svg.text(600, 26, "nv-code — nivdantas", "label", anchor="middle"))
    svg.add(svg.text(1176, 26, "Tako Ink", "label-accent", anchor="end"))

    svg.add('<g class="fade">')
    nv_icon(svg, 562, 78, 76)
    svg.add(svg.text(600, 218, "Nivaldo Dantas", font=SEMI, size=56, anchor="middle", tracking=-0.03))
    svg.add(svg.text(600, 254, "Software engineer. I build the interface, the API, and the connections between them.",
                     "lead", anchor="middle"))
    svg.add("</g>")

    # Profile chips, like NV-CODE's sidebar profiles.
    widths = [svg.width(n, "chip") + 40 for n, _ in CHIPS]
    x = 600 - (sum(widths) + 8 * (len(CHIPS) - 1)) / 2
    svg.add('<g class="fade" style="animation-delay:.15s">')
    for (name, dot), w in zip(CHIPS, widths):
        svg.add(f'<rect x="{x:.1f}" y="274" width="{w:.1f}" height="28" rx="14" fill="{c["raised"]}" stroke="{c["border"]}"/>'
                f'<circle cx="{x + 16:.1f}" cy="288" r="4" fill="{dot}"/>'
                + svg.text(x + 27, 292.5, name, "chip"))
        x += w + 8
    svg.add("</g>")

    # A composer that types a line, sends it, then clears.
    typed = svg.width(PHRASE, "composer")
    n = len(PHRASE)
    svg.css.append(
        f".type{{animation:type 9s steps({n}) infinite}}"
        f"@keyframes type{{0%{{width:0}}40%,82%{{width:{typed:.0f}px}}92%,100%{{width:0}}}}"
        f".caret{{animation:caret 9s steps({n}) infinite,blink 1s step-end infinite}}"
        f"@keyframes caret{{0%{{transform:translateX(0)}}40%,82%{{transform:translateX({typed:.0f}px)}}92%,100%{{transform:translateX(0)}}}}"
        "@keyframes blink{50%{opacity:0}}"
        ".hint{animation:hint 9s step-end infinite}@keyframes hint{0%{opacity:1}1%{opacity:0}92%{opacity:1}}"
        ".send{transform-box:fill-box;transform-origin:center;animation:send 9s ease-in-out infinite}"
        f"@keyframes send{{0%,40%{{fill:{c['border']}}}44%,82%{{fill:{c['accent']}}}86%{{transform:scale(.88)}}90%,100%{{fill:{c['border']};transform:none}}}}"
        f".fill{{transform-box:fill-box;animation:fill 2.4s {EXPO} .6s both}}@keyframes fill{{from{{transform:scaleX(0)}}}}"
        "@media (prefers-reduced-motion: reduce){.type{width:1000px}.hint{opacity:0}}"
    )
    x0, y0, cw = 264, 324, 672
    svg.defs.append(f'<clipPath id="typed"><rect class="type" x="{x0 + 22}" y="{y0}" width="0" height="56"/></clipPath>')
    grain_pattern(svg)
    bx = x0 + cw - 6 - svg.width("Weekly", "label") - 92
    svg.add(
        '<g class="fade" style="animation-delay:.3s">'
        f'<rect x="{x0}" y="{y0}" width="{cw}" height="56" rx="18" fill="{c["raised"]}" stroke="{c["border"]}"/>'
        f'<g class="hint">{svg.text(x0 + 22, y0 + 33, "Ask Niv to build something…", "composer", fill=c["muted"])}</g>'
        f'<g clip-path="url(#typed)">{svg.text(x0 + 22, y0 + 33, PHRASE, "composer")}</g>'
        f'<rect class="caret motion-only" x="{x0 + 23}" y="{y0 + 18}" width="1.6" height="20" fill="{c["accent_text"]}"/>'
        f'<circle class="send" cx="{x0 + cw - 30}" cy="{y0 + 28}" r="15" fill="{c["border"]}"/>'
        f'<path d="M{x0 + cw - 30} {y0 + 35}V{y0 + 21}M{x0 + cw - 35.5} {y0 + 26.5}L{x0 + cw - 30} {y0 + 21}L{x0 + cw - 24.5} {y0 + 26.5}" '
        f'fill="none" stroke="{WHITE}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/>'
        + svg.text(x0 + 6, y0 + 82, "Interfaces · APIs · Automation · AI", "label")
        + svg.text(x0 + cw - 6, y0 + 82, "Weekly", "label", anchor="end")
        + f'<rect x="{bx:.1f}" y="{y0 + 73}" width="80" height="10" rx="2" fill="{c["border"]}"/>'
        f'<g class="fill"><rect x="{bx:.1f}" y="{y0 + 73}" width="58" height="10" rx="2" fill="{c["accent"]}"/>'
        f'<rect x="{bx:.1f}" y="{y0 + 73}" width="58" height="10" rx="2" fill="url(#grain)"/></g>'
        "</g>"
    )

    # The tako walks the ground along the bottom.
    ground = 522
    ground_line(svg, 24, 1176, ground + 2)
    tako(svg, "tk", 36, ground, 1128, px=3)
    return svg.render()


# ---------------------------------------------------------------- project rows

GRID = 24


def shape_mask(shape, x, y):
    dx, dy = x + 0.5 - 12, y + 0.5 - 12
    if shape == "circle":
        return dx * dx + dy * dy <= 11.6 ** 2
    if shape == "hexagon":
        return abs(dy) <= 10.6 and abs(dx) <= 11.8 - abs(dy) * 0.55
    if shape == "diamond":
        return abs(dx) + abs(dy) <= 12.2
    qx, qy = max(abs(dx) - 5.5, 0), max(abs(dy) - 5.5, 0)  # rounded square
    return abs(dx) <= 11.5 and abs(dy) <= 11.5 and qx * qx + qy * qy <= 36


def avatar(svg, x, y, shape, size=56, working=False):
    """A dithered face in the home-glow blues, with white ink-ringed eyes that blink."""
    stops = [BLUE["light"], BLUE["mid"], BLUE["dark"]]
    layers = {s: "" for s in stops}
    for gy in range(GRID):
        for gx in range(GRID):
            if not shape_mask(shape, gx, gy):
                continue
            u, v = (gx + 0.5) / GRID - 0.32, (gy + 0.5) / GRID - 0.28
            s = max(0.0, min(1.0, math.hypot(u, v) / 0.92)) * 2
            band = min(1, math.floor(s))
            layers[stops[band + 1 if s - band > bayer(gx, gy) else band]] += f"M{gx} {gy}h1v1h-1z"
    body = "".join(f'<path fill="{k}" d="{d}"/>' for k, d in layers.items() if d)

    def eyes(closed):
        cells = set()
        for x0 in (7, 14):
            if closed:
                cells |= {(x0 + i, 13) for i in range(3)}
            else:
                cells |= {(x0 + i, 9 + j) for i in range(3) for j in range(5) if not (j in (0, 4) and i in (0, 2))}
        ring = {(a + da, b + db) for a, b in cells for da, db in ((1, 0), (-1, 0), (0, 1), (0, -1))} - cells
        path = lambda cs: "".join(f"M{a} {b}h1v1h-1z" for a, b in sorted(cs))
        return f'<path fill="{INK}" d="{path(ring)}"/><path fill="{WHITE}" d="{path(cells)}"/>'

    svg.css.append(
        ".eo{animation:eo 4.6s step-end infinite}.es{opacity:0;animation:es 4.6s step-end infinite}"
        "@keyframes eo{0%{opacity:1}92%{opacity:0}96%{opacity:1}}"
        "@keyframes es{0%{opacity:0}92%{opacity:1}96%{opacity:0}}"
        + (".look{animation:look 3.2s step-end infinite}"
           "@keyframes look{0%{transform:translateX(-1px)}40%{transform:translateX(1px)}80%{transform:none}}"
           if working else "")
    )
    svg.add(f'<g transform="translate({x} {y}) scale({size / GRID})" shape-rendering="crispEdges">{body}'
            f'<g class="look"><g class="eo">{eyes(False)}</g><g class="es">{eyes(True)}</g></g></g>')


def tako_avatar(svg, x, y, size=56):
    x, size = x - 4, size + 8
    px = size / 42
    svg.css.append(".ta{animation:ta 2.6s ease-in-out infinite}@keyframes ta{50%{transform:translateY(-2px)}}")
    svg.add(f'<g class="ta"><g transform="translate({x} {y + (size - 28 * px) / 2:.1f}) scale({px:.4f})" '
            f'shape-rendering="crispEdges">{body_sprite()}{face_sprite("happy", "open")}</g></g>')


PROJECTS = [
    {
        "slug": "nv-code",
        "name": "NV-CODE",
        "kind": "Desktop & web app",
        "status": ("Nightly", "live"),
        "description": "A fork of T3 Code Nightly with bot rows, sidebar profiles, usage widgets, and the Tako Ink theme.",
        "tags": ["TypeScript", "React", "Electron", "Effect"],
        "avatar": "nv",
    },
    {
        "slug": "bolota",
        "name": "Bolota",
        "kind": "AI & conversation",
        "status": ("Shipped", "done"),
        "description": "A veterinary assistant that connects natural language to the information a pet shop needs.",
        "tags": ["Gemini", "TypeScript", "Express", "SQLite", "Docker"],
        "avatar": "circle",
    },
    {
        "slug": "n-store",
        "name": "n-store",
        "kind": "Commerce & systems",
        "status": ("In development", "working"),
        "description": "An e-commerce platform exploring the pieces behind a complete shopping experience.",
        "tags": ["Laravel", "PHP", "Blade"],
        "avatar": "hexagon",
    },
    {
        "slug": "takostreak",
        "name": "TakoStreak",
        "kind": "Small tools, daily habits",
        "status": ("In development", "working"),
        "description": "Fluffy streaks for everyone. A playful project about showing up, one day at a time.",
        "tags": ["React", "TanStack", "Express", "TypeScript"],
        "avatar": "tako",
    },
]


def project_row(theme, p):
    svg = Svg(1200, 124, theme, f"{p['name']}: {p['description']}")
    c = svg.c
    label, state = p["status"]
    svg.css.append(
        NUDGE
        + ".pulse{transform-box:fill-box;transform-origin:center;animation:pulse 2s ease-in-out infinite}"
        "@keyframes pulse{50%{opacity:.35;transform:scale(.7)}}"
        ".dots circle{animation:dots 1.2s ease-in-out infinite}@keyframes dots{0%,60%,100%{opacity:.25}30%{opacity:1}}"
    )
    svg.defs.append(f'<radialGradient id="tint" cx="0" cy="0" r="1"><stop offset="0" stop-color="{c["accent"]}" stop-opacity=".16"/>'
                    f'<stop offset="1" stop-color="{c["accent"]}" stop-opacity="0"/></radialGradient>')
    svg.add(f'<rect x="0.5" y="0.5" width="1199" height="123" rx="14" fill="{c["card"]}" stroke="{c["border"]}"/>'
            '<rect x="1" y="1" width="560" height="122" rx="13" fill="url(#tint)"/>')

    ax, ay = 28, 34
    if p["avatar"] == "nv":
        nv_icon(svg, ax, ay, 56)
    elif p["avatar"] == "tako":
        tako_avatar(svg, ax, ay)
    else:
        avatar(svg, ax, ay, p["avatar"], working=state == "working")

    x = 108
    svg.add(svg.text(x, 50, p["name"], font=SEMI, size=22, tracking=-0.01))
    sx = x + SEMI.width(p["name"], 22, -0.01) + 14
    svg.add(svg.text(sx, 49, p["kind"], "label"))
    sx += svg.width(p["kind"], "label") + 14

    # Live status, like a bot row's status dot.
    working = state == "working"
    w = svg.width(label, "label-accent") + (36 if working else 30)
    svg.add(f'<rect x="{sx:.1f}" y="34" width="{w:.1f}" height="22" rx="11" fill="none" stroke="{c["border"]}"/>')
    if working:
        svg.add('<g class="dots">' + "".join(
            f'<circle cx="{sx + 10 + k * 4.5:.1f}" cy="45" r="1.6" fill="{c["accent_text"]}" style="animation-delay:{k * .15:.2f}s"/>'
            for k in range(3)) + "</g>")
        svg.add(svg.text(sx + 26, 49, label, "label-accent"))
    else:
        color = "#4ade80" if state == "live" else c["accent_text"]
        svg.add(f'<circle class="pulse" cx="{sx + 13:.1f}" cy="45" r="3.5" fill="{color}"/>')
        svg.add(svg.text(sx + 23, 49, label, "label-accent"))

    svg.add(svg.text(x, 78, p["description"], "body"))
    tx = x
    for tag in p["tags"]:
        markup, tw = svg.pill(tx, 90, tag, height=20, pad=8)
        svg.add(markup)
        tx += tw + 6

    svg.add(svg.text(1148, 49, f"nivdantas/{p['slug']}", "label", anchor="end"))
    svg.add(f'<g class="go">{arrow(1158, 39.5, c["accent_text"])}</g>')
    return svg.render()


# ---------------------------------------------------------------- footer


def footer(theme):
    svg = Svg(1200, 270, theme, "Let's build the next thing. Interfaces, APIs, and everything in between. "
                                "nivdantas@icloud.com")
    c = svg.c
    svg.css.append(FADE + NUDGE)
    window(svg)
    svg.add('<g clip-path="url(#window)">')
    glow(svg, "fg", 960, 190, 1.5)
    svg.add("</g>")
    svg.add('<g class="fade">')
    svg.add(svg.text(48, 56, "One more connection", "label-accent"))
    svg.add(svg.text(46, 112, "Let’s build the next thing.", font=SEMI, size=44, tracking=-0.03))
    svg.add(svg.text(48, 148, "Interfaces, APIs, and everything in between.", "lead"))
    mail = "nivdantas@icloud.com"
    bw = svg.width(mail, "button") + 54
    svg.add(f'<rect x="48" y="180" width="{bw:.1f}" height="44" rx="22" fill="{c["accent"]}"/>'
            + svg.text(70, 206.5, mail, "button")
            + f'<g class="go">{arrow(48 + bw - 30, 197.5, WHITE)}</g>')
    site = "nivdantas.com"
    sx = 48 + bw + 10
    sw = svg.width(site, "button") + 44
    svg.add(f'<rect x="{sx:.1f}" y="180.5" width="{sw:.1f}" height="43" rx="21.5" fill="{c["raised"]}" stroke="{c["border"]}"/>'
            + svg.text(sx + 22, 206.5, site, "button", fill=c["text"]))
    svg.add("</g>")
    ground = 222
    ground_line(svg, 860, 1080, ground + 2)
    tako(svg, "nap", 908, ground, 126, px=3, script=NAP, still_face="doze")
    return svg.render()


# ---------------------------------------------------------------- build


def main():
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.svg"):
        old.unlink()
    builders = {"header": header, "footer": footer}
    for p in PROJECTS:
        builders[f"project-{p['slug']}"] = lambda theme, p=p: project_row(theme, p)
    for name, build in builders.items():
        for theme in THEMES:
            reset_fonts()
            path = OUT / f"{name}-{theme}.svg"
            path.write_text(build(theme), encoding="utf-8")
            print(f"{path.name:32} {path.stat().st_size / 1024:6.1f} KB")


if __name__ == "__main__":
    main()
