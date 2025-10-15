#!/usr/bin/env python3
"""Debug Hollywood's misses to see where the duplicate AGM-154 comes from."""

from src.tacview_log_analyzer.linking import extract_shots_hits_kills
from src.tacview_log_analyzer.parser import parse_file
from src.tacview_log_analyzer.viewmodel import build_pilot_view_model


def main():
    xml_path = r"g:\BMS\4.38\Analysis\2025-10-11_19-10-19.xml"
    
    print("Loading XML file...")
    debriefing = parse_file(xml_path)
    
    # Check for multiple AGM-154 shots
    shots_all, hits_all, kills_all, interceptions_all = extract_shots_hits_kills(debriefing.events)
    hollywood_agm_shots = [s for s in shots_all if s.shooter_pilot == "Hollywood" and "AGM-154" in s.weapon_name]
    
    print(f"\nFound {len(hollywood_agm_shots)} AGM-154 shots by Hollywood:")
    for i, shot in enumerate(hollywood_agm_shots):
        print(f"  Shot {i+1}: ID={shot.weapon_id}, Time={shot.time:.2f}, Event={id(shot.event)}")
    
    print("\nBuilding viewmodel...")
    vm = build_pilot_view_model(debriefing.events, debriefing.mission)
    
    # Find Hollywood in the pilots
    hollywood = None
    for pilot in vm["pilots"]:
        if pilot["pilot"] == "Hollywood":
            hollywood = pilot
            break
    
    if not hollywood:
        print("Hollywood not found!")
        return
    
    print(f"\nHollywood chains: {len(hollywood['chains'])}")
    for i, chain in enumerate(hollywood["chains"]):
        print(f"  Chain {i+1}: {chain['weapon']} at {chain['shotStr']}")
        print(f"    Target: {chain['targetName']}")
        print(f"    Intercepted: {chain.get('intercepted', False)}")
        print(f"    Flags would show: {_get_flags(chain)}")
    
    print(f"\nHollywood misses: {len(hollywood['misses'])}")
    for i, miss in enumerate(hollywood["misses"]):
        print(f"  Miss {i+1}: {miss['weapon']} at {miss['shotStr']}")
        print(f"    Intercepted: {miss.get('intercepted', False)}")
        print(f"    Domain: {miss['domain']}")

def _get_flags(chain):
    flags = []
    if chain.get('intercepted', False):
        flags.append(f"Intercepted by {chain.get('interceptorName', 'Unknown')}")
    if chain.get('shooterMismatch', False):
        flags.append("ShooterMismatch")
    if chain.get('friendly', False):
        flags.append("Friendly")
    return ", ".join(flags) if flags else ""

if __name__ == "__main__":
    main()