#!/usr/bin/env python3
"""Generate index.md: a list of every Markdown file in this repository.

index.md is fully generated -- there are no marker comments wrapping
the list, so the file the renderer in index.html displays is simply
the heading followed by a Markdown list:

    # LA Solarpunk

    - [[2026-06-21-westwood-greenway|Visiting the Westwood Greenway]] — 2026-06-21
    - [[2026-06-18-how-to-write-a-post|How to Write a Blog Post]] — 2026-06-18

Do not edit index.md by hand; edit the Markdown posts themselves and
rerun this script (the GitHub Actions workflow does so on every push).

Each entry is a wikilink, ``[[path-without-.md|Title]]``, using the
file's front-matter `title:` when present, then its first `# Heading`,
then a humanised version of the file name. Entries are sorted newest
first by the `YYYY-MM-DD-` prefix in the file name; undated files
follow, in title order.

Usage:
    python3 scripts/build-index.py              # regenerate index.md
    python3 scripts/build-index.py --site-dir _site
        # regenerate index.md and assemble a deployable copy of the
        # site (index.html, index.md, every Markdown file, and any
        # other static assets) under _site/

The generated index.md itself, build output, VCS/CI metadata, and
hidden directories are never indexed. Standard library only.

Image/media embeds must use wikilink embed style, ``![[file.jpg|alt]]``
(the form the renderer in index.html understands, for images, video,
audio, and page embeds alike). Standard Markdown images
``![alt](file.jpg)`` and raw ``<img>`` tags fail the build, as do
embeds pointing at local files that do not exist.
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INDEX_FILE = ROOT / "index.md"
HEADING = "# LA Solarpunk"

# Directories that are never scanned for Markdown and never copied to
# the deployable site. Anything hidden (``.git``, ``.github``, ...) is
# skipped as well, as are ``node_modules`` and build output.
SKIP_DIRS = {"_site", "dist", "node_modules", "vendor", "__pycache__",
             "scripts"}

DATE_PREFIX = re.compile(r"^(\d{4}-\d{2}-\d{2})-(.+)$")

# Media extensions the renderer's ![[...]] embed handler recognises.
MEDIA_EXTS = {
    "png", "jpg", "jpeg", "gif", "svg", "webp", "bmp", "avif", "ico",
    "mp4", "webm", "ogg", "ogv", "mov", "m4v", "avi",
    "mp3", "wav", "oga", "m4a", "aac", "flac",
}
STANDARD_IMAGE = re.compile(r"!\[[^\]\n]*\]\([^)\n]+\)")
HTML_IMAGE = re.compile(r"<img\b", re.IGNORECASE)
WIKILINK_EMBED = re.compile(r"!\[\[([^\]\n]+)\]\]")


def is_skipped(path: Path) -> bool:
    """True if any part of path (relative to ROOT) is a skipped dir."""
    rel = path.relative_to(ROOT)
    return any(
        part in SKIP_DIRS or part.startswith(".") or part.startswith("_")
        for part in rel.parts[:-1]
    )


def find_markdown_files() -> list[Path]:
    """Every Markdown file in the repo, except the generated index."""
    found = []
    for path in sorted(ROOT.rglob("*.md")):
        if path.resolve() == INDEX_FILE.resolve():
            continue  # index.md lists everything but itself
        if is_skipped(path):
            continue
        found.append(path)
    return found


def title_for(path: Path) -> str:
    """Best display title: front matter, first heading, or file name."""
    text = path.read_text(encoding="utf-8", errors="replace")

    # YAML front matter between the first pair of --- lines.
    if text.startswith("---"):
        end = text.find("\n---", 3)
        if end != -1:
            for line in text[3:end].splitlines():
                match = re.match(r"^title\s*:\s*(.+?)\s*$", line)
                if match:
                    return match.group(1).strip("\"'")

    for line in text.splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*\s*$", line)
        if match:
            return match.group(1).strip()

    stem = path.stem
    date = DATE_PREFIX.match(stem)
    if date:
        stem = date.group(2)
    return stem.replace("-", " ").replace("_", " ").title()


def sort_key(path: Path) -> tuple[str, str, str]:
    """Newest first by date prefix, then title, then path."""
    date = DATE_PREFIX.match(path.stem)
    # Negating the date string gives descending order within an
    # ascending sort; undated files (empty date) sort last.
    return (date.group(1) if date else "", title_for(path).lower(),
            path.relative_to(ROOT).as_posix())


def render_list(files: list[Path]) -> str:
    ordered = sorted(files, key=sort_key, reverse=False)
    # Newest first: sort dated entries descending, undated last.
    dated = [p for p in ordered if DATE_PREFIX.match(p.stem)]
    undated = [p for p in ordered if not DATE_PREFIX.match(p.stem)]
    dated.sort(key=lambda p: DATE_PREFIX.match(p.stem).group(1), reverse=True)
    items = []
    for path in dated + undated:
        rel = path.relative_to(ROOT).as_posix()
        # Wikilink target: the path without its .md extension; the
        # renderer (index.html) appends .md and loads it in-page.
        target = rel[:-3] if rel.lower().endswith(".md") else rel
        # A title containing | or ] would break the wikilink syntax.
        title = title_for(path).replace("|", "/").replace("]", "")
        date = DATE_PREFIX.match(path.stem)
        suffix = f" — {date.group(1)}" if date else ""
        items.append(f"- [[{target}|{title}]]{suffix}")
    return "\n".join(items) if items else "_No posts yet._"


def check_image_links(files: list[Path]) -> list[str]:
    """Problems with image/media links, in wikilink-embed terms.

    Returns a list of human-readable errors: standard Markdown images
    or <img> tags (which must be ![[file|alt]] instead), and ![[...]]
    embeds whose local media file does not exist. Code examples are
    ignored, so documenting the old syntax in backticks is fine.
    """
    errors = []
    for path in files + ([INDEX_FILE] if INDEX_FILE.exists() else []):
        text = path.read_text(encoding="utf-8", errors="replace")
        text = re.sub(r"```.*?```", "", text, flags=re.S)
        text = re.sub(r"`[^`\n]*`", "", text)
        rel = path.relative_to(ROOT).as_posix()
        for match in STANDARD_IMAGE.finditer(text):
            errors.append(
                f"{rel}: standard image link {match.group(0)!r} — "
                "use wikilink embed style, e.g. ![[file.jpg|alt text]]"
            )
        if HTML_IMAGE.search(text):
            errors.append(f"{rel}: <img> tag — use ![[file.jpg|alt text]] instead")
        for match in WIKILINK_EMBED.finditer(text):
            target = match.group(1).split("|", 1)[0].strip()
            ext = target.rsplit(".", 1)[-1].lower() if "." in target else ""
            if ext not in MEDIA_EXTS or "://" in target:
                continue  # page wikilink, remote URL, or extensionless
            if not ((ROOT / target).exists() or (path.parent / target).exists()):
                errors.append(f"{rel}: embed target does not exist: {target!r}")
    return errors


def write_index(files: list[Path]) -> None:
    """Write index.md as a heading followed by the generated list.

    No marker comments: index.md is generated in full on every run,
    so old marker-wrapped files are replaced by the plain list.
    """
    text = f"{HEADING}\n\n{render_list(files)}\n"
    INDEX_FILE.write_text(text, encoding="utf-8")


def build_site(files: list[Path], site_dir: Path) -> None:
    """Assemble a deployable copy of the site under site_dir."""
    if site_dir.exists():
        shutil.rmtree(site_dir)
    site_dir.mkdir(parents=True)

    include = files + [INDEX_FILE]
    for path in sorted(ROOT.rglob("*")):
        if not path.is_file() or path.suffix.lower() == ".md":
            continue
        if path.name.startswith(".") or is_skipped(path):
            continue
        include.append(path)

    for path in include:
        dest = site_dir / path.relative_to(ROOT)
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, dest)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--site-dir",
        type=Path,
        default=None,
        help="also assemble a deployable copy of the site in this directory",
    )
    args = parser.parse_args(argv)

    files = find_markdown_files()
    errors = check_image_links(files)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 1
    write_index(files)
    print(f"index.md: listed {len(files)} Markdown file(s)")
    for path in sorted(files, key=lambda p: p.relative_to(ROOT).as_posix()):
        print(f"  - {path.relative_to(ROOT).as_posix()}")

    if args.site_dir:
        site_dir = args.site_dir if args.site_dir.is_absolute() else ROOT / args.site_dir
        build_site(files, site_dir)
        print(f"site: assembled in {site_dir.relative_to(ROOT)}/")
    return 0


if __name__ == "__main__":
    sys.exit(main())
