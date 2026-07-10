#!/usr/bin/env python3
"""Generate Software Bill of Materials (SBOM) for Zayd release artifacts.

Reads uv.lock and pnpm-lock.yaml to produce a structured SBOM JSON document
with dependency versions, licenses (where available), and checksums.

Usage:
    python scripts/generate-sbom.py [--output sbom.json] [--verbose]

Output (stdout or --output file):
    A JSON document with 'metadata', 'python', 'typescript', and 'digest' keys.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
UV_LOCK = REPO_ROOT / "uv.lock"
PNPM_LOCK = REPO_ROOT / "pnpm-lock.yaml"
SBOM_VERSION = "zayd-sbom-v1"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Zayd SBOM")
    parser.add_argument(
        "--output", "-o",
        type=str,
        default=None,
        help="Write SBOM to file instead of stdout",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print progress information",
    )
    return parser.parse_args()


def log(msg: str, verbose: bool = False) -> None:
    if verbose:
        print(f"[sbom] {msg}", file=sys.stderr)


# ----------------------------------------------------------------
# Python dependencies (uv.lock)
# ----------------------------------------------------------------


def parse_uv_lock(path: Path) -> list[dict[str, Any]]:
    """Extract Python dependency metadata from uv.lock (TOML format)."""
    try:
        import tomllib  # Python 3.11+
    except ImportError:
        import tomli as tomllib  # type: ignore[import-untyped]

    with open(path, "rb") as f:
        data = tomllib.load(f)

    deps: list[dict[str, Any]] = []
    for pkg in data.get("package", []):
        name = pkg.get("name", "unknown")
        version = pkg.get("version", "0.0.0")
        source = pkg.get("source", {})
        sdist = pkg.get("sdist") or {}
        wheels = pkg.get("wheels") or []

        # Extract the best available hash
        hashes: list[str] = []
        if sdist.get("hash"):
            hashes.append(sdist["hash"])
        for wheel in wheels:
            if wheel.get("hash"):
                hashes.append(wheel["hash"])

        dep: dict[str, Any] = {
            "name": name,
            "version": version,
            "type": "python",
            "source": source.get("registry", "unknown"),
        }
        if hashes:
            dep["hashes"] = hashes
        deps.append(dep)

    return deps


# ----------------------------------------------------------------
# TypeScript / Node dependencies (pnpm-lock.yaml)
# ----------------------------------------------------------------


def parse_pnpm_lock(path: Path) -> list[dict[str, Any]]:
    """Extract JS dependency metadata from pnpm-lock.yaml."""
    try:
        import yaml  # pyyaml
    except ImportError:
        log("WARNING: PyYAML not installed -- skipping pnpm-lock.yaml parsing")
        return []

    with open(path, encoding="utf-8") as f:
        data = yaml.safe_load(f)

    deps: list[dict[str, Any]] = []
    packages = data.get("packages", {}) if isinstance(data, dict) else {}

    for spec, info in packages.items():
        if not isinstance(info, dict):
            continue
        # spec format: "name@version"
        # Some entries are "/@scope/name@version" or "name@version"
        # Extract the version from the spec
        match = re.match(r"^(?:/@?[^/]+)?/?([^@]+)@(.+)$", str(spec))
        if not match:
            continue
        name = match.group(1).strip()
        version = match.group(2).strip()

        resolution = info.get("resolution", {})
        integrity = resolution.get("integrity", "") if isinstance(resolution, dict) else ""

        dep: dict[str, Any] = {
            "name": name,
            "version": version,
            "type": "javascript",
            "source": "npm",
        }
        if integrity:
            dep["integrity"] = integrity
        deps.append(dep)

    return deps


# ----------------------------------------------------------------
# Try to fetch live license info (best-effort)
# ----------------------------------------------------------------


def fetch_python_licenses(deps: list[dict[str, Any]], verbose: bool = False) -> None:
    """Try to fetch license info for Python packages via pip (if available)."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show"] + [d["name"] for d in deps],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Parse pip show output per-package
        current_name = None
        for line in result.stdout.splitlines():
            if line.startswith("Name: "):
                current_name = line[6:].strip().lower()
            elif line.startswith("License: ") and current_name:
                lic = line[9:].strip()
                for dep in deps:
                    if dep["name"].lower() == current_name:
                        dep["license"] = lic
                        break
                current_name = None
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        log("pip show not available -- skipping Python license lookup", verbose)


# ----------------------------------------------------------------
# Checksums
# ----------------------------------------------------------------


def sha256_file(path: Path) -> str:
    """Compute SHA256 digest of a file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def compute_checksums() -> dict[str, str]:
    """Compute SHA256 digests for key lockfiles and the repo manifest."""
    checksums: dict[str, str] = {}
    targets = [
        ("uv.lock", UV_LOCK),
        ("pnpm-lock.yaml", PNPM_LOCK),
        ("pyproject.toml", REPO_ROOT / "pyproject.toml"),
        ("package.json", REPO_ROOT / "package.json"),
    ]
    for label, path in targets:
        if path.exists():
            checksums[label] = sha256_file(path)
    return checksums


# ----------------------------------------------------------------
# SBOM assembly
# ----------------------------------------------------------------


def generate_sbom(verbose: bool = False) -> dict[str, Any]:
    """Generate the full SBOM document."""
    log("Parsing uv.lock...", verbose)
    python_deps = parse_uv_lock(UV_LOCK)

    log("Parsing pnpm-lock.yaml...", verbose)
    ts_deps = parse_pnpm_lock(PNPM_LOCK)

    log("Computing checksums...", verbose)
    checksums = compute_checksums()

    # Get git info if available
    git_commit = ""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=5, cwd=REPO_ROOT,
        )
        if result.returncode == 0:
            git_commit = result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        pass

    sbom: dict[str, Any] = {
        "sbom_version": SBOM_VERSION,
        "metadata": {
            "generated_at": os.environ.get("SOURCE_DATE_EPOCH", ""),
            "generator": "zayd-generate-sbom",
            "git_commit": git_commit,
            "repo": "zayd-thai-islamic-knowledge-assistant",
        },
        "python": {
            "count": len(python_deps),
            "dependencies": python_deps,
        },
        "typescript": {
            "count": len(ts_deps),
            "dependencies": ts_deps,
        },
        "checksums": checksums,
    }

    # Compute a digest over the serialized SBOM (without its own digest field)
    serialized = json.dumps(sbom, ensure_ascii=False, sort_keys=True)
    sbom["digest"] = {
        "algorithm": "sha256",
        "value": hashlib.sha256(serialized.encode("utf-8")).hexdigest(),
    }

    return sbom


def main() -> None:
    args = parse_args()
    verbose = args.verbose

    log("Generating SBOM for Zayd release artifacts...", verbose)
    sbom = generate_sbom(verbose=verbose)

    output = json.dumps(sbom, ensure_ascii=False, indent=2)
    if args.output:
        dest = Path(args.output)
        dest.write_text(output, encoding="utf-8")
        log(f"SBOM written to {dest}", verbose)
    else:
        print(output)


if __name__ == "__main__":
    main()
