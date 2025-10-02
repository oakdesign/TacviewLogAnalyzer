from __future__ import annotations

import textwrap
from pathlib import Path

from tacview_log_analyzer.linking import (extract_shots_hits_kills,
                                          link_events_combined,
                                          link_events_deterministic,
                                          link_events_heuristic)
from tacview_log_analyzer.parser import parse_file


def write_xml(tmp_path: Path, body: str) -> Path:
    xml = textwrap.dedent(
        f"""
        <?xml version="1.0" encoding="utf-8" standalone="yes"?>
        <TacviewDebriefing Version="1.2.6">
          <FlightRecording><Source>DCS</Source><Recorder>Tacview</Recorder><RecordingTime>2025-01-01</RecordingTime></FlightRecording>
          <Mission><Title>Test</Title><MissionTime>2025-01-01</MissionTime><Duration>1</Duration></Mission>
          <Events>
            {body}
          </Events>
        </TacviewDebriefing>
        """
    ).strip()
    p = tmp_path / "sample.xml"
    p.write_text(xml, encoding="utf-8")
    return p


def test_deterministic_linking_basic(tmp_path: Path):
    body = """
    <Event>
      <Time>10</Time>
      <Location/>
      <PrimaryObject ID=\"30787\"><Type>Aircraft</Type><Name>F-15C Eagle</Name><Pilot>Streak</Pilot><Coalition>NATO</Coalition></PrimaryObject>
      <Action>HasFired</Action>
      <SecondaryObject ID=\"31310\"><Type>Missile</Type><Name>AIM-7M Sparrow III</Name><Coalition>NATO</Coalition><Parent>30787</Parent></SecondaryObject>
      <LockedObject ID=\"31197\"><Type>Aircraft</Type><Name>MiG-31 Foxhound</Name><Coalition>CCCP</Coalition></LockedObject>
    </Event>
    <Event>
      <Time>12</Time>
      <Location/>
      <PrimaryObject ID=\"31197\"><Type>Aircraft</Type><Name>MiG-31 Foxhound</Name><Coalition>CCCP</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"31310\"><Type>Missile</Type><Name>AIM-7M Sparrow III</Name><Coalition>NATO</Coalition><Parent>30787</Parent></SecondaryObject>
      <ParentObject ID=\"30787\"><Type>Aircraft</Type><Name>F-15C Eagle</Name><Pilot>Streak</Pilot><Coalition>NATO</Coalition></ParentObject>
    </Event>
    <Event>
      <Time>13</Time>
      <Location/>
      <PrimaryObject ID=\"31197\"><Type>Aircraft</Type><Name>MiG-31 Foxhound</Name><Coalition>CCCP</Coalition></PrimaryObject>
      <Action>HasBeenDestroyed</Action>
      <SecondaryObject ID=\"30787\"><Type>Aircraft</Type><Name>F-15C Eagle</Name><Pilot>Streak</Pilot><Coalition>NATO</Coalition></SecondaryObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    chains, l_shots, l_hits, l_kills = link_events_deterministic(deb.events, consume=True)
    assert len(chains) == 1
    c = chains[0]
    assert c.shot.weapon_id == 31310
    assert c.hit and c.kill
    assert c.shooter_consistent is True
    # leftovers consumed
    assert l_shots == [] and l_hits == [] and l_kills == []


def test_deterministic_linking_shooter_mismatch(tmp_path: Path):
    body = """
    <Event>
      <Time>10</Time>
      <PrimaryObject ID=\"100\"><Type>Aircraft</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></PrimaryObject>
      <Action>HasFired</Action>
      <SecondaryObject ID=\"900\"><Type>Missile</Type><Name>M1</Name><Coalition>N</Coalition><Parent>100</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>11</Time>
      <PrimaryObject ID=\"200\"><Type>Aircraft</Type><Name>T1</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"900\"><Type>Missile</Type><Name>M1</Name><Coalition>N</Coalition><Parent>999</Parent></SecondaryObject>
      <ParentObject ID=\"999\"><Type>Aircraft</Type><Name>P2</Name><Pilot>B</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    chains, l_shots, l_hits, l_kills = link_events_deterministic(deb.events, consume=False)
    assert len(chains) == 1
    assert chains[0].shooter_consistent is False
    # Not consumed
    assert len(l_shots) == 1 and len(l_hits) == 1 and len(l_kills) == 0


