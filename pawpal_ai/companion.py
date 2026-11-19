"""The virtual companion: a game-style pet that mirrors how well the real pet is cared for.

Two interchangeable personas share one set of facts, so switching style changes the voice and
never the content:
  - "realistic": a warm, animal-like voice
  - "robotic":   a terse robot-dog voice that reports numbers
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from .care_log import VIRTUAL, CareLog

STYLES = ("realistic", "robotic")
# need -> (task types that restore it, hours until it is fully drained)
NEEDS = {"belly": ({"feeding"}, 10), "fun": ({"walk", "enrichment"}, 12), "clean": ({"grooming"}, 72)}


@dataclass(frozen=True)
class CompanionState:
    belly: int
    fun: int
    clean: int

    @property
    def mood(self) -> str:
        avg = (self.belly + self.fun + self.clean) / 3
        return "happy" if avg >= 66 else "okay" if avg >= 33 else "needy"


def compute_state(log: CareLog, pet_name: str, now: datetime) -> CompanionState:
    """Needs drain linearly since the last *virtual* care event; no history means fully drained."""
    levels = {}
    for need, (types, hours) in NEEDS.items():
        events = [e for e in log.query(pet_name, VIRTUAL, until=now) if e.task_type in types]
        if not events:
            levels[need] = 0
            continue
        elapsed = (now - events[-1].timestamp).total_seconds() / 3600
        levels[need] = max(0, round(100 * (1 - elapsed / hours)))
    return CompanionState(**levels)


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

    def describe_state(self, state: CompanionState) -> str:
        if self.style == "robotic":
            return f"STATUS {self.pet_name.upper()}-UNIT: belly {state.belly}% | fun {state.fun}% | clean {state.clean}% | mood={state.mood}"
        return f"{self.pet_name} feels {state.mood}: belly {state.belly}%, fun {state.fun}%, fresh {state.clean}%."


VOICES = {
    "realistic": {
        "greeting": "Woof! Good morning! Here's what your pets need today.",
        "upcoming": "{name} usually has {task} around {time}. Almost time!",
        "overdue": "{name} is waiting for {task}. It's normally around {time}, and it hasn't happened yet today.",
        "done": "Yay! {name} had {task} at {time}. Tail wags!",
        "learning": "I'm still learning {name}'s {task} routine ({n} so far). I'll start predicting after a few more days.",
        "all_done": "Everything on the list is done. Good human, {name}!",
        "no_answer": "I don't have a trustworthy answer in my notes about that. Your vet is the best person to ask.",
    },
    "robotic": {
        "greeting": "BOOT COMPLETE. Daily care briefing for {name}'s pets.",
        "upcoming": "ALERT: {task} expected at {time}. T-minus under 30 min.",
        "overdue": "OVERDUE: {task} not logged. Expected {time}. Please execute.",
        "done": "LOGGED: {task} at {time}. Task closed.",
        "learning": "CALIBRATING: {task} sample size {n}. Predictions disabled until enough data.",
        "all_done": "ALL TASKS CLOSED for {name}'s pets. Standing by.",
        "no_answer": "QUERY UNRESOLVED: no reliable entry in knowledge base. Consult veterinarian.",
    },
}
