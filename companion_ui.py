"""Streamlit tab for the virtual companion, daily briefing, care history and Q&A."""
from __future__ import annotations

from datetime import datetime
from html import escape
from pathlib import Path

import streamlit as st

from pawpal_ai.agent import CareAgent
from pawpal_ai.care_log import REAL, VIRTUAL, VALID_TYPES, CareEvent, CareLog
from pawpal_ai.companion import STYLES, Companion, compute_state
from pawpal_ai.demo_data import build_demo
from pawpal_ai.retriever import KnowledgeBase

LOG_PATH = Path("data/care_log.json")


@st.cache_resource
def _kb() -> KnowledgeBase:
    return KnowledgeBase()


def _ensure_log() -> CareLog:
    if "care_log" not in st.session_state:
        st.session_state.care_log = CareLog.load(LOG_PATH)
    return st.session_state.care_log


def render(owner, availability) -> None:
    care_log = _ensure_log()
    if st.button("🎲 Load demo household (Rex & Mia, 14 days of history)"):
        demo_owner, demo_avail, demo_log = build_demo(datetime.now())
        st.session_state.owner, st.session_state.availability = demo_owner, demo_avail
        st.session_state.care_log = demo_log
        st.rerun()

    if not owner.pets:
        st.info("Add a pet first (or load the demo household) to meet your companion.")
        return

    c1, c2 = st.columns(2)
    pet = next(p for p in owner.pets if p.name == c1.selectbox("Companion for", [p.name for p in owner.pets]))
    style = c2.radio("Companion style", STYLES, horizontal=True,
                     format_func=lambda s: "🐶 Realistic" if s == "realistic" else "🤖 Robotic")
    now = datetime.now()
    companion = Companion(pet.name, pet.species, style)
    state = compute_state(care_log, pet.name, now)

    st.markdown(f"### {companion.avatar} {escape(pet.name)}")
    st.caption(companion.describe_state(state))
    m = st.columns(3)
    m[0].metric("Belly", f"{state.belly}%")
    m[1].metric("Fun", f"{state.fun}%")
    m[2].metric("Clean", f"{state.clean}%")
    st.progress(min(100, (state.belly + state.fun + state.clean) // 3) / 100, text=f"Mood: {state.mood}")

    st.markdown("#### Log care")
    st.caption("**Real** care is what you did for the actual animal; it trains the routine learner. "
               "**Virtual** care is play with the companion and does not count as real care.")
    b = st.columns(5)
    for col, kind in zip(b, sorted(VALID_TYPES)):
        if col.button(kind.title(), key=f"log_{kind}", use_container_width=True):
            source = REAL if st.session_state.get("log_source", REAL) == REAL else VIRTUAL
            care_log.record(CareEvent(pet.name, kind, datetime.now().replace(second=0, microsecond=0), source))
            care_log.save(LOG_PATH)
            st.rerun()
    st.radio("Logging as", [REAL, VIRTUAL], key="log_source", horizontal=True,
             format_func=lambda s: "🐕 Real pet" if s == REAL else "🎮 Virtual companion")

    agent = CareAgent(owner, availability, care_log, _kb(), style)
    brief = agent.run(now)
    st.markdown("#### Today's briefing")
    st.info(brief.greeting)
    for n in brief.nudges:
        st.warning(n)
    for a in brief.alerts:
        st.error(a)
    for d in brief.done:
        st.success(f"Done: {d}")
    for l in brief.lines:
        with st.container(border=True):
            st.markdown(f"**{l.slot.start:%H:%M}-{l.slot.end:%H:%M}** · {escape(l.task.pet.name)}: {escape(l.task.title)}")
            st.caption(f"Why: {l.reason}")
            if l.tip:
                st.caption(f"💡 {l.tip}  _[{l.source}]_")
    for note in brief.learning:
        st.caption(f"🌱 {note}")
    with st.expander("🔍 What the agent did (reasoning trace)"):
        st.json(brief.trace)

    st.markdown("#### Ask about your pet")
    q = st.text_input("Question", placeholder="Can Rex eat grapes?")
    if q:
        ans = agent.ask(q, pet.name)
        (st.error if ans.reason == "emergency" else st.warning if ans.refused else st.success)(ans.text)
        for s in ans.sources:
            st.caption(f"Source: {s}")

    st.markdown("#### Care history")
    rows = [{"When": f"{e.timestamp:%Y-%m-%d %H:%M}", "Pet": e.pet_name, "Care": e.task_type.title(),
             "Who": "🐕 Real" if e.source == REAL else "🎮 Virtual"} for e in reversed(care_log.events[-30:])]
    st.dataframe(rows, use_container_width=True, hide_index=True) if rows else st.caption("No care logged yet.")
