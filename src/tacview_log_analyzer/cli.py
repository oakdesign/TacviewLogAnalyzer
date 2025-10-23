from __future__ import annotations

import argparse
import os
import socket
import sys
import webbrowser
from pathlib import Path

from . import __version__
from .linking import (extract_shots_hits_kills, link_events_combined,
                      link_events_deterministic, link_events_heuristic,
                      render_chains, render_leftovers)
from .parser import parse_file
from .stats import (accumulate_pilot_stats, compute_aa_kills_by_target,
                    compute_flight_outcomes_by_pilot,
                    compute_flight_time_by_pilot, render_aa_kills_by_target,
                    render_pilot_stats)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tacview-analyze",
        description="Tacview Log Analyzer (skeleton). Parses XML logs and generates statistics.",
    )
    parser.add_argument(
        "xml",
        nargs="?",
        type=Path,
        help="Path to Tacview XML log file to analyze",
    )
    parser.add_argument(
        "-V",
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
        help="Show version and exit",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Optional output path for generated report (not implemented)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Print per-pilot summary (shots, hits, kills)",
    )
    parser.add_argument(
        "--chains",
        action="store_true",
        help="Print linked chains (deterministic) and unlinked leftovers",
    )
    parser.add_argument(
        "--leftovers-limit",
        type=int,
        default=20,
        help="Max lines to show per leftovers section (0 = no limit)",
    )
    parser.add_argument(
        "--no-leftovers",
        action="store_true",
        help="When used with --chains, suppress printing leftovers",
    )
    parser.add_argument(
        "--chains-heuristic",
        action="store_true",
        help="Print chains from heuristic linking (e.g., bombs ripples) and leftovers",
    )
    parser.add_argument(
        "--chains-combined",
        action="store_true",
        help="Run deterministic linking first, then heuristic on leftovers; print chains and Misses (excluding Shell & Parachutist)",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help="Start local web UI (FastAPI) to browse the tree view; use path argument to pre-load a file",
    )
    parser.add_argument(
        "--web-host",
        default="127.0.0.1",
        help="Host interface to bind the web UI (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--web-port",
        type=int,
        default=8000,
        help="TCP port for the web UI (default: 8000)",
    )
    parser.add_argument(
        "--web-auto-port",
        action="store_true",
        help="If the chosen port can't be bound, try common alternates automatically (8090, 9000, 5000, 5500, 18080)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    
    # Check if running without arguments (likely double-clicked)
    if argv is None:
        argv = sys.argv[1:]
    
    # If no arguments provided, auto-start web mode for user convenience
    if not argv:
        print("🚀 Tacview Log Analyzer - Web Interface")
        print("=" * 50)
        print("No arguments provided - starting web interface...")
        print("📁 Place XML files in the same folder as this executable")
        print("🌐 The web interface will open in your browser")
        print("❌ Press Ctrl+C to exit\n")
        
        # Auto-start web mode with user-friendly defaults
        argv = ["--web", "--web-auto-port"]
    
    args = parser.parse_args(argv)

    if args.web:
        try:
            import uvicorn  # type: ignore
        except Exception:
            print("Web UI requires optional deps: fastapi, uvicorn, jinja2. Install with: pip install .[dev]")
            return 1
        # Optionally pass xml path via env var consumed by web_entry
        if args.xml is not None:
            os.environ["TLA_XML"] = str(args.xml)
        # Probe port availability/permission and optionally auto-pick
        def _can_bind(host: str, port: int) -> bool:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind((host, port))
                return True
            except OSError:
                return False

        host = str(args.web_host)
        port = int(args.web_port)
        auto_started = not sys.argv[1:]  # True if started with no arguments (auto mode)
        
        if not _can_bind(host, port):
            if args.web_auto_port:
                for p in [8090, 9000, 5000, 5500, 18080]:
                    if p == port:
                        continue
                    if _can_bind(host, p):
                        port = p
                        if auto_started:
                            print(f"⚠️  Port {args.web_port} unavailable - using port {port}")
                        else:
                            print(f"[web] Port {args.web_port} unavailable or not permitted; switching to {port}")
                        break
                else:
                    print("[web] No alternative port found. Try --web-host 0.0.0.0 or run on a permitted port.")
                    return 1
            else:
                print(f"[web] Cannot bind to {host}:{port}. Try --web-port 8090 or --web-auto-port.")
                return 1

        # Auto-open browser when started without arguments (double-clicked)
        if auto_started:
            url = f"http://{host}:{port}"
            print(f"🌐 Starting web server at {url}")
            print("📂 Opening browser...")
            try:
                webbrowser.open(url)
            except Exception as e:
                print(f"⚠️  Could not auto-open browser: {e}")
                print(f"   Please manually open: {url}")
        
        uvicorn.run(
            "tacview_log_analyzer.web_entry:app",
            host=host,
            port=port,
            reload=False,
        )
        return 0

    if args.xml is None:
        parser.print_help()
        return 0

    print(f"[skeleton] Would analyze: {args.xml}")

    if args.summary:
        deb = parse_file(args.xml)
        stats = accumulate_pilot_stats(deb.events)
        outcomes = compute_flight_outcomes_by_pilot(deb.events)
        # Get chains and shots for A-A kills analysis
        chains, _, _, _ = link_events_combined(deb.events)
        shots_all, _, _, _ = extract_shots_hits_kills(deb.events)
        aa_kills = compute_aa_kills_by_target(chains, shots_all)
        
        # derive ftimes for compatibility
        ftimes = {p: d for p, (d, _r) in outcomes.items()}
        # augment render with end reasons appended
        # to keep render_pilot_stats simple, post-process its string
        base = render_pilot_stats(stats, ftimes)
        lines = []
        for line in base.splitlines():
            # line starts with pilot name
            pilot = line.split(":", 1)[0]
            reason = outcomes[pilot][1] if pilot in outcomes else None
            if reason:
                line = f"{line} · FlightEnded {reason}"
            lines.append(line)
        print("\n".join(lines))
        
        # Add A-A kills by target
        aa_summary = render_aa_kills_by_target(aa_kills)
        print(aa_summary)
    elif args.chains:
        deb = parse_file(args.xml)
        chains, l_shots, l_hits, l_kills = link_events_deterministic(deb.events, consume=True)
        for line in render_chains(chains):
            print(line)
        if not args.no_leftovers:
            for line in render_leftovers(l_shots, l_hits, l_kills, limit=args.leftovers_limit):
                print(line)
    elif args.chains_heuristic:
        deb = parse_file(args.xml)
        chains, l_shots, l_hits, l_kills = link_events_heuristic(deb.events)
        for line in render_chains(chains):
            print(line)
        if not args.no_leftovers:
            for line in render_leftovers(l_shots, l_hits, l_kills, limit=args.leftovers_limit):
                print(line)
    elif args.chains_combined:
        deb = parse_file(args.xml)
        chains, l_shots, l_hits, l_kills = link_events_combined(deb.events)
        for line in render_chains(chains):
            print(line)
        if not args.no_leftovers:
            for line in render_leftovers(
                l_shots,
                l_hits,
                l_kills,
                limit=args.leftovers_limit,
                exclude_shot_types=["Shell", "Parachutist"],
                shots_label="Misses",
            ):
                print(line)
    else:
        print("[skeleton] No action requested. Try --summary.")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
