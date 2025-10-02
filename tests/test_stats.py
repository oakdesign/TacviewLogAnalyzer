from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path

from tacview_log_analyzer.models import Action
from tacview_log_analyzer.parser import parse_file
from tacview_log_analyzer.stats import (accumulate_pilot_stats,
                                        render_pilot_stats)


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


def test_accumulate_pilot_stats(tmp_path: Path):
    body = """
    <Event><Time>1</Time><Action>HasFired</Action><PrimaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>Alpha</Pilot><Coalition>NATO</Coalition></PrimaryObject></Event>
    <Event><Time>2</Time><Action>HasBeenHitBy</Action><ParentObject ID="1"><Type>A</Type><Name>X</Name><Pilot>Alpha</Pilot><Coalition>NATO</Coalition></ParentObject></Event>
    <Event><Time>3</Time><Action>HasBeenDestroyed</Action><SecondaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>Alpha</Pilot><Coalition>NATO</Coalition></SecondaryObject></Event>
    <Event><Time>4</Time><Action>HasFired</Action><PrimaryObject ID="2"><Type>A</Type><Name>X</Name><Pilot>Beta</Pilot><Coalition>NATO</Coalition></PrimaryObject></Event>
    <Event><Time>5</Time><Action>HasBeenHitBy</Action><ParentObject ID="2"><Type>A</Type><Name>X</Name><Pilot>Beta</Pilot><Coalition>NATO</Coalition></ParentObject></Event>
    """
    xml_path = write_xml(tmp_path, body)
    deb = parse_file(xml_path)
    stats = accumulate_pilot_stats(deb.events)
    assert stats["Alpha"].shots == 1
    assert stats["Alpha"].hits == 1
    assert stats["Alpha"].kills == 1
    assert stats["Beta"].shots == 1
    assert stats["Beta"].hits == 1
    assert stats["Beta"].kills == 0


def test_cli_summary_output(tmp_path: Path):
    body = """
    <Event><Time>1</Time><Action>HasFired</Action><PrimaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>Alpha</Pilot><Coalition>NATO</Coalition></PrimaryObject></Event>
    <Event><Time>2</Time><Action>HasBeenHitBy</Action><ParentObject ID="1"><Type>A</Type><Name>X</Name><Pilot>Alpha</Pilot><Coalition>NATO</Coalition></ParentObject></Event>
    <Event><Time>3</Time><Action>HasBeenDestroyed</Action><SecondaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>Alpha</Pilot><Coalition>NATO</Coalition></SecondaryObject></Event>
    """
    xml_path = write_xml(tmp_path, body)
    cmd = [sys.executable, "-m", "tacview_log_analyzer.cli", str(xml_path), "--summary"]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    assert proc.returncode == 0
    assert "Alpha: 1 shots, 1 hits, 1 kills" in proc.stdout


def test_per_weapon_shots_per_pilot(tmp_path: Path):
    body = """
    <Event>
      <Time>1</Time>
      <Action>HasFired</Action>
      <PrimaryObject ID=\"1\"><Type>A</Type><Name>X</Name><Pilot>FritZ</Pilot><Coalition>NATO</Coalition></PrimaryObject>
      <SecondaryObject ID=\"101\"><Type>Missile</Type><Name>AIM-7M Sparrow III</Name><Coalition>NATO</Coalition><Parent>1</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>2</Time>
      <Action>HasFired</Action>
      <PrimaryObject ID=\"1\"><Type>A</Type><Name>X</Name><Pilot>FritZ</Pilot><Coalition>NATO</Coalition></PrimaryObject>
      <SecondaryObject ID=\"102\"><Type>Missile</Type><Name>AIM-7M Sparrow III</Name><Coalition>NATO</Coalition><Parent>1</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>3</Time>
      <Action>HasFired</Action>
      <PrimaryObject ID=\"1\"><Type>A</Type><Name>X</Name><Pilot>FritZ</Pilot><Coalition>NATO</Coalition></PrimaryObject>
      <SecondaryObject ID=\"103\"><Type>Missile</Type><Name>AIM-9M Sidewinder</Name><Coalition>NATO</Coalition><Parent>1</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>4</Time>
      <Action>HasFired</Action>
      <PrimaryObject ID=\"1\"><Type>A</Type><Name>X</Name><Pilot>FritZ</Pilot><Coalition>NATO</Coalition></PrimaryObject>
      <SecondaryObject ID=\"104\"><Type>Missile</Type><Name>AIM-9M Sidewinder</Name><Coalition>NATO</Coalition><Parent>1</Parent></SecondaryObject>
    </Event>
    <Event>
      <Time>5</Time>
      <Action>HasFired</Action>
      <PrimaryObject ID=\"1\"><Type>A</Type><Name>X</Name><Pilot>FritZ</Pilot><Coalition>NATO</Coalition></PrimaryObject>
      <SecondaryObject ID=\"105\"><Type>Missile</Type><Name>AIM-7M Sparrow III</Name><Coalition>NATO</Coalition><Parent>1</Parent></SecondaryObject>
    </Event>
    """
    xml_path = write_xml(tmp_path, body)
    from tacview_log_analyzer.parser import parse_file

    deb = parse_file(xml_path)
    stats = accumulate_pilot_stats(deb.events)
    s = stats["FritZ"]
    # 5 total: 3 AIM-7M, 2 AIM-9M
    assert s.shots == 5 and s.hits == 0 and s.kills == 0
    # Render check
    rendered = render_pilot_stats({"FritZ": s})
    assert "FritZ: 5 shots, 0 hits, 0 kills" in rendered
    assert "  AIM-7M Sparrow III: 3 shots" in rendered
    assert "  AIM-9M Sidewinder: 2 shots" in rendered
