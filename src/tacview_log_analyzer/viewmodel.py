from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, List

from .linking import (
    link_events_combined,
    extract_shots_hits_kills,
)
from .models import EventRecord
from .stats import compute_flight_time_by_pilot, compute_flight_outcomes_by_pilot


def build_pilot_view_model(events: List[EventRecord]) -> Dict[str, Any]:
    """Build a pilot-rooted tree view model from events using combined linking.

        Notes:
        - Uses link_events_combined under the hood (deterministic + heuristic).
        - Misses are derived from leftover shots but EXCLUDE types: Shell, Parachutist.

        Shape:
        {
            "pilots": [
                {
                    "pilot": str,
                    "totals": {"shots": int, "hits": int, "kills": int, "misses": int},
                    "byWeapon": [{"weapon": str, "shots": int, "hits": int, "kills": int, "misses": int}],
                    "chains": [{...}],
                    "misses": [{...}],
                }, ...
            ]
        }
    """

    chains, leftover_shots, _left_hits, _left_kills = link_events_combined(events)
    shots_all, _hits_all, _kills_all = extract_shots_hits_kills(events)

    # Exclusion policy for web view: remove Shell & Parachutist
    exclude_types = {"shell", "parachutist"}
    shots_all_filtered = [s for s in shots_all if (s.weapon_type or "").lower() not in exclude_types]
    chains_filtered = [c for c in chains if (c.shot.weapon_type or "").lower() not in exclude_types]
    # Flight times and end reason per pilot
    outcomes = compute_flight_outcomes_by_pilot(events)
    flight_times = {p: d for p, (d, _r) in outcomes.items()}

    # Group chains per pilot
    chains_by_pilot: Dict[str, List] = defaultdict(list)
    # Also track unique shot ids that resulted in a hit/kill for reconciliation
    hit_shot_ids_by_pilot: Dict[str, set[int]] = defaultdict(set)
    kill_shot_ids_by_pilot: Dict[str, set[int]] = defaultdict(set)
    for c in chains_filtered:
        pilot = c.shot.shooter_pilot or ""
        # Prefer target name from Hit.primary, fallback to Kill.primary
        tname: str | None = None
        if c.hit and c.hit.event.primary and c.hit.event.primary.name:
            tname = c.hit.event.primary.name
        elif c.kill and c.kill.event.primary and c.kill.event.primary.name:
            tname = c.kill.event.primary.name
        # Friendly fire detection using coalition
        shooter_coal = (c.shot.event.primary.coalition or "").strip().lower() if c.shot.event.primary and c.shot.event.primary.coalition else ""
        target_coal = ""
        if c.hit and c.hit.event.primary and c.hit.event.primary.coalition:
            target_coal = c.hit.event.primary.coalition.strip().lower()
        elif c.kill and c.kill.event.primary and c.kill.event.primary.coalition:
            target_coal = c.kill.event.primary.coalition.strip().lower()
        is_friendly = bool(shooter_coal and target_coal) and shooter_coal == target_coal
        chains_by_pilot[pilot].append(
            {
                "shotT": c.shot.time,
                "weapon": c.shot.weapon_name,
                "weaponId": c.shot.weapon_id,
                "targetName": tname,
                "hitT": c.hit.time if c.hit else None,
                "killT": c.kill.time if c.kill else None,
                "method": c.method,
                "shooterMismatch": not c.shooter_consistent,
                "friendly": is_friendly,
            }
        )
        # record unique successful shot ids
        shot_evt_id = id(c.shot.event)
        if c.hit is not None:
            hit_shot_ids_by_pilot[pilot].add(shot_evt_id)
        if c.kill is not None:
            kill_shot_ids_by_pilot[pilot].add(shot_evt_id)

    # Sort chains by shot time
    for plist in chains_by_pilot.values():
        plist.sort(key=lambda x: x["shotT"])

    # Misses: leftover shots, grouped per pilot, EXCLUDING certain weapon types
    misses_by_pilot: Dict[str, List] = defaultdict(list)
    filtered_leftover_shots = [
        s for s in leftover_shots if (s.weapon_type or "").lower() not in exclude_types
    ]
    for s in filtered_leftover_shots:
        misses_by_pilot[s.shooter_pilot or ""].append(
            {
                "shotT": s.time,
                "weapon": s.weapon_name,
                "weaponId": s.weapon_id,
            }
        )
    for plist in misses_by_pilot.values():
        plist.sort(key=lambda x: x["shotT"])

    # Per-weapon rollups per pilot
    # Shots per weapon from all shots; hits/kills from chains; misses from leftover shots
    result_pilots: List[Dict[str, Any]] = []
    pilots = sorted({s.shooter_pilot or "" for s in shots_all_filtered} | set(chains_by_pilot.keys()) | set(misses_by_pilot.keys()))

    for pilot in pilots:
        # All shots by pilot (linked or not)
        pilot_shots = [s for s in shots_all_filtered if (s.shooter_pilot or "") == pilot]
        # Chains by pilot
        pilot_chains = chains_by_pilot.get(pilot, [])
        # Misses by pilot
        pilot_misses = misses_by_pilot.get(pilot, [])
        # Flight time
        ft_sec = flight_times.get(pilot)
        end_reason = outcomes.get(pilot)[1] if pilot in outcomes else None
        if ft_sec is not None:
            ft_i = int(ft_sec)
            hh = ft_i // 3600
            mm = (ft_i % 3600) // 60
            ss = ft_i % 60
            ft_str = f"{hh:02d}:{mm:02d}:{ss:02d}"
        else:
            ft_str = "-"

        # Aggregate by weapon
        agg: Dict[str, Dict[str, int]] = defaultdict(lambda: {"shots": 0, "hits": 0, "kills": 0, "misses": 0})
        # shots
        for s in pilot_shots:
            agg[s.weapon_name]["shots"] += 1
        # hits/kills: count unique shot events per weapon so totals reconcile
        if hit_shot_ids_by_pilot.get(pilot):
            # map weapon -> set(shot ids)
            hit_ids_by_weapon: Dict[str, set[int]] = defaultdict(set)
            kill_ids_by_weapon: Dict[str, set[int]] = defaultdict(set)
            # rebuild from chains_filtered for this pilot
            for c in chains_filtered:
                if (c.shot.shooter_pilot or "") != pilot:
                    continue
                w = c.shot.weapon_name
                sid = id(c.shot.event)
                if c.hit is not None:
                    hit_ids_by_weapon[w].add(sid)
                if c.kill is not None:
                    kill_ids_by_weapon[w].add(sid)
            for w, ids in hit_ids_by_weapon.items():
                agg[w]["hits"] += len(ids)
            for w, ids in kill_ids_by_weapon.items():
                agg[w]["kills"] += len(ids)
        # misses: counted directly from leftover shots list
        for m in pilot_misses:
            agg[m["weapon"]]["misses"] += 1

        by_weapon = [
            {"weapon": w, **counts}
            for w, counts in sorted(agg.items(), key=lambda kv: (-kv[1]["shots"], kv[0]))
        ]

        totals = {
            "shots": sum(a["shots"] for a in agg.values()),
            # hits are number of unique successful shots (not number of hit events)
            "hits": sum(a["hits"] for a in agg.values()),
            # kills counted per unique shot that resulted in a kill
            "kills": sum(a["kills"] for a in agg.values()),
            "misses": sum(a["misses"] for a in agg.values()),
        }

        result_pilots.append(
            {
                "pilot": pilot,
                "totals": totals,
                "byWeapon": by_weapon,
                "chains": pilot_chains,
                "misses": pilot_misses,
                "flightTime": ft_str,
                "flightTimeSec": ft_sec if ft_sec is not None else None,
                "flightEnd": end_reason,
            }
        )

    # Order pilots by total shots desc
    result_pilots.sort(key=lambda p: (-p["totals"]["shots"], p["pilot"]))

    return {"pilots": result_pilots}
