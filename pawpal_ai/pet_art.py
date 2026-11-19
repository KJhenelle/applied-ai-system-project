"""Chibi-style SVG art for the virtual companion (no image files, no dependencies).

`render_html()` returns a self-contained HTML snippet: smooth vector art with CSS animation
(bobbing, blinking, tail wag, ear twitch). The pet's *mood* picks the face, the lowest *need* picks
a thought bubble, and a one-shot *reaction* plays after the owner logs care.

Two art styles show the same state:
  realistic: soft fur, warm colors, big glossy eyes
  robotic:   brushed-metal panels, glowing visor eyes, a status LED on the antenna
"""
from __future__ import annotations

from .companion import CompanionState
from .props import all_props
from .scene import period, scene_svg

MOODS = ("happy", "okay", "needy")
REACTIONS = {"feeding": "eat", "walk": "walk", "enrichment": "play", "grooming": "groom", "meds": "heart"}
NEED_BUBBLE = {"belly": "🍖", "fun": "🧸", "clean": "🛁"}
REACTION_EMOJI = {"eat": "😋", "play": "🎾", "walk": "🦮", "groom": "✨", "heart": "💖"}

PALETTES = {
    ("dog", "realistic"): dict(fur="#e8b878", dark="#a9693a", light="#fff1dc", inner="#f6c4b8", ear="#b9703f"),
    ("cat", "realistic"): dict(fur="#f4a85c", dark="#c9702a", light="#fff3e2", inner="#ffb8c2", ear="#f4a85c"),
    ("dog", "robotic"): dict(fur="#b9c6d8", dark="#5d6f89", light="#e9eff7", inner="#6dd5ed", ear="#8fa1bb"),
    ("cat", "robotic"): dict(fur="#c8bfe0", dark="#6b5f93", light="#efeaf8", inner="#9be7ff", ear="#a79ccc"),
}
LED = {"happy": "#3ddc84", "okay": "#ffc83d", "needy": "#ff5d5d"}

CSS = """
html,body{margin:0;background:transparent;font-family:system-ui,sans-serif;height:100%}
.stage{position:relative;height:100%;min-height:300px;border-radius:26px;overflow:hidden;box-shadow:inset 0 0 0 1px rgba(0,0,0,.06)}
.scene{position:absolute;inset:0;width:100%;height:100%}
.pet{position:absolute;left:50%;bottom:-6px;transform:translateX(-50%);width:min(235px,60vw);height:auto;aspect-ratio:1;overflow:visible}
.cloud{animation:drift 60s linear infinite}
.chip{position:absolute;left:14px;top:12px;padding:5px 12px;border-radius:999px;font-size:12.5px;font-weight:700;letter-spacing:.02em;background:rgba(255,255,255,.82);color:#4a3b45;backdrop-filter:blur(4px)}
.robotic .chip{background:rgba(20,28,64,.7);color:#8cf0ff}
@keyframes drift{from{transform:translateX(-40px)}50%{transform:translateX(40px)}to{transform:translateX(-40px)}}
.bob{animation:bob 2.6s ease-in-out infinite;transform-box:fill-box;transform-origin:50% 100%}
.needy .bob{animation-duration:4.2s}
.tail{transform-box:fill-box;transform-origin:0% 100%;animation:wag 0.5s ease-in-out infinite alternate}
.okay .tail{animation-duration:1.2s}
.needy .tail{animation-duration:3s}
.eyes{transform-box:fill-box;transform-origin:50% 50%;animation:blink 4.5s infinite}
.ear-l{transform-box:fill-box;transform-origin:80% 90%;animation:twitch 6s ease-in-out infinite}
.ear-r{transform-box:fill-box;transform-origin:20% 90%;animation:twitch 6s ease-in-out 1.7s infinite reverse}
.led{animation:pulse 1.6s ease-in-out infinite}
.bubble{animation:float 2.4s ease-in-out infinite}
.fx{transform-box:fill-box;transform-origin:50% 50%}
.react-eat .bob{animation:chomp 0.55s ease-in-out 3}
.react-play .bob{animation:hop 0.6s ease-out 3}
.react-groom .bob{animation:shake 0.4s ease-in-out 4}
.react-heart .bob{animation:hop 0.9s ease-out 2}
.fx-float{animation:rise 1.8s ease-out 1 forwards}
@keyframes bob{0%,100%{transform:translateY(0) scale(1,1)}50%{transform:translateY(-5px) scale(1.01,.99)}}
@keyframes wag{from{transform:rotate(-18deg)}to{transform:rotate(22deg)}}
@keyframes blink{0%,93%,100%{transform:scaleY(1)}96%{transform:scaleY(.08)}}
@keyframes twitch{0%,90%,100%{transform:rotate(0)}94%{transform:rotate(-7deg)}97%{transform:rotate(3deg)}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
@keyframes float{0%,100%{transform:translateY(0)}50%{transform:translateY(-6px)}}
@keyframes chomp{0%,100%{transform:scale(1,1)}50%{transform:scale(1.07,.93)}}
@keyframes hop{0%,100%{transform:translateY(0)}40%{transform:translateY(-26px) rotate(-4deg)}70%{transform:translateY(-8px) rotate(3deg)}}
@keyframes shake{0%,100%{transform:rotate(0)}25%{transform:rotate(-6deg)}75%{transform:rotate(6deg)}}
@keyframes rise{0%{opacity:0;transform:translateY(20px) scale(.6)}20%{opacity:1}100%{opacity:0;transform:translateY(-70px) scale(1.25)}}
@media (prefers-reduced-motion:reduce){*{animation:none!important}}
"""


