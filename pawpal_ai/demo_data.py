"""Deterministic synthetic history so demos, tests and the eval harness are reproducible."""
from __future__ import annotations

import random
from datetime import date, datetime, time, timedelta

from pawpal_system import Frequency, Owner, Pet, Priority, Task, TaskType, TimeSlot

from .care_log import REAL, VIRTUAL, CareEvent, CareLog

# Ground truth the learner is supposed to rediscover: (pet, type, minute of day, jitter in minutes)
TRUE_ROUTINE = [
    ("Rex", "walk", 7 * 60 + 45, 12),
    ("Rex", "feeding", 7 * 60 + 30, 10),
    ("Rex", "feeding", 18 * 60, 15),
]


def build_demo(now: datetime, days: int = 14, seed: int = 7) -> tuple[Owner, list[TimeSlot], CareLog]:
    rng = random.Random(seed)
    owner = Owner("Jordan", "jordan@example.com")
    rex, mia = Pet("Rex", "dog", 3), Pet("Mia", "cat", 5)
    owner.add_pet(rex)
    owner.add_pet(mia)
    rex.add_task(Task("Morning walk", rex, TaskType.WALK, 30, Priority.MEDIUM))
    rex.add_task(Task("Breakfast", rex, TaskType.FEEDING, 10, Priority.HIGH))
    rex.add_task(Task("Dinner", rex, TaskType.FEEDING, 10, Priority.HIGH))
    rex.add_task(Task("Heartworm meds", rex, TaskType.MEDS, 5, Priority.HIGH, required=True))
    mia.add_task(Task("Wand toy play", mia, TaskType.ENRICHMENT, 15, Priority.LOW))
    availability = [TimeSlot(time(7), time(9)), TimeSlot(time(17, 30), time(19))]

    log = CareLog()
    today = now.date()
    for d in range(days, 0, -1):
        day = today - timedelta(days=d)
        for pet, kind, minute, jitter in TRUE_ROUTINE:
            m = minute + rng.randint(-jitter, jitter)
            log.record(CareEvent(pet, kind, datetime.combine(day, time(m // 60, m % 60)), REAL))
    # Rex was groomed three days ago (weekly care, so it does not drain his real wellbeing yet).
    log.record(CareEvent("Rex", "grooming", datetime.combine(today - timedelta(days=3), time(10, 0)), REAL))
    # Mia is new to the app: only two days of data, so the system must say "still learning".
    for d in (2, 1):
        log.record(CareEvent("Mia", "enrichment", datetime.combine(today - timedelta(days=d), time(17, 40)), REAL))
    # Some virtual-companion play from yesterday evening.
    log.record(CareEvent("Rex", "feeding", datetime.combine(today - timedelta(days=1), time(18, 5)), VIRTUAL))
    return owner, availability, log
