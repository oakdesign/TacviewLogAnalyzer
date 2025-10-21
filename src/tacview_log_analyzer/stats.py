from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, Literal, Optional, Tuple

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
            occ = e.occurrences if e.occurrences and e.occurrences > 0 else 1
            pstats = bucket(e.primary.pilot or "")
            pstats.shots += occ
            # weapon information from SecondaryObject (missile/bomb)
            wname = (e.secondary.name if e.secondary and e.secondary.name else "Unknown").strip()
            wtype = (e.secondary.type if e.secondary and e.secondary.type else "").strip()
            key = (wname, wtype)
            pstats.weapon_shots[key] = pstats.weapon_shots.get(key, 0) + occ
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


def determine_shot_domain(chains, shots_all):
    """Determine domain (AA/AG) for each shot using the same logic as viewmodel.py.
    
    Args:
        chains: List of Chain objects from linking module
        shots_all: List of all Shot objects
        
    Returns:
        Dict mapping shot event IDs to domain strings ('AA' or 'AG')
    """
    exclude_types = {"shell", "parachutist"}
    aa_types = {"aircraft", "helicopter"}
    weapon_ids_aa: set[int] = set()
    weapon_names_aa: set[str] = set()
    shot_domain: dict[int, str] = {}  # id(shot.event) -> 'AA' | 'AG'

    # Pass 1: classify by locked object
    for s in shots_all:
        if (s.weapon_type or "").lower() in exclude_types:
            continue
        if s.event.locked_object and s.event.locked_object.type and s.event.locked_object.type.lower() in aa_types:
            shot_domain[id(s.event)] = "AA"
            weapon_names_aa.add(s.weapon_name)
            if s.weapon_id is not None:
                weapon_ids_aa.add(s.weapon_id)

    # Pass 2: use target type from chains where not already classified
    chains_filtered = [c for c in chains if (c.shot.weapon_type or "").lower() not in exclude_types]
    for c in chains_filtered:
        sid = id(c.shot.event)
        if sid in shot_domain:
            continue
        target_type = None
        if c.hit and c.hit.event.primary and c.hit.event.primary.type:
            target_type = c.hit.event.primary.type
        elif c.kill and c.kill.event.primary and c.kill.event.primary.type:
            target_type = c.kill.event.primary.type
        if target_type and target_type.lower() in aa_types:
            shot_domain[sid] = "AA"
            weapon_names_aa.add(c.shot.weapon_name)
            if c.shot.weapon_id is not None:
                weapon_ids_aa.add(c.shot.weapon_id)

    # Pass 3: propagate weapon-based AA classification, remaining -> AG
    for s in shots_all:
        if (s.weapon_type or "").lower() in exclude_types:
            continue
        sid = id(s.event)
        if sid in shot_domain:
            continue
        # Propagate AA if weapon id OR weapon name previously classified AA
        if (s.weapon_id is not None and s.weapon_id in weapon_ids_aa) or (s.weapon_name in weapon_names_aa):
            shot_domain[sid] = "AA"
        else:
            shot_domain[sid] = "AG"

    # Ensure every filtered chain shot has domain
    for c in chains_filtered:
        sid = id(c.shot.event)
        if sid not in shot_domain:
            shot_domain[sid] = "AG"
            
    return shot_domain


def compute_aa_kills_by_target(chains, shots_all) -> Dict[str, int]:
    """Compute A-A (Air-to-Air) kills grouped by target aircraft type.
    
    Args:
        chains: List of Chain objects from linking module
        shots_all: List of all Shot objects for domain classification
        
    Returns:
        Dict mapping aircraft type names to total kill counts
    """
    # Determine A-A vs A-G domain for each shot using existing logic
    shot_domain = determine_shot_domain(chains, shots_all)
    
    # Group A-A kills by target aircraft type
    targets = {}
    for chain in chains:
        if chain.kill:
            # Check if this shot is classified as A-A
            if shot_domain.get(id(chain.shot.event), "AG") == "AA":
                # Get target aircraft type from kill event Primary (the destroyed aircraft)
                if chain.kill.event.primary:
                    target_aircraft = chain.kill.event.primary.name or "Unknown Aircraft"
                else:
                    target_aircraft = "Unknown Aircraft"
                
                # Group by aircraft type only (no individual IDs or pilot names)
                if target_aircraft not in targets:
                    targets[target_aircraft] = 0
                targets[target_aircraft] += 1
    
    return targets


def render_aa_kills_by_target(aa_kills: Dict[str, int]) -> str:
    """Render A-A kills grouped by target aircraft type in a readable format."""
    if not aa_kills:
        return "No A-A kills found."
    
    lines = ["", "A-A Kills by Target:"]
    total_kills = sum(aa_kills.values())
    lines.append(f"Total A-A kills: {total_kills}")
    lines.append("")
    
    # Sort aircraft types by kill count (descending) then name
    for aircraft_type in sorted(aa_kills.keys(), key=lambda t: (-aa_kills[t], t)):
        kill_count = aa_kills[aircraft_type]
        plural = "kills" if kill_count != 1 else "kill"
        lines.append(f"{aircraft_type}, {kill_count}, {plural}")
    
    return "\n".join(lines)
