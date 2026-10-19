"""Source fingerprints shared by experiment runners and result validation."""

import hashlib
from pathlib import Path

from .paths import PROJECT_ROOT


def source_fingerprint(extra_files=()):
    """Hash relative filenames and normalized source bytes, independent of OS newlines."""
    files = set((PROJECT_ROOT / "src/mica_comm").rglob("*.py"))
    files.update(Path(path).resolve() for path in extra_files)
    hashes = {}
    for path in sorted(files):
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        content = path.read_text(encoding="utf-8-sig").replace("\r\n", "\n").encode()
        hashes[relative] = hashlib.sha256(content).hexdigest()
    digest = hashlib.sha256()
    for relative, value in sorted(hashes.items()):
        digest.update(f"{relative}\0{value}\n".encode())
    return {"source_sha256": digest.hexdigest(), "source_files": hashes}
