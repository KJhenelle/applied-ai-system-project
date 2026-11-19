"""Clickable props for the companion scene, as standalone SVGs.

Garden props (bowl, ball, leash, brush, medicine chest) and lab props (pellet dock, energy orb, cable
leash, polisher, wall panel) tell the same story in two art styles. The scene's JavaScript attaches
click / drag behavior; these functions only draw.
"""
from __future__ import annotations

PROP_ACTIONS = {"bowl": "feed", "ball": "play", "leash": "walk", "brush": "groom", "cabinet": "meds"}


def _svg(view: str, body: str, label: str) -> str:
    return f'<svg viewBox="{view}" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{label}" overflow="visible">{body}</svg>'


def bowl(style: str, full: bool) -> str:
    if style == "robotic":
        pellets = ('<circle cx="46" cy="30" r="6" fill="#ffb35e"/><circle cx="62" cy="34" r="6" fill="#ffd479"/>'
                   '<circle cx="78" cy="30" r="6" fill="#ffb35e"/><circle cx="54" cy="24" r="5" fill="#ffd479"/>') if full else ""
        body = ('<ellipse cx="60" cy="68" rx="52" ry="7" fill="#000" opacity=".25"/>'
                '<path d="M14 40 h92 l-10 28 h-72 z" fill="#7d8fb8" stroke="#56658f" stroke-width="3" stroke-linejoin="round"/>'
                '<ellipse cx="60" cy="40" rx="46" ry="11" fill="#34406b" stroke="#56658f" stroke-width="3"/>'
                f'<ellipse cx="60" cy="41" rx="36" ry="7" fill="#1d2547"/>{pellets}'
                '<rect x="46" y="54" width="28" height="6" rx="3" fill="#4be1ff" opacity=".9"/>')
    else:
        food = ('<ellipse cx="60" cy="33" rx="32" ry="9" fill="#b9733d"/><circle cx="44" cy="27" r="7" fill="#c98547"/>'
                '<circle cx="62" cy="24" r="7" fill="#a9622f"/><circle cx="78" cy="28" r="7" fill="#c98547"/>') if full else ""
        body = ('<ellipse cx="60" cy="68" rx="52" ry="7" fill="#000" opacity=".14"/>'
                '<path d="M12 36 h96 l-12 32 h-72 z" fill="#ff7b8c"/><ellipse cx="60" cy="36" rx="48" ry="13" fill="#ff9aa8"/>'
                f'<ellipse cx="60" cy="37" rx="36" ry="9" fill="#d95f72"/>{food}'
                '<rect x="38" y="50" width="44" height="9" rx="4.5" fill="#fff" opacity=".55"/>')
    return _svg("0 0 120 76", body, "Food bowl")


def ball(style: str) -> str:
    if style == "robotic":
        spokes = "".join(f'<rect x="-4" y="-34" width="8" height="12" rx="3" fill="#b07bff" transform="rotate({a})"/>' for a in range(0, 360, 45))
        body = f'<g transform="translate(40 40)"><circle r="28" fill="#b07bff"/><circle r="13" fill="#1d2347"/><circle r="5" fill="#4be1ff"/>{spokes}</g>'
    else:
        body = ('<circle cx="40" cy="40" r="30" fill="#5cc8ff"/><path d="M12 34 Q40 52 68 34" fill="none" stroke="#fff" stroke-width="4"/>'
                '<path d="M40 10 Q52 40 40 70" fill="none" stroke="#fff" stroke-width="3" opacity=".6"/><circle cx="29" cy="27" r="7" fill="#fff" opacity=".6"/>')
    return _svg("0 0 80 84", '<ellipse cx="40" cy="78" rx="26" ry="5" fill="#000" opacity=".14"/>' + body, "Ball")


