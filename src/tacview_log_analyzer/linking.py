from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

from .models import Action, EventRecord, ObjectInfo
from .parser import has_pilot


@dataclass(slots=True)
class Shot:
    event: EventRecord
    time: float
    weapon_id: Optional[int]
    weapon_name: str
    weapon_type: str
    shooter_id: Optional[int]
    shooter_pilot: str
    locked_target_id: Optional[int]
    # For bombs with Occurrences>1, allow multiple hits to consume one shot
    remaining_occurrences: int = 1


@dataclass(slots=True)
class Hit:
    event: EventRecord
    time: float
    weapon_id: Optional[int]
    target_id: Optional[int]
    shooter_id_from_parent: Optional[int]
    shooter_pilot: str


@dataclass(slots=True)
class Kill:
    event: EventRecord
    time: float
    target_id: Optional[int]
    killer_pilot: str


@dataclass(slots=True)
class Chain:
    shot: Shot
    hit: Optional[Hit] = None
    kill: Optional[Kill] = None
    method: str = "deterministic"  # or "heuristic" later
    shooter_consistent: bool = True
    # Additional kills attributed to area-effect (e.g., bomb) beyond primary kill
    extra_kills: list[Kill] = field(default_factory=list)
    # Interception tracking for A-G weapons shot down by enemy missiles
    intercepted: bool = False
    interceptor_name: Optional[str] = None
    interception_time: Optional[float] = None


def _mk_shot(e: EventRecord) -> Optional[Shot]:
    if e.action != Action.HAS_FIRED or not e.primary or not has_pilot(e.primary):
        return None
    weapon_name = (e.secondary.name if e.secondary and e.secondary.name else "Unknown").strip()
    weapon_type = (e.secondary.type if e.secondary and e.secondary.type else "").strip()
    weapon_id = e.secondary.id if e.secondary else None
    shooter_pilot = (e.primary.pilot or "").strip()
    locked_target_id = e.locked_object.id if e.locked_object else None
    occ = e.occurrences if e.occurrences and e.occurrences > 0 else 1
    return Shot(
        event=e,
        time=e.time,
        weapon_id=weapon_id,
        weapon_name=weapon_name,
        weapon_type=weapon_type,
        shooter_id=e.primary.id if e.primary else None,
        shooter_pilot=shooter_pilot,
        locked_target_id=locked_target_id,
        remaining_occurrences=occ,
    )


def _mk_hit(e: EventRecord) -> Optional[Hit]:
    if e.action != Action.HAS_BEEN_HIT_BY or not e.parent_object or not has_pilot(e.parent_object):
        return None
    weapon_id = e.secondary.id if e.secondary else None
    target_id = e.primary.id if e.primary else None
    shooter_id = e.parent_object.id if e.parent_object else None
    shooter_pilot = (e.parent_object.pilot or "").strip() if e.parent_object else ""
    return Hit(
        event=e,
        time=e.time,
        weapon_id=weapon_id,
        target_id=target_id,
        shooter_id_from_parent=shooter_id,
        shooter_pilot=shooter_pilot,
    )


def _mk_kill(e: EventRecord) -> Optional[Kill]:
    if e.action != Action.HAS_BEEN_DESTROYED or not e.secondary or not has_pilot(e.secondary):
        return None
    target_id = e.primary.id if e.primary else None
    killer_pilot = (e.secondary.pilot or "").strip()
    return Kill(event=e, time=e.time, target_id=target_id, killer_pilot=killer_pilot)


@dataclass(slots=True) 
class Interception:
    """Represents an A-G weapon being intercepted by enemy missiles."""
    event: EventRecord
    time: float
    weapon_id: Optional[int]  # ID of intercepted A-G weapon
    interceptor_name: str  # Name of intercepting missile/system
    pilot: str  # Pilot who fired the intercepted weapon


