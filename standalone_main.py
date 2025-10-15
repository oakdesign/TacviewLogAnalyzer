#!/usr/bin/env python3
"""Standalone entry point for TacviewLogAnalyzer executable."""

import sys
from pathlib import Path

# Add the package to Python path for absolute imports
package_dir = Path(__file__).parent / 'src'
if package_dir.exists():
    sys.path.insert(0, str(package_dir))

# Now import and run
try:
    from tacview_log_analyzer.cli import main
    raise SystemExit(main())
except ImportError as e:
    print(f"Import error: {e}")
    print(f"Python path: {sys.path}")
    sys.exit(1)