from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional


class Action(str, Enum):
    HAS_FIRED = "HasFired"
    HAS_BEEN_HIT_BY = "HasBeenHitBy"
    HAS_BEEN_DESTROYED = "HasBeenDestroyed"
    HAS_TAKEN_OFF = "HasTakenOff"
    HAS_LANDED = "HasLanded"
    HAS_ENTERED_THE_AREA = "HasEnteredTheArea"


@dataclass(slots=True)
class Location:
    longitude: float
    latitude: float
    altitude: float


@dataclass(slots=True)
class ObjectInfo:
    id: Optional[int]
    type: Optional[str]
    name: Optional[str]
    coalition: Optional[str]
    pilot: Optional[str] = None
    parent: Optional[int] = None


@dataclass(slots=True)
class EventRecord:
    time: float
    action: Action
    location: Optional[Location]
    primary: Optional[ObjectInfo]
    secondary: Optional[ObjectInfo]
    parent_object: Optional[ObjectInfo]
    locked_object: Optional[ObjectInfo]
    occurrences: Optional[int] = None


@dataclass(slots=True)
class FlightRecording:
    source: Optional[str]
    recorder: Optional[str]
    recording_time: Optional[str]


@dataclass(slots=True)
class Mission:
    title: Optional[str]
    mission_time: Optional[str]
    duration: Optional[float]
    main_aircraft_id: Optional[int] = None


@dataclass(slots=True)
class TacviewDebriefing:
    version: Optional[str]
    flight_recording: Optional[FlightRecording]
    mission: Optional[Mission]
    events: list[EventRecord]
