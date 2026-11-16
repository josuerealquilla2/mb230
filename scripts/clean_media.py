from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Remove media not referenced by the canonical dataset"
    )
    parser.add_argument("--canonical-dir", required=True, type=Path)
    parser.add_argument("--media-dir", required=True, type=Path)
    parser.add_argument("--apply", action="store_true", help="Delete files; otherwise only report")
    args = parser.parse_args()

    media_root = args.media_dir.resolve(strict=True)
    questions_path = args.canonical_dir.resolve(strict=True) / "questions.jsonl"
    referenced: set[Path] = set()
    for line in questions_path.read_text(encoding="utf-8").splitlines():
        question = json.loads(line)
        for media in question.get("media", []):
            candidate = (media_root / media["relative_path"]).resolve(strict=True)
            if not candidate.is_relative_to(media_root):
                raise ValueError(f"Media path escapes its root: {candidate}")
            referenced.add(candidate)

    existing = {path.resolve() for path in media_root.rglob("*.webp") if path.is_file()}
    unreferenced = sorted(existing - referenced)
    bytes_to_remove = sum(path.stat().st_size for path in unreferenced)
    print(
        f"Referenced: {len(referenced)}; unreferenced: {len(unreferenced)}; "
        f"unreferenced bytes: {bytes_to_remove}"
    )
    if not args.apply:
        return

    for path in unreferenced:
        path.unlink()
    for directory in sorted(media_root.iterdir()):
        if directory.is_dir() and not any(directory.iterdir()):
            directory.rmdir()
    print(f"Removed {len(unreferenced)} unreferenced generated files.")


if __name__ == "__main__":
    main()