def _mk_interception(e: EventRecord) -> Optional[Interception]:
    """Detect A-G weapon interceptions.
    
    Pattern: HasBeenHitBy event where:
    - PrimaryObject: Enemy missile (interceptor) 
    - SecondaryObject: A-G weapon (AGM, GBU, etc.)
    - ParentObject: Aircraft with pilot (who fired the A-G weapon)
    """
    if (e.action != Action.HAS_BEEN_HIT_BY or 
        not e.primary or not e.secondary or not e.parent_object or
        not has_pilot(e.parent_object)):
        return None
    
    # Check if secondary object (the weapon being hit) is an A-G weapon type
    weapon_name = (e.secondary.name or "").upper()
    weapon_type = (e.secondary.type or "").lower()
    
    # A-G weapon indicators (bombs, missiles targeting ground)
    ag_weapon_names = {"AGM", "GBU", "JDAM", "JSOW", "SDB", "HARM", "HELLFIRE"}
    is_ag_weapon = (weapon_type == "missile" and 
                   any(ag_name in weapon_name for ag_name in ag_weapon_names))
    
    # Check if primary (interceptor) is an enemy missile
    interceptor_type = (e.primary.type or "").lower()  
    interceptor_coalition = (e.primary.coalition or "").strip()
    weapon_coalition = (e.secondary.coalition or "").strip()
    
    is_enemy_interceptor = (interceptor_type == "missile" and 
                          interceptor_coalition != weapon_coalition and
                          interceptor_coalition and weapon_coalition)
    
    if is_ag_weapon and is_enemy_interceptor:
        return Interception(
            event=e,
            time=e.time,
            weapon_id=e.secondary.id,
            interceptor_name=e.primary.name or "Unknown",
            pilot=(e.parent_object.pilot or "").strip()
        )
    
    return None


def extract_shots_hits_kills(events: List[EventRecord]):
    shots: List[Shot] = []
    hits: List[Hit] = []
    kills: List[Kill] = []
    interceptions: List[Interception] = []
    for e in events:
        s = _mk_shot(e)
        if s:
            shots.append(s)
        h = _mk_hit(e)
        if h:
            hits.append(h)
        k = _mk_kill(e)
        if k:
            kills.append(k)
        i = _mk_interception(e)
        if i:
            interceptions.append(i)
        # Note: removed continue statements to allow events to be classified as multiple types
    # sort by time to enable deterministic nearest-previous search
    shots.sort(key=lambda x: x.time)
    hits.sort(key=lambda x: x.time)
    kills.sort(key=lambda x: x.time)
    interceptions.sort(key=lambda x: x.time)
    return shots, hits, kills, interceptions


