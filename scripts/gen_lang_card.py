"""Render a language-breakdown card as SVG.

Monochrome card, solid muted accents for the languages themselves, led by
the ranjiv.dev brand blue. Karla is embedded as base64 because GitHub
serves README images through a proxy that blocks external font requests.

Run by .github/workflows/snake.yml; output lands on the `output` branch.
"""

import base64
import json
import os
import urllib.request
from collections import Counter

USER = os.environ.get("GH_USER", "Ranj04")
TOKEN = os.environ.get("GITHUB_TOKEN", "")
OUT = os.environ.get("OUT", "dist/languages.svg")
FONT_FILE = os.environ.get("FONT_FILE", "assets/karla.woff2")
TOP_N = 6

BRAND = "#2B83F5"
# Brand blue leads; the rest stay muted — slate, bronze, olive, rust, gunmetal.
PALETTE = [BRAND, "#6B7A8C", "#6B4F3A", "#5C6B5A", "#8C4A3C", "#4A4E58"]
OTHER = "#272B33"

BG, BORDER, FG, MUTED = "#0D1117", "#30363D", "#E6EDF3", "#8B949E"

W, PAD = 840, 24
BAR_Y, BAR_H = 62, 10


def api(path):
    req = urllib.request.Request(f"https://api.github.com/{path}")
    req.add_header("Accept", "application/vnd.github+json")
    if TOKEN:
        req.add_header("Authorization", f"Bearer {TOKEN}")
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def collect():
    totals = Counter()
    page = 1
    while True:
        repos = api(f"users/{USER}/repos?per_page=100&page={page}")
        if not repos:
            break
        for repo in repos:
            if repo["fork"]:
                continue
            for lang, count in api(f"repos/{USER}/{repo['name']}/languages").items():
                totals[lang] += count
        page += 1
    return totals


def font_face():
    with open(FONT_FILE, "rb") as fh:
        b64 = base64.b64encode(fh.read()).decode()
    return (
        "@font-face{font-family:'Karla';font-style:normal;font-weight:400 600;"
        f"src:url(data:font/woff2;base64,{b64}) format('woff2');}}"
    )


def esc(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def render(totals):
    total = sum(totals.values())
    if not total:
        raise SystemExit("no language data returned")

    top = totals.most_common(TOP_N)
    rest = total - sum(c for _, c in top)
    rows = [(name, count / total * 100, PALETTE[i]) for i, (name, count) in enumerate(top)]
    if rest > 0:
        rows.append(("Other", rest / total * 100, OTHER))

    bar_w = W - PAD * 2
    segments, x = [], PAD
    for _, pct, color in rows:
        seg = bar_w * pct / 100
        segments.append(f'<rect x="{x:.2f}" y="{BAR_Y}" width="{seg:.2f}" '
                        f'height="{BAR_H}" fill="{color}" />')
        x += seg

    # Two columns of legend entries.
    per_col = (len(rows) + 1) // 2
    legend = []
    for i, (name, pct, color) in enumerate(rows):
        col, row = i // per_col, i % per_col
        lx = PAD + col * (bar_w / 2)
        ly = 104 + row * 26
        legend.append(
            f'<rect x="{lx}" y="{ly - 9}" width="10" height="10" rx="2" fill="{color}" />'
            f'<text x="{lx + 18}" y="{ly}" class="lbl">{esc(name)}</text>'
            f'<text x="{lx + 188}" y="{ly}" class="pct" text-anchor="end">{pct:.1f}%</text>'
        )

    height = 104 + per_col * 26 + 14

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{height}" \
viewBox="0 0 {W} {height}" role="img" aria-label="Top languages">
  <defs>
    <clipPath id="barclip">
      <rect x="{PAD}" y="{BAR_Y}" width="{bar_w}" height="{BAR_H}" rx="5" />
    </clipPath>
    <style>
      {font_face()}
      text {{ font-family:'Karla',-apple-system,BlinkMacSystemFont,sans-serif; }}
      .ttl {{ font-size:15px; font-weight:600; fill:{FG}; }}
      .lbl {{ font-size:13px; font-weight:500; fill:{FG}; }}
      .pct {{ font-size:13px; font-weight:400; fill:{MUTED}; }}
    </style>
  </defs>
  <rect x="0.5" y="0.5" width="{W - 1}" height="{height - 1}" rx="6"
        fill="{BG}" stroke="{BORDER}" />
  <text x="{PAD}" y="36" class="ttl">Top Languages</text>
  <g clip-path="url(#barclip)">{"".join(segments)}</g>
  {"".join(legend)}
</svg>
'''


if __name__ == "__main__":
    svg = render(collect())
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w") as fh:
        fh.write(svg)
    print(f"wrote {OUT} ({len(svg):,} bytes)")
