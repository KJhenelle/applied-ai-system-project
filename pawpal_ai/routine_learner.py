"""Learn a pet's typical daily routine from its real care history.

Deliberately statistical (median time-of-day + spread) rather than a black box: every
number can be explained to the owner, and confidence is honest about small samples.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time
from statistics import median, pstdev

from .care_log import REAL, CareEvent

MIN_EVENTS = 3          # below this we report "still learning" and do not influence the plan
FULL_CONFIDENCE_N = 10  # sample size at which the sample-size factor saturates
SPREAD_LIMIT_MIN = 120  # a std-dev this large means "no real routine" -> consistency 0


@dataclass(frozen=True)
class RoutinePattern:
    pet_name: str
    task_type: str
    typical_minute: int  # minutes after midnight
    spread_minutes: int
    n_events: int
    confidence: float

    @property
    def learned(self) -> bool:
        return self.n_events >= MIN_EVENTS

    @property
    def typical_time(self) -> time:
        return time(self.typical_minute // 60, self.typical_minute % 60)


def _minute_of_day(ts: datetime) -> int:
    return ts.hour * 60 + ts.minute


def _circular_median(minutes: list[int]) -> int:
    """Median that is safe around midnight (a 23:50 and a 00:10 meal are 20 min apart)."""
    if max(minutes) - min(minutes) > 12 * 60:
        minutes = [m if m >= 12 * 60 else m + 24 * 60 for m in minutes]
    return int(median(minutes)) % (24 * 60)


def learn_routine(events: list[CareEvent], pet_name: str) -> list[RoutinePattern]:
    """One pattern per task type, built from *real* events only (virtual play is not evidence)."""
    by_type: dict[str, list[int]] = {}
    for e in events:
        if e.pet_name.lower() == pet_name.lower() and e.source == REAL:
            by_type.setdefault(e.task_type, []).append(_minute_of_day(e.timestamp))
    patterns = []
    for task_type, minutes in sorted(by_type.items()):
        # Several events per day of one type (two meals) would blur into one noisy pattern, so
        # cluster by half-day first.
        for cluster in _split_clusters(minutes):
            patterns.append(_pattern(pet_name, task_type, cluster))
    return patterns


def _split_clusters(minutes: list[int]) -> list[list[int]]:
    """Split a type's times into groups separated by gaps > 3h (breakfast vs dinner)."""
    ordered = sorted(minutes)
    clusters, current = [], [ordered[0]]
    for m in ordered[1:]:
        if m - current[-1] > 180:
            clusters.append(current)
            current = []
        current.append(m)
    clusters.append(current)
    # drop one-off outliers (a single stray event is not a routine)
    big = [c for c in clusters if len(c) >= MIN_EVENTS]
    return big or [max(clusters, key=len)]


def _pattern(pet_name: str, task_type: str, minutes: list[int]) -> RoutinePattern:
    n = len(minutes)
    typical = _circular_median(minutes)
    shifted = [((m - typical + 720) % 1440) - 720 for m in minutes]
    spread = round(pstdev(shifted)) if n > 1 else SPREAD_LIMIT_MIN
    size_factor = min(1.0, n / FULL_CONFIDENCE_N)
    consistency = max(0.0, 1 - spread / SPREAD_LIMIT_MIN)
    return RoutinePattern(pet_name, task_type, typical, spread, n, round(size_factor * consistency, 2))


def reliable(patterns: list[RoutinePattern], threshold: float = 0.5) -> list[RoutinePattern]:
    return [p for p in patterns if p.learned and p.confidence >= threshold]