def link_events_deterministic(
    events: List[EventRecord],
    consume: bool = True,
    *,
    hit_kill_time_tolerance: float = 0.25,
) -> Tuple[List[Chain], List[Shot], List[Hit], List[Kill]]:
    """Link events deterministically using weapon_id and target_id.

    - Shot→Hit: join on weapon_id, nearest prior shot if multiple (usually unique).
    - Hit→Kill: for each kill, pick the most recent prior hit for the same target_id.
    - If consume is True, linked shots/hits/kills are removed from leftovers.
    - shooter_consistent is set False when hit.parent_object.id != shot.primary.id.
    """

    shots, hits, kills, interceptions = extract_shots_hits_kills(events)

    # Index shots by weapon_id for quick lookup
    shots_by_weapon: Dict[int, List[Shot]] = {}
    for s in shots:
        if s.weapon_id is not None:
            shots_by_weapon.setdefault(s.weapon_id, []).append(s)

    # Sort each weapon list by time
    for lst in shots_by_weapon.values():
        lst.sort(key=lambda x: x.time)

    # Track consumption
    consumed_shots: set[int] = set()  # by index in 'shots'
    consumed_hits: set[int] = set()
    consumed_kills: set[int] = set()

    # Build preliminary chains by linking Hit to Shot using weapon_id
    chains: List[Chain] = []
    hit_to_chain_idx: Dict[int, int] = {}

    for h_idx, h in enumerate(hits):
        if h.weapon_id is None:
            continue
        candidates = shots_by_weapon.get(h.weapon_id)
        if not candidates:
            continue
        # pick the nearest prior shot
        chosen: Optional[Shot] = None
        for s in candidates:
            if s.time <= h.time:
                chosen = s
            else:
                break
        if chosen is None:
            continue
        # find shot index for consumption
        s_idx = shots.index(chosen)
        consistent = (h.shooter_id_from_parent == chosen.shooter_id)
        chain = Chain(shot=chosen, hit=h, method="deterministic", shooter_consistent=bool(consistent))
        chains.append(chain)
        hit_to_chain_idx[h_idx] = len(chains) - 1
        if consume:
            consumed_shots.add(s_idx)
            consumed_hits.add(h_idx)

    # Link Kill to the most recent prior Hit for same target_id
    # Build index: target_id -> list of (hit_index)
    hits_by_target: Dict[int, List[int]] = {}
    for idx, h in enumerate(hits):
        if h.target_id is not None:
            hits_by_target.setdefault(h.target_id, []).append(idx)
    for lst in hits_by_target.values():
        lst.sort(key=lambda i: hits[i].time)

    for k_idx, k in enumerate(kills):
        if k.target_id is None:
            continue
        candidate_hit_indices = hits_by_target.get(k.target_id)
        if not candidate_hit_indices:
            continue
        chosen_hit_idx: Optional[int] = None
        for idx in candidate_hit_indices:
            if hits[idx].time <= k.time + hit_kill_time_tolerance:
                chosen_hit_idx = idx
            else:
                break
        if chosen_hit_idx is None:
            continue
        # Attach to existing chain if that hit is already part of one; otherwise create a chain if we can find its shot
        chain_idx = hit_to_chain_idx.get(chosen_hit_idx)
        if chain_idx is not None:
            chains[chain_idx].kill = k
        else:
            # Try to find a shot for this hit via weapon_id (non-consuming fallback inside deterministic scope)
            h = hits[chosen_hit_idx]
            chosen_shot: Optional[Shot] = None
            if h.weapon_id is not None:
                for s in shots_by_weapon.get(h.weapon_id, []):
                    if s.time <= h.time:
                        chosen_shot = s
                    else:
                        break
            if chosen_shot is not None:
                consistent = (h.shooter_id_from_parent == chosen_shot.shooter_id)
                chains.append(Chain(shot=chosen_shot, hit=h, kill=k, shooter_consistent=bool(consistent)))
                # mark consumption if needed
                if consume:
                    consumed_shots.add(shots.index(chosen_shot))
                    consumed_hits.add(chosen_hit_idx)
                    consumed_kills.add(k_idx)
            else:
                # Without a shot, we skip creating partial chain to keep deterministic policy strict
                continue
        if consume:
            consumed_kills.add(k_idx)

    # Compute leftovers
    leftover_shots = [s for i, s in enumerate(shots) if i not in consumed_shots]
    leftover_hits = [h for i, h in enumerate(hits) if i not in consumed_hits]
    leftover_kills = [k for i, k in enumerate(kills) if i not in consumed_kills]

    return chains, leftover_shots, leftover_hits, leftover_kills