def mood_of(state: CompanionState) -> str:
    return state.mood


def lowest_need(state: CompanionState) -> str | None:
    """The need to show in a thought bubble, or None if nothing is low."""
    needs = {"belly": state.belly, "fun": state.fun, "clean": state.clean}
    name = min(needs, key=needs.get)
    return name if needs[name] < 40 else None


# ------------------------------------------------------------------ shared pieces
def _mouth(mood: str, color: str, tongue: bool) -> str:
    if mood == "happy":
        tongue_svg = '<ellipse cx="150" cy="186" rx="8" ry="7" fill="#ff8fa3"/>' if tongue else ""
        return f'<path d="M130 168 Q150 196 170 168 Z" fill="#7a2f3a"/>{tongue_svg}<path d="M130 168 Q150 196 170 168" fill="none" stroke="{color}" stroke-width="3" stroke-linecap="round"/>'
    if mood == "okay":
        return f'<path d="M138 172 Q150 180 162 172" fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round"/>'
    return f'<path d="M138 180 Q150 166 162 180" fill="none" stroke="{color}" stroke-width="3.5" stroke-linecap="round"/>'


def _eyes_organic(mood: str) -> str:
    ry = {"happy": 22, "okay": 20, "needy": 18}[mood]
    brows = ""
    if mood == "needy":
        brows = ('<path d="M94 122 L130 108" stroke="#3a2a30" stroke-width="4" stroke-linecap="round"/>'
                 '<path d="M206 122 L170 108" stroke="#3a2a30" stroke-width="4" stroke-linecap="round"/>')
    sparkle = ""
    if mood == "happy":
        sparkle = '<circle cx="124" cy="127" r="3" fill="#fff"/><circle cx="188" cy="127" r="3" fill="#fff"/>'
    cy = 136 if mood != "needy" else 140
    eyes = "".join(
        f'<ellipse cx="{cx}" cy="{cy}" rx="18" ry="{ry}" fill="#2b2230"/>'
        f'<circle cx="{cx + 6}" cy="{cy - 8}" r="7" fill="#fff"/><circle cx="{cx - 6}" cy="{cy + 8}" r="3.2" fill="#fff" opacity=".85"/>'
        for cx in (118, 182))
    return f'<g class="eyes">{eyes}{sparkle}</g>{brows}'


def _bubble(need: str | None) -> str:
    if not need:
        return ""
    return (f'<g class="bubble"><ellipse cx="232" cy="52" rx="30" ry="26" fill="#fff" stroke="#d9d2e4" stroke-width="3"/>'
            f'<circle cx="204" cy="86" r="7" fill="#fff" stroke="#d9d2e4" stroke-width="3"/>'
            f'<circle cx="192" cy="100" r="4" fill="#fff" stroke="#d9d2e4" stroke-width="3"/>'
            f'<text x="232" y="62" font-size="28" text-anchor="middle">{NEED_BUBBLE[need]}</text></g>')


