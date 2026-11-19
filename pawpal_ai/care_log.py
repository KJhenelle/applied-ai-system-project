"""Append-only history of care events, for the real pet and for the virtual companion."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from pathlib import Path

REAL, VIRTUAL = "real", "virtual"
VALID_TYPES = {"walk", "feeding", "meds", "enrichment", "grooming"}


@dataclass(frozen=True)
class CareEvent:
    pet_name: str
    task_type: str
    timestamp: datetime
    source: str = REAL  # "real" = the actual animal, "virtual" = the companion game
    title: str = ""

    def __post_init__(self) -> None:
        if self.task_type not in VALID_TYPES:
            raise ValueError(f"unknown task type {self.task_type!r}")
        if self.source not in (REAL, VIRTUAL):
            raise ValueError(f"unknown source {self.source!r}")


class CareLog:
    def __init__(self, events: list[CareEvent] | None = None) -> None:
        self.events: list[CareEvent] = sorted(events or [], key=lambda e: e.timestamp)

    def record(self, event: CareEvent) -> None:
        self.events.append(event)
        self.events.sort(key=lambda e: e.timestamp)

    def query(
        self,
        pet_name: str | None = None,
        source: str | None = None,
        task_type: str | None = None,
        since: datetime | None = None,
        until: datetime | None = None,
    ) -> list[CareEvent]:
        return [
            e
            for e in self.events
            if (pet_name is None or e.pet_name.lower() == pet_name.lower())
            and (source is None or e.source == source)
            and (task_type is None or e.task_type == task_type)
            and (since is None or e.timestamp >= since)
            and (until is None or e.timestamp <= until)
        ]

    def last_n_days(self, pet_name: str, now: datetime, days: int, source: str = REAL):
        return self.query(pet_name, source, since=now - timedelta(days=days), until=now)

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        data = [{**asdict(e), "timestamp": e.timestamp.isoformat()} for e in self.events]
        path.write_text(json.dumps(data, indent=2))

    @classmethod
    def load(cls, path: str | Path) -> "CareLog":
        path = Path(path)
        if not path.exists():
            return cls()
        try:
            raw = json.loads(path.read_text())
            return cls([CareEvent(**{**r, "timestamp": datetime.fromisoformat(r["timestamp"])}) for r in raw])
        except (ValueError, KeyError, TypeError):
            # A corrupt history file must never crash the app; start fresh and keep the bad file.
            path.rename(path.with_suffix(".corrupt"))
            return cls()
