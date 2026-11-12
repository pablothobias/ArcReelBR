#!/usr/bin/env python3
"""Run full quality gates by domain, with only one run per machine at a time.

    uv run python scripts/gate.py --changed            # Select domains from changes relative to origin/main
    uv run python scripts/gate.py backend frontend     # Name domains explicitly
    uv run python scripts/gate.py --list               # Show domain trigger paths and steps

Full-gate pytest and vitest runs parallelize using machine cores. Concurrent worktrees
compete for them, with vitest jsdom cases timing out first. A machine-level file lock
queues gate runs: the holder uses the machine exclusively through completion, while
queued runs print only waiting information. Domain commands and triggers are defined
only here.

The lock defaults to the user directory, visible to all worktrees on the machine;
`ARCREEL_GATE_LOCK` overrides its path. Stop at the first failed command with its exit
code, just like chaining commands with `&&`.
"""

from __future__ import annotations

import argparse
import fnmatch
import os
import subprocess
import sys
import time
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path
from typing import IO

import portalocker

ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = Path(os.environ.get("ARCREEL_GATE_LOCK") or Path.home() / ".cache" / "arcreel" / "gate.lock")


@dataclass(frozen=True)
class Step:
    argv: tuple[str, ...]
    cwd: Path = ROOT

    def describe(self) -> str:
        command = " ".join(self.argv)
        return command if self.cwd == ROOT else f"{command}    # cwd={self.cwd.relative_to(ROOT)}"


UV = ("uv", "run")
# Domain → steps. See pytest configuration comments in pyproject.toml for `-n 4 --dist loadfile`,
# and the backend test step in .github/workflows/test.yml for `--max-worker-restart=0`.
DOMAINS: dict[str, tuple[Step, ...]] = {
    "backend": (
        Step((*UV, "ruff", "check", ".")),
        Step((*UV, "ruff", "format", "--check", ".")),
        Step((*UV, "basedpyright", "--warnings")),
        Step((*UV, "lint-imports")),
        Step((*UV, "deptry", "lib", "server", "alembic", "scripts", "tests")),
        Step((*UV, "python", "-m", "pytest", "-n", "4", "--dist", "loadfile", "--max-worker-restart=0")),
    ),
    "market-core": (
        Step((*UV, "deptry", "src", "tests"), ROOT / "packages" / "arcreel-market-core"),
        Step((*UV, "python", "-m", "pytest"), ROOT / "packages" / "arcreel-market-core"),
    ),
    "catalog-core": (
        Step((*UV, "deptry", "src", "tests"), ROOT / "packages" / "arcreel-catalog-core"),
        Step((*UV, "python", "-m", "pytest"), ROOT / "packages" / "arcreel-catalog-core"),
    ),
    "tests": (Step((*UV, "python", "scripts/audit_tests.py", "--check")),),
    "conventions": (Step((*UV, "python", "scripts/audit_conventions.py", "--check")),),
    "workflows": (
        Step((*UV, "pre-commit", "run", "--all-files", "actionlint")),
        Step((*UV, "pre-commit", "run", "--all-files", "zizmor")),
    ),
    "frontend": (Step(("pnpm", "check"), ROOT / "frontend"),),
    "website": (Step(("pnpm", "check"), ROOT / "website"),),
}

# Domain → trigger paths, using fnmatch wildcards (`*` also crosses directory separators).
# Maintain alongside CI .github/actions/domain-filter/action.yml: CI backend maps to backend,
# market-core and catalog-core here; workflow maps to workflows. CI docker (Dockerfile, public/)
# has no local gate. The tests and conventions domains are structural audits taking seconds;
# triggers such as newly added exemption comments cannot be inferred from paths, so always
# include them when selecting domains from changes.
TRIGGERS: dict[str, tuple[str, ...]] = {
    "backend": (
        "lib/*",
        "server/*",
        "alembic/*",
        "alembic.ini",
        "scripts/*",
        "tests/*",
        "agent_runtime_profile/*",
        "packages/*",
        "pyproject.toml",
        "uv.lock",
        ".gitignore",  # ruff file discovery respects gitignore
        # Frontend sources read directly by backend contract tests
        "frontend/src/i18n/*/dashboard.ts",
        "frontend/src/i18n/*/events.ts",
        "frontend/src/types/workflow.ts",
        "frontend/src/data/example-templates/*",
        "frontend/src/test/contracts/*",
    ),
    "market-core": ("packages/arcreel-market-core/*",),
    "catalog-core": ("packages/arcreel-catalog-core/*",),
    "workflows": (".github/*", ".pre-commit-config.yaml"),
    "frontend": ("frontend/*",),
    # website-checks also reports missing/stale translation-lockfile entries, with special mappings for CONTRIBUTING and both READMEs
    "website": ("website/*", "CONTRIBUTING.md", "README.md", "README.en.md", ".claude/skills/translate-docs/*"),
}
ALWAYS_WHEN_CHANGED = ("tests", "conventions")


def select_domains(paths: Iterable[str]) -> list[str]:
    """Select domains by changed paths in DOMAINS order; always include the audits that take seconds."""
    changed = list(paths)
    hit = {
        name
        for name, patterns in TRIGGERS.items()
        if any(fnmatch.fnmatchcase(path, pattern) for path in changed for pattern in patterns)
    }
    hit.update(ALWAYS_WHEN_CHANGED)
    return [name for name in DOMAINS if name in hit]


