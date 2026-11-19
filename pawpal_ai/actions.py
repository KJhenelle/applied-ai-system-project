"""Turn a click/drag from the browser into a care event, safely.

The scene's JavaScript is *client input*: it is validated here exactly like any other user input, so a
malformed or tampered message can only ever be ignored, never crash the app or write a bad event.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime

from .care_log import REAL, VIRTUAL, CareEvent, CareLog

log = logging.getLogger("pawpal.actions")

ACTION_TO_CARE = {"feed": "feeding", "play": "enrichment", "walk": "walk", "groom": "grooming", "meds": "meds"}
CARE_TO_NEED = {"feeding": "belly", "enrichment": "fun", "walk": "fun", "grooming": "clean"}
VERB = {"feed": "Fed", "play": "Played with", "walk": "Walked", "groom": "Groomed", "meds": "Gave meds to"}


@dataclass(frozen=True)
class ActionResult:
    ok: bool
    message: str = ""
    event: CareEvent | None = None


def handle_action(log_: CareLog, pet_name: str, raw: object, now: datetime) -> ActionResult:
    """Validate `raw` ({"type": ..., "mode": ...}) and record the event. Never raises."""
    if not isinstance(raw, dict):
        log.warning("ignored action: not an object (%r)", type(raw).__name__)
        return ActionResult(False, "ignored")
    kind, mode = raw.get("type"), raw.get("mode")
    # isinstance first: an unhashable value (a list) must be rejected, not raise inside the `in` test.
    if not (isinstance(kind, str) and isinstance(mode, str)) or kind not in ACTION_TO_CARE or mode not in (REAL, VIRTUAL):
        log.warning("ignored action: type=%r mode=%r", kind, mode)
        return ActionResult(False, "ignored")
    if not pet_name:
        return ActionResult(False, "ignored")
    event = CareEvent(pet_name, ACTION_TO_CARE[kind], now.replace(second=0, microsecond=0), mode)
    log_.record(event)
    who = "for real" if mode == REAL else "in the game"
    log.info("action %s recorded (%s) for %s", kind, mode, pet_name)
    return ActionResult(True, f"{VERB[kind]} {pet_name} {who}", event)
