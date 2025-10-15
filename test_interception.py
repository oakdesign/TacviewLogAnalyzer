#!/usr/bin/env python3
"""Test script to verify interception detection."""

from src.tacview_log_analyzer.linking import (extract_shots_hits_kills,
                                              link_events_combined)
from src.tacview_log_analyzer.parser import parse_file


def main():
    xml_path = r"g:\BMS\4.38\Analysis\2025-10-11_19-10-19.xml"
    
    print("Loading XML file...")
    debriefing = parse_file(xml_path)
    
    # Look for the specific event around time 21012.11
    print("Looking for HasBeenHitBy events around time 21012.11...")
    from src.tacview_log_analyzer.models import Action
    
    target_events = []
    for e in debriefing.events:
        if (e.action == Action.HAS_BEEN_HIT_BY and 
            21010 <= e.time <= 21015 and
            e.secondary and "AGM-154 JSOW" in (e.secondary.name or "")):
            target_events.append(e)
            print(f"  Found event at {e.time:.2f}")
            print(f"    Primary: {e.primary.type if e.primary else None} - {e.primary.name if e.primary else None}")
            print(f"    Secondary: {e.secondary.type if e.secondary else None} - {e.secondary.name if e.secondary else None}")
            print(f"    Parent: {e.parent_object.pilot if e.parent_object else None}")
    
    if not target_events:
        print("  No matching events found!")
        print("  Let me check all HasBeenHitBy events with JSOW...")
        for e in debriefing.events:
            if (e.action == Action.HAS_BEEN_HIT_BY and 
                e.secondary and "JSOW" in (e.secondary.name or "")):
                print(f"  Found JSOW hit at {e.time:.2f}")
    
    # Test the interception function directly on our target event
    if target_events:
        from src.tacview_log_analyzer.linking import _mk_interception
        print("Testing _mk_interception on target event...")
        result = _mk_interception(target_events[0])
        print(f"Result: {result}")
    
    print("Extracting events...")
    shots_all, hits_all, kills_all, interceptions_all = extract_shots_hits_kills(debriefing.events)
    
    print(f"\nFound {len(interceptions_all)} interceptions:")
    for i in interceptions_all:
        print(f"  Time: {i.time:.2f}, Pilot: {i.pilot}, Weapon: {i.weapon_id}, Interceptor: {i.interceptor_name}")
    
    print("\nRunning combined linking...")
    chains, leftover_shots, leftover_hits, leftover_kills = link_events_combined(debriefing.events)
    
    intercepted_chains = [c for c in chains if getattr(c, 'intercepted', False)]
    print(f"\nFound {len(intercepted_chains)} intercepted chains:")
    for c in intercepted_chains:
        print(f"  Pilot: {c.shot.shooter_pilot}, Weapon: {c.shot.weapon_name}, Interceptor: {getattr(c, 'interceptor_name', 'Unknown')}")
    
    # Look specifically for Hollywood's AGM-154 JSOW
    hollywood_chains = [c for c in chains if c.shot.shooter_pilot == "Hollywood"]
    print(f"\nHollywood chains ({len(hollywood_chains)}):")
    for c in hollywood_chains:
        intercepted = getattr(c, 'intercepted', False)
        interceptor = getattr(c, 'interceptor_name', None)
        print(f"  Weapon: {c.shot.weapon_name}, Hit: {c.hit is not None}, Kill: {c.kill is not None}, Intercepted: {intercepted}, Interceptor: {interceptor}")

if __name__ == "__main__":
    main()