def render_chains(chains: List[Chain]) -> List[str]:
    lines: List[str] = []
    for c in chains:
        pilot = c.shot.shooter_pilot
        wname = c.shot.weapon_name
        wid = c.shot.weapon_id
        tgt = c.hit.target_id if c.hit else None
        # Friendly fire detection by coalition comparison
        # Hits: compare target primary (victim) vs shooter's parent coalition on HasBeenHitBy
        friendly_hit = False
        if c.hit:
            tgt_coal = (c.hit.event.primary.coalition or "").strip().lower() if c.hit.event.primary and c.hit.event.primary.coalition else ""
            shooter_parent = (c.hit.event.parent_object.coalition or "").strip().lower() if c.hit.event.parent_object and c.hit.event.parent_object.coalition else ""
            friendly_hit = bool(tgt_coal and shooter_parent and tgt_coal == shooter_parent)
        # Kills: compare kill primary (victim) vs kill secondary (attacker)
        friendly_kill = False
        if c.kill:
            kprim = (c.kill.event.primary.coalition or "").strip().lower() if c.kill.event.primary and c.kill.event.primary.coalition else ""
            ksec = (c.kill.event.secondary.coalition or "").strip().lower() if c.kill.event.secondary and c.kill.event.secondary.coalition else ""
            friendly_kill = bool(kprim and ksec and kprim == ksec)
        friendly = friendly_hit or friendly_kill
        parts = [
            f"Pilot={pilot}",
            f"Weapon={wname}",
            f"WeaponID={wid}",
            f"ShotT={c.shot.time:.2f}",
        ]
        if c.hit:
            parts += [f"HitT={c.hit.time:.2f}", f"TargetID={tgt}"]
        if c.kill:
            parts += [f"KillT={c.kill.time:.2f}"]
        if not c.shooter_consistent:
            parts += ["ShooterMismatch"]
        if friendly:
            parts += ["FriendlyFire"]
        lines.append("Chain: " + ", ".join(parts))
    return lines


def render_leftovers(
    leftover_shots: List[Shot],
    leftover_hits: List[Hit],
    leftover_kills: List[Kill],
    *,
    limit: int = 20,
    exclude_shot_types: Optional[List[str]] = None,
    shots_label: str = "Unlinked Shots",
) -> List[str]:
    lines: List[str] = []
    # Optionally filter shots by weapon_type exclusion list
    filtered_shots = leftover_shots
    if exclude_shot_types:
        excl = {t.lower() for t in exclude_shot_types}
        filtered_shots = [s for s in leftover_shots if (s.weapon_type or "").lower() not in excl]

    if filtered_shots:
        lines.append(f"{shots_label}: {len(filtered_shots)}")
        show_n = len(filtered_shots) if limit == 0 else min(limit, len(filtered_shots))
        for s in filtered_shots[:show_n]:  # cap output
            lines.append(
                f"  Shot: Pilot={s.shooter_pilot}, Weapon={s.weapon_name}, WeaponID={s.weapon_id}, T={s.time:.2f}"
            )
        if limit != 0 and len(filtered_shots) > limit:
            lines.append(f"  ... and {len(filtered_shots) - limit} more")
    if leftover_hits:
        lines.append(f"Unlinked Hits: {len(leftover_hits)}")
        show_n = len(leftover_hits) if limit == 0 else min(limit, len(leftover_hits))
        for h in leftover_hits[:show_n]:
            lines.append(
                f"  Hit: Pilot={h.shooter_pilot}, WeaponID={h.weapon_id}, TargetID={h.target_id}, T={h.time:.2f}"
            )
        if limit != 0 and len(leftover_hits) > limit:
            lines.append(f"  ... and {len(leftover_hits) - limit} more")
    if leftover_kills:
        lines.append(f"Unlinked Kills: {len(leftover_kills)}")
        show_n = len(leftover_kills) if limit == 0 else min(limit, len(leftover_kills))
        for k in leftover_kills[:show_n]:
            lines.append(f"  Kill: KillerPilot={k.killer_pilot}, TargetID={k.target_id}, T={k.time:.2f}")
        if limit != 0 and len(leftover_kills) > limit:
            lines.append(f"  ... and {len(leftover_kills) - limit} more")
    return lines


