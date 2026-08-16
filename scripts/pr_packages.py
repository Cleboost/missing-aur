#!/usr/bin/env python3
"""List package app names changed relative to a git base ref."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from lib.git_changed import changed_apps


def main() -> None:
    ap = argparse.ArgumentParser(description="List changed package app directories")
    ap.add_argument(
        "--base",
        default="origin/main",
        help="Git base ref to compare against (default: origin/main)",
    )
    args = ap.parse_args()
    apps = changed_apps(args.base)
    if apps:
        print(" ".join(apps))


if __name__ == "__main__":
    main()
