from __future__ import annotations

import subprocess
import sys
import textwrap
from pathlib import Path


def run_cli(*args: str) -> subprocess.CompletedProcess:
    # Run the package as a module via the CLI script entry
    cmd = [sys.executable, "-m", "tacview_log_analyzer.cli", *args]
    return subprocess.run(cmd, capture_output=True, text=True)


def test_no_args_shows_help():
    proc = run_cli()
    assert proc.returncode == 0
    assert "Tacview Log Analyzer" in proc.stdout


def test_version_flag():
    proc = run_cli("--version")
    assert proc.returncode == 0
    assert proc.stdout.strip().startswith("tacview-analyze ")


def test_with_xml_path_prints_placeholder(tmp_path: Path):
    xml_file = tmp_path / "sample.xml"
    xml_file.write_text("<root />", encoding="utf-8")
    proc = run_cli(str(xml_file))
    assert proc.returncode == 0
    assert f"Would analyze: {xml_file}" in proc.stdout


def test_cli_chains_runs(tmp_path: Path):
        xml = tmp_path / "x.xml"
        xml_text = textwrap.dedent(
                """
                <?xml version="1.0" encoding="utf-8" standalone="yes"?>
                <TacviewDebriefing Version="1.2.6">
                    <FlightRecording><Source>DCS</Source><Recorder>Tacview</Recorder><RecordingTime>2025</RecordingTime></FlightRecording>
                    <Mission><Title>T</Title><MissionTime>2025</MissionTime><Duration>1</Duration></Mission>
                    <Events>
                        <Event>
                            <Time>1</Time>
                            <PrimaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>P</Pilot><Coalition>N</Coalition></PrimaryObject>
                            <Action>HasFired</Action>
                            <SecondaryObject ID="10"><Type>Missile</Type><Name>M</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
                        </Event>
                        <Event>
                            <Time>2</Time>
                            <PrimaryObject ID="99"><Type>T</Type><Name>Y</Name><Coalition>C</Coalition></PrimaryObject>
                            <Action>HasBeenHitBy</Action>
                            <SecondaryObject ID="10"><Type>Missile</Type><Name>M</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
                            <ParentObject ID="1"><Type>A</Type><Name>X</Name><Pilot>P</Pilot><Coalition>N</Coalition></ParentObject>
                        </Event>
                    </Events>
                </TacviewDebriefing>
                """
        ).lstrip()
        xml.write_text(xml_text, encoding="utf-8")
        proc = run_cli(str(xml), "--chains")
        assert proc.returncode == 0
        assert "Chain:" in proc.stdout


def test_cli_chains_heuristic_runs(tmp_path: Path):
        xml = tmp_path / "x.xml"
        xml_text = textwrap.dedent(
                """
                <?xml version="1.0" encoding="utf-8" standalone="yes"?>
                <TacviewDebriefing Version="1.2.6">
                    <FlightRecording><Source>DCS</Source><Recorder>Tacview</Recorder><RecordingTime>2025</RecordingTime></FlightRecording>
                    <Mission><Title>T</Title><MissionTime>2025</MissionTime><Duration>1</Duration></Mission>
                    <Events>
                        <Event>
                            <Time>1</Time>
                            <PrimaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>P</Pilot><Coalition>N</Coalition></PrimaryObject>
                            <Action>HasFired</Action>
                            <SecondaryObject ID="500"><Type>Bomb</Type><Name>B</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
                            <Occurrences>1</Occurrences>
                        </Event>
                        <Event>
                            <Time>2</Time>
                            <PrimaryObject ID="99"><Type>T</Type><Name>Y</Name><Coalition>C</Coalition></PrimaryObject>
                            <Action>HasBeenHitBy</Action>
                            <SecondaryObject ID="999"><Type>Bomb</Type><Name>B</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
                            <ParentObject ID="1"><Type>A</Type><Name>X</Name><Pilot>P</Pilot><Coalition>N</Coalition></ParentObject>
                        </Event>
                    </Events>
                </TacviewDebriefing>
                """
        ).lstrip()
        xml.write_text(xml_text, encoding="utf-8")
        proc = run_cli(str(xml), "--chains-heuristic")
        assert proc.returncode == 0
        assert "Chain:" in proc.stdout


def test_cli_chains_combined_filters_misses(tmp_path: Path):
        xml = tmp_path / "x.xml"
        xml_text = textwrap.dedent(
                """
                <?xml version="1.0" encoding="utf-8" standalone="yes"?>
                <TacviewDebriefing Version="1.2.6">
                    <FlightRecording><Source>DCS</Source><Recorder>Tacview</Recorder><RecordingTime>2025</RecordingTime></FlightRecording>
                    <Mission><Title>T</Title><MissionTime>2025</MissionTime><Duration>1</Duration></Mission>
                    <Events>
                        <!-- Two shots: one Shell and one Bomb; only Bomb should appear as Miss if unlinked -->
                        <Event>
                            <Time>1</Time>
                            <PrimaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>P</Pilot><Coalition>N</Coalition></PrimaryObject>
                            <Action>HasFired</Action>
                            <SecondaryObject ID="10"><Type>Shell</Type><Name>GUN</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
                        </Event>
                        <Event>
                            <Time>2</Time>
                            <PrimaryObject ID="1"><Type>A</Type><Name>X</Name><Pilot>P</Pilot><Coalition>N</Coalition></PrimaryObject>
                            <Action>HasFired</Action>
                            <SecondaryObject ID="20"><Type>Bomb</Type><Name>B</Name><Coalition>N</Coalition><Parent>1</Parent></SecondaryObject>
                        </Event>
                        <!-- No hits/kills: both shots are unlinked; Shell should be filtered from Misses -->
                    </Events>
                </TacviewDebriefing>
                """
        ).lstrip()
        xml.write_text(xml_text, encoding="utf-8")
        proc = run_cli(str(xml), "--chains-combined")
        assert proc.returncode == 0
        assert "Misses:" in proc.stdout
        # Should not list Shell shot line
        assert "Weapon=GUN" not in proc.stdout
        # Bomb should be shown as miss
        assert "Weapon=B" in proc.stdout
