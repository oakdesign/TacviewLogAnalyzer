from __future__ import annotations

import argparse
from pathlib import Path

from . import __version__


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
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.xml is None:
        parser.print_help()
        return 0

    # Placeholder for future business logic
    print(f"[skeleton] Would analyze: {args.xml}")
    if args.output:
        print(f"[skeleton] Would write report to: {args.output}")

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