def _vcs(root: Path, *args: str) -> str:
    # Decode paths as UTF-8 regardless of platform locale; preserve non-UTF-8 bytes with surrogateescape.
    completed = subprocess.run(
        ("git", *args),  # noqa: S607 -- git is intentionally resolved through PATH in the developer environment
        cwd=root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="surrogateescape",
        check=True,
    )
    return completed.stdout


def changed_paths(base: str, root: Path = ROOT) -> list[str]:
    """All changes from the common ancestor of base and HEAD: committed, uncommitted and untracked.

    Disable rename detection to list both old and new paths of moved files: the old
    domain may fail because the file is absent. Read NUL-separated paths so non-ASCII
    paths remain original text rather than quoted escape sequences.
    """
    merge_base = _vcs(root, "merge-base", base, "HEAD").strip()
    tracked = _vcs(root, "diff", "--name-only", "--no-renames", "-z", merge_base).split("\0")
    untracked = _vcs(root, "ls-files", "--others", "--exclude-standard", "-z").split("\0")
    return sorted({*tracked, *untracked} - {""})


def _holder_note() -> str:
    try:
        note = LOCK_PATH.read_text(encoding="utf-8").strip()
    except OSError:
        return ""
    return f" (current holder: {note})" if note else ""


def _write_holder(handle: IO[str] | None, note: str) -> None:
    """The lock file contains the holder description, letting queued runs identify the active runner."""
    if handle is None:
        return
    handle.seek(0)
    handle.truncate()
    handle.write(note)
    handle.flush()


def _acquire_gate_lock() -> portalocker.Lock:
    """Return after acquiring the machine lock; retry once per second while held, announcing the queue only once."""
    LOCK_PATH.parent.mkdir(parents=True, exist_ok=True)
    # Holder descriptions contain non-ASCII text; explicitly read/write UTF-8 to avoid Windows locale encoding.
    lock = portalocker.Lock(LOCK_PATH, mode="a", encoding="utf-8")
    waited_from = time.monotonic()
    announced = False
    while True:
        try:
            lock.acquire(timeout=0, fail_when_locked=True)
        except portalocker.AlreadyLocked:
            if not announced:
                print(f"[gate] another gate run is active; queued waiting on {LOCK_PATH}{_holder_note()}", flush=True)
                announced = True
            time.sleep(1.0)
            continue
        if announced:
            print(f"[gate] acquired the lock after waiting {time.monotonic() - waited_from:.0f}s", flush=True)
        return lock


def _run(step: Step) -> int:
    started = time.monotonic()
    print(f"\n$ {step.describe()}", flush=True)
    code = subprocess.run(step.argv, cwd=step.cwd, check=False).returncode
    print(f"[gate] {'ok' if code == 0 else f'exit {code}'} in {time.monotonic() - started:.0f}s", flush=True)
    return code


def run_domains(domains: list[str]) -> int:
    steps = [step for name in domains for step in DOMAINS[name]]
    lock = _acquire_gate_lock()
    try:
        _write_holder(lock.fh, f"pid {os.getpid()} · {ROOT} · {' '.join(domains)}")
        started = time.monotonic()
        for step in steps:
            code = _run(step)
            if code != 0:
                return code
        print(f"\n[gate] {' '.join(domains)} all passed in {time.monotonic() - started:.0f}s", flush=True)
        return 0
    finally:
        _write_holder(lock.fh, "")
        lock.release()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("domains", nargs="*", metavar="DOMAIN", help="|".join(DOMAINS))
    parser.add_argument(
        "--changed",
        nargs="?",
        const="origin/main",
        metavar="BASE",
        help="Select domains from changes relative to BASE (default origin/main); can be combined with named domains",
    )
    parser.add_argument("--list", action="store_true", help="List each domain's trigger paths and steps, then exit")
    args = parser.parse_args(argv)
    if args.list:
        for name, steps in DOMAINS.items():
            triggers = TRIGGERS.get(name)
            print(f"{name}    # {' '.join(triggers) if triggers else 'always runs when selecting by changes'}")
            for step in steps:
                print(f"  {step.describe()}")
        return 0
    unknown = [name for name in args.domains if name not in DOMAINS]
    if unknown:
        parser.error(f"Unknown domains: {', '.join(unknown)}; choose from {', '.join(DOMAINS)}")
    selected: set[str] = set(args.domains)
    if args.changed is not None:
        try:
            paths = changed_paths(args.changed)
        except subprocess.CalledProcessError as error:
            parser.error(f"Failed to read changes relative to {args.changed}: {error.stderr.strip()}")
        picked = select_domains(paths)
        print(
            f"[gate] {len(paths)} files changed relative to {args.changed}; matched domains: {' '.join(picked)}",
            flush=True,
        )
        selected.update(picked)
    domains = [name for name in DOMAINS if name in selected]
    if not domains:
        parser.error("Give at least one domain name or --changed, or use --list to see them")
    return run_domains(domains)


if __name__ == "__main__":
    sys.exit(main())
