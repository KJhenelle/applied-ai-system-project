"""End-to-end demo: python demo.py  (fixed clock + seeded data, so output is reproducible)."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from pawpal_ai.agent import Briefing, CareAgent
from pawpal_ai.care_log import REAL, VIRTUAL, CareEvent
from pawpal_ai.companion import Companion, compute_synced_state
from pawpal_ai.demo_data import build_demo

NOW = datetime(2026, 11, 18, 7, 10)


def show_briefing(b: Briefing) -> None:
    print(b.greeting)
    for l in b.lines:
        print(f"  {l.slot.start:%H:%M}-{l.slot.end:%H:%M}  {l.task.pet.name}: {l.task.title}")
        print(f"      why: {l.reason}")
        if l.tip:
            print(f"      tip: {l.tip}  [{l.source}]")
    for label, items in (("done", b.done), ("nudge", b.nudges), ("learning", b.learning), ("ALERT", b.alerts)):
        for i in items:
            print(f"  [{label}] {i}")
    print(f"  {b.companion_status}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--trace", default="logs/agent_trace.jsonl")
    args = parser.parse_args()
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(filename="logs/pawpal.log", level=logging.INFO,
                        format="%(asctime)s %(name)s %(levelname)s %(message)s")

    owner, availability, care_log = build_demo(NOW)
    agent = CareAgent(owner, availability, care_log, style="realistic", trace_path=Path(args.trace))

    print("=== INPUT 1: 07:10 briefing, realistic companion ===")
    show_briefing(agent.run(NOW))

    print("\n=== INPUT 2: same day 09:40, robotic companion; Rex's breakfast logged, walk missed ===")
    later = datetime(2026, 11, 18, 9, 40)
    care_log.record(CareEvent("Rex", "feeding", datetime(2026, 11, 18, 7, 33), REAL))
    agent.style = "robotic"
    show_briefing(agent.run(later))

    print("\n=== INPUT 3: questions (RAG + guardrails) ===")
    for q, pet in [("Can Rex eat grapes?", "Rex"),
                   ("How often should Mia have play sessions?", "Mia"),
                   ("What is the best cryptocurrency?", "Rex"),
                   ("Rex ate chocolate an hour ago", "Rex"),
                   ("   ", "Rex")]:
        a = agent.ask(q, pet)
        print(f"Q: {q!r}")
        print(f"A: {a.text}")
        print(f"   sources={a.sources} refused={a.refused} reason={a.reason or '-'}")

    print("\n=== INPUT 4: real/virtual sync (companion can't be happier than the real pet) ===")
    sync_demo(care_log)


def show_sync(care_log, when, label) -> None:
    synced = compute_synced_state(care_log, "Rex", when)
    voice = Companion("Rex", "dog", "robotic")
    f = lambda c: f"belly {c.belly:>3}% fun {c.fun:>3}% clean {c.clean:>3}% -> {c.mood}"
    print(f"[{label}]")
    print(f"  game-only companion : {f(synced.virtual)}")
    print(f"  real Rex            : {f(synced.real)}")
    print(f"  SHOWN companion     : {f(synced.shown)}")
    print(f"  {voice.sync_note(synced) or '(no real-care limit)'}")


def sync_demo(care_log) -> None:
    when = datetime(2026, 11, 18, 9, 40)
    for kind in ("feeding", "walk", "grooming"):  # plenty of game play, no real walk or grooming
        care_log.record(CareEvent("Rex", kind, when, VIRTUAL))
    show_sync(care_log, when, "09:40 lots of virtual play, Rex not walked yet")
    care_log.record(CareEvent("Rex", "walk", datetime(2026, 11, 18, 9, 45), REAL))
    show_sync(care_log, datetime(2026, 11, 18, 9, 46), "09:46 after a REAL walk is logged")


if __name__ == "__main__":
    main()
