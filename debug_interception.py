#!/usr/bin/env python3
"""Debug interception detection function."""

from src.tacview_log_analyzer.models import Action
from src.tacview_log_analyzer.parser import has_pilot, parse_file


def debug_interception(e):
    """Debug version of _mk_interception with logging."""
    print(f"\n=== Debugging event at {e.time:.2f} ===")
    
    # Check basic conditions
    is_hit_by = e.action == Action.HAS_BEEN_HIT_BY
    has_primary = e.primary is not None
    has_secondary = e.secondary is not None
    has_parent = e.parent_object is not None
    has_pilot_parent = has_pilot(e.parent_object) if e.parent_object else False
    
    print(f"Action is HasBeenHitBy: {is_hit_by}")
    print(f"Has primary: {has_primary}")
    print(f"Has secondary: {has_secondary}")
    print(f"Has parent: {has_parent}")
    print(f"Has pilot parent: {has_pilot_parent}")
    
    if not (is_hit_by and has_primary and has_secondary and has_parent and has_pilot_parent):
        print("Basic conditions not met")
        return None
    
    # Check weapon name
    weapon_name = (e.secondary.name or "").upper()
    weapon_type = (e.secondary.type or "").lower()
    
    print(f"Weapon name: '{weapon_name}'")
    print(f"Weapon type: '{weapon_type}'")
    
    # A-G weapon indicators
    ag_weapon_names = {"AGM", "GBU", "JDAM", "JSOW", "SDB", "HARM", "HELLFIRE"}
    has_ag_name = any(ag_name in weapon_name for ag_name in ag_weapon_names)
    is_missile_type = weapon_type == "missile"
    is_ag_weapon = is_missile_type and has_ag_name
    
    print(f"Has A-G name: {has_ag_name} (checking for {ag_weapon_names})")
    print(f"Is missile type: {is_missile_type}")
    print(f"Is A-G weapon: {is_ag_weapon}")
    
    # Check interceptor
    interceptor_type = (e.primary.type or "").lower()
    interceptor_coalition = (e.primary.coalition or "").strip()
    weapon_coalition = (e.secondary.coalition or "").strip()
    
    print(f"Interceptor type: '{interceptor_type}'")
    print(f"Interceptor coalition: '{interceptor_coalition}'")
    print(f"Weapon coalition: '{weapon_coalition}'")
    
    is_interceptor_missile = interceptor_type == "missile"
    coalitions_different = interceptor_coalition != weapon_coalition
    both_have_coalition = interceptor_coalition and weapon_coalition
    is_enemy_interceptor = is_interceptor_missile and coalitions_different and both_have_coalition
    
    print(f"Interceptor is missile: {is_interceptor_missile}")
    print(f"Coalitions different: {coalitions_different}")
    print(f"Both have coalition: {both_have_coalition}")
    print(f"Is enemy interceptor: {is_enemy_interceptor}")
    
    if is_ag_weapon and is_enemy_interceptor:
        print("✅ INTERCEPTION DETECTED!")
        return True
    else:
        print("❌ Not an interception")
        return False

def main():
    xml_path = r"g:\BMS\4.38\Analysis\2025-10-11_19-10-19.xml"
    
    print("Loading XML file...")
    debriefing = parse_file(xml_path)
    
    print("Looking for the specific event at 21012.11...")
    for e in debriefing.events:
        if (e.action == Action.HAS_BEEN_HIT_BY and 
            21012.0 <= e.time <= 21012.2 and
            e.secondary and "JSOW" in (e.secondary.name or "")):
            debug_interception(e)
            break

if __name__ == "__main__":
    main()