def link_events_heuristic(
    events: List[EventRecord],
    *,
    fired_hit_window: float = 60.0,
    prefer_locked_target: bool = True,
    hit_kill_time_tolerance: float = 0.25,
) -> Tuple[List[Chain], List[Shot], List[Hit], List[Kill]]:
    """Heuristic linking for cases without reliable weapon_id (e.g., bombs/ripples).

    Strategy:
    - Build shots/hits/kills (human-filtered) and start from leftovers that deterministic pass would keep.
    - For each Hit with missing or non-unique weapon_id, find candidate Shots by same pilot within a time window
      before the hit; if prefer_locked_target and shot.locked_target_id == hit.target_id, prioritize those.
    - Consume from Shot.remaining_occurrences so a single HasFired with Occurrences=N can link up to N hits.
    - Then link Kill to the most recent prior hit for the same target as in deterministic pass.
    - Mark method="heuristic".
    """

    shots, hits, kills, interceptions = extract_shots_hits_kills(events)

    # Index shots per pilot for quick time-based search
    shots_by_pilot: Dict[str, List[Shot]] = {}
    for s in shots:
        shots_by_pilot.setdefault(s.shooter_pilot, []).append(s)
    for lst in shots_by_pilot.values():
        lst.sort(key=lambda x: x.time)

    # Track consumption
    consumed_shots: Dict[int, int] = {}  # index -> remaining after links (for info)
    consumed_hits: set[int] = set()
    consumed_kills: set[int] = set()

    chains: List[Chain] = []
    hit_to_chain_idx: Dict[int, int] = {}

    # Link Hit to Shot heuristically
    for h_idx, h in enumerate(hits):
        # Skip if weapon_id present - that should be handled by deterministic
        # But allow bombs (Type==Bomb) to be heuristically matched even if ID exists (IDs may be unreliable)
        is_bomb = False
        if h.event.secondary and h.event.secondary.type:
            is_bomb = h.event.secondary.type.lower() == "bomb"

        if h.weapon_id is not None and not is_bomb:
            continue
        pilot = h.shooter_pilot
        cand = shots_by_pilot.get(pilot, [])
        if not cand:
            continue
        # Choose candidates within window before hit
        window_cands = [s for s in cand if 0 <= h.time - s.time <= fired_hit_window and s.remaining_occurrences > 0]
        if not window_cands:
            continue
        best: Optional[Shot] = None
        # Prefer locked target matches if enabled
        if prefer_locked_target and h.target_id is not None:
            locked_matches = [s for s in window_cands if s.locked_target_id == h.target_id]
            if locked_matches:
                # nearest in time
                best = max(locked_matches, key=lambda s: s.time)
        if best is None:
            # fallback: nearest prior in time
            best = max(window_cands, key=lambda s: s.time)
        if best is None:
            continue
        # form chain and consume one occurrence
        c = Chain(shot=best, hit=h, method="heuristic")
        chains.append(c)
        hit_to_chain_idx[h_idx] = len(chains) - 1
        best.remaining_occurrences -= 1
        consumed_shots[shots.index(best)] = best.remaining_occurrences
        consumed_hits.add(h_idx)

    # Link Kill via target as before
    hits_by_target: Dict[int, List[int]] = {}
    for idx, h in enumerate(hits):
        if h.target_id is not None:
            hits_by_target.setdefault(h.target_id, []).append(idx)
    for lst in hits_by_target.values():
        lst.sort(key=lambda i: hits[i].time)

    for k_idx, k in enumerate(kills):
        if k.target_id is None:
            continue
        idxs = hits_by_target.get(k.target_id)
        if not idxs:
            continue
        chosen_hit_idx: Optional[int] = None
        for idx in idxs:
            # Allow small tolerance: sometimes kill is logged slightly before/after hit
            if hits[idx].time <= k.time + hit_kill_time_tolerance:
                chosen_hit_idx = idx
            else:
                break
        if chosen_hit_idx is None:
            continue
        chain_idx = hit_to_chain_idx.get(chosen_hit_idx)
        if chain_idx is not None:
            chains[chain_idx].kill = k
            consumed_kills.add(k_idx)

    # Compute leftovers: shots with remaining_occurrences>0 are considered leftover
    leftover_shots = [s for s in shots if s.remaining_occurrences > 0]
    leftover_hits = [h for i, h in enumerate(hits) if i not in consumed_hits]
    leftover_kills = [k for i, k in enumerate(kills) if i not in consumed_kills]
    return chains, leftover_shots, leftover_hits, leftover_kills


