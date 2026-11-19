"""End-to-end demo: python demo.py  (fixed clock + seeded data, so output is reproducible)."""
from __future__ import annotations

import argparse
import logging
from datetime import datetime
from pathlib import Path

from pawpal_ai.agent import Briefing, CareAgent
from pawpal_ai.care_log import REAL, CareEvent
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


if __name__ == "__main__":
    main()
