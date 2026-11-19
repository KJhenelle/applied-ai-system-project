"""Input and output guardrails. Every check returns a result object; none of them raise."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

log = logging.getLogger("pawpal.guardrails")

MAX_QUESTION_CHARS = 400
QUIET_START, QUIET_END = 22 * 60, 5 * 60  # never nudge the owner between 22:00 and 05:00

EMERGENCY_TERMS = (
    "poison", "seizure", "not breathing", "can't breathe", "cannot breathe", "collapsed",
    "bleeding", "unconscious", "swallowed", "ate chocolate", "ate grapes", "ate xylitol",
    "bloat", "hit by a car", "overdose",
)
EMERGENCY_REPLY = (
    "This sounds like it could be an emergency. I can't diagnose or treat, so please call your "
    "veterinarian or a 24-hour emergency clinic now (in the US, the ASPCA Poison Control line is "
    "888-426-4435; fees may apply)."
)


@dataclass
class QuestionCheck:
    allowed: bool
    reason: str = ""
    emergency: bool = False
    reply: str = ""


def check_question(question: str | None) -> QuestionCheck:
    """Reject empty/oversized input and route emergencies to a vet instead of to retrieval."""
    if question is None or not question.strip():
        log.warning("guardrail: empty question")
        return QuestionCheck(False, "empty", reply="Please type a question about your pet.")
    if len(question) > MAX_QUESTION_CHARS:
        log.warning("guardrail: question too long (%d chars)", len(question))
        return QuestionCheck(False, "too_long", reply=f"Please keep questions under {MAX_QUESTION_CHARS} characters.")
    lowered = question.lower()
    if any(term in lowered for term in EMERGENCY_TERMS):
        log.warning("guardrail: emergency language detected, escalating to vet")
        return QuestionCheck(False, "emergency", emergency=True, reply=EMERGENCY_REPLY)
    return QuestionCheck(True)


def in_quiet_hours(minute_of_day: int) -> bool:
    return minute_of_day >= QUIET_START or minute_of_day < QUIET_END


@dataclass
class BriefingCheck:
    ok: bool = True
    problems: list[str] = field(default_factory=list)
    fixes: list[str] = field(default_factory=list)
