"""``python -m arcreel_catalog_core``: CLI used by catalog data repository CI."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Sequence
from pathlib import Path

from .dataset import CATALOG_FILENAME, MANIFEST_FILENAME, check_catalog_files, make_manifest
from .reading import CatalogFormatError


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m arcreel_catalog_core")
    commands = parser.add_subparsers(dest="command", required=True)
    check = commands.add_parser("check", help=f"Validate {MANIFEST_FILENAME} and {CATALOG_FILENAME} in the directory")
    check.add_argument("directory", type=Path)
    write = commands.add_parser("write-manifest", help=f"Write {MANIFEST_FILENAME} from {CATALOG_FILENAME}")
    write.add_argument("directory", type=Path)
    args = parser.parse_args(argv)
    directory: Path = args.directory
    catalog_content = (directory / CATALOG_FILENAME).read_bytes()

    if args.command == "write-manifest":
        try:
            manifest = make_manifest(catalog_content)
        except CatalogFormatError as exc:
            for issue in exc.issues:
                print(issue, file=sys.stderr)
            return 1
        (directory / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        return 0

    issues = check_catalog_files((directory / MANIFEST_FILENAME).read_bytes(), catalog_content)
    for issue in issues:
        print(issue, file=sys.stderr)
    return 1 if issues else 0
