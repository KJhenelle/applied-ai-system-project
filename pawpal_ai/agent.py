"""The care agent: observe -> learn -> plan -> retrieve -> check, with a saved reasoning trace.

The pieces are not decoration. The learned routine changes *when* tasks are scheduled, the
retrieved guidance is attached to (and gates) each recommendation, and the checker can remove
or flag output before the owner ever sees it.
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from datetime import date, datetime, time
from pathlib import Path

from pawpal_system import DailyPlan, Owner, Scheduler, Task, TimeSlot

from . import guardrails
from .care_log import REAL, CareLog
from .companion import Companion, compute_synced_state
from .retriever import KnowledgeBase, tokenize
from .routine_learner import RoutinePattern, learn_routine, reliable

log = logging.getLogger("pawpal.agent")
TRACE_PATH = Path("logs/agent_trace.jsonl")
TOPIC_QUERY = {
    "walk": "daily walks exercise", "feeding": "feeding schedule meals", "meds": "giving medication on schedule",
    "enrichment": "play enrichment", "grooming": "grooming brushing",
}
MIN_TIP_SCORE = 0.2
ASK_MIN_SCORE = 0.15  # stricter than tips: an off-topic question must get "I don't know", not a stretch


@dataclass
class PlanLine:
    task: Task
    slot: TimeSlot
    reason: str
    tip: str = ""
    source: str = ""


@dataclass
class Briefing:
    day: date
    greeting: str
    lines: list[PlanLine] = field(default_factory=list)
    done: list[str] = field(default_factory=list)
    nudges: list[str] = field(default_factory=list)
    learning: list[str] = field(default_factory=list)
    alerts: list[str] = field(default_factory=list)
    patterns: list[RoutinePattern] = field(default_factory=list)
    trace: list[dict] = field(default_factory=list)
    companion_status: str = ""
    all_done: str = ""


@dataclass
class Answer:
    text: str
    sources: list[str] = field(default_factory=list)
    refused: bool = False
    reason: str = ""


def _fmt(minute: int) -> str:
    return f"{minute // 60:02d}:{minute % 60:02d}"


class CareAgent:
    def __init__(self, owner: Owner, availability: list[TimeSlot], care_log: CareLog,
                 kb: KnowledgeBase | None = None, style: str = "realistic",
                 trace_path: Path | None = TRACE_PATH) -> None:
        self.owner, self.availability, self.care_log = owner, availability, care_log
        self.kb = kb or KnowledgeBase()
        self.style = style
        self.trace_path = trace_path

    # ---------------------------------------------------------------- briefing
    def run(self, now: datetime) -> Briefing:
        day = now.date()
        trace: list[dict] = []

        def step(name: str, **detail) -> None:
            trace.append({"step": name, **detail})
            log.info("agent step=%s %s", name, detail)

        voice = Companion(self.owner.name or "your pet", "dog", self.style)
        briefing = Briefing(day, voice.say("greeting"), trace=trace)

        # 1. OBSERVE - match today's real events to pending tasks so finished work is not re-planned.
        pending = self.owner.get_all_tasks(day)
        todays = [e for e in self.care_log.query(source=REAL, since=datetime.combine(day, time.min), until=now)]
        unmatched = list(todays)
        remaining: list[Task] = []
        for task in pending:
            match = next((e for e in unmatched if e.pet_name == task.pet.name and e.task_type == task.type.value), None)
            if match:
                unmatched.remove(match)
                briefing.done.append(f"{task.pet.name}: {task.title} at {match.timestamp:%H:%M}")
            else:
                remaining.append(task)
        step("observe", pending=len(pending), already_done=len(briefing.done), remaining=len(remaining))

        # 2. LEARN - per-pet routine from real history only.
        hints: dict[int, tuple[TimeSlot, str]] = {}
        for pet in self.owner.pets:
            patterns = learn_routine(self.care_log.query(pet.name, REAL, until=now), pet.name)
            briefing.patterns += patterns
            # A routine slot already satisfied today (breakfast logged) must not be reused for dinner.
            good = [p for p in reliable(patterns) if not self._satisfied(p, todays)]
            used: set[int] = set()
            for task in sorted(remaining, key=lambda t: t.priority.value * -1):
                if task.pet is not pet or task.preferred_time is not None:
                    continue
                cands = [p for p in good if p.task_type == task.type.value and id(p) not in used]
                if not cands:
                    continue
                p = min(cands, key=lambda c: c.typical_minute)
                used.add(id(p))
                half = max(15, p.spread_minutes)
                lo, hi = max(0, p.typical_minute - half), min(24 * 60 - 1, p.typical_minute + half + task.duration_minutes)
                hints[id(task)] = (
                    TimeSlot(time(lo // 60, lo % 60), time(hi // 60, hi % 60)),
                    f"learned routine: usually ~{_fmt(p.typical_minute)} (±{p.spread_minutes} min, confidence {p.confidence})",
                )
            for p in patterns:
                if not p.learned:
                    briefing.learning.append(Companion(pet.name, pet.species, self.style).say("learning", task=p.task_type, n=p.n_events))
            if not patterns:
                briefing.learning.append(Companion(pet.name, pet.species, self.style).say("learning", task="care", n=0))
        step("learn", patterns=[f"{p.pet_name}/{p.task_type}@{_fmt(p.typical_minute)} n={p.n_events} conf={p.confidence}" for p in briefing.patterns],
             hints_applied=len(hints))

        # 3. PLAN - the scheduler now sees learned windows for tasks that had no preferred time.
        scheduler = Scheduler(self._owner_view(remaining), self._future_windows(now))
        plan = scheduler.schedule_tasks(day, hints)
        step("plan", scheduled=len(plan.items), unscheduled=len(plan.unscheduled))

        # 4. RETRIEVE - attach cited guidance to every line.
        for item in plan.items:
            tip, src = self._tip_for(item.task)
            briefing.lines.append(PlanLine(item.task, item.slot, item.reason, tip, src))
        step("retrieve", tips=sum(1 for l in briefing.lines if l.tip))

        # 5. CHECK - validate output, repair what we can, flag the rest.
        self._check(briefing, plan, remaining)
        step("check", alerts=briefing.alerts)

        # Nudges come last because they depend on the final state of the day.
        briefing.nudges = self._nudges(now, briefing.patterns, todays)
        if not briefing.lines and not briefing.nudges and not briefing.alerts:
            briefing.all_done = Companion(self.owner.name, "dog", self.style).say("all_done")
        first = self.owner.pets[0] if self.owner.pets else None
        if first:
            synced = compute_synced_state(self.care_log, first.name, now)
            voice = Companion(first.name, first.species, self.style)
            briefing.companion_status = voice.describe_state(synced.shown)
            note = voice.sync_note(synced)
            if note:
                briefing.companion_status += "\n  " + note
        self._write_trace(day, trace)
        return briefing

    def _future_windows(self, now: datetime) -> list[TimeSlot]:
        """Availability with the past removed: a briefing must never schedule care before `now`."""
        out = []
        for w in self.availability:
            start = max(w.start, now.time().replace(second=0, microsecond=0))
            if start < w.end:
                out.append(TimeSlot(start, w.end))
        return out

    @staticmethod
    def _satisfied(p: RoutinePattern, todays) -> bool:
        return any(e.pet_name == p.pet_name and e.task_type == p.task_type
                   and abs(e.timestamp.hour * 60 + e.timestamp.minute - p.typical_minute) <= max(90, 2 * p.spread_minutes)
                   for e in todays)

    def _owner_view(self, tasks: list[Task]) -> Owner:
        """A throwaway owner holding only the remaining tasks, so the real owner is never mutated."""
        view = Owner(self.owner.name, self.owner.email)
        by_pet: dict[int, list[Task]] = {}
        for t in tasks:
            by_pet.setdefault(id(t.pet), []).append(t)
        for pet in self.owner.pets:
            if id(pet) in by_pet:
                shadow = type(pet)(pet.name, pet.species, pet.age, pet.notes)
                shadow.tasks = by_pet[id(pet)]  # same Task objects, so id() hints still match
                view.pets.append(shadow)
        return view

    def _tip_for(self, task: Task) -> tuple[str, str]:
        query = f"{TOPIC_QUERY[task.type.value]} {task.pet.species}"
        hits = self.kb.retrieve(query, task.pet.species, k=1, min_score=MIN_TIP_SCORE)
        if not hits:
            return "", ""
        sentence = re.split(r"(?<=[.!?])\s+", hits[0].chunk.text)[0]
        return sentence, f"{hits[0].chunk.source} > {hits[0].chunk.heading}"

    def _check(self, b: Briefing, plan: DailyPlan, remaining: list[Task]) -> None:
        # Rule 1: a required task (meds) must be scheduled or loudly flagged, never silently lost.
        scheduled = {id(l.task) for l in b.lines}
        for task in remaining:
            if task.required and id(task) not in scheduled:
                msg = f"REQUIRED task not scheduled: {task.pet.name}: {task.title}. Make time for it or call your vet."
                b.alerts.append(msg)
                log.error(msg)
        # Rule 2: never schedule care in quiet hours; flag instead of silently shifting.
        for l in b.lines:
            if guardrails.in_quiet_hours(l.slot.start.hour * 60 + l.slot.start.minute):
                b.alerts.append(f"{l.task.pet.name}: {l.task.title} lands in quiet hours ({l.slot.start:%H:%M}); check availability.")
        # Rule 3: no advice without a citation.
        for l in b.lines:
            if l.tip and not l.source:
                l.tip = ""
                b.alerts.append("Removed uncited tip.")
        for task in plan.unscheduled:
            if not task.required:
                b.alerts.append(f"Could not fit: {task.pet.name}: {task.title} ({task.duration_minutes} min).")

    def _nudges(self, now: datetime, patterns: list[RoutinePattern], todays) -> list[str]:
        nudges = []
        minute_now = now.hour * 60 + now.minute
        for p in reliable(patterns):
            voice = Companion(p.pet_name, self._species(p.pet_name), self.style)
            if self._satisfied(p, todays):
                continue
            slack = max(30, 2 * p.spread_minutes)
            kw = dict(task=p.task_type, time=_fmt(p.typical_minute))
            if minute_now > p.typical_minute + slack:
                nudges.append(voice.say("overdue", **kw))
            elif p.typical_minute - 30 <= minute_now <= p.typical_minute + slack:
                nudges.append(voice.say("upcoming", **kw))
        return nudges

    def _species(self, pet_name: str) -> str:
        return next((p.species for p in self.owner.pets if p.name == pet_name), "dog")

    def _write_trace(self, day: date, trace: list[dict]) -> None:
        if self.trace_path is None:
            return
        try:
            self.trace_path.parent.mkdir(parents=True, exist_ok=True)
            with self.trace_path.open("a") as f:
                f.write(json.dumps({"day": day.isoformat(), "style": self.style, "trace": trace}) + "\n")
        except OSError as exc:  # logging must never take the app down
            log.warning("could not write trace: %s", exc)

    # ---------------------------------------------------------------- Q&A
    def ask(self, question: str, pet_name: str | None = None) -> Answer:
        check = guardrails.check_question(question)
        if not check.allowed:
            return Answer(check.reply, refused=True, reason=check.reason)
        species = self._species(pet_name) if pet_name else None
        # Gate on the raw question first: adding the species word below would otherwise let any
        # off-topic question match every "dogs" chunk.
        if not self.kb.retrieve(question, species, k=1, min_score=ASK_MIN_SCORE):
            hits = []
        else:
            # Owners say "Rex" while the notes say "dogs", so add the species word for ranking.
            hits = self.kb.retrieve(f"{question} {species or ''}", species, k=2, min_score=ASK_MIN_SCORE)
        if not hits:
            log.info("ask: no retrieval hit for %r", question)
            return Answer(Companion(pet_name or "your pet", species or "dog", self.style).say("no_answer"),
                          refused=True, reason="no_retrieval")
        qtokens = set(tokenize(question))
        sentences = [(s, h.chunk) for h in hits for s in re.split(r"(?<=[.!?])\s+", h.chunk.text)]
        ranked = sorted(sentences, key=lambda sc: -len(qtokens & set(tokenize(sc[0]))))
        chosen = [s for s, _ in ranked[:2]]
        sources = sorted({f"{c.source} > {c.heading}" for s, c in ranked[:2]})
        return Answer(" ".join(chosen), sources)
