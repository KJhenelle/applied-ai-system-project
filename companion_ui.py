"""Streamlit tab for the virtual companion, daily briefing, care history and Q&A."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components

from pawpal_ai.agent import CareAgent
from pawpal_ai.care_log import REAL, VIRTUAL, VALID_TYPES, CareEvent, CareLog
from pawpal_ai.companion import STYLES, Companion, compute_synced_state
from pawpal_ai.demo_data import build_demo
from pawpal_ai.pet_art import REACTIONS, render_html
from pawpal_ai.retriever import KnowledgeBase
from ui_theme import banner

LOG_PATH = Path("data/care_log.json")


@st.cache_resource
def _kb() -> KnowledgeBase:
    return KnowledgeBase()


def _show_html(html: str, height: int) -> None:
    """Embed generated HTML. Only enum-validated values go into it, never user text."""
    if hasattr(st, "iframe"):  # newer Streamlit; components.v1.html is deprecated there
        st.iframe(html, height=height)
    else:
        components.html(html, height=height)


def _ensure_log() -> CareLog:
    if "care_log" not in st.session_state:
        st.session_state.care_log = CareLog.load(LOG_PATH)
    return st.session_state.care_log


CARE_BUTTONS = [("feeding", "🍖 Feed"), ("walk", "🦮 Walk"), ("enrichment", "🧸 Play"),
                ("grooming", "🛁 Groom"), ("meds", "💊 Meds")]
TYPE_EMOJI = {"feeding": "🍖", "walk": "🦮", "meds": "💊", "enrichment": "🧸", "grooming": "🛁"}
NEED_LABEL = {"belly": "🍖 Belly", "fun": "🎾 Fun", "clean": "🛁 Clean"}


def _bar(need: str, shown: int, real: int, game: int) -> str:
    cls = "hi" if shown >= 66 else "mid" if shown >= 33 else "lo"
    return (f'<div class="need"><div class="row"><span>{NEED_LABEL[need]}</span><span>{shown}%</span></div>'
            f'<div class="track"><div class="fill {cls}" style="width:{shown}%"></div>'
            f'<div class="tick" style="left:calc({real}% - 1px)" title="real pet {real}%"></div></div>'
            f'<div class="cap">real pet {real}% &middot; game {game}%</div></div>')


def _status_card(pet, companion, synced) -> str:
    s = synced.shown
    bars = "".join(_bar(n, getattr(s, n), getattr(synced.real, n), getattr(synced.virtual, n)) for n in NEED_LABEL)
    return (f'<div class="card status"><h3>{escape(pet.name)}<span class="mood mood-{s.mood}">{s.mood.title()}</span></h3>'
            f'<div class="sub">{escape(pet.species.title())} &middot; {pet.age} yr</div>'
            f'<div class="quote">&ldquo;{escape(companion.mood_line(s))}&rdquo;</div>'
            f'{bars}<div class="foot">The dark tick is how well the '
            f'<b>real</b> pet is cared for; the companion can never go past it.</div></div>')


def _sync_banner(companion, synced) -> str:
    note = companion.sync_note(synced)
    if note:
        return f'<div class="sync" style="margin-top:.7rem">🔗 {escape(note)}</div>'
    return '<div class="sync ok" style="margin-top:.7rem">🔗 In sync: real care is keeping up, so the companion can be as happy as play allows.</div>'


def _slot_card(line) -> str:
    tip = f'<div class="tip">💡 {escape(line.tip)} <small>[{escape(line.source)}]</small></div>' if line.tip else ""
    return (f'<div class="slot"><div class="time">{line.slot.start:%H:%M}<br>{line.slot.end:%H:%M}</div><div>'
            f'<div class="title">{TYPE_EMOJI[line.task.type.value]} {escape(line.task.pet.name)}: {escape(line.task.title)}</div>'
            f'<div class="why">Why: {escape(line.reason)}</div>{tip}</div></div>')


def _trio_html() -> str:
    """Three of the companion characters side by side on a transparent background."""
    from pawpal_ai.pet_art import CSS, build_svg
    pets = [("dog", "realistic", "happy"), ("dog", "robotic", "happy"), ("cat", "realistic", "happy")]
    svgs = "".join(build_svg(sp, st_, md).replace("<svg ", '<svg class="trio" ', 1) for sp, st_, md in pets)
    return (f"<style>{CSS}.trio{{width:200px;height:200px;margin:0 6px}}.row{{display:flex;justify-content:center;align-items:flex-end;height:100%}}"
            f"</style><div class='row happy'>{svgs}</div>")


def _empty_state() -> None:
    _show_html(_trio_html(), 230)
    st.markdown('<div class="empty"><h3>Meet your PawPal companion</h3>'
                '<div class="section-sub">A virtual pet that mirrors how well your <b>real</b> pet is cared for, learns their routine, '
                'and tells you what to do next.</div></div>', unsafe_allow_html=True)
    st.write("")
    c = st.columns([1, 2, 1])[1]
    if c.button("✨ Try the demo household (Rex & Mia)", type="primary", use_container_width=True):
        _load_demo()
    c.caption("Or add your own pet in the **Pets** tab.")


def _load_demo() -> None:
    owner, avail, log = build_demo(datetime.now())
    st.session_state.owner, st.session_state.availability, st.session_state.care_log = owner, avail, log
    st.rerun()


def render(owner, availability) -> None:
    care_log = _ensure_log()
    if not owner.pets:
        if st.query_params.get("demo") == "1":  # shareable link: ?demo=1
            _load_demo()
        _empty_state()
        return

    top = st.columns([2, 3, 2])
    pet_name = top[0].selectbox("Companion for", [p.name for p in owner.pets], key="companion_pet")
    pet = next(p for p in owner.pets if p.name == pet_name)
    style = top[1].segmented_control("Style", list(STYLES), default="realistic", key="companion_style",
                                     format_func=lambda x: "🐶 Realistic" if x == "realistic" else "⚙️ Robotic") or "realistic"
    if top[2].button("🎲 Reset demo", use_container_width=True):
        _load_demo()

    now = datetime.now()
    companion = Companion(pet.name, pet.species, style)
    synced = compute_synced_state(care_log, pet.name, now)
    reaction = st.session_state.pop("reaction", None)  # one-shot, so it doesn't replay
    left, right = st.columns([3, 2], gap="medium")
    with left:
        _show_html(render_html(pet.species, style, synced.shown, reaction, now.hour), 360)
        st.markdown(_sync_banner(companion, synced), unsafe_allow_html=True)
    with right:
        st.markdown(_status_card(pet, companion, synced), unsafe_allow_html=True)

    st.markdown("#### Log care")
    source = st.segmented_control("Logging as", [REAL, VIRTUAL], default=REAL, key="log_source",
                                  format_func=lambda x: "🐕 Real pet" if x == REAL else "🎮 Virtual companion") or REAL
    st.caption("**Real** care is what you did for the actual animal, so it trains the routine learner and unlocks the companion's mood. "
               "**Virtual** care is play with the companion and can never raise it above the real pet's level.")
    for col, (kind, label) in zip(st.columns(len(CARE_BUTTONS)), CARE_BUTTONS):
        if col.button(label, key=f"log_{kind}", use_container_width=True):
            care_log.record(CareEvent(pet.name, kind, datetime.now().replace(second=0, microsecond=0), source))
            care_log.save(LOG_PATH)
            st.session_state.reaction = REACTIONS[kind]
            st.rerun()

    agent = CareAgent(owner, availability, care_log, _kb(), style)
    brief = agent.run(now)
    st.markdown("#### Today's briefing")
    st.markdown(banner("hello", brief.greeting, "👋"), unsafe_allow_html=True)
    html = "".join(banner("warn", n, "⏰") for n in brief.nudges)
    if brief.all_done:
        html += banner("ok", brief.all_done, "🎉")
    unfit = [a.removeprefix("Could not fit: ").rstrip(".") for a in brief.alerts if a.startswith("Could not fit: ")]
    html += "".join(banner("err", a, "⚠️") for a in brief.alerts if not a.startswith("Could not fit: "))
    if unfit:  # one calm banner instead of one red box per task
        html += banner("warn", "No free window left today for: " + "; ".join(unfit) + ". Add availability or do them tomorrow.", "🗓️")
    if brief.done:
        html += banner("ok", "Done today: " + "  ·  ".join(brief.done), "✅")
    st.markdown(html, unsafe_allow_html=True)
    if brief.lines:
        st.markdown(f'<div class="section-sub">Planned for the rest of today ({len(brief.lines)} tasks)</div>'
                    + "".join(_slot_card(l) for l in brief.lines), unsafe_allow_html=True)
    st.markdown("".join(banner("info", n, "🌱") for n in brief.learning), unsafe_allow_html=True)
    with st.expander("🔍 What the agent did (reasoning trace)"):
        st.json(brief.trace)

    st.markdown("#### Ask about your pet")
    q = st.text_input("Question", placeholder="Can Rex eat grapes?", label_visibility="collapsed")
    if q:
        ans = agent.ask(q, pet.name)
        kind = "err" if ans.reason == "emergency" else "warn" if ans.refused else "ok"
        chips = "".join(f'<span class="src">📚 {escape(x)}</span>' for x in ans.sources)
        st.markdown(f'<div class="banner {kind}"><div>{escape(ans.text)}<div>{chips}</div></div></div>', unsafe_allow_html=True)

    with st.expander("📒 Care history (last 30)"):
        rows = [{"When": f"{e.timestamp:%Y-%m-%d %H:%M}", "Pet": e.pet_name, "Care": e.task_type.title(),
                 "Who": "🐕 Real" if e.source == REAL else "🎮 Virtual"} for e in reversed(care_log.events[-30:])]
        st.dataframe(rows, use_container_width=True, hide_index=True) if rows else st.caption("No care logged yet.")
