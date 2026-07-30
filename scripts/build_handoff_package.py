"""Build and audit the source-only ErgoStudy prototype handoff ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROJECT_VERSION = "1.0.0-prototype"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "handoff"
MANIFEST_PATH = PROJECT_ROOT / "data" / "processed" / "package_manifest.json"
ZIP_NAME = f"ErgoStudy-AI-{PROJECT_VERSION}.zip"

EXCLUDED_PARTS = {
    ".git",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".ipynb_checkpoints",
    ".cache",
    "huggingface_cache",
    "models",
    "tmp",
    "temp",
    "handoff",
}
EXCLUDED_PREFIXES = ("chroma_db/", "data/processed/embedding_cache/")
EXCLUDED_SUFFIXES = (".pyc", ".pyo", ".log", ".npy", ".npz", ".pem", ".key")
EXCLUDED_NAMES = {".env", "package_manifest.json"}
TEXT_SUFFIXES = {
    ".py", ".ps1", ".md", ".txt", ".json", ".jsonl", ".csv", ".toml", ".yaml", ".yml"
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(r"(?i)(?:api[_-]?key|access[_-]?token|client[_-]?secret)\s*[:=]\s*['\"][^'\"]{8,}"),
    re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b"),
)


def git_output(*arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=PROJECT_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return result.stdout.strip()


def exclusion_reason(relative: PurePosixPath) -> str | None:
    text = relative.as_posix()
    if any(part in EXCLUDED_PARTS for part in relative.parts):
        return "excluded directory"
    if any(text.startswith(prefix) for prefix in EXCLUDED_PREFIXES):
        return "excluded generated data"
    if relative.name in EXCLUDED_NAMES or relative.name.startswith(".env."):
        return "excluded local or generated file"
    if text.endswith(EXCLUDED_SUFFIXES):
        return "excluded generated or sensitive suffix"
    return None


def candidate_files() -> list[Path]:
    names = git_output("ls-files", "--cached", "--others", "--exclude-standard").splitlines()
    files: list[Path] = []
    for name in sorted(set(names)):
        relative = PurePosixPath(name)
        path = PROJECT_ROOT.joinpath(*relative.parts)
        if path.is_file() and exclusion_reason(relative) is None:
            files.append(path)
    return files


def audit_text(path: Path) -> list[str]:
    if path.suffix.casefold() not in TEXT_SUFFIXES:
        return []
    try:
        text = path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return ["is not valid UTF-8 text"]
    issues: list[str] = []
    machine_paths = (
        str(PROJECT_ROOT),
        str(Path.home()),
    )
    lowered = text.casefold()
    if any(value.casefold() in lowered for value in machine_paths):
        issues.append("contains a machine-specific absolute path")
    if any(pattern.search(text) for pattern in SECRET_PATTERNS):
        issues.append("contains text matching a secret pattern")
    return issues


def deterministic_zip(output_path: Path, files: list[Path]) -> None:
    with ZipFile(output_path, "w", compression=ZIP_DEFLATED, compresslevel=9) as archive:
        for path in files:
            relative = path.relative_to(PROJECT_ROOT).as_posix()
            info = ZipInfo(relative, date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def audit_zip(path: Path, expected: list[str]) -> dict[str, object]:
    with ZipFile(path) as archive:
        names = archive.namelist()
        bad = [name for name in names if exclusion_reason(PurePosixPath(name)) is not None]
        missing = sorted(set(expected) - set(names))
        unexpected = sorted(set(names) - set(expected))
        corrupt_member = archive.testzip()
    return {
        "passed": not bad and not missing and not unexpected and corrupt_member is None,
        "excluded_entries_found": bad,
        "missing_entries": missing,
        "unexpected_entries": unexpected,
        "corrupt_member": corrupt_member,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / ZIP_NAME

    files = candidate_files()
    text_issues: dict[str, list[str]] = {}
    for path in files:
        issues = audit_text(path)
        if issues:
            text_issues[path.relative_to(PROJECT_ROOT).as_posix()] = issues
    if text_issues:
        raise RuntimeError("Package text audit failed:\n" + json.dumps(text_issues, indent=2))

    deterministic_zip(output_path, files)
    relative_names = [path.relative_to(PROJECT_ROOT).as_posix() for path in files]
    audit = audit_zip(output_path, relative_names)
    if not audit["passed"]:
        raise RuntimeError("Package-content audit failed: " + json.dumps(audit, indent=2))

    manifest = {
        "project_name": "ErgoStudy AI",
        "project_version": PROJECT_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "git_commit": git_output("rev-parse", "HEAD"),
        "zip_file": ZIP_NAME,
        "zip_path": str(output_path),
        "zip_sha256": sha256(output_path),
        "included_file_count": len(files),
        "included_size_bytes": sum(path.stat().st_size for path in files),
        "zip_size_bytes": output_path.stat().st_size,
        "exclusion_rules": {
            "directories": sorted(EXCLUDED_PARTS),
            "prefixes": list(EXCLUDED_PREFIXES),
            "suffixes": list(EXCLUDED_SUFFIXES),
            "names": sorted(EXCLUDED_NAMES),
            "notes": [
                "The ZIP itself is never committed.",
                "Chroma contents and model caches are rebuilt locally from included source data and scripts.",
                "This external manifest is excluded from the ZIP so its ZIP hash is not self-referential."
            ],
        },
        "audit": {
            "package_content": audit,
            "machine_specific_absolute_paths": "passed",
            "secret_patterns": "passed",
        },
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Created {output_path}")
    print(f"Files: {manifest['included_file_count']}")
    print(f"ZIP size: {manifest['zip_size_bytes']} bytes")
    print(f"SHA-256: {manifest['zip_sha256']}")
    print(f"Manifest: {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
