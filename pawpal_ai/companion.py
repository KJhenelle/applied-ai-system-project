"""The virtual companion: a game-style pet that mirrors how well the real pet is cared for.

Two interchangeable personas share one set of facts, so switching style changes the voice and
never the content:
  - "realistic": a warm, animal-like voice
  - "robotic":   a terse robot-dog voice that reports numbers
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .care_log import REAL, VIRTUAL, CareLog

STYLES = ("realistic", "robotic")
# need -> (task types that restore it, hours until it is fully drained)
NEEDS = {"belly": ({"feeding"}, 10), "fun": ({"walk", "enrichment"}, 12), "clean": ({"grooming"}, 72)}


# Real-pet needs drain more slowly: a real dog is fine with two meals a day and a daily walk, while
# the game pet is a toy that gets hungry in hours. Grooming is roughly weekly.
LIMIT_BELOW = 60  # a real need above this is not worth nagging about, even if it is below the game's
REAL_HOURS = {"belly": 24, "fun": 36, "clean": 168}


@dataclass(frozen=True)
class CompanionState:
    belly: int
    fun: int
    clean: int

    @property
    def mood(self) -> str:
        avg = (self.belly + self.fun + self.clean) / 3
        return "happy" if avg >= 66 else "okay" if avg >= 33 else "needy"


@dataclass(frozen=True)
class SyncedState:
    """The companion is a mirror: it can never feel better than the real pet is cared for."""

    virtual: CompanionState  # what the game interactions alone would give
    real: CompanionState     # from real care events only
    shown: CompanionState    # per-need minimum of the two; this is what the owner sees
    limited_by: tuple[str, ...]  # needs where real care, not game play, is the bottleneck


def _levels(log: CareLog, pet_name: str, now: datetime, source: str, hours: dict[str, int]) -> CompanionState:
    """Needs drain linearly since the last event from `source`; no history means fully drained."""
    levels = {}
    for need, (types, _) in NEEDS.items():
        events = [e for e in log.query(pet_name, source, until=now) if e.task_type in types]
        if not events:
            levels[need] = 0
            continue
        elapsed = (now - events[-1].timestamp).total_seconds() / 3600
        levels[need] = max(0, min(100, round(100 * (1 - elapsed / hours[need]))))
    return CompanionState(**levels)


def compute_state(log: CareLog, pet_name: str, now: datetime) -> CompanionState:
    """Virtual-only needs (game interactions)."""
    return _levels(log, pet_name, now, VIRTUAL, {n: h for n, (_, h) in NEEDS.items()})


def compute_real_state(log: CareLog, pet_name: str, now: datetime) -> CompanionState:
    """How well the *real* animal has been cared for, from real events only."""
    return _levels(log, pet_name, now, REAL, REAL_HOURS)


def compute_synced_state(log: CareLog, pet_name: str, now: datetime) -> SyncedState:
    v, r = compute_state(log, pet_name, now), compute_real_state(log, pet_name, now)
    shown = CompanionState(*(min(getattr(v, n), getattr(r, n)) for n in NEEDS))
    limited = tuple(n for n in NEEDS if getattr(r, n) < LIMIT_BELOW and getattr(r, n) < getattr(v, n))
    return SyncedState(v, r, shown, limited)


class Companion:
    def __init__(self, pet_name: str, species: str, style: str = "realistic") -> None:
        if style not in STYLES:
            raise ValueError(f"style must be one of {STYLES}")
        self.pet_name, self.species, self.style = pet_name, species, style

    @property
    def avatar(self) -> str:
        if self.style == "robotic":
            return "🤖🐕" if self.species == "dog" else "🤖🐈"
        return "🐶" if self.species == "dog" else "🐱"

    def say(self, kind: str, **kw) -> str:
        """Render one message kind in the active voice. Unknown kinds raise KeyError (a bug)."""
        return VOICES[self.style][kind].format(name=self.pet_name, **kw)

    def mood_line(self, state: CompanionState) -> str:
        return self.say(f"mood_{state.mood}")

    def sync_note(self, synced: SyncedState) -> str:
        """Empty when game play, not real care, is the limit."""
        names = {"belly": "fed", "fun": "walked or played with", "clean": "groomed"}
        if not synced.limited_by:
            return ""
        return self.say("synced", needs=" and ".join(names[n] for n in synced.limited_by))

    def describe_state(self, state: CompanionState) -> str:
        if self.style == "robotic":
            return f"STATUS {self.pet_name.upper()}-UNIT: belly {state.belly}% | fun {state.fun}% | clean {state.clean}% | mood={state.mood}"
        return f"{self.pet_name} feels {state.mood}: belly {state.belly}%, fun {state.fun}%, fresh {state.clean}%."


VOICES = {
    "realistic": {
        "greeting": "Woof! Here's what your pets need today.",
        "upcoming": "{name} usually has {task} around {time}. Almost time!",
        "overdue": "{name} is waiting for {task}. It's normally around {time}, and it hasn't happened yet today.",
        "done": "Yay! {name} had {task} at {time}. Tail wags!",
        "learning": "I'm still learning {name}'s {task} routine ({n} so far). I'll start predicting after a few more days.",
        "all_done": "Everything on the list is done. Good human, {name}!",
        "no_answer": "I don't have a trustworthy answer in my notes about that. Your vet is the best person to ask.",
        "mood_happy": "Best day ever! Tail wags for everyone!",
        "mood_okay": "I'm doing alright. A little more love and I'll be bouncing!",
        "mood_needy": "I'm feeling pretty low... please check on the real {name}.",
        "synced": "I can't feel any better until the real {name} gets {needs}. Playing with me won't fix that!",
    },
    "robotic": {
        "greeting": "BOOT COMPLETE. Daily care briefing for {name}'s pets.",
        "upcoming": "ALERT: {task} expected at {time}. T-minus under 30 min.",
        "overdue": "OVERDUE: {task} not logged. Expected {time}. Please execute.",
        "done": "LOGGED: {task} at {time}. Task closed.",
        "learning": "CALIBRATING: {task} sample size {n}. Predictions disabled until enough data.",
        "all_done": "ALL TASKS CLOSED for {name}'s pets. Standing by.",
        "no_answer": "QUERY UNRESOLVED: no reliable entry in knowledge base. Consult veterinarian.",
        "mood_happy": "ALL SYSTEMS OPTIMAL. Happiness at maximum.",
        "mood_okay": "Systems nominal. Minor care deficits detected.",
        "mood_needy": "WARNING: low power and low morale. Check real {name} now.",
        "synced": "SYNC LIMIT: unit mood capped by real {name} care deficit ({needs}). Simulated care cannot override.",
    },
}
