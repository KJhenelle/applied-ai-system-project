"""Background scenes for the companion stage (pure SVG, no assets).

realistic: a garden whose sky follows the real time of day (dawn, day, sunset, night), with a fence,
           flowers, drifting clouds, a food bowl that is full or empty and a ball.
robotic:   a neon lab with a window onto a night skyline, a perspective grid floor, a glowing charging
           pad and a food-pellet dock that fills or empties.
"""
from __future__ import annotations

W, H = 600, 340

# (sky top, sky bottom, hill far, hill near, sun/moon color, star opacity, ground)
SKIES = {
    "dawn":   ("#ffd6c2", "#ffeede", "#bfe3b4", "#9ad48f", "#ffb36b", 0.0, "#8fcf86"),
    "day":    ("#8fd3ff", "#dff3ff", "#b7e8a6", "#86d17a", "#ffe27a", 0.0, "#7fcb73"),
    "sunset": ("#7a6bd1", "#ffb48a", "#8fb579", "#6aa56a", "#ffd479", 0.15, "#5f9d62"),
    "night":  ("#1c2350", "#3a3f7c", "#2f5a55", "#244a47", "#f4f1d0", 1.0, "#2a5a4f"),
}


def period(hour: int) -> str:
    if 5 <= hour < 9:
        return "dawn"
    if 9 <= hour < 17:
        return "day"
    if 17 <= hour < 20:
        return "sunset"
    return "night"


def _flowers() -> str:
    spots = [(40, 300, "#ff8fb1"), (92, 316, "#ffd24d"), (150, 304, "#ffffff"), (452, 306, "#ff8fb1"),
             (512, 318, "#ffd24d"), (566, 300, "#ffffff"), (330, 322, "#c9a7ff")]
    return "".join(
        f'<g><line x1="{x}" y1="{y}" x2="{x}" y2="{y + 14}" stroke="#4d9b4f" stroke-width="3" stroke-linecap="round"/>'
        f'<circle cx="{x}" cy="{y}" r="6.5" fill="{c}"/><circle cx="{x}" cy="{y}" r="2.8" fill="#ffb300"/></g>'
        for x, y, c in spots)


def _fence() -> str:
    boards = "".join(f'<path d="M{x} 232 v-46 l9 -9 l9 9 v46 z" fill="#fffaf0" stroke="#e9dcc3" stroke-width="2"/>' for x in range(-6, 620, 36))
    return f'<g opacity=".95">{boards}<rect x="-10" y="198" width="640" height="8" rx="4" fill="#f3e6cc"/><rect x="-10" y="218" width="640" height="8" rx="4" fill="#f3e6cc"/></g>'


def _bowl(full: bool, x: int = 120, y: int = 296) -> str:
    food = ('<ellipse cx="{x}" cy="{yy}" rx="22" ry="8" fill="#b9733d"/>'
            '<circle cx="{a}" cy="{b}" r="5" fill="#c98547"/><circle cx="{c}" cy="{b2}" r="5" fill="#a9622f"/><circle cx="{x}" cy="{b3}" r="5" fill="#c98547"/>'
            ).format(x=x, yy=y - 6, a=x - 10, b=y - 11, c=x + 10, b2=y - 10, b3=y - 14) if full else ""
    return (f'<ellipse cx="{x}" cy="{y + 12}" rx="34" ry="7" fill="#000" opacity=".12"/>'
            f'<path d="M{x - 32} {y - 4} h64 l-8 24 h-48 z" fill="#ff7b8c"/><ellipse cx="{x}" cy="{y - 4}" rx="32" ry="9" fill="#ff9aa8"/>'
            f'<ellipse cx="{x}" cy="{y - 4}" rx="24" ry="6" fill="#d95f72"/>{food}'
            f'<rect x="{x - 14}" y="{y + 6}" width="28" height="7" rx="3.5" fill="#fff" opacity=".55"/>')


def _ball(x: int = 480, y: int = 300) -> str:
    return (f'<ellipse cx="{x}" cy="{y + 18}" rx="22" ry="5" fill="#000" opacity=".12"/>'
            f'<circle cx="{x}" cy="{y}" r="20" fill="#5cc8ff"/><path d="M{x - 18} {y - 4} Q{x} {y + 8} {x + 18} {y - 4}" fill="none" stroke="#fff" stroke-width="3"/>'
            f'<circle cx="{x - 7}" cy="{y - 8}" r="5" fill="#fff" opacity=".6"/>')


