#!/usr/bin/env python3
"""Aplica el estilo "terminal" al SVG que genera Platane/snk.

Uso: python3 style_snake.py <fichero.svg> [...]

- Cambia la paleta (:root) a verdes sobre fondo oscuro y serpiente cian.
- Envuelve el gráfico en un panel con barra de título y leyenda.
- Añade líneas de escaneo y un borde sutil.
No toca las animaciones: solo añade elementos y reescribe variables CSS.
"""
import re
import sys

PALETTE = {
    "--cb": "#00000000",  # borde de cada celda (transparente)
    "--cs": "#00e5ff",    # serpiente
    "--ce": "#0f1f17",    # celda vacía / ya comida
    "--c0": "#0f1f17",
    "--c1": "#0b4a2a",
    "--c2": "#0e7a3d",
    "--c3": "#12b34f",
    "--c4": "#00ff66",
}
MONO = "'Fira Code','JetBrains Mono','SFMono-Regular',Menlo,Consolas,'DejaVu Sans Mono','Liberation Mono',monospace"
TOP = 40      # espacio extra arriba para la barra de título
SIDE = 8      # espacio extra a cada lado
BOTTOM = 12   # espacio extra abajo


def restyle(svg: str) -> str:
    # 1) paleta: reescribe solo las variables conocidas dentro de :root{...}
    def set_vars(m):
        body = m.group(1)
        for name, value in PALETTE.items():
            if re.search(re.escape(name) + r":", body):
                body = re.sub(re.escape(name) + r":[^;}]*", f"{name}:{value}", body)
            else:
                body += f";{name}:{value}"
        return ":root{" + body + "}"

    svg = re.sub(r":root\{([^}]*)\}", set_vars, svg, count=1)

    # 2) nuevo viewBox con hueco para el panel
    m = re.search(r'viewBox="(-?[\d.]+) (-?[\d.]+) ([\d.]+) ([\d.]+)"', svg)
    if not m:
        raise SystemExit("viewBox no encontrado: ¿cambió el formato de snk?")
    x, y, w, h = (float(v) for v in m.groups())
    nx, ny = x - SIDE, y - TOP
    nw, nh = w + 2 * SIDE, h + TOP + BOTTOM
    svg = svg.replace(m.group(0), f'viewBox="{nx:g} {ny:g} {nw:g} {nh:g}"', 1)
    svg = re.sub(r'(<svg[^>]*?) width="[\d.]+" height="[\d.]+"',
                 rf'\1 width="{nw:g}" height="{nh:g}"', svg, count=1)

    # 3) panel (detrás de todo) + título + leyenda
    right = nx + nw
    cx = nx + nw / 2
    ty = ny  # arriba del panel
    legend = []
    lx = right - 52           # tras la palabra "más"
    legend.append(f'<text class="sn-t" x="{right - 14:g}" y="{ty + 23:g}" text-anchor="end">más</text>')
    for i in range(4, -1, -1):  # de más oscuro a más claro, de derecha a izquierda
        legend.append(
            f'<rect x="{lx - (4 - i) * 16 - 12:g}" y="{ty + 12:g}" width="12" height="12" rx="2" '
            f'style="fill:var(--c{i})"/>'
        )
    legend.append(
        f'<text class="sn-t" x="{lx - 4 * 16 - 20:g}" y="{ty + 23:g}" text-anchor="end">menos</text>'
    )
    panel = (
        f'<defs><clipPath id="sn-pnl"><rect x="{nx:g}" y="{ny:g}" width="{nw:g}" height="{nh:g}" rx="12"/></clipPath>'
        '<pattern id="sn-scan" width="4" height="4" patternUnits="userSpaceOnUse">'
        '<rect width="4" height="1" fill="#000" opacity=".22"/></pattern></defs>'
        '<g clip-path="url(#sn-pnl)">'
        f'<rect x="{nx:g}" y="{ny:g}" width="{nw:g}" height="{nh:g}" fill="#070b09"/>'
        f'<rect x="{nx:g}" y="{ny:g}" width="{nw:g}" height="36" fill="#0c1410"/>'
        f'<rect x="{nx:g}" y="{ny + 36:g}" width="{nw:g}" height="1" fill="#1c3326"/>'
        f'<circle cx="{nx + 22:g}" cy="{ty + 18:g}" r="5" fill="#ff5f56" opacity=".85"/>'
        f'<circle cx="{nx + 42:g}" cy="{ty + 18:g}" r="5" fill="#ffbd2e" opacity=".85"/>'
        f'<circle cx="{nx + 62:g}" cy="{ty + 18:g}" r="5" fill="#27c93f" opacity=".85"/>'
        f'<text class="sn-t" x="{cx:g}" y="{ty + 23:g}" text-anchor="middle">snake.sh  ~/contribuciones</text>'
        + "".join(legend)
        + "</g>"
    )
    extra_css = f".sn-t{{font-family:{MONO};font-size:12px;fill:#5a7d68}}"
    svg = svg.replace("</style>", extra_css + "</style>", 1)
    svg = svg.replace("</style>", "</style>" + panel, 1)

    # 4) por encima de todo: líneas de escaneo y borde
    overlay = (
        '<g clip-path="url(#sn-pnl)" pointer-events="none">'
        f'<rect x="{nx:g}" y="{ny:g}" width="{nw:g}" height="{nh:g}" fill="url(#sn-scan)"/></g>'
        f'<rect x="{nx + .75:g}" y="{ny + .75:g}" width="{nw - 1.5:g}" height="{nh - 1.5:g}" rx="12" '
        'fill="none" stroke="#1c3326" stroke-width="1.5" pointer-events="none"/>'
    )
    return svg.replace("</svg>", overlay + "</svg>")


if __name__ == "__main__":
    for path in sys.argv[1:]:
        with open(path, encoding="utf-8") as fh:
            original = fh.read()
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(restyle(original))
        print(f"estilizado: {path}")
