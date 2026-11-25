#!/usr/bin/env python3
"""Genera un "skyline" animado a partir del calendario de contribuciones de GitHub.

Uso:  GITHUB_TOKEN=... GH_USER=usuario python3 skyline.py salida.svg

Cada día es una torre cuya altura depende del nivel de actividad (0-4). No usa
dependencias externas: solo la biblioteca estándar de Python.

Para probar sin red: SKYLINE_FIXTURE=calendario.json (misma forma que la respuesta
de la API: {"totalContributions": n, "weeks": [{"contributionDays": [...]}]}).
"""
import json
import os
import sys
import urllib.request
from xml.sax.saxutils import escape

QUERY = """
query($login: String!) {
  user(login: $login) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks { contributionDays { contributionCount contributionLevel weekday date } }
      }
    }
  }
}
"""
LEVELS = {"NONE": 0, "FIRST_QUARTILE": 1, "SECOND_QUARTILE": 2, "THIRD_QUARTILE": 3, "FOURTH_QUARTILE": 4}
MESES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]

MONO = "'Fira Code','JetBrains Mono','SFMono-Regular',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"
W = 1000
# geometría de las torres (proyección oblicua: la profundidad va arriba a la derecha)
TW, DX, DY, GAP = 15, 7, 11, 1.2
X0, Y0 = 40, 214
HEIGHTS = {0: 1.5, 1: 9, 2: 18, 3: 29, 4: 42}
TOP = {0: "#12261b", 1: "#1d8a4d", 2: "#19c25f", 3: "#00e860", 4: "#7dffb0"}
FRONT = {1: "#0b4a2a", 2: "#0c7a3b", 3: "#09a049", 4: "#00c653"}
SIDE = {1: "#073520", 2: "#095a2c", 3: "#07803a", 4: "#009c40"}


