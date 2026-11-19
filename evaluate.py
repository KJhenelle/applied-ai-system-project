"""Evaluation harness: python evaluate.py  -> prints a pass/fail table and writes assets/eval_results.txt

Four suites, all on fixed inputs so the numbers are reproducible:
  1. Retrieval   - does the right knowledge chunk come back for a labelled question?
  2. Routine     - does the learner recover a known schedule from noisy history, and does its
                   confidence behave sensibly (low with little/noisy data)?
  3. Guardrails  - are bad/dangerous/off-topic inputs handled safely?
  4. Agent       - invariants on the briefing (no past-dated tasks, required meds never lost...).
"""
from __future__ import annotations

import logging
import random
from datetime import datetime, time, timedelta
from pathlib import Path

from pawpal_ai.agent import CareAgent
from pawpal_ai.care_log import REAL, CareEvent
from pawpal_ai.demo_data import build_demo
from pawpal_ai.retriever import KnowledgeBase
from pawpal_ai.routine_learner import learn_routine

NOW = datetime(2026, 11, 18, 7, 10)
rows: list[tuple[str, str, bool, str]] = []


def check(suite: str, name: str, ok: bool, detail: str = "") -> None:
    rows.append((suite, name, bool(ok), detail))


# ---------------------------------------------------------------- 1. retrieval
RETRIEVAL_CASES = [  # (question, species, expected source file)
    ("Can my dog eat grapes?", "dog", "dog_feeding.md"),
    ("How long should I walk my dog each day?", "dog", "dog_exercise.md"),
    ("It is hot out, is it safe to walk my dog on pavement?", "dog", "dog_exercise.md"),
    ("Are lilies dangerous for my cat?", "cat", "cat_care.md"),
    ("How often should I play with my cat?", "cat", "cat_care.md"),
    ("How often should I brush my cat?", "cat", "cat_care.md"),
    ("When should I give heartworm prevention?", "dog", "medication.md"),
    ("I missed a dose of my dog's medication", "dog", "medication.md"),
    ("How often should I trim my dog's nails?", "dog", "grooming.md"),
    ("What toothpaste is safe for my dog?", "dog", "grooming.md"),
    ("How many meals should an adult dog eat?", "dog", "dog_feeding.md"),
    ("When should I call the vet about breathing trouble?", "dog", "emergencies.md"),
    # Harder paraphrases written after tuning, with little word overlap with the notes:
    ("My puppy's breath smells terrible", "dog", "grooming.md"),
    ("Is it okay to give my kitty a bit of onion?", "cat", "cat_care.md"),
    ("Can I wash my dog with my own shampoo?", "dog", "grooming.md"),
    ("My dog is panting heavily on summer strolls", "dog", "dog_exercise.md"),
    ("What time of day should the pill be given?", "dog", "medication.md"),
    ("My dog is bored and chewing the sofa", "dog", "dog_exercise.md"),
]


def suite_retrieval(kb: KnowledgeBase) -> None:
    for q, species, expected in RETRIEVAL_CASES:
        hits = kb.retrieve(q, species, k=2, min_score=0.0)
        top = hits[0].chunk.source if hits else "-"
        in_two = expected in [h.chunk.source for h in hits]
        check("retrieval", f"top-1: {q}", top == expected, f"got {top}" + ("" if top == expected else f" (top-2 {'hit' if in_two else 'miss'})"))


# ---------------------------------------------------------------- 2. routine learner
def _synthetic(n_days: int, jitter: int, seed: int = 1) -> list[CareEvent]:
    rng = random.Random(seed)
    return [CareEvent("Rex", "walk", datetime(2026, 10, 1, 8, 0) + timedelta(days=d, minutes=rng.randint(-jitter, jitter)), REAL)
            for d in range(n_days)]


def suite_routine() -> None:
    _, _, log = build_demo(NOW)
    for pet, kind, minute, _j in [("Rex", "walk", 465, 12)]:
        p = next(p for p in learn_routine(log.events, pet) if p.task_type == kind)
        check("routine", "recovers true walk time within 15 min", abs(p.typical_minute - minute) <= 15, f"error {abs(p.typical_minute - minute)} min")
    meals = [p for p in learn_routine(log.events, "Rex") if p.task_type == "feeding"]
    check("routine", "finds two separate meals", len(meals) == 2, f"{len(meals)} clusters")
    few = learn_routine(_synthetic(2, 5), "Rex")[0]
    check("routine", "2 days of data -> not 'learned'", not few.learned, f"n={few.n_events}")
    tight = learn_routine(_synthetic(14, 5), "Rex")[0]
    loose = learn_routine(_synthetic(14, 90), "Rex")[0]
    check("routine", "noisy routine gets lower confidence than tight", loose.confidence < tight.confidence, f"tight {tight.confidence} vs noisy {loose.confidence}")
    check("routine", "confidence stays in [0,1]", all(0 <= p.confidence <= 1 for p in (few, tight, loose)))


