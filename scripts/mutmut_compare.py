#!/usr/bin/env python3
"""Compare two mutmut runs using the three-level acceptance rules in docs/testing/mutmut-runbook.md.

Read `*.meta` files in two directories (mutmut writes one per source module in `mutants/`), using
only `exit_code_by_key` (mutant name → exit code), not terminal summaries that omit unknown codes
such as segmentation faults.

Three levels:
1. Reworked mutants (`--reworked`): all must be killed.
2. Baseline-killed mutants must not survive; timeouts require fresh-process verification.
3. Baseline survivors not reworked: newly killed mutants are recorded without alarm; killing any
   declared equivalent (`--equivalent`) invalidates the entire run.

`exit code == 1` means killed, `0` survived; other codes require review, preventing acceptance until
resolved. Different mutant-name sets or same-function source hashes fail immediately: changed source
regenerates `mutants/`, invalidating comparison. Empty reworked lists are also invalid input.

No third-party dependencies. See `--help` and `docs/testing/mutmut-runbook.md`.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path

KILLED = 1
SURVIVED = 0

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_INVALID = 2


@dataclass
class ComparisonReport:
    """Three-level acceptance results; nonempty `invalid` makes remaining fields untrustworthy."""

    invalid: list[str] = field(default_factory=list)
    reworked_killed: list[str] = field(default_factory=list)
    reworked_survived: list[str] = field(default_factory=list)
    reworked_recheck: list[tuple[str, int]] = field(default_factory=list)
    baseline_killed_total: int = 0
    regressed: list[str] = field(default_factory=list)
    baseline_killed_recheck: list[tuple[str, int]] = field(default_factory=list)
    untouched_total: int = 0
    untouched_killed: list[str] = field(default_factory=list)
    equivalent_killed: list[str] = field(default_factory=list)
    equivalent_recheck: list[tuple[str, int]] = field(default_factory=list)

    @property
    def pending_recheck(self) -> bool:
        """Non-0/1 outcomes such as timeouts require fresh-process review before a conclusion.

        Level three reviews only equivalent mutants; other untouched kills are merely recorded and
        abnormal exit codes do not affect the conclusion.
        """
        return bool(self.reworked_recheck or self.baseline_killed_recheck or self.equivalent_recheck)

    @property
    def passed(self) -> bool:
        return not (
            self.invalid or self.reworked_survived or self.regressed or self.equivalent_killed or self.pending_recheck
        )


@dataclass(frozen=True)
class MetaSnapshot:
    """One mutmut run: mutant name → exit code and mutated-function source hashes."""

    exit_codes: Mapping[str, int | None]
    function_hashes: Mapping[str, str]


def load_meta(root: Path) -> MetaSnapshot:
    """Merge `exit_code_by_key` and `hash_by_function_name` across all directory `*.meta` files.

    Hash keys are module.function: mutant `lib.a.x_f__mutmut_3` has .meta `hash_by_function_name` key `x_f`; recover the
    module prefix from mutant names. Reject missing `hash_by_function_name` or any mutant function
    without a hash: source-hash checks are prerequisite, and omissions silently disable validation.
    """
    exit_codes: dict[str, int | None] = {}
    function_hashes: dict[str, str] = {}
    for meta in sorted(root.rglob("*.meta")):
        with meta.open(encoding="utf-8") as f:
            data = json.load(f)
        codes = data.get("exit_code_by_key")
        hashes = data.get("hash_by_function_name")
        if not isinstance(codes, dict) or not isinstance(hashes, dict):
            raise ValueError(f"{meta} is missing exit_code_by_key or hash_by_function_name")
        modules: set[str] = set()
        for key, code in codes.items():
            if not isinstance(key, str) or not (code is None or isinstance(code, int)):
                raise ValueError(f"{meta} exit_code_by_key has an invalid item: {key!r}: {code!r}")
            if key in exit_codes:
                raise ValueError(f"mutant {key} appears more than once under {root}")
            exit_codes[key] = code
            modules.add(key.partition("__mutmut_")[0].rpartition(".")[0])
        if len(modules) > 1:
            raise ValueError(f"{meta} mixes mutants from several modules: {sorted(modules)}")
        module = modules.pop() if modules else ""
        unhashed = sorted({key.partition("__mutmut_")[0].rpartition(".")[2] for key in codes} - set(hashes))
        if unhashed:
            raise ValueError(f"{meta} hash_by_function_name is missing the functions of these mutants: {unhashed}")
        for func, digest in hashes.items():
            if not isinstance(func, str) or not isinstance(digest, str):
                raise ValueError(f"{meta} hash_by_function_name has an invalid item: {func!r}: {digest!r}")
            function_hashes[f"{module}.{func}" if module else func] = digest
    if not exit_codes:
        raise ValueError(f"No *.meta under {root}, or their exit_code_by_key is empty")
    return MetaSnapshot(exit_codes=exit_codes, function_hashes=function_hashes)


def read_names(path: Path) -> list[str]:
    """One mutant name per line, ignoring empty lines and `#` comments."""
    names: list[str] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            names.append(stripped)
    return names


def compare(
    baseline: Mapping[str, int | None],
    current: Mapping[str, int | None],
    reworked: Iterable[str],
    equivalent: Iterable[str] = (),
    *,
    baseline_hashes: Mapping[str, str] | None = None,
    current_hashes: Mapping[str, str] | None = None,
) -> ComparisonReport:
    reworked_set = set(reworked)
    equivalent_set = set(equivalent)
    invalid: list[str] = []

    if not reworked_set:
        invalid.append("Reworked list is empty: no mutant to verify; check that the list file was generated correctly")
    changed_functions = sorted(
        func
        for func, digest in (baseline_hashes or {}).items()
        if func in (current_hashes or {}) and (current_hashes or {})[func] != digest
    )
    if changed_functions:
        invalid.append(
            f"{len(changed_functions)} function source hashes differ between baseline and this round: mutant names may be unchanged while their meaning changed; rebuild the baseline first"
        )
        invalid.extend(f"  source changed {func}" for func in changed_functions[:10])
    if baseline_hashes is not None or current_hashes is not None:
        hash_only_baseline = sorted(set(baseline_hashes or {}) - set(current_hashes or {}))
        hash_only_current = sorted(set(current_hashes or {}) - set(baseline_hashes or {}))
        if hash_only_baseline or hash_only_current:
            invalid.append(
                f"Function hash sets differ between baseline and this round (baseline only {len(hash_only_baseline)}, "
                f"this round only {len(hash_only_current)}): the source changed or .meta is incomplete; rebuild the baseline first"
            )
            invalid.extend(f"  baseline-only hash {func}" for func in hash_only_baseline[:10])
            invalid.extend(f"  this-round-only hash {func}" for func in hash_only_current[:10])
    missing = sorted(set(baseline) - set(current))
    extra = sorted(set(current) - set(baseline))
    if missing or extra:
        invalid.append(
            f"Mutant name sets differ between baseline and this round (baseline only {len(missing)}, this round only {len(extra)}): the source changed; rebuild the baseline first"
        )
        invalid.extend(f"  baseline only {name}" for name in missing[:10])
        invalid.extend(f"  this round only {name}" for name in extra[:10])
    invalid.extend(
        f"Reworked-list mutant is not in the baseline: {name}" for name in sorted(reworked_set - set(baseline))
    )
    invalid.extend(
        f"Reworked-list mutant is already killed in the baseline, so the rework cannot be shown to work: {name}"
        for name in sorted(reworked_set & set(baseline))
        if baseline[name] == KILLED
    )
    invalid.extend(
        f"Mutant is in both the reworked list and the equivalent-mutant list: {name}"
        for name in sorted(equivalent_set & reworked_set)
    )
    invalid.extend(
        f"Equivalent-list mutant is not in the baseline: {name}" for name in sorted(equivalent_set - set(baseline))
    )
    invalid.extend(
        f"Equivalent-list mutant is already killed in the baseline: equivalent mutants cannot be killed, so the baseline itself is suspect; check for a false-kill chain first: {name}"
        for name in sorted(equivalent_set & set(baseline))
        if baseline[name] == KILLED
    )
    if invalid:
        return ComparisonReport(invalid=invalid)

    report = ComparisonReport()
    for name in sorted(baseline):
        before = baseline[name]
        after = current[name]
        if name in reworked_set:
            if after == KILLED:
                report.reworked_killed.append(name)
            elif after == SURVIVED:
                report.reworked_survived.append(name)
            else:
                report.reworked_recheck.append((name, _code(after)))
        elif before == KILLED:
            report.baseline_killed_total += 1
            if after == SURVIVED:
                report.regressed.append(name)
            elif after != KILLED:
                report.baseline_killed_recheck.append((name, _code(after)))
        else:
            report.untouched_total += 1
            if after == KILLED:
                report.untouched_killed.append(name)
                if name in equivalent_set:
                    report.equivalent_killed.append(name)
            elif after != SURVIVED and name in equivalent_set:
                report.equivalent_recheck.append((name, _code(after)))
    return report


def _code(value: int | None) -> int:
    # None means mutmut unchecked; use a sentinel distinct from real exit codes so reports sort and print.
    return -1 if value is None else value


def render(report: ComparisonReport) -> str:
    lines: list[str] = []
    if report.invalid:
        lines.append("Comparison invalid:")
        lines.extend(report.invalid)
        return "\n".join(lines)

    lines.append("| Layer | Count | Result |")
    lines.append("| --- | ---: | --- |")
    reworked_total = len(report.reworked_killed) + len(report.reworked_survived) + len(report.reworked_recheck)
    lines.append(
        f"| Mutants targeted by this rework | {reworked_total} | killed {len(report.reworked_killed)}, "
        f"survived {len(report.reworked_survived)}, pending recheck {len(report.reworked_recheck)} |"
    )
    lines.append(
        f"| Mutants killed in the baseline | {report.baseline_killed_total} | regressed {len(report.regressed)}, "
        f"pending recheck {len(report.baseline_killed_recheck)} |"
    )
    lines.append(
        f"| Mutants surviving in the baseline and not reworked | {report.untouched_total} | incidentally killed {len(report.untouched_killed)}, "
        f"of which equivalent mutants {len(report.equivalent_killed)}, equivalent mutants pending recheck {len(report.equivalent_recheck)} |"
    )

    _section(lines, "Still surviving after rework (rework ineffective)", report.reworked_survived)
    _section(
        lines,
        "Pending recheck after rework (a new process runs only the related tests; 1 failed means killed)",
        _with_codes(report.reworked_recheck),
    )
    _section(lines, "Regressed (killed in the baseline, surviving this round)", report.regressed)
    _section(
        lines,
        "Baseline killed now pending recheck (recheck in a new process; 1 failed means the guard holds; only all passing is a regression)",
        _with_codes(report.baseline_killed_recheck),
    )
    _section(lines, "Incidentally killed (recorded only)", report.untouched_killed)
    _section(
        lines,
        "Equivalent mutants killed: the whole round is void; check for a false-kill chain first",
        report.equivalent_killed,
    )
    _section(
        lines,
        "Equivalent mutants pending recheck (recheck in a new process; 1 failed means killed and the whole round is void)",
        _with_codes(report.equivalent_recheck),
    )
    lines.append("")
    if report.passed:
        lines.append("Verification passed")
    elif report.reworked_survived or report.regressed or report.equivalent_killed:
        lines.append("Verification failed")
    else:
        lines.append(
            "Verification incomplete: items are pending recheck; recheck them in a new process, update the baseline or this round's .meta from the result, then compare again"
        )
    return "\n".join(lines)


def _with_codes(items: list[tuple[str, int]]) -> list[str]:
    return [f"{name}  exit code {code}" for name, code in items]


def _section(lines: list[str], title: str, items: list[str]) -> None:
    if not items:
        return
    lines.append("")
    lines.append(f"## {title}（{len(items)}）")
    lines.extend(f"- {item}" for item in items)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument(
        "--baseline", type=Path, required=True, help="Directory holding the *.meta files of the round before the rework"
    )
    parser.add_argument(
        "--current",
        type=Path,
        required=True,
        help="Directory holding the *.meta files of the rerun after the rework, usually mutants/",
    )
    parser.add_argument(
        "--reworked", type=Path, required=True, help="List of mutants targeted by this rework, one per line"
    )
    parser.add_argument(
        "--equivalent",
        type=Path,
        help="List of mutants judged equivalent, one per line; if any is killed the whole round is void",
    )
    args = parser.parse_args(argv)

    try:
        baseline = load_meta(args.baseline)
        current = load_meta(args.current)
        reworked = read_names(args.reworked)
        equivalent = read_names(args.equivalent) if args.equivalent else []
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"Failed to read input: {exc}", file=sys.stderr)
        return EXIT_INVALID

    report = compare(
        baseline.exit_codes,
        current.exit_codes,
        reworked,
        equivalent,
        baseline_hashes=baseline.function_hashes,
        current_hashes=current.function_hashes,
    )
    print(render(report))
    if report.invalid:
        return EXIT_INVALID
    return EXIT_OK if report.passed else EXIT_FAILED


if __name__ == "__main__":
    sys.exit(main())