def fetch_calendar(user, token):
    if os.environ.get("SKYLINE_FIXTURE"):
        with open(os.environ["SKYLINE_FIXTURE"], encoding="utf-8") as fh:
            return json.load(fh)
    req = urllib.request.Request(
        "https://api.github.com/graphql",
        data=json.dumps({"query": QUERY, "variables": {"login": user}}).encode(),
        headers={
            "Authorization": f"bearer {token}",
            "Content-Type": "application/json",
            "User-Agent": "skyline-generator",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.load(resp)
    if data.get("errors") or not (data.get("data") or {}).get("user"):
        raise SystemExit(f"Error de la API de GitHub: {data.get('errors') or 'usuario no encontrado'}")
    return data["data"]["user"]["contributionsCollection"]["contributionCalendar"]


def build_grid(calendar):
    weeks = calendar["weeks"]
    grid = [[None] * len(weeks) for _ in range(7)]
    dates = {}
    for i, week in enumerate(weeks):
        for day in week["contributionDays"]:
            grid[day["weekday"]][i] = LEVELS.get(day["contributionLevel"], 0)
            dates.setdefault(i, day["date"])
    return grid, dates


def render(calendar):
    grid, dates = build_grid(calendar)
    cols = len(grid[0])
    total = calendar["totalContributions"]
    active = sum(1 for row in grid for v in row if v)
    total_txt = f"{total:,}".replace(",", ".")

    # suelo: una baldosa por día
    floor = []
    for i in range(cols):
        for j in range(7):
            if grid[j][i] is None:
                continue
            x, y = X0 + i * (TW + GAP) + j * DX, Y0 - j * DY
            floor.append(f"M{x:.1f},{y:.1f}L{x + TW:.1f},{y:.1f}L{x + TW + DX:.1f},{y - DY:.1f}L{x + DX:.1f},{y - DY:.1f}Z")

    # torres: de atrás hacia delante, de izquierda a derecha
    towers = []
    order = sorted(((i, j) for i in range(cols) for j in range(7) if grid[j][i]), key=lambda t: (-t[1], t[0]))
    for i, j in order:
        lvl = grid[j][i]
        h = HEIGHTS[lvl]
        x, y = X0 + i * (TW + GAP) + j * DX, Y0 - j * DY
        front = f"{x:.1f},{y:.1f} {x + TW:.1f},{y:.1f} {x + TW:.1f},{y - h:.1f} {x:.1f},{y - h:.1f}"
        side = f"{x + TW:.1f},{y:.1f} {x + TW + DX:.1f},{y - DY:.1f} {x + TW + DX:.1f},{y - DY - h:.1f} {x + TW:.1f},{y - h:.1f}"
        top = f"{x:.1f},{y - h:.1f} {x + TW:.1f},{y - h:.1f} {x + TW + DX:.1f},{y - h - DY:.1f} {x + DX:.1f},{y - h - DY:.1f}"
        towers.append(
            f'<g class="tw" style="transform-origin:{x + TW / 2:.1f}px {y:.1f}px;animation-delay:{i * 0.07 + (6 - j) * 0.03:.2f}s">'
            f'<polygon points="{front}" fill="{FRONT[lvl]}"/><polygon points="{side}" fill="{SIDE[lvl]}"/>'
            f'<polygon class="tp" style="animation-delay:{i * 0.09 + j * 0.05:.2f}s" points="{top}" fill="{TOP[lvl]}"/></g>'
        )

    # etiquetas de mes bajo la fila frontal
    cand, last = [], None
    for i in range(cols - 1):
        d = dates.get(i)
        if not d:
            continue
        month = int(d[5:7]) - 1
        if month != last:
            cand.append((i, month))
            last = month
    # si dos meses quedan demasiado juntos (p. ej. al principio), se omite el primero
    if len(cand) > 1 and cand[1][0] - cand[0][0] < 3:
        cand.pop(0)
    labels = [
        f'<text class="mes" x="{X0 + i * (TW + GAP):.1f}" y="{Y0 + 18}">{MESES[m]}</text>' for i, m in cand
    ]

    # leyenda
    right, sq = 960, 11
    first_sq = right - 22 - 8 - 5 * (sq + 4) + 4
    legend = [f'<text class="mono lab" x="{right}" y="256" text-anchor="end">más</text>']
    for k in range(5):
        legend.append(f'<rect x="{first_sq + k * (sq + 4)}" y="247" width="{sq}" height="{sq}" rx="2" fill="{TOP[k]}"/>')
    legend.append(f'<text class="mono lab" x="{first_sq - 8}" y="256" text-anchor="end">menos</text>')

    status = (
        f'<text class="mono lab" x="40" y="256">&gt; skyline --render  <tspan fill="#00ff66">[ OK ]</tspan>  '
        f"{total_txt} contribuciones · {active} días activos</text>"
    )
    H = 272
    css = f""".mono{{font-family:{MONO}}}
.ttl{{font-family:{MONO};font-size:12px;fill:#5a7d68}}
.lab{{font-size:12px;fill:#6fae85}}
.mes{{font-family:{MONO};font-size:11px;fill:#4a7a5c}}
.tw{{animation:grow 12s cubic-bezier(.2,.9,.3,1.1) infinite both}}
@keyframes grow{{0%{{transform:scaleY(0)}}6%{{transform:scaleY(1)}}86%{{transform:scaleY(1)}}93%,100%{{transform:scaleY(0)}}}}
.tp{{animation:shim 5s ease-in-out infinite}}
@keyframes shim{{0%,100%{{fill-opacity:.82}}50%{{fill-opacity:1}}}}
.vbeam{{animation:vb 9s linear infinite}}
@keyframes vb{{from{{transform:translateX(-120px)}}to{{transform:translateX(1060px)}}}}
@media (prefers-reduced-motion: reduce){{*{{animation:none !important}}.vbeam{{display:none}}}}"""

    return f"""<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="t d">
<title id="t">Skyline de contribuciones</title>
<desc id="d">{escape(f"Ciudad de torres: cada día es una torre y su altura depende de la actividad. {total_txt} contribuciones en el último año, {active} días activos.")}</desc>
<defs><style>{css}</style>
<clipPath id="rnd"><rect width="{W}" height="{H}" rx="12"/></clipPath>
<pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse"><rect width="4" height="1" fill="#000" opacity=".16"/></pattern>
<radialGradient id="vig" cx=".5" cy=".5" r=".75"><stop offset=".6" stop-color="#000" stop-opacity="0"/><stop offset="1" stop-color="#000" stop-opacity=".5"/></radialGradient>
<linearGradient id="vbg" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#00ff66" stop-opacity="0"/><stop offset=".5" stop-color="#00ff66" stop-opacity=".07"/><stop offset="1" stop-color="#00ff66" stop-opacity="0"/></linearGradient>
</defs>
<g clip-path="url(#rnd)">
<rect width="{W}" height="{H}" fill="#070b09"/>
<path d="{''.join(floor)}" fill="{TOP[0]}" stroke="#070b09" stroke-width=".8"/>
{''.join(towers)}
{''.join(labels)}
{status}{''.join(legend)}
<rect width="{W}" height="30" fill="#0c1410"/><rect y="30" width="{W}" height="1" fill="#1c3326"/>
<circle cx="22" cy="15" r="5" fill="#ff5f56" opacity=".85"/><circle cx="42" cy="15" r="5" fill="#ffbd2e" opacity=".85"/><circle cx="62" cy="15" r="5" fill="#27c93f" opacity=".85"/>
<text class="ttl" x="500" y="19" text-anchor="middle">matias@dev: ~/skyline</text>
<rect class="vbeam" y="31" width="120" height="{H - 31}" fill="url(#vbg)"/>
<rect width="{W}" height="{H}" fill="url(#scan)"/><rect width="{W}" height="{H}" fill="url(#vig)"/>
</g>
<rect x=".75" y=".75" width="{W - 1.5}" height="{H - 1.5}" rx="12" fill="none" stroke="#1c3326" stroke-width="1.5"/>
</svg>
"""


def main():
    if len(sys.argv) != 2:
        raise SystemExit("Uso: skyline.py salida.svg")
    user = os.environ.get("GH_USER", "")
    token = os.environ.get("GITHUB_TOKEN", "")
    if not os.environ.get("SKYLINE_FIXTURE") and not (user and token):
        raise SystemExit("Faltan las variables GH_USER y GITHUB_TOKEN")
    svg = render(fetch_calendar(user, token))
    os.makedirs(os.path.dirname(os.path.abspath(sys.argv[1])), exist_ok=True)
    with open(sys.argv[1], "w", encoding="utf-8") as fh:
        fh.write(svg)
    print(f"skyline generado: {sys.argv[1]} ({len(svg)} bytes)")


if __name__ == "__main__":
    main()