def garden(hour: int, belly: int) -> str:
    pid = period(hour)
    top, bottom, far, near, orb, stars, ground = SKIES[pid]
    night = period(hour) == "night"
    star_svg = "".join(f'<circle cx="{x}" cy="{y}" r="{r}" fill="#fff" opacity="{stars}"/>'
                       for x, y, r in [(60, 40, 2), (140, 78, 1.6), (250, 30, 2.2), (330, 70, 1.5), (420, 36, 2), (520, 84, 1.7), (570, 30, 1.4), (200, 110, 1.3)]) if stars else ""
    cloud_color = "#ffffff" if not night else "#59609e"
    cloud = lambda x, y, s, d: (f'<g class="cloud" style="animation-delay:{d}s"><g transform="translate({x} {y}) scale({s})" fill="{cloud_color}" opacity="{0.9 if not night else .45}">'
                                '<ellipse cx="0" cy="0" rx="40" ry="16"/><ellipse cx="-22" cy="4" rx="24" ry="14"/><ellipse cx="26" cy="5" rx="26" ry="13"/><ellipse cx="6" cy="-12" rx="22" ry="14"/></g></g>')
    orb_svg = (f'<circle cx="490" cy="70" r="34" fill="{orb}" opacity=".35"/><circle cx="490" cy="70" r="24" fill="{orb}"/>' if not night else
               f'<circle cx="490" cy="72" r="26" fill="{orb}"/><circle cx="500" cy="66" r="22" fill="{top}" opacity=".85"/>')
    return f"""<svg class="scene" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs><linearGradient id="sky-{pid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{top}"/><stop offset="1" stop-color="{bottom}"/></linearGradient></defs>
  <rect width="{W}" height="{H}" fill="url(#sky-{pid})"/>
  {star_svg}{orb_svg}
  {cloud(110, 70, 1, 0)}{cloud(330, 110, .75, -9)}{cloud(560, 48, .6, -18)}
  <path d="M-10 214 Q90 150 200 196 T400 180 T620 200 V340 H-10Z" fill="{far}"/>
  <path d="M-10 236 Q120 190 260 226 T620 222 V340 H-10Z" fill="{near}"/>
  {_fence()}
  <path d="M-10 252 Q300 232 620 252 V340 H-10Z" fill="{ground}"/>
  <path d="M-10 276 Q300 262 620 276 V340 H-10Z" fill="#000" opacity=".06"/>
  {_flowers()}{_bowl(belly >= 50)}{_ball()}
</svg>"""


def lab(belly: int) -> str:
    skyline = "".join(f'<rect x="{x}" y="{200 - h}" width="{w}" height="{h}" fill="#1b2a52"/>' +
                      "".join(f'<rect x="{x + 5}" y="{200 - h + 8 + r * 14}" width="5" height="6" fill="#ffd479" opacity=".8"/>' for r in range(max(1, h // 22)) if (x + r) % 3)
                      for x, w, h in [(380, 34, 80), (418, 26, 110), (448, 40, 64), (492, 30, 96), (526, 38, 70)])
    grid = "".join(f'<line x1="{x}" y1="252" x2="{300 + (x - 300) * 3.4}" y2="340" stroke="#4be1ff" stroke-width="1.2" opacity=".35"/>' for x in range(0, 640, 50))
    rows = "".join(f'<line x1="0" y1="{y}" x2="600" y2="{y}" stroke="#4be1ff" stroke-width="1.2" opacity=".28"/>' for y in (262, 278, 300, 328))
    pellets = ('<circle cx="124" cy="296" r="5" fill="#ffb35e"/><circle cx="138" cy="299" r="5" fill="#ffd479"/><circle cx="110" cy="299" r="5" fill="#ffd479"/>' if belly >= 50 else "")
    return f"""<svg class="scene" viewBox="0 0 {W} {H}" preserveAspectRatio="xMidYMid slice" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
  <defs>
    <linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1d2347"/><stop offset="1" stop-color="#2d3566"/></linearGradient>
    <radialGradient id="pad" cx=".5" cy=".5" r=".5"><stop offset="0" stop-color="#4be1ff" stop-opacity=".75"/><stop offset="1" stop-color="#4be1ff" stop-opacity="0"/></radialGradient>
  </defs>
  <rect width="{W}" height="{H}" fill="url(#wall)"/>
  {"".join(f'<rect x="{x}" y="14" width="86" height="40" rx="8" fill="#ffffff" opacity=".04"/>' for x in range(14, 600, 96))}
  <rect x="360" y="40" width="226" height="160" rx="18" fill="#0d1230" stroke="#4b5aa8" stroke-width="5"/>
  <rect x="368" y="48" width="210" height="144" rx="12" fill="#101a45"/>
  {"".join(f'<circle cx="{x}" cy="{y}" r="1.6" fill="#fff" opacity=".8"/>' for x, y in [(390, 70), (430, 62), (480, 80), (530, 66), (560, 96), (410, 100)])}
  <g transform="translate(0 0)">{skyline}</g>
  <line x1="473" y1="48" x2="473" y2="192" stroke="#4b5aa8" stroke-width="4"/><line x1="368" y1="120" x2="578" y2="120" stroke="#4b5aa8" stroke-width="4"/>
  <rect x="24" y="70" width="230" height="6" rx="3" fill="#4be1ff" opacity=".8" class="led"/>
  <rect x="24" y="90" width="150" height="6" rx="3" fill="#b07bff" opacity=".7" class="led" style="animation-delay:-.8s"/>
  <rect x="-10" y="200" width="620" height="140" fill="#161c3d"/>
  <rect x="-10" y="244" width="620" height="96" fill="#1e2650"/>
  {grid}{rows}
  <ellipse cx="300" cy="300" rx="150" ry="34" fill="url(#pad)"/>
  <ellipse cx="300" cy="300" rx="104" ry="22" fill="none" stroke="#4be1ff" stroke-width="3" opacity=".8"/>
  <path d="M90 306 h70 l-8 -18 h-54 z" fill="#7d8fb8"/><rect x="90" y="306" width="70" height="8" rx="4" fill="#56658f"/>{pellets}
  <g transform="translate(480 300)"><circle r="19" fill="#b07bff"/><circle r="9" fill="#1d2347"/>{"".join(f'<rect x="-3" y="-25" width="6" height="9" rx="2" fill="#b07bff" transform="rotate({a})"/>' for a in range(0, 360, 45))}</g>
</svg>"""


def scene_svg(style: str, hour: int, belly: int) -> str:
    if style == "robotic":
        return lab(belly)
    return garden(hour, belly)