def _fx(reaction: str | None) -> str:
    if not reaction:
        return ""
    e = REACTION_EMOJI[reaction]
    spots = [(70, 70, 0), (230, 90, 0.25), (150, 40, 0.5)]
    return "".join(f'<text class="fx fx-float" x="{x}" y="{y}" font-size="30" text-anchor="middle" '
                   f'style="animation-delay:{d}s;opacity:0">{e}</text>' for x, y, d in spots)


# ------------------------------------------------------------------ realistic chibi
def _realistic(species: str, mood: str, p: dict) -> str:
    dog = species == "dog"
    tail = (f'<path class="tail" d="M196 232 Q236 220 232 176 Q226 204 200 214 Z" fill="{p["dark"]}"/>' if dog else
            f'<path class="tail" d="M196 236 Q250 244 244 188 Q238 222 198 222 Z" fill="{p["dark"]}" stroke="{p["dark"]}" stroke-width="10" stroke-linejoin="round"/>')
    droop = 14 if mood == "needy" else 0
    if dog:
        ears = (f'<g class="ear-l"><ellipse cx="74" cy="{120 + droop}" rx="26" ry="46" transform="rotate({18 + droop} 74 {120 + droop})" fill="{p["ear"]}"/></g>'
                f'<g class="ear-r"><ellipse cx="226" cy="{120 + droop}" rx="26" ry="46" transform="rotate({-18 - droop} 226 {120 + droop})" fill="{p["ear"]}"/></g>')
        muzzle = f'<ellipse cx="150" cy="162" rx="36" ry="26" fill="{p["light"]}"/>'
        nose = '<ellipse cx="150" cy="154" rx="11" ry="8" fill="#3a2a30"/><ellipse cx="146" cy="151" rx="3.5" ry="2" fill="#fff" opacity=".7"/>'
        patch = f'<ellipse cx="206" cy="112" rx="26" ry="24" fill="{p["dark"]}" opacity=".55"/>'
        whiskers = ""
    else:
        t = 0 if mood != "needy" else 8
        ears = (f'<g class="ear-l"><path d="M64 {104 + t} L74 {26 + t} L128 {66 + t} Z" fill="{p["ear"]}" stroke="{p["ear"]}" stroke-width="8" stroke-linejoin="round"/>'
                f'<path d="M80 {88 + t} L84 {50 + t} L110 {70 + t} Z" fill="{p["inner"]}"/></g>'
                f'<g class="ear-r"><path d="M236 {104 + t} L226 {26 + t} L172 {66 + t} Z" fill="{p["ear"]}" stroke="{p["ear"]}" stroke-width="8" stroke-linejoin="round"/>'
                f'<path d="M220 {88 + t} L216 {50 + t} L190 {70 + t} Z" fill="{p["inner"]}"/></g>')
        muzzle = f'<ellipse cx="150" cy="164" rx="28" ry="20" fill="{p["light"]}"/>'
        nose = '<path d="M141 154 Q150 150 159 154 Q150 166 141 154Z" fill="#ff8fa3"/>'
        patch = f'<path d="M140 62 L150 92 L160 62 Z" fill="{p["dark"]}" opacity=".6"/><path d="M118 70 L128 92 L136 68Z" fill="{p["dark"]}" opacity=".5"/><path d="M164 68 L172 92 L182 70Z" fill="{p["dark"]}" opacity=".5"/>'
        whiskers = ('<g stroke="#8a6a5a" stroke-width="2.5" stroke-linecap="round" opacity=".75">'
                    '<path d="M104 166 L66 158"/><path d="M104 174 L68 182"/><path d="M196 166 L234 158"/><path d="M196 174 L232 182"/></g>')
    paws = "".join(f'<ellipse cx="{x}" cy="266" rx="19" ry="12" fill="{p["light"]}"/>' for x in (118, 182))
    return f"""
    <g class="bob">
      {tail}
      <ellipse cx="150" cy="226" rx="54" ry="44" fill="{p['fur']}"/>
      <ellipse cx="150" cy="234" rx="32" ry="28" fill="{p['light']}"/>
      {paws}
      {ears}
      <ellipse cx="150" cy="132" rx="90" ry="80" fill="{p['fur']}"/>
      {patch}
      {muzzle}
      <ellipse cx="86" cy="164" rx="15" ry="10" fill="#ff9aa8" opacity=".55"/>
      <ellipse cx="214" cy="164" rx="15" ry="10" fill="#ff9aa8" opacity=".55"/>
      {_eyes_organic(mood)}
      {nose}
      {_mouth(mood, "#7a2f3a", dog)}
      {whiskers}
    </g>"""


