from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Tuple, Optional, Literal

from .models import Action, EventRecord
from .parser import has_pilot


@dataclass(slots=True)
class PilotStats:
    shots: int = 0
    hits: int = 0
    kills: int = 0
    # weapon key: (weapon_name, weapon_type)
    weapon_shots: Dict[Tuple[str, str], int] = field(default_factory=dict)


def accumulate_pilot_stats(events: Iterable[EventRecord]) -> dict[str, PilotStats]:
    by_pilot: Dict[str, PilotStats] = {}

    def bucket(name: str) -> PilotStats:
        if name not in by_pilot:
            by_pilot[name] = PilotStats()
        return by_pilot[name]

    for e in events:
        if e.action == Action.HAS_FIRED and e.primary and has_pilot(e.primary):
            pstats = bucket(e.primary.pilot or "")
            pstats.shots += 1
            # weapon information from SecondaryObject (missile)
            wname = (e.secondary.name if e.secondary and e.secondary.name else "Unknown").strip()
            wtype = (e.secondary.type if e.secondary and e.secondary.type else "").strip()
            key = (wname, wtype)
            pstats.weapon_shots[key] = pstats.weapon_shots.get(key, 0) + 1
        elif e.action == Action.HAS_BEEN_HIT_BY and e.parent_object and has_pilot(e.parent_object):
            bucket(e.parent_object.pilot or "").hits += 1
        elif e.action == Action.HAS_BEEN_DESTROYED and e.secondary and has_pilot(e.secondary):
            bucket(e.secondary.pilot or "").kills += 1

    return by_pilot


def compute_flight_time_by_pilot(events: Iterable[EventRecord]) -> dict[str, float]:
    """Compute flight time (seconds) per pilot using the rules:
    - Start: first HasTakenOff event with Pilot in PrimaryObject
    - End (pick first after start): HasLanded (Primary pilot) OR HasFired with Parachutist in Secondary.type
      OR HasBeenDestroyed with Secondary pilot
    Returns pilots with start and end detected; others are omitted.
    """
    # sort by time for causal ordering
    evs = sorted(list(events), key=lambda e: e.time)
    takeoff: Dict[str, float] = {}
    end: Dict[str, float] = {}

    for e in evs:
        if e.action == Action.HAS_TAKEN_OFF and e.primary and has_pilot(e.primary):
            p = (e.primary.pilot or "").strip()
            if p and p not in takeoff:
                takeoff[p] = e.time
        elif e.action == Action.HAS_LANDED and e.primary and has_pilot(e.primary):
            p = (e.primary.pilot or "").strip()
            if p in takeoff and p not in end and e.time >= takeoff[p]:
                end[p] = e.time
        elif e.action == Action.HAS_FIRED and e.primary and has_pilot(e.primary):
            # Ejection: Secondary.type == Parachutist
            stype = (e.secondary.type if e.secondary and e.secondary.type else "").strip().lower()
            if stype == "parachutist":
                p = (e.primary.pilot or "").strip()
                if p in takeoff and p not in end and e.time >= takeoff[p]:
                    end[p] = e.time
        elif e.action == Action.HAS_BEEN_DESTROYED and e.primary and has_pilot(e.primary):
            # Shot down: destroyed entity's pilot is in PrimaryObject
            p = (e.primary.pilot or "").strip()
            if p in takeoff and p not in end and e.time >= takeoff[p]:
                end[p] = e.time

    result: Dict[str, float] = {}
    for p, t0 in takeoff.items():
        t1 = end.get(p)
        if t1 is not None and t1 >= t0:
            result[p] = t1 - t0
    return result


def compute_flight_outcomes_by_pilot(
    events: Iterable[EventRecord],
) -> dict[str, tuple[float, Literal["Landed", "Ejected", "Shot down"]]]:
    """Compute flight time and end reason per pilot.
    Returns mapping for pilots where both takeoff and an end event exist.
    End reason precedence is based on first event after takeoff among:
      - Landed: HasLanded primary pilot
      - Ejected: HasFired with Secondary.type == Parachutist
      - Shot down: HasBeenDestroyed with Secondary pilot
    """
    evs = sorted(list(events), key=lambda e: e.time)
    takeoff: Dict[str, float] = {}
    end: Dict[str, tuple[float, str]] = {}

    for e in evs:
        if e.action == Action.HAS_TAKEN_OFF and e.primary and has_pilot(e.primary):
            p = (e.primary.pilot or "").strip()
            if p and p not in takeoff:
                takeoff[p] = e.time
        elif e.action == Action.HAS_LANDED and e.primary and has_pilot(e.primary):
            p = (e.primary.pilot or "").strip()
            if p in takeoff and p not in end and e.time >= takeoff[p]:
                end[p] = (e.time, "Landed")
        elif e.action == Action.HAS_FIRED and e.primary and has_pilot(e.primary):
            stype = (e.secondary.type if e.secondary and e.secondary.type else "").strip().lower()
            if stype == "parachutist":
                p = (e.primary.pilot or "").strip()
                if p in takeoff and p not in end and e.time >= takeoff[p]:
                    end[p] = (e.time, "Ejected")
        elif e.action == Action.HAS_BEEN_DESTROYED and e.primary and has_pilot(e.primary):
            p = (e.primary.pilot or "").strip()
            if p in takeoff and p not in end and e.time >= takeoff[p]:
                end[p] = (e.time, "Shot down")

    result: Dict[str, tuple[float, Literal["Landed", "Ejected", "Shot down"]]] = {}
    for p, t0 in takeoff.items():
        e = end.get(p)
        if e is not None and e[0] >= t0:
            result[p] = (e[0] - t0, e[1])  # duration, reason
    return result


def render_pilot_stats(stats: dict[str, PilotStats], ftimes: Optional[dict[str, float]] = None) -> str:
    lines: list[str] = []
    for pilot in sorted(stats.keys(), key=lambda s: s.lower()):
        s = stats[pilot]
        if ftimes and pilot in ftimes:
            ft = int(ftimes[pilot])
            hh = ft // 3600
            mm = (ft % 3600) // 60
            ss = ft % 60
            fts = f" {hh:02d}:{mm:02d}:{ss:02d}"
        else:
            fts = ""
        lines.append(f"{pilot}: {s.shots} shots, {s.hits} hits, {s.kills} kills{fts}")
        # Pretty-print weapon breakdown, sort by count desc then name
        for (wname, wtype), count in sorted(
            s.weapon_shots.items(), key=lambda kv: (-kv[1], kv[0][0].lower())
        ):
            # type currently unused in display but retained for future special cases
            lines.append(f"  {wname}: {count} shots")
    return "\n".join(lines)