def link_events_combined(
    events: List[EventRecord],
    *,
    hit_kill_time_tolerance: float = 0.25,
    fired_hit_window: float = 60.0,
    prefer_locked_target: bool = True,
) -> Tuple[List[Chain], List[Shot], List[Hit], List[Kill]]:
    """Run deterministic linking first, then heuristic on leftovers, merge results.

    - Deterministic pass consumes exact matches (weapon_id/target).
    - Heuristic pass then tries to link remaining events (e.g., bombs/ripples).
    - Returns all chains and final leftovers.
    """

    # First pass: deterministic with consumption
    d_chains, d_left_shots, d_left_hits, d_left_kills = link_events_deterministic(
        events, consume=True, hit_kill_time_tolerance=hit_kill_time_tolerance
    )

    # Build a synthetic list of events from leftovers for heuristic pass
    # Easier: just run heuristic on full events and allow it to skip deterministic cases by logic;
    # but to avoid double-linking, we can filter out hits that were already part of deterministic chains.
    # Compute times/ids of linked deterministic hits to exclude them.
    linked_hit_ids = {id(c.hit.event) for c in d_chains if c.hit is not None}

    # Filter events: keep only those hits not already linked deterministically
    # Shots/Kills can stay; heuristic will only link remaining hits, and we won't mutate deterministic chains.
    filtered_events: List[EventRecord] = []
    for e in events:
        if e.action.name == Action.HAS_BEEN_HIT_BY.name:
            # check if this exact EventRecord was already used
            if id(e) in linked_hit_ids:
                continue
        filtered_events.append(e)

    h_chains, _h_left_shots, _h_left_hits, _h_left_kills = link_events_heuristic(
        filtered_events,
        fired_hit_window=fired_hit_window,
    prefer_locked_target=prefer_locked_target,
    hit_kill_time_tolerance=hit_kill_time_tolerance,
    )

    # Merge chains; deterministic first, then heuristic
    all_chains = d_chains + h_chains

    # Compute final leftovers based on events not used by any chain
    shots_all, hits_all, kills_all, interceptions_all = extract_shots_hits_kills(events)
    used_shot_ids = {id(c.shot.event) for c in all_chains if c.shot is not None}
    used_hit_ids = {id(c.hit.event) for c in all_chains if c.hit is not None}
    used_kill_ids = {id(c.kill.event) for c in all_chains if c.kill is not None}

    final_left_shots = [s for s in shots_all if id(s.event) not in used_shot_ids]
    final_left_hits = [h for h in hits_all if id(h.event) not in used_hit_ids]
    final_left_kills = [k for k in kills_all if id(k.event) not in used_kill_ids]

    # --- Area-effect extra kill attribution (bomb / precision weapon splash) ---
    # Extended rules:
    #  - Consider shots with weapon_type == 'bomb' OR weapon_name containing tokens typical for precision A-G munitions
    #    (JDAM, GBU, SDB) as area-effect capable.
    #  - Allow a small time tolerance (e.g., <= 0.15s) between primary kill time and secondary destroys.
    #  - Use haversine distance threshold (default ~120m) instead of simple degree box for proximity.
    #  - Skip events already linked as primary kills.
    from math import asin, cos, radians, sin, sqrt

    area_tokens = ["gbu", "jdam", "sdb", "agm"]
    time_tol = 0.15  # seconds
    dist_m_threshold = 120.0  # meters

    def _is_area_effect_chain(c: Chain) -> bool:
        wt = (c.shot.weapon_type or "").lower()
        wn = (c.shot.weapon_name or "").lower()
        if wt == "bomb":
            return True
        return any(tok in wn for tok in area_tokens)

    def _haversine_m(lat1, lon1, lat2, lon2):
        # Earth radius meters
        R = 6371000.0
        dlat = radians(lat2 - lat1)
        dlon = radians(lon2 - lon1)
        a = sin(dlat/2)**2 + cos(radians(lat1))*cos(radians(lat2))*sin(dlon/2)**2
        cang = 2 * asin(min(1.0, sqrt(a)))
        return R * cang

    # Pre-collect raw destroy events (including those without pilot in secondary)
    destroy_events: List[EventRecord] = [e for e in events if e.action == Action.HAS_BEEN_DESTROYED]
    # Simple proximity checker in lat/long degrees (rough)
    def _near(e1: EventRecord, e2: EventRecord) -> bool:
        if not e1.location or not e2.location:
            return False
        d = _haversine_m(e1.location.latitude, e1.location.longitude, e2.location.latitude, e2.location.longitude)
        return d <= dist_m_threshold

    kill_event_ids_used = {id(c.kill.event) for c in all_chains if c.kill is not None}
    for c in all_chains:
        if not _is_area_effect_chain(c) or c.kill is None:
            continue
        base_kill_evt = c.kill.event
        base_time = base_kill_evt.time
        # gather other destroys within time tolerance & proximity
        for e in destroy_events:
            if e is base_kill_evt:
                continue
            if abs(e.time - base_time) > time_tol:
                continue
            if not _near(base_kill_evt, e):
                continue
            # avoid re-attributing kills already linked via other chains' primary kill
            if id(e) in kill_event_ids_used:
                continue
            # fabricate a Kill object referencing same shooter pilot (if available) or empty
            kp = c.shot.shooter_pilot
            extra = Kill(event=e, time=e.time, target_id=e.primary.id if e.primary else None, killer_pilot=kp)
            c.extra_kills.append(extra)
            kill_event_ids_used.add(id(e))

    # Process interceptions - link intercepted A-G weapons to existing chains
    cleared_hit_event_ids = _process_interceptions(all_chains, interceptions_all)
    
    # Recalculate final leftovers AFTER interception processing
    # Include cleared hit events as "used" to prevent them from appearing in misses
    used_shot_ids = {id(c.shot.event) for c in all_chains if c.shot is not None}
    used_hit_ids = {id(c.hit.event) for c in all_chains if c.hit is not None} | cleared_hit_event_ids
    used_kill_ids = {id(c.kill.event) for c in all_chains if c.kill is not None}
    
    final_left_shots = [s for s in shots_all if id(s.event) not in used_shot_ids]
    final_left_hits = [h for h in hits_all if id(h.event) not in used_hit_ids]
    final_left_kills = [k for k in kills_all if id(k.event) not in used_kill_ids]

    return all_chains, final_left_shots, final_left_hits, final_left_kills


