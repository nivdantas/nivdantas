"""Draws live contribution cards in the style of NV-CODE's usage widgets.

Run daily by .github/workflows/profile.yml:
    python scripts/build_usage.py <out-dir> [login]
Reads GITHUB_TOKEN (or falls back to `gh auth token` locally).
"""

import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

from inkkit import EXPO, SEMI, THEMES, Svg, grain_pattern, reset_fonts

QUERY = """query($login: String!) { user(login: $login) { contributionsCollection {
  contributionCalendar { totalContributions weeks { contributionDays { date contributionCount } } } } } }"""


def fetch(login):
    token = os.environ.get("GITHUB_TOKEN") or subprocess.run(
        ["gh", "auth", "token"], capture_output=True, text=True, check=True).stdout.strip()
    request = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": login}}).encode(),
        headers={"Authorization": f"bearer {token}", "Content-Type": "application/json",
                 "User-Agent": "profile-usage-cards"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        data = json.load(response)
    if data.get("errors"):
        raise RuntimeError("GitHub returned GraphQL errors while fetching the contribution calendar.")
    user = (data.get("data") or {}).get("user")
    if user is None:
        raise RuntimeError(f"GitHub returned no contribution calendar for {login}.")
    calendar = user["contributionsCollection"]["contributionCalendar"]
    weeks = [[(dt.date.fromisoformat(d["date"]), d["contributionCount"]) for d in w["contributionDays"]]
             for w in calendar["weeks"]]
    return calendar["totalContributions"], weeks


def stats(total, weeks):
    days = [d for w in weeks for d in w]
    if not days:
        raise ValueError("The contribution calendar contains no days.")
    today = days[-1][0]
    counts = [c for _, c in days]
    # Current streak: today may still be empty, so it counts back from yesterday.
    i = len(counts) - 1
    if counts[i] == 0:
        i -= 1
    current = 0
    while i >= 0 and counts[i] > 0:
        current += 1
        i -= 1
    longest = run = 0
    for c in counts:
        run = run + 1 if c else 0
        longest = max(longest, run)
    this_week = sum(c for _, c in weeks[-1])
    past = [sum(c for _, c in w) for w in weeks[:-1]]
    best = max(past + [this_week])
    complete_weeks = [total for week, total in zip(weeks[:-1], past) if len(week) == 7]
    elapsed = (today.weekday() + 1) % 7 + 1  # Sunday is day one.
    pace = "on"
    if complete_weeks:
        expected = sum(complete_weeks) / len(complete_weeks) * elapsed / 7
        pace = "ahead" if this_week > expected * 1.1 else "behind" if this_week < expected * 0.9 else "on"
    return {
        "today": today,
        "total": total,
        "current": current,
        "longest": longest,
        "this_week": this_week,
        "best": best,
        "pace": pace,
        "resets": 8 - elapsed,
        "weekly": [(w[0][0], sum(c for _, c in w)) for w in weeks],
    }


def plural(n, word):
    return f"{n} {word}{'' if n == 1 else 's'}"


def card(svg, x, y, w, h, title):
    c = svg.c
    gid = f"tint{x}"
    svg.defs.append(f'<radialGradient id="{gid}" cx="0" cy="0" r="1"><stop offset="0" stop-color="{c["accent"]}" stop-opacity=".14"/>'
                    f'<stop offset="1" stop-color="{c["accent"]}" stop-opacity="0"/></radialGradient>')
    svg.add(f'<rect x="{x + .5}" y="{y + .5}" width="{w - 1}" height="{h - 1}" rx="14" fill="{c["card"]}" stroke="{c["border"]}"/>'
            f'<rect x="{x + 1}" y="{y + 1}" width="{w * .78:.0f}" height="{h - 2}" rx="13" fill="url(#{gid})"/>')
    svg.add(svg.text(x + 22, y + 34, title, "strong"))


def meter(svg, x, y, w, value, maximum, delay):
    c = svg.c
    fill = max(0.0, min(1.0, value / maximum if maximum else 0)) * w
    svg.add(f'<rect x="{x}" y="{y}" width="{w}" height="12" rx="3" fill="{c["border"]}"/>')
    if fill:
        svg.add(f'<g class="grow" style="animation-delay:{delay}s">'
                f'<rect x="{x}" y="{y}" width="{fill:.1f}" height="12" rx="3" fill="{c["accent"]}"/>'
                f'<rect x="{x}" y="{y}" width="{fill:.1f}" height="12" rx="3" fill="url(#grain)"/></g>')


PACE = {"ahead": ("↑", "Ahead of pace"), "behind": ("↓", "Behind pace"), "on": ("→", "On pace")}


def usage(theme, s):
    svg = Svg(1200, 236, theme, (
        f"{s['this_week']} contributions this week, a {s['current']}-day streak, "
        f"{s['total']} contributions in the last year."))
    c = svg.c
    grain_pattern(svg)
    svg.css.append(
        f".grow{{transform-box:fill-box;animation:grow 1.6s {EXPO} both}}@keyframes grow{{from{{transform:scaleX(0)}}}}"
        f".rise{{transform-box:fill-box;transform-origin:50% 100%;animation:rise 1.2s {EXPO} both}}"
        "@keyframes rise{from{transform:scaleY(0)}}"
        ".now{animation:now 2s ease-in-out infinite}@keyframes now{50%{opacity:.45}}"
    )

    # Contribution meters, after "Weekly limits".
    x, w = 0, 588
    card(svg, x, 0, w, 236, "Contributions")
    arrow_glyph, pace_label = PACE[s["pace"]]
    svg.add(svg.text(x + w - 22, 34, f"{arrow_glyph} {pace_label}", "label-accent", anchor="end"))
    svg.add(svg.text(x + 22, 70, "This week", "strong"))
    svg.add(svg.text(x + w - 22, 70, f"{s['this_week']} · best week {s['best']}", "small", anchor="end"))
    meter(svg, x + 22, 80, w - 44, s["this_week"], s["best"], 0.1)
    resets = "Resets tomorrow" if s["resets"] == 1 else f"Resets in {s['resets']} days"
    svg.add(svg.text(x + 22, 110, resets, "small"))
    svg.add(svg.text(x + 22, 148, "Current streak", "strong"))
    svg.add(svg.text(x + w - 22, 148, f"{plural(s['current'], 'day')} of {s['longest']}", "small", anchor="end"))
    meter(svg, x + 22, 158, w - 44, s["current"], max(1, s["longest"]), 0.25)
    svg.add(svg.text(x + 22, 188, f"Longest this year: {plural(s['longest'], 'day')}", "small"))
    svg.add(svg.text(x + 22, 216, f"{plural(s['total'], 'contribution')} in the last year", "label"))

    # Weekly bars, after "Daily token activity".
    x, w = 612, 588
    card(svg, x, 0, w, 236, "Weekly activity")
    recent = s["weekly"]
    recent_total = sum(n for _, n in recent)
    svg.add(svg.text(x + w - 22, 34, "Last 12 months", "label", anchor="end"))
    svg.add(svg.text(x + 22, 76, f"{recent_total}", font=SEMI, size=30, tracking=-0.02))
    svg.add(svg.text(x + 22 + SEMI.width(f"{recent_total}", 30, -0.02) + 10, 76,
                     "contribution" if recent_total == 1 else "contributions", "small"))
    top, base = 96, 190
    peak = max([n for _, n in recent] + [1])
    gap = 3
    bw = (w - 44 - gap * (len(recent) - 1)) / len(recent)
    svg.add(f'<line x1="{x + 22}" y1="{base + .5}" x2="{x + w - 22}" y2="{base + .5}" stroke="{c["border"]}"/>')
    for i, (day, n) in enumerate(recent):
        bx = x + 22 + i * (bw + gap)
        hgt = max(2, (base - top) * n / peak) if n else 2
        color = c["accent"] if n else c["border"]
        klass = "rise now" if i == len(recent) - 1 and n else "rise"
        svg.add(f'<g class="{klass}" style="animation-delay:{0.01 * i:.2f}s">'
                f'<rect x="{bx:.1f}" y="{base - hgt:.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="2" fill="{color}"/>'
                + (f'<rect x="{bx:.1f}" y="{base - hgt:.1f}" width="{bw:.1f}" height="{hgt:.1f}" rx="2" fill="url(#grain)"/>' if n else "")
                + "</g>")
    first_day = recent[0][0]
    svg.add(svg.text(x + 22, 214, f"{first_day:%b} {first_day.day}", "label"))
    svg.add(svg.text(x + w - 22, 214, f"This week · updated daily", "label", anchor="end"))
    return svg.render()


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "assets")
    login = sys.argv[2] if len(sys.argv) > 2 else "nivdantas"
    out.mkdir(parents=True, exist_ok=True)
    s = stats(*fetch(login))
    for theme in THEMES:
        reset_fonts()
        (out / f"usage-{theme}.svg").write_text(usage(theme, s), encoding="utf-8")
    print(f"week {s['this_week']} (best {s['best']}, {s['pace']}), streak {s['current']}/{s['longest']}, total {s['total']}")


if __name__ == "__main__":
    main()
