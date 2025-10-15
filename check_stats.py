#!/usr/bin/env python3

from src.tacview_log_analyzer.linking import link_events_combined
from src.tacview_log_analyzer.parser import parse_file


def main():
    # Parse the XML file
    data = parse_file(r'g:\BMS\4.38\Analysis\2025-10-11_19-10-19.xml')
    
    # Link events and build chains
    chains, shots, hits, kills = link_events_combined(data.events)
    
    # Find Hollywood's chains
    hollywood_chains = [c for c in chains if c.shot.shooter_pilot == 'Hollywood']
    
    # Count stats manually
    total_shots = len(hollywood_chains)
    total_hits = len([c for c in hollywood_chains if c.hit and not c.intercepted])
    total_kills = len([c for c in hollywood_chains if c.kill and not c.intercepted])
    intercepted_count = len([c for c in hollywood_chains if c.intercepted])
    total_misses = total_shots - total_hits
    
    print(f"Hollywood's Statistics:")
    print(f"  Total shots: {total_shots}")
    print(f"  Hits (excluding intercepted): {total_hits}")  
    print(f"  Kills (excluding intercepted): {total_kills}")
    print(f"  Intercepted weapons: {intercepted_count}")
    print(f"  Misses: {total_misses}")
    print(f"  Hit rate: {total_hits/total_shots:.1%}" if total_shots > 0 else "  Hit rate: N/A")
    
    print(f"\nChain Details:")
    for i, chain in enumerate(hollywood_chains, 1):
        status_parts = []
        if chain.intercepted:
            status_parts.append(f"INTERCEPTED by {chain.interceptor_name}")
        if chain.hit and not chain.intercepted:
            status_parts.append("HIT")
        if chain.kill and not chain.intercepted:
            status_parts.append("KILL")
        if not status_parts:
            status_parts.append("MISS")
            
        status = " + ".join(status_parts)
        weapon = chain.shot.weapon_name
        target = chain.hit.target_name if chain.hit else "Unknown"
        print(f"  Chain {i}: {weapon} -> {target} ({status})")

if __name__ == "__main__":
    main()