def _process_interceptions(chains: List[Chain], interceptions: List[Interception]) -> set[int]:
    """Link interceptions to existing chains based on weapon ID and pilot matching.
    Returns set of hit event IDs that were cleared due to interception."""
    # Index chains by weapon ID for quick lookup
    chains_by_weapon: Dict[int, List[Chain]] = {}
    for c in chains:
        if c.shot.weapon_id is not None:
            chains_by_weapon.setdefault(c.shot.weapon_id, []).append(c)
    
    # Track hit events that get cleared due to interception
    cleared_hit_event_ids: set[int] = set()
    
    # For each interception, find matching chain and mark as intercepted
    for interception in interceptions:
        if interception.weapon_id is None:
            continue
        
        matching_chains = chains_by_weapon.get(interception.weapon_id, [])
        for chain in matching_chains:
            # Verify pilot matches and interception time is after shot time
            if (chain.shot.shooter_pilot == interception.pilot and
                interception.time >= chain.shot.time):
                
                # Mark chain as intercepted and clear hit/kill data
                # The weapon was destroyed before reaching its intended target
                chain.intercepted = True
                chain.interceptor_name = interception.interceptor_name
                chain.interception_time = interception.time
                
                # Track the hit event ID before clearing it
                if chain.hit is not None:
                    cleared_hit_event_ids.add(id(chain.hit.event))
                
                # Clear hit and kill data since weapon never reached intended target
                chain.hit = None
                chain.kill = None
                chain.extra_kills = []  # No splash damage if intercepted before impact
                
                # Only link to first matching chain to avoid duplicates
                break
    
    return cleared_hit_event_ids


