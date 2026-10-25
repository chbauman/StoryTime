"""Prints the notes of a version from `CHANGELOG.md`, for the release.

Run from the repository root: `python tools/changelog_notes.py 1.2.3`.
It fails if there is no section `## [1.2.3]` or the section is empty, so a
release can not be made without describing it.
"""

import re
import sys
from pathlib import Path

CHANGELOG = Path(__file__).resolve().parent.parent / "CHANGELOG.md"


def notes_for(changelog: str, version: str) -> str:
    """The text of the section of a version, without its heading."""
    heading = re.compile(rf"^## \[{re.escape(version)}\].*$", re.MULTILINE)
    match = heading.search(changelog)
    if match is None:
        raise ValueError(f"CHANGELOG.md has no section for version {version}.")
    rest = changelog[match.end() :]
    following = re.search(r"^## \[", rest, re.MULTILINE)
    notes = (rest[: following.start()] if following else rest).strip()
    if not notes:
        raise ValueError(f"The section of version {version} is empty.")
    return notes + "\n"


def main(version: str) -> None:
    print(notes_for(CHANGELOG.read_text(encoding="utf8"), version), end="")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    try:
        main(sys.argv[1])
    except ValueError as error:
        sys.exit(str(error))
