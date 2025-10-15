from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Iterable, Optional

from .models import (Action, EventRecord, FlightRecording, Location, Mission,
                     ObjectInfo, TacviewDebriefing)


def _text(node: Optional[ET.Element]) -> Optional[str]:
    return node.text if node is not None else None


def _float(node: Optional[ET.Element]) -> Optional[float]:
    try:
        return float(node.text) if node is not None and node.text is not None else None
    except (TypeError, ValueError):
        return None


def _int(text: Optional[str]) -> Optional[int]:
    try:
        return int(text) if text is not None else None
    except (TypeError, ValueError):
        return None


def _parse_location(node: Optional[ET.Element]) -> Optional[Location]:
    if node is None:
        return None
    return Location(
        longitude=_float(node.find("Longitude")) or 0.0,
        latitude=_float(node.find("Latitude")) or 0.0,
        altitude=_float(node.find("Altitude")) or 0.0,
    )


def _parse_object(node: Optional[ET.Element]) -> Optional[ObjectInfo]:
    if node is None:
        return None
    return ObjectInfo(
        id=_int(node.get("ID")),
        type=_text(node.find("Type")),
        name=_text(node.find("Name")),
        coalition=_text(node.find("Coalition")),
        pilot=_text(node.find("Pilot")),
        parent=_int(_text(node.find("Parent"))),
    )


def _parse_event(event: ET.Element) -> Optional[EventRecord]:
    action_text = _text(event.find("Action"))
    if action_text not in {a.value for a in Action}:
        return None
    action = Action(action_text)  # type: ignore[arg-type]

    time_value = _float(event.find("Time")) or 0.0
    location = _parse_location(event.find("Location"))
    primary = _parse_object(event.find("PrimaryObject"))
    secondary = _parse_object(event.find("SecondaryObject"))
    parent_object = _parse_object(event.find("ParentObject"))
    locked_object = _parse_object(event.find("LockedObject"))

    return EventRecord(
        time=time_value,
        action=action,
        location=location,
        primary=primary,
        secondary=secondary,
        parent_object=parent_object,
        locked_object=locked_object,
        occurrences=_int(_text(event.find("Occurrences"))),
    )


def parse_file(path: Path | str) -> TacviewDebriefing:
    root = ET.parse(str(path)).getroot()

    version = root.get("Version")

    fr_node = root.find("FlightRecording")
    fr = None
    if fr_node is not None:
        fr = FlightRecording(
            source=_text(fr_node.find("Source")),
            recorder=_text(fr_node.find("Recorder")),
            recording_time=_text(fr_node.find("RecordingTime")),
        )

    mission_node = root.find("Mission")
    mission = None
    if mission_node is not None:
        main_ac_id = None
        try:
            main_ac_id = int(_text(mission_node.find("MainAircraftID")) or "")
        except Exception:
            main_ac_id = None
        mission = Mission(
            title=_text(mission_node.find("Title")),
            mission_time=_text(mission_node.find("MissionTime")),
            duration=_float(mission_node.find("Duration")),
            main_aircraft_id=main_ac_id,
        )

    events: list[EventRecord] = []
    events_node = root.find("Events")
    if events_node is not None:
        for e in events_node.findall("Event"):
            rec = _parse_event(e)
            if rec is not None:
                events.append(rec)

    return TacviewDebriefing(
        version=version,
        flight_recording=fr,
        mission=mission,
        events=events,
    )


def filter_events(records: Iterable[EventRecord], *actions: Action) -> list[EventRecord]:
    action_set = set(actions)
    return [r for r in records if r.action in action_set]


def has_pilot(obj: Optional[ObjectInfo]) -> bool:
    if not obj:
        return False
    if obj.pilot is None:
        return False
    return obj.pilot.strip() != ""


def extract_human_pilots(events: list[EventRecord], mission: Mission | None = None) -> set[str]:
    """Extract all human pilots from events based on HasEnteredTheArea events and MainAircraftID.
    
    Logic:
    1. Find all HasEnteredTheArea events with Pilot on PrimaryObject
    2. Add MainAircraftID pilot from mission (server flight special case)
    3. Return unique set of pilot names (excluding empty/None)
    """
    pilots: set[str] = set()
    
    # Method 1: HasEnteredTheArea events with pilot
    for event in events:
        if (event.action == Action.HAS_ENTERED_THE_AREA and 
            event.primary and 
            event.primary.pilot and 
            event.primary.pilot.strip()):
            pilots.add(event.primary.pilot.strip())
    
    # Method 2: MainAircraftID from mission (server flight)
    if mission and mission.main_aircraft_id is not None:
        # Find the pilot associated with the main aircraft ID
        for event in events:
            if (event.primary and 
                event.primary.id == mission.main_aircraft_id and 
                event.primary.pilot and 
                event.primary.pilot.strip()):
                pilots.add(event.primary.pilot.strip())
                break  # Found the main aircraft pilot
    
    return pilots
