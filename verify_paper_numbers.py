#!/usr/bin/env python3
"""
verify_paper_numbers.py — Standalone CLI to verify paper #1296's numerical
claims against the canonical reproducibility tarball.

Usage:
    # Verify against the tarball directly (extracts to a temp dir, cleans up).
    # Paper sources are auto-resolved from the tarball's `paper/` subdirectory.
    python verify_paper_numbers.py --tarball neurips_1296_bundle.tar.gz

    # Verify against an already-extracted depository, with paper from a
    # separate location:
    python verify_paper_numbers.py --depository /path/to/NeurIPS2026_1296 \\
                                   --paper /path/to/paper

    # Strict mode: exit 1 on any FAIL
    python verify_paper_numbers.py --tarball bundle.tar.gz --strict

    # Verbose: also print PASS lines
    python verify_paper_numbers.py --tarball bundle.tar.gz --verbose

This script asserts every numerical claim in the NeurIPS 2026 paper #1296.
For each claim, the script extracts the value from the paper's .tex source
files at runtime AND extracts the corresponding canonical value from the
reproducibility depository (CSVs/JSONs) at runtime, then compares them within
tolerance. Neither side hard-codes expected values — open verifier_core.py
to inspect the paper-extractor / canonical-extractor pairs that define what
is being checked.

Tolerance defaults:
    ±0.001  for individual values where paper is precise (3+ decimal places)
    ±0.005  for cross-method aggregates
    ±0.01   for "≈ X" claims rounded to 2 decimal places
    ±0.05   for "≈ X" claims rounded to 1 decimal place
    p ≤ X   checked as inequality (canonical ≤ paper bound)

Exit codes:
    0   no FAIL claims (default behavior, regardless of FAIL count)
    1   one or more FAIL claims AND --strict was set
    2   one or more ERROR conditions (missing source file, malformed CSV,
        broken paper extractor, etc.) — always exits 2 on error.
"""

from __future__ import annotations

import argparse
import shutil
import sys
import tarfile
import tempfile
from pathlib import Path

# Allow running from anywhere — add this script's dir to path
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import paper_extractors as pe
import verifier_core as vc


def _find_depository_root(extract_dir: Path) -> Path:
    """The tarball top-level should contain a single directory `NeurIPS2026_1296/`.
    Find it. If not, look for the canonical sentinel files at depth ≤ 2.
    """
    sentinel = "multi_criteria_outputs"
    if (extract_dir / sentinel).is_dir():
        return extract_dir
    for child in extract_dir.iterdir():
        if child.is_dir() and (child / sentinel).is_dir():
            return child
    raise FileNotFoundError(
        f"Could not find depository root in {extract_dir}. "
        f"Expected a directory containing '{sentinel}/'."
    )


def _find_paper_dir(extract_dir: Path) -> Path:
    """The tarball should contain a `paper/` subdirectory with the .tex sources.

    Look for it inside the depository root, then directly inside extract_dir.
    """
    # Try inside the depository root first
    try:
        dep_root = _find_depository_root(extract_dir)
        paper_dir = dep_root / "paper"
        if paper_dir.is_dir() and any(paper_dir.glob("*.tex")):
            return paper_dir
    except FileNotFoundError:
        pass
    # Fall back to extract_dir/paper or extract_dir
    for candidate in (extract_dir / "paper", extract_dir):
        if candidate.is_dir() and any(candidate.glob("*.tex")):
            return candidate
    raise FileNotFoundError(
        f"Could not find paper sources in {extract_dir}. "
        f"Expected a `paper/` directory containing main.tex and appendix .tex files."
    )


def _extract_tarball(tarball_path: Path, dest: Path) -> Path:
    if not tarball_path.exists():
        sys.stderr.write(f"ERROR: tarball not found: {tarball_path}\n")
        sys.exit(2)
    with tarfile.open(tarball_path, "r:*") as tf:
        # Safe extraction (Python 3.12+ supports `filter`; older versions fall back)
        try:
            tf.extractall(dest, filter="data")
        except TypeError:
            tf.extractall(dest)
    return dest


