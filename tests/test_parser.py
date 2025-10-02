from __future__ import annotations

import textwrap
from pathlib import Path

from tacview_log_analyzer.models import Action
from tacview_log_analyzer.parser import filter_events, has_pilot, parse_file


def write_xml(tmp_path: Path, body: str) -> Path:
    xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="utf-8" standalone="yes"?>
        <TacviewDebriefing Version="1.2.6">
          <FlightRecording>
            <Source>DCS</Source>
            <Recorder>Tacview</Recorder>
            <RecordingTime>2025-09-26T00:00:00Z</RecordingTime>
          </FlightRecording>
          <Mission>
            <Title>Test</Title>
            <MissionTime>2025-09-26T00:00:00Z</MissionTime>
            <Duration>1.0</Duration>
          </Mission>
          <Events>
          {body}
          </Events>
        </TacviewDebriefing>
        """
    ).strip()
    p = tmp_path / "sample.xml"
    p.write_text(xml, encoding="utf-8")
    return p


def test_parse_has_fired_with_locked_object(tmp_path: Path):
    body = """
    <Event>
        <Time>61911.78</Time>
        <Location>
            <Longitude>7.3416138</Longitude>
            <Latitude>53.5931922</Latitude>
            <Altitude>10260.28</Altitude>
        </Location>
        <PrimaryObject ID="30787">
            <Type>Aircraft</Type>
            <Name>F-15C Eagle</Name>
            <Pilot>Streak</Pilot>
            <Coalition>NATO</Coalition>
        </PrimaryObject>
        <Action>HasFired</Action>
        <SecondaryObject ID="31310">
            <Type>Missile</Type>
            <Name>AIM-7M Sparrow III</Name>
            <Coalition>NATO</Coalition>
            <Parent>30787</Parent>
        </SecondaryObject>
        <LockedObject ID="31197">
            <Type>Aircraft</Type>
            <Name>MiG-31 Foxhound</Name>
            <Coalition>CCCP</Coalition>
        </LockedObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    assert deb.version == "1.2.6"
    assert deb.flight_recording and deb.mission
    assert len(deb.events) == 1
    e = deb.events[0]
    assert e.action == Action.HAS_FIRED
    assert e.locked_object is not None
    assert e.secondary and e.secondary.parent == 30787


def test_parse_has_been_hit_by_with_parent_pilot(tmp_path: Path):
    body = """
    <Event>
        <Time>61940.55</Time>
        <Location>
            <Longitude>7.749504</Longitude>
            <Latitude>53.605184</Latitude>
            <Altitude>7931.58</Altitude>
        </Location>
        <PrimaryObject ID="31197">
            <Type>Aircraft</Type>
            <Name>MiG-31 Foxhound</Name>
            <Coalition>CCCP</Coalition>
        </PrimaryObject>
        <Action>HasBeenHitBy</Action>
        <SecondaryObject ID="31310">
            <Type>Missile</Type>
            <Name>AIM-7M Sparrow III</Name>
            <Coalition>NATO</Coalition>
            <Parent>30787</Parent>
        </SecondaryObject>
        <ParentObject ID="30787">
            <Type>Aircraft</Type>
            <Name>F-15C Eagle</Name>
            <Pilot>Streak</Pilot>
            <Coalition>NATO</Coalition>
        </ParentObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    e = deb.events[0]
    assert e.action == Action.HAS_BEEN_HIT_BY
    assert e.parent_object and has_pilot(e.parent_object)


def test_parse_has_been_destroyed(tmp_path: Path):
    body = """
    <Event>
        <Time>61940.56</Time>
        <Location>
            <Longitude>7.749504</Longitude>
            <Latitude>53.605184</Latitude>
            <Altitude>7931.58</Altitude>
        </Location>
        <PrimaryObject ID="31197">
            <Type>Aircraft</Type>
            <Name>MiG-31 Foxhound</Name>
            <Coalition>CCCP</Coalition>
        </PrimaryObject>
        <Action>HasBeenDestroyed</Action>
        <SecondaryObject ID="30787">
            <Type>Aircraft</Type>
            <Name>F-15C Eagle</Name>
            <Pilot>Streak</Pilot>
            <Coalition>NATO</Coalition>
        </SecondaryObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    e = deb.events[0]
    assert e.action == Action.HAS_BEEN_DESTROYED
    assert e.secondary and has_pilot(e.secondary)


def test_filter_events_by_action(tmp_path: Path):
    body = """
    <Event><Time>1</Time><Action>HasFired</Action></Event>
    <Event><Time>2</Time><Action>HasBeenHitBy</Action></Event>
    <Event><Time>3</Time><Action>HasBeenDestroyed</Action></Event>
    <Event><Time>4</Time><Action>IgnoredUnknown</Action></Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    hits = filter_events(deb.events, Action.HAS_BEEN_HIT_BY)
    assert [e.time for e in hits] == [2.0]