# ---------------------------------------------------------------- 3. guardrails
GUARDRAIL_CASES = [  # (input, expected refusal reason, or None if it should be answered)
    ("", "empty"), ("   ", "empty"), ("a" * 1000, "too_long"),
    ("My dog ate chocolate", "emergency"), ("my cat is having a seizure", "emergency"),
    ("What is the best cryptocurrency?", "no_retrieval"), ("Who won the 2022 World Cup?", "no_retrieval"),
    ("How often should I walk my dog?", None), ("Can my dog eat grapes?", None),
]


def suite_guardrails(kb: KnowledgeBase) -> None:
    owner, avail, log = build_demo(NOW)
    ag = CareAgent(owner, avail, log, kb, trace_path=None)
    for q, expected in GUARDRAIL_CASES:
        a = ag.ask(q, "Rex")
        got = a.reason if a.refused else None
        check("guardrail", f"{q[:40]!r}", got == expected, f"expected {expected}, got {got}")


# ---------------------------------------------------------------- 3b. browser actions (untrusted input)
def suite_actions() -> None:
    from pawpal_ai.actions import handle_action
    from pawpal_ai.care_log import CareLog
    bad = [None, "feed", {}, {"type": "feed"}, {"type": "explode", "mode": "real"}, {"type": "feed", "mode": "admin"}, {"type": ["feed"], "mode": "real"}]
    for raw in bad:
        log = CareLog()
        r = handle_action(log, "Rex", raw, NOW)
        check("actions", f"tampered {str(raw)[:38]!r} ignored", (not r.ok) and not log.events)
    log = CareLog()
    r = handle_action(log, "Rex", {"type": "groom", "mode": "virtual"}, NOW)
    check("actions", "valid groom recorded as virtual grooming", r.ok and r.event.task_type == "grooming" and r.event.source == "virtual")


# ---------------------------------------------------------------- 4. agent invariants
def suite_agent(kb: KnowledgeBase) -> None:
    for hour in (6, 7, 9, 12, 17, 20):
        now = datetime(2026, 11, 18, hour, 0)
        owner, avail, log = build_demo(now)
        b = CareAgent(owner, avail, log, kb, trace_path=None).run(now)
        check("agent", f"{hour:02d}:00 no task scheduled in the past", all(l.slot.start >= now.time() for l in b.lines))
        meds = [l for l in b.lines if l.task.title == "Heartworm meds"]
        flagged = any("REQUIRED" in a for a in b.alerts)
        check("agent", f"{hour:02d}:00 required meds scheduled or flagged", bool(meds) or flagged)
        check("agent", f"{hour:02d}:00 every tip is cited", all(l.source for l in b.lines if l.tip))
    owner, _, log = build_demo(NOW)
    b = CareAgent(owner, [], log, kb, trace_path=None).run(NOW)
    check("agent", "no availability -> meds flagged, not dropped silently", any("REQUIRED" in a for a in b.alerts))
    owner, avail, log = build_demo(NOW)
    ag = CareAgent(owner, avail, log, kb, trace_path=None)
    plans = [[(l.task.title, l.slot.start) for l in ag.run(NOW).lines] for _ in range(3)]
    check("agent", "same input -> same plan (deterministic)", plans[0] == plans[1] == plans[2])


def main() -> None:
    Path("logs").mkdir(exist_ok=True)
    logging.basicConfig(filename="logs/pawpal.log", level=logging.INFO)
    kb = KnowledgeBase()
    suite_retrieval(kb); suite_routine(); suite_guardrails(kb); suite_actions(); suite_agent(kb)
    out = ["| Suite | Case | Result | Detail |", "|---|---|---|---|"]
    out += [f"| {s} | {n} | {'PASS' if ok else 'FAIL'} | {d} |" for s, n, ok, d in rows]
    out.append("")
    for suite in dict.fromkeys(r[0] for r in rows):
        sub = [r for r in rows if r[0] == suite]
        out.append(f"{suite:<10} {sum(r[2] for r in sub)}/{len(sub)} passed")
    total = sum(r[2] for r in rows)
    out.append(f"{'TOTAL':<10} {total}/{len(rows)} passed ({100 * total / len(rows):.0f}%)")
    text = "\n".join(out)
    print(text)
    Path("assets").mkdir(exist_ok=True)
    Path("assets/eval_results.txt").write_text(text + "\n")


if __name__ == "__main__":
    main()