def main(argv=None):
    p = argparse.ArgumentParser(
        description="Verify NeurIPS 2026 paper #1296 numerical claims against canonical outputs.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--tarball", type=Path,
                     help="Path to neurips_1296_bundle.tar.gz. Paper sources are "
                          "auto-resolved from the tarball's `paper/` subdirectory.")
    src.add_argument("--depository", type=Path,
                     help="Path to an already-extracted NeurIPS2026_1296 directory. "
                          "Use with --paper to specify paper-source location.")
    p.add_argument("--paper", type=Path, default=None,
                   help="Path to the directory containing the paper's .tex sources "
                        "(main.tex, appendix_*.tex, etc.). If omitted, looks for "
                        "`<depository>/paper/`.")
    p.add_argument("--strict", action="store_true",
                   help="Exit 1 if any FAIL. Default: exit 0 with FAIL summary.")
    p.add_argument("--verbose", "-v", action="store_true",
                   help="Print PASS lines too. Default: summarize PASSes, list FAILs.")
    p.add_argument("--no-color", action="store_true",
                   help="Disable ANSI color codes in output.")
    args = p.parse_args(argv)

    # ANSI colors (disabled if not a TTY or --no-color)
    use_color = (not args.no_color) and sys.stdout.isatty()
    GREEN = "\033[92m" if use_color else ""
    RED   = "\033[91m" if use_color else ""
    YEL   = "\033[93m" if use_color else ""
    DIM   = "\033[2m"  if use_color else ""
    RESET = "\033[0m"  if use_color else ""

    print()
    print("=" * 78)
    print("  NeurIPS 2026 paper #1296 — paper-vs-canonical verifier")
    print("=" * 78)

    # Locate the depository and paper sources
    tmpdir = None
    if args.depository:
        dep_root = args.depository.resolve()
        if not dep_root.exists():
            sys.stderr.write(f"ERROR: depository not found: {dep_root}\n")
            sys.exit(2)
        try:
            dep_root = _find_depository_root(dep_root)
        except FileNotFoundError as e:
            if (dep_root / "multi_criteria_outputs").is_dir():
                pass  # already at root
            else:
                sys.stderr.write(f"ERROR: {e}\n")
                sys.exit(2)

        # Resolve paper sources: explicit --paper, else <depository>/paper/
        if args.paper is not None:
            paper_dir = args.paper.resolve()
        else:
            paper_dir = dep_root / "paper"
        if not paper_dir.is_dir() or not any(paper_dir.glob("*.tex")):
            sys.stderr.write(
                f"ERROR: paper sources not found at {paper_dir}.\n"
                f"  Pass --paper /path/to/paper, or ensure your depository has a paper/ subdir.\n"
            )
            sys.exit(2)
        print(f"  Depository:  {dep_root}")
        print(f"  Paper dir:   {paper_dir}")
    else:
        # Tarball mode: extract, find depository, find paper inside it
        tmpdir = Path(tempfile.mkdtemp(prefix="verify_1296_"))
        print(f"  Extracting tarball to: {tmpdir}")
        _extract_tarball(args.tarball.resolve(), tmpdir)
        try:
            dep_root = _find_depository_root(tmpdir)
            paper_dir = _find_paper_dir(tmpdir)
        except FileNotFoundError as e:
            sys.stderr.write(f"ERROR: {e}\n")
            sys.exit(2)
        # Allow --paper to override the in-tarball paper dir
        if args.paper is not None:
            paper_dir = args.paper.resolve()
            if not paper_dir.is_dir() or not any(paper_dir.glob("*.tex")):
                sys.stderr.write(f"ERROR: --paper path has no .tex files: {paper_dir}\n")
                sys.exit(2)
        print(f"  Depository:  {dep_root}")
        print(f"  Paper dir:   {paper_dir}")

    # Load paper sources
    try:
        paper_sources = pe.load_paper_sources(paper_dir)
    except Exception as e:
        sys.stderr.write(f"ERROR: failed to load paper sources: {e}\n")
        sys.exit(2)
    print(f"  Paper files: {', '.join(sorted(paper_sources.keys()))}")
    print(f"  Total checks:      {len(vc.CHECKS)}")
    print("=" * 78)
    print()

    try:
        results = vc.run_all(paper_sources, dep_root)
    finally:
        if tmpdir is not None and tmpdir.exists():
            try:
                shutil.rmtree(tmpdir)
            except Exception as e:
                sys.stderr.write(f"WARNING: could not clean up temp dir {tmpdir}: {e}\n")

    n_pass = sum(1 for r in results if r.status == "PASS")
    n_fail = sum(1 for r in results if r.status == "FAIL")
    n_err  = sum(1 for r in results if r.status == "ERROR")

    if args.verbose:
        for r in results:
            if r.status == "PASS":
                print(f"  {GREEN}[PASS]{RESET} {DIM}{r.check.description}{RESET}")
        if n_pass > 0:
            print()

    # Always show FAILs and ERRORs
    if n_fail > 0:
        print(f"{RED}--- FAILED CHECKS ---{RESET}")
        for r in results:
            if r.status == "FAIL":
                line = vc.format_result(r)
                print(line.replace("[FAIL]", f"{RED}[FAIL]{RESET}"))
                print()

    if n_err > 0:
        print(f"{YEL}--- ERROR CHECKS ---{RESET}")
        for r in results:
            if r.status == "ERROR":
                line = vc.format_result(r)
                print(line.replace("[ERR ]", f"{YEL}[ERR ]{RESET}"))
                print()

    # Summary
    print("=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    print(f"  Total checks:  {len(results)}")
    pass_color = GREEN if n_pass == len(results) else ""
    print(f"  {pass_color}Passed:        {n_pass}{RESET}")
    fail_color = RED if n_fail > 0 else ""
    print(f"  {fail_color}Failed:        {n_fail}{RESET}")
    err_color  = YEL if n_err > 0 else ""
    print(f"  {err_color}Errors:        {n_err}{RESET}")
    print("=" * 78)

    if n_err > 0:
        print()
        print(f"  {YEL}NOTE:{RESET} Errors usually indicate one of:")
        print(f"        - the depository is incomplete (missing canonical CSV/JSON)")
        print(f"        - the paper was edited in a way that broke an extractor's regex")
        print(f"        - the tarball or paper directory was modified post-release.")
        print(f"        Each check has paper_loc and a description; open verifier_core.py")
        print(f"        to see exactly what each check extracts and compares.")
        sys.exit(2)

    if n_fail > 0:
        print()
        print(f"  {RED}NOTE:{RESET} Failed checks indicate paper claims that do not match the canonical")
        print(f"        outputs within tolerance. Either the paper was edited post-tarball-release,")
        print(f"        or the canonical CSVs were modified. Each [FAIL] line above shows both")
        print(f"        the paper-extracted value and the canonical-extracted value, plus the")
        print(f"        paper_loc telling you where in the .tex source the claim appears.")
        if args.strict:
            sys.exit(1)

    print()
    sys.exit(0)


if __name__ == "__main__":
    main()
