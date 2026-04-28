"""
    pint.pint_convert
    ~~~~~~~~~~~~~~~~~

    Command-line tool for unit conversion.
"""
from __future__ import annotations

import argparse
import sys


def main():
    """Main entry point for pint-convert command."""
    parser = argparse.ArgumentParser(
        description="Convert between units using pint."
    )
    parser.add_argument(
        "value",
        type=str,
        help="Value with units to convert (e.g., '10 m')",
    )
    parser.add_argument(
        "target",
        type=str,
        nargs="?",
        help="Target units (e.g., 'ft')",
    )

    args = parser.parse_args()

    from . import UnitRegistry

    ureg = UnitRegistry()

    try:
        q = ureg.parse_expression(args.value)

        if args.target:
            q = q.to(args.target)

        print(q)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
