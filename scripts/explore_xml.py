from __future__ import annotations

import sys
from collections import Counter, defaultdict
from pathlib import Path

from tacview_log_analyzer.models import Action
from tacview_log_analyzer.parser import has_pilot, parse_file


def main(argv: list[str]) -> int:
    if not argv:
        print("Usage: python scripts/explore_xml.py <file.xml>")
        return 2
    path = Path(argv[0])
    deb = parse_file(path)

    print(f"File: {path}")
    print(f"Version: {deb.version}")
    print(f"Events total: {len(deb.events)}")

    by_action = Counter(e.action for e in deb.events)
    print("By action:")
    for act, cnt in by_action.most_common():
        print(f"  {act.value}: {cnt}")

    def pct(n: int, d: int) -> str:
        return f"{(100.0*n/d):.1f}%" if d else "n/a"

    # Pilot presence per action according to your rules
    fired = [e for e in deb.events if e.action == Action.HAS_FIRED]
    hits = [e for e in deb.events if e.action == Action.HAS_BEEN_HIT_BY]
    kills = [e for e in deb.events if e.action == Action.HAS_BEEN_DESTROYED]

    fired_human = [e for e in fired if e.primary and has_pilot(e.primary)]
    hits_human = [e for e in hits if e.parent_object and has_pilot(e.parent_object)]
    kills_human = [e for e in kills if e.secondary and has_pilot(e.secondary)]

    print("Pilot presence (per your counting rules):")
    print(f"  HasFired human: {len(fired_human)}/{len(fired)} ({pct(len(fired_human), len(fired))})")
    print(f"  HasBeenHitBy human: {len(hits_human)}/{len(hits)} ({pct(len(hits_human), len(hits))})")
    print(f"  HasBeenDestroyed human: {len(kills_human)}/{len(kills)} ({pct(len(kills_human), len(kills))})")

    # Weapon ID relationships (SecondaryObject.ID)
    fired_by_missile = {}
    for e in fired_human:
        mid = e.secondary.id if e.secondary else None
        if mid is not None:
            fired_by_missile[mid] = e

    hit_with_missile = [e for e in hits_human if e.secondary and e.secondary.id is not None]
    hit_has_fired_match = sum(1 for e in hit_with_missile if e.secondary.id in fired_by_missile)
    print("Weapon ID linkage:")
    print(f"  Fired (human) with weapon id: {len(fired_by_missile)}")
    print(f"  Hit (human) with weapon id: {len(hit_with_missile)}")
    print(f"  Hits linked to a prior Fired by weapon id: {hit_has_fired_match}/{len(hit_with_missile)}")

    # Parent relationships consistency checks
    parent_mismatch = 0
    checked = 0
    for e in hit_with_missile:
        checked += 1
        shooter_id_from_hit_parent = e.parent_object.id if e.parent_object else None
        mid = e.secondary.id if e.secondary else None
        fe = fired_by_missile.get(mid)
        shooter_id_from_fired_primary = fe.primary.id if fe and fe.primary else None
        if shooter_id_from_hit_parent != shooter_id_from_fired_primary:
            parent_mismatch += 1
    print("Shooter consistency across Fired->Hit:")
    print(f"  Checked: {checked}, mismatches: {parent_mismatch}")

    # Weapon distribution from HasFired
    weapon_counts = Counter()
    for e in fired_human:
        wname = (e.secondary.name if e.secondary and e.secondary.name else "Unknown").strip()
        weapon_counts[wname] += 1
    print("Top weapons (HasFired by human):")
    for name, cnt in weapon_counts.most_common(10):
        print(f"  {name}: {cnt}")

    # Destroyed linkage heuristic: target id continuity
    # For each kill, try to find a preceding hit with same target (PrimaryObject in hit == PrimaryObject in kill)
    kills_linked_via_target = 0
    for k in kills_human:
        kid = k.primary.id if k.primary else None  # destroyed target id
        kt = k.time
        # find the last hit on the same target before kill time
        prev_hits = [h for h in hits if h.primary and h.primary.id == kid and h.time <= kt]
        if prev_hits:
            kills_linked_via_target += 1
    print("Destroyed linkage via target id (heuristic):")
    print(f"  Kills linked to prior hit by same target id: {kills_linked_via_target}/{len(kills_human)}")

    # Distinct <Type> values across all object nodes
    type_values = set()
    for e in deb.events:
        for obj in (e.primary, e.secondary, e.parent_object, e.locked_object):
            if obj and obj.type and obj.type.strip():
                type_values.add(obj.type.strip())
    print("Distinct <Type> values ({}):".format(len(type_values)))
    for t in sorted(type_values, key=lambda s: s.lower()):
        print(f"  {t}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