def leash(style: str) -> str:
    c, d = ("#4be1ff", "#1d9fb8") if style == "robotic" else ("#ff6b6b", "#c94545")
    body = (f'<path d="M30 6 v12" stroke="#8a7a83" stroke-width="5" stroke-linecap="round"/><circle cx="30" cy="6" r="5" fill="#8a7a83"/>'
            f'<path d="M30 16 C6 22 4 62 24 72 C44 82 56 50 40 40" fill="none" stroke="{c}" stroke-width="9" stroke-linecap="round"/>'
            f'<path d="M30 16 C10 24 8 58 24 68" fill="none" stroke="{d}" stroke-width="3" stroke-linecap="round" opacity=".6"/>'
            f'<rect x="32" y="34" width="20" height="14" rx="5" fill="#ffd24d" stroke="#d9a400" stroke-width="2" transform="rotate(25 42 41)"/>')
    return _svg("0 0 64 90", body, "Leash")


def brush(style: str) -> str:
    if style == "robotic":
        body = ('<ellipse cx="70" cy="44" rx="56" ry="5" fill="#000" opacity=".2"/>'
                '<rect x="8" y="14" width="64" height="20" rx="10" fill="#7d8fb8" stroke="#56658f" stroke-width="3"/>'
                '<rect x="16" y="20" width="22" height="8" rx="4" fill="#4be1ff"/>'
                '<rect x="70" y="10" width="46" height="28" rx="8" fill="#34406b" stroke="#56658f" stroke-width="3"/>'
                + "".join(f'<rect x="{x}" y="14" width="3" height="20" rx="1.5" fill="#4be1ff"/>' for x in range(76, 112, 7)))
    else:
        body = ('<ellipse cx="62" cy="46" rx="52" ry="5" fill="#000" opacity=".14"/>'
                '<rect x="4" y="16" width="70" height="16" rx="8" fill="#c98547" stroke="#a9622f" stroke-width="3"/>'
                '<rect x="68" y="8" width="46" height="32" rx="8" fill="#ffd9a8" stroke="#e0b070" stroke-width="3"/>'
                + "".join(f'<rect x="{x}" y="2" width="3.5" height="14" rx="1.7" fill="#7a5a3a"/>' for x in range(74, 112, 7)))
    return _svg("0 0 120 50", body, "Grooming brush")


def cabinet(style: str) -> str:
    if style == "robotic":
        frame, door, cross, glow = "#34406b", "#46558d", "#3ddc84", ' filter="url(#cglow)"'
    else:
        frame, door, cross, glow = "#f3e6cc", "#fffaf0", "#e5484d", ""
    body = (f'<defs><filter id="cglow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.5" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter></defs>'
            f'<rect x="4" y="4" width="92" height="104" rx="12" fill="{frame}" stroke="#8a7a83" stroke-width="3"/>'
            '<rect x="14" y="14" width="72" height="84" rx="8" fill="#2b2230" opacity=".85"/>'
            '<g class="shelf"><rect x="20" y="50" width="60" height="4" fill="#8a7a83"/>'
            '<rect x="24" y="30" width="14" height="20" rx="3" fill="#ffd24d"/><rect x="42" y="34" width="12" height="16" rx="3" fill="#5cc8ff"/>'
            '<rect x="58" y="28" width="16" height="22" rx="3" fill="#ff8fb1"/>'
            '<rect x="24" y="68" width="18" height="24" rx="3" fill="#b9e4c9"/><rect x="48" y="72" width="26" height="20" rx="3" fill="#ffd0a8"/></g>'
            f'<g class="door"><rect x="14" y="14" width="72" height="84" rx="8" fill="{door}" stroke="#8a7a83" stroke-width="2"/>'
            f'<rect x="43" y="34" width="14" height="44" rx="3" fill="{cross}"{glow}/><rect x="28" y="49" width="44" height="14" rx="3" fill="{cross}"{glow}/>'
            '<circle cx="78" cy="56" r="3.5" fill="#8a7a83"/></g>')
    return _svg("0 0 100 112", body, "Medicine cabinet")


def all_props(style: str, belly: int) -> dict[str, str]:
    """Every prop for a style; the bowl is full when the pet's belly is at least half full."""
    return {"bowl": bowl(style, belly >= 50), "ball": ball(style), "leash": leash(style),
            "brush": brush(style), "cabinet": cabinet(style)}