# ------------------------------------------------------------------ robotic chibi
def _robot_eyes(mood: str) -> str:
    glow = "#5ef2ff" if mood != "needy" else "#ffb35e"
    if mood == "happy":  # ^ ^ arcs
        shapes = "".join(f'<path d="M{cx - 16} 140 Q{cx} 116 {cx + 16} 140" fill="none" stroke="{glow}" stroke-width="9" stroke-linecap="round"/>' for cx in (120, 180))
    elif mood == "okay":
        shapes = "".join(f'<circle cx="{cx}" cy="132" r="13" fill="{glow}"/><circle cx="{cx + 4}" cy="128" r="4" fill="#fff"/>' for cx in (120, 180))
    else:  # sad eyes: round glow with a dark lid slanting down toward the outer corner
        shapes = "".join(
            f'<circle cx="{cx}" cy="134" r="13" fill="{glow}"/><circle cx="{cx + 4}" cy="136" r="4" fill="#fff"/>'
            f'<polygon points="{cx + d * 16},{118} {cx - d * 3},{118} {cx + d * 16},{138}" fill="#1d2536"/>'
            for cx, d in ((120, -1), (180, 1)))
    return f'<g class="eyes" filter="url(#glow)">{shapes}</g>'


def _robotic(species: str, mood: str, p: dict) -> str:
    dog = species == "dog"
    led = LED[mood]
    if dog:
        ears = (f'<g class="ear-l"><rect x="46" y="86" width="34" height="64" rx="16" fill="{p["ear"]}" stroke="{p["dark"]}" stroke-width="4"/><rect x="55" y="100" width="16" height="30" rx="8" fill="{p["inner"]}" opacity=".8"/></g>'
                f'<g class="ear-r"><rect x="220" y="86" width="34" height="64" rx="16" fill="{p["ear"]}" stroke="{p["dark"]}" stroke-width="4"/><rect x="229" y="100" width="16" height="30" rx="8" fill="{p["inner"]}" opacity=".8"/></g>')
    else:
        ears = (f'<g class="ear-l"><path d="M62 96 L70 34 L120 70 Z" fill="{p["ear"]}" stroke="{p["dark"]}" stroke-width="4" stroke-linejoin="round"/><path d="M78 84 L80 54 L102 72 Z" fill="{p["inner"]}" opacity=".8"/></g>'
                f'<g class="ear-r"><path d="M238 96 L230 34 L180 70 Z" fill="{p["ear"]}" stroke="{p["dark"]}" stroke-width="4" stroke-linejoin="round"/><path d="M222 84 L220 54 L198 72 Z" fill="{p["inner"]}" opacity=".8"/></g>')
    mouth_color = "#5ef2ff" if mood != "needy" else "#ffb35e"
    mouth = {"happy": "M132 178 Q150 196 168 178", "okay": "M136 182 L164 182", "needy": "M136 188 Q150 176 164 188"}[mood]
    tail = f'<path class="tail" d="M198 232 Q240 226 236 184" fill="none" stroke="{p["dark"]}" stroke-width="12" stroke-linecap="round" stroke-dasharray="14 5"/>'
    return f"""
    <defs>
      <linearGradient id="metal" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{p['light']}"/><stop offset="1" stop-color="{p['fur']}"/></linearGradient>
      <filter id="glow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="2.5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
    </defs>
    <g class="bob">
      {tail}
      <rect x="98" y="190" width="104" height="78" rx="30" fill="url(#metal)" stroke="{p['dark']}" stroke-width="4"/>
      <rect x="126" y="206" width="48" height="30" rx="10" fill="#1d2536"/>
      <circle cx="150" cy="221" r="8" fill="{led}" class="led"/>
      {"".join(f'<rect x="{x - 20}" y="258" width="40" height="18" rx="9" fill="{p["ear"]}" stroke="{p["dark"]}" stroke-width="3"/>' for x in (118, 182))}
      <line x1="150" y1="52" x2="150" y2="26" stroke="{p['dark']}" stroke-width="5" stroke-linecap="round"/>
      <circle cx="150" cy="22" r="8" fill="{led}" class="led" filter="url(#glow)"/>
      {ears}
      <rect x="54" y="50" width="192" height="150" rx="58" fill="url(#metal)" stroke="{p['dark']}" stroke-width="4"/>
      <rect x="78" y="94" width="144" height="70" rx="34" fill="#1d2536"/>
      <rect x="84" y="99" width="132" height="20" rx="10" fill="#fff" opacity=".07"/>
      {_robot_eyes(mood)}
      <path d="{mouth}" fill="none" stroke="{mouth_color}" stroke-width="5" stroke-linecap="round" filter="url(#glow)"/>
      <circle cx="68" cy="66" r="4" fill="{p['dark']}"/><circle cx="232" cy="66" r="4" fill="{p['dark']}"/>
      <circle cx="68" cy="184" r="4" fill="{p['dark']}"/><circle cx="232" cy="184" r="4" fill="{p['dark']}"/>
      <ellipse cx="150" cy="156" rx="9" ry="6" fill="#1d2536" stroke="{p['dark']}" stroke-width="2"/>
    </g>"""


