"""Saving and loading the household, and exporting the daily plan.

Everything lives in a data directory (default ./data, override with PAWPAL_DATA_DIR). A corrupt or
unreadable file never crashes the app: it is set aside as *.corrupt and the app starts fresh.
"""
from __future__ import annotations

import json
import logging
import os
import re
import zlib
from datetime import date, datetime, time, timezone
from pathlib import Path

from pawpal_system import DailyPlan, Frequency, Owner, Pet, Priority, Task, TaskType, TimeSlot

log = logging.getLogger("pawpal.storage")


def data_dir() -> Path:
    return Path(os.environ.get("PAWPAL_DATA_DIR", "data"))


def household_path() -> Path:
    return data_dir() / "household.json"


def care_log_path() -> Path:
    return data_dir() / "care_log.json"


# ---------------------------------------------------------------- household
def household_to_dict(owner: Owner, availability: list[TimeSlot]) -> dict:
    return {"version": 1, **owner._to_dict(),
            "availability": [{"start": s.start.isoformat(), "end": s.end.isoformat()} for s in availability]}


def _slot(d: dict | None) -> TimeSlot | None:
    return None if d is None else TimeSlot(time.fromisoformat(d["start"]), time.fromisoformat(d["end"]))


def household_from_dict(d: dict) -> tuple[Owner, list[TimeSlot]]:
    owner = Owner(str(d["name"]), str(d.get("email", "")))
    for p in d.get("pets", []):
        pet = Pet(str(p["name"]), str(p["species"]), int(p["age"]), str(p.get("notes", "")))
        owner.add_pet(pet)
        for t in p.get("tasks", []):
            pet.add_task(Task(
                title=str(t["title"]), pet=pet, type=TaskType(t["type"]), duration_minutes=int(t["duration_minutes"]),
                priority=Priority[t["priority"]], frequency=Frequency(t["frequency"]), preferred_time=_slot(t.get("preferred_time")),
                due_date=date.fromisoformat(t["due_date"]) if t.get("due_date") else None,
                required=bool(t.get("required", False)), is_completed=bool(t.get("is_completed", False))))
    return owner, [_slot(s) for s in d.get("availability", [])]


def save_household(owner: Owner, availability: list[TimeSlot], path: Path | None = None) -> str:
    """Write atomically (temp file then rename) so a crash mid-save cannot corrupt the saved household.
    Returns the JSON text written, so callers can skip saving when nothing changed."""
    path = path or household_path()
    text = json.dumps(household_to_dict(owner, availability), indent=2, sort_keys=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(path)
    return text


def load_household(path: Path | None = None) -> tuple[Owner, list[TimeSlot]] | None:
    path = path or household_path()
    if not path.exists():
        return None
    try:
        return household_from_dict(json.loads(path.read_text()))
    except (ValueError, KeyError, TypeError) as exc:
        log.error("household file unreadable (%s); setting it aside", exc)
        path.replace(path.with_suffix(".corrupt"))
        return None


# ---------------------------------------------------------------- plan export
def plan_to_text(plan: DailyPlan) -> str:
    lines = [f"PawPal+ plan for {plan.date:%A %B %d, %Y}", ""]
    for i in plan.items:
        lines.append(f"{i.slot.start:%H:%M}-{i.slot.end:%H:%M}  {i.pet.name}: {i.task.title}  ({i.reason})")
    for t in plan.unscheduled:
        lines.append(f"NOT SCHEDULED{' (REQUIRED)' if t.required else ''}: {t.pet.name}: {t.title}")
    if not plan.items:
        lines.append("Nothing scheduled.")
    return "\n".join(lines) + "\n"


def _ics_escape(text: str) -> str:
    return re.sub(r"([\;,])", r"\\\1", text).replace("\r", "").replace("\n", "\\n")


def _fold(line: str) -> str:
    """RFC 5545: lines longer than 75 octets are folded with CRLF + space."""
    out, cur = [], line
    while len(cur.encode()) > 74:
        cut = 74
        while len(cur[:cut].encode()) > 74:
            cut -= 1
        out.append(cur[:cut]); cur = " " + cur[cut:]
    out.append(cur)
    return "\r\n".join(out)


def plan_to_ics(plan: DailyPlan, now: datetime | None = None) -> str:
    """A calendar file (floating local times) that opens in Apple/Google/Outlook calendars."""
    stamp = (now or datetime.now(timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//PawPal+ Companion//EN", "CALSCALE:GREGORIAN"]
    for n, i in enumerate(plan.items):
        start = datetime.combine(plan.date, i.slot.start).strftime("%Y%m%dT%H%M%S")
        end = datetime.combine(plan.date, i.slot.end).strftime("%Y%m%dT%H%M%S")
        lines += ["BEGIN:VEVENT", f"UID:pawpal-{plan.date:%Y%m%d}-{n}-{zlib.crc32(f'{i.pet.name}|{i.task.title}'.encode()):08x}@pawpal.local",
                  f"DTSTAMP:{stamp}", f"DTSTART:{start}", f"DTEND:{end}",
                  f"SUMMARY:{_ics_escape(f'{i.pet.name}: {i.task.title}')}", f"DESCRIPTION:{_ics_escape(i.reason)}", "END:VEVENT"]
    lines.append("END:VCALENDAR")
    return "\r\n".join(_fold(l) for l in lines) + "\r\n"
