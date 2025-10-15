#!/usr/bin/env python3
"""Debug the duplicate intercepted weapon display issue."""

from src.tacview_log_analyzer.linking import link_events_combined
from src.tacview_log_analyzer.parser import parse_file


def main():
    xml_path = r"g:\BMS\4.38\Analysis\2025-10-11_19-10-19.xml"
    
    print("Loading XML file...")
    debriefing = parse_file(xml_path)
    
    print("\nLinking events...")
    chains, leftover_shots, leftover_hits, leftover_kills = link_events_combined(debriefing.events)
    
    # Find Hollywood's chains
    hollywood_chains = [c for c in chains if c.shot.shooter_pilot == "Hollywood"]
    print(f"\nHollywood has {len(hollywood_chains)} chains:")
    
    for i, c in enumerate(hollywood_chains):
        intercepted = getattr(c, 'intercepted', False)
        print(f"  Chain {i+1}: {c.shot.weapon_name} (ID: {c.shot.weapon_id}) at {c.shot.time:.2f}")
        print(f"    Intercepted: {intercepted}")
        print(f"    Has hit: {c.hit is not None}")
        print(f"    Has kill: {c.kill is not None}")
        print(f"    Shot event ID: {id(c.shot.event)}")
        if c.hit:
            print(f"    Hit event ID: {id(c.hit.event)}")
    
    # Find Hollywood's leftover shots
    hollywood_leftover_shots = [s for s in leftover_shots if s.shooter_pilot == "Hollywood"]
    print(f"\nHollywood has {len(hollywood_leftover_shots)} leftover shots:")
    
    for i, s in enumerate(hollywood_leftover_shots):
        print(f"  Shot {i+1}: {s.weapon_name} (ID: {s.weapon_id}) at {s.time:.2f}")
        print(f"    Shot event ID: {id(s.event)}")
        print(f"    Weapon type: {s.weapon_type}")
    
    # Check for shot ID overlaps
    chain_shot_ids = {id(c.shot.event) for c in hollywood_chains}
    leftover_shot_ids = {id(s.event) for s in hollywood_leftover_shots}
    
    overlap = chain_shot_ids & leftover_shot_ids
    if overlap:
        print(f"\n❌ PROBLEM: {len(overlap)} shot events appear in BOTH chains and leftovers!")
        for event_id in overlap:
            print(f"  Event ID: {event_id}")
    else:
        print(f"\n✅ Good: No overlap between chain shots and leftover shots")
    
    # Look for AGM-154 JSOW specifically
    agm_chains = [c for c in hollywood_chains if "AGM-154" in c.shot.weapon_name]
    agm_leftovers = [s for s in hollywood_leftover_shots if "AGM-154" in s.weapon_name]
    
    print(f"\nAGM-154 JSOW analysis:")
    print(f"  In chains: {len(agm_chains)}")
    print(f"  In leftovers: {len(agm_leftovers)}")
    
    if agm_chains:
        agm_chain = agm_chains[0]
        print(f"  Chain intercepted: {getattr(agm_chain, 'intercepted', False)}")
        print(f"  Chain weapon ID: {agm_chain.shot.weapon_id}")
        print(f"  Chain shot time: {agm_chain.shot.time}")
    
    if agm_leftovers:
        agm_leftover = agm_leftovers[0]
        print(f"  Leftover weapon ID: {agm_leftover.weapon_id}")  
        print(f"  Leftover shot time: {agm_leftover.time}")

if __name__ == "__main__":
    main()