def test_kill_hit_time_tolerance(tmp_path: Path):
    body = """
    <Event>
      <Time>10</Time>
      <PrimaryObject ID=\"1\"><Type>A</Type><Name>P</Name><Pilot>X</Pilot><Coalition>N</Coalition></PrimaryObject>
      <Action>HasFired</Action>
      <SecondaryObject ID=\"99\"><Type>Missile</Type><Name>M</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>20.00</Time>
      <PrimaryObject ID=\"200\"><Type>T</Type><Name>T</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"99\"><Type>Missile</Type><Name>M</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
      <ParentObject ID=\"1\"><Type>A</Type><Name>P</Name><Pilot>X</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    <Event>
      <Time>20.01</Time>
      <PrimaryObject ID=\"200\"><Type>T</Type><Name>T</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenDestroyed</Action>
      <SecondaryObject ID=\"1\"><Type>A</Type><Name>P</Name><Pilot>X</Pilot><Coalition>N</Coalition></SecondaryObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    chains, l_s, l_h, l_k = link_events_deterministic(deb.events, consume=True, hit_kill_time_tolerance=0.05)
    assert len(chains) == 1 and chains[0].kill is not None


def test_heuristic_linking_bomb_ripple(tmp_path: Path):
    body = """
    <Event>
      <Time>10</Time>
      <PrimaryObject ID=\"1\"><Type>Aircraft</Type><Name>P</Name><Pilot>Alpha</Pilot><Coalition>N</Coalition></PrimaryObject>
      <Action>HasFired</Action>
      <SecondaryObject ID=\"500\"><Type>Bomb</Type><Name>MK-82</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
      <Occurrences>2</Occurrences>
    </Event>
    <Event>
      <Time>12</Time>
      <PrimaryObject ID=\"200\"><Type>Ground</Type><Name>T1</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"999\"><Type>Bomb</Type><Name>MK-82</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
      <ParentObject ID=\"1\"><Type>Aircraft</Type><Name>P</Name><Pilot>Alpha</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    <Event>
      <Time>13</Time>
      <PrimaryObject ID=\"201\"><Type>Ground</Type><Name>T2</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"1000\"><Type>Bomb</Type><Name>MK-82</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
      <ParentObject ID=\"1\"><Type>Aircraft</Type><Name>P</Name><Pilot>Alpha</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    chains, l_shots, l_hits, l_kills = link_events_heuristic(deb.events)
    # Both hits should be linked to the single fired event (Occurrences=2)
    assert len(chains) == 2
    assert all(c.method == "heuristic" for c in chains)
    assert l_hits == [] and l_kills == []
    # Shot occurrences consumed fully => no leftover shots
    assert l_shots == []


def test_combined_links_deterministic_and_heuristic(tmp_path: Path):
    body = """
    <!-- Deterministic missile hit/kill -->
    <Event>
      <Time>5</Time>
      <PrimaryObject ID=\"10\"><Type>A</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></PrimaryObject>
      <Action>HasFired</Action>
      <SecondaryObject ID=\"90\"><Type>Missile</Type><Name>M1</Name><Coalition>N</Coalition><Parent>10</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>6</Time>
      <PrimaryObject ID=\"20\"><Type>T</Type><Name>T1</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"90\"><Type>Missile</Type><Name>M1</Name><Coalition>N</Coalition><Parent>10</Parent></SecondaryObject>
      <ParentObject ID=\"10\"><Type>A</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    <Event>
      <Time>6.05</Time>
      <PrimaryObject ID=\"20\"><Type>T</Type><Name>T1</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenDestroyed</Action>
      <SecondaryObject ID=\"10\"><Type>A</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></SecondaryObject>
    </Event>
    <!-- Heuristic bomb ripple -->
    <Event>
      <Time>10</Time>
      <PrimaryObject ID=\"10\"><Type>A</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></PrimaryObject>
      <Action>HasFired</Action>
      <SecondaryObject ID=\"500\"><Type>Bomb</Type><Name>B</Name><Coalition>N</Coalition><Parent>10</Parent></SecondaryObject>
      <Occurrences>2</Occurrences>
    </Event>
    <Event>
      <Time>12</Time>
      <PrimaryObject ID=\"30\"><Type>T</Type><Name>T2</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"999\"><Type>Bomb</Type><Name>B</Name><Coalition>N</Coalition><Parent>10</Parent></SecondaryObject>
      <ParentObject ID=\"10\"><Type>A</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    <Event>
      <Time>13</Time>
      <PrimaryObject ID=\"31\"><Type>T</Type><Name>T3</Name><Coalition>C</Coalition></PrimaryObject>
      <Action>HasBeenHitBy</Action>
      <SecondaryObject ID=\"1000\"><Type>Bomb</Type><Name>B</Name><Coalition>N</Coalition><Parent>10</Parent></SecondaryObject>
      <ParentObject ID=\"10\"><Type>A</Type><Name>P1</Name><Pilot>A</Pilot><Coalition>N</Coalition></ParentObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    chains, l_shots, l_hits, l_kills = link_events_combined(deb.events)
    # Expect 1 deterministic chain + 2 heuristic chains
    assert len(chains) == 3
    assert l_hits == [] and l_kills == []