# ------------------------------------------------------------------ public API
def build_svg(species: str, style: str, mood: str, need: str | None = None, reaction: str | None = None) -> str:
    if mood not in MOODS:
        raise ValueError(f"mood must be one of {MOODS}")
    if style not in ("realistic", "robotic"):
        raise ValueError("style must be 'realistic' or 'robotic'")
    if reaction is not None and reaction not in REACTION_EMOJI:
        raise ValueError(f"reaction must be one of {tuple(REACTION_EMOJI)}")
    species = species if species in ("dog", "cat") else "dog"  # "other" falls back to the dog art
    p = PALETTES[(species, style)]
    body = (_realistic if style == "realistic" else _robotic)(species, mood, p)
    return (f'<svg viewBox="0 0 300 300" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{style} {species}, feeling {mood}">'
            f'<ellipse cx="150" cy="278" rx="72" ry="9" fill="#000" opacity=".12"/>{body}{_bubble(need)}{_fx(reaction)}</svg>')


def render_html(species: str, style: str, state: CompanionState, reaction: str | None = None,
                hour: int | None = None) -> str:
    """Full HTML snippet (scene + pet) for st.iframe / components.html, or saving to a file."""
    from datetime import datetime

    hour = datetime.now().hour if hour is None else hour
    svg = build_svg(species, style, state.mood, lowest_need(state), reaction).replace("<svg ", '<svg class="pet" ', 1)
    cls = f"{style} {state.mood}" + (f" react-{reaction}" if reaction else "")
    label = {"dawn": "Morning", "day": "Daytime", "sunset": "Evening", "night": "Night"}[period(hour)] if style == "realistic" else "Lab mode"
    return f"<style>{CSS}</style><div class='stage {cls}'>{scene_svg(style, hour, state.belly)}<div class='chip'>{label}</div>{svg}</div>"


def stage_label(style: str, hour: int) -> str:
    return {"dawn": "Morning", "day": "Daytime", "sunset": "Evening", "night": "Night"}[period(hour)] if style == "realistic" else "Lab mode"


def stage_payload(species: str, style: str, state: CompanionState, hour: int, name: str, mode: str = "virtual") -> dict:
    """Everything the interactive stage needs to draw itself (panels are added by the caller)."""
    return {
        "scene": scene_svg(style, hour, state.belly, props=False),
        "pet": build_svg(species, style, state.mood, lowest_need(state)).replace("<svg ", '<svg class="pet" ', 1),
        "props": all_props(style, state.belly),
        "style": style, "mood": state.mood, "chip": stage_label(style, hour), "name": name, "mode": mode,
    }


def component_css() -> str:
    """The shared animation CSS without the page-level html/body rule (which would leak globally)."""
    return "\n".join(l for l in CSS.strip().splitlines() if not l.startswith("html,body"))
