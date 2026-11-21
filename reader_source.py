#!/usr/bin/env python3
"""Compose the reader from editable components without changing published bytes."""
import argparse
from pathlib import Path

SOURCE_DIR = "reader_sources"
CSS_MARKER = "/* @reader-css@ */"
RUNTIME_MARKER = "/* @reader-runtime@ */"
COUNTRY_MARKER = "/* @reader-country-data@ */\n"
TRAVEL_MARKER = "/* @reader-travel@ */\n"
COUNTRY_START = "const TODAY_COUNTRY_PHOTOS=Object.freeze("
COUNTRY_END = "// Track the photograph that actually loaded"


def _read(path):
    # Preserve the exact newline and Unicode content of the old reader.
    return path.read_bytes().decode("utf-8")


def _insert(text, marker, content):
    if text.count(marker) != 1:
        raise ValueError("Missing or duplicated reader source marker: " + marker)
    return text.replace(marker, content, 1)


def render_reader(root, *, country_data=None):
    directory = Path(root) / SOURCE_DIR
    template = _read(directory / "template.html")
    css = _read(directory / "core.css")
    runtime = _read(directory / "core.js")
    if country_data is None:
        country_data = _read(directory / "country-data.js")
    travel = _read(directory / "travel.js")
    runtime = _insert(runtime, COUNTRY_MARKER, country_data)
    runtime = _insert(runtime, TRAVEL_MARKER, travel)
    result = _insert(template, CSS_MARKER, css)
    result = _insert(result, RUNTIME_MARKER, runtime)
    if "@reader-" in result:
        raise ValueError("Unresolved reader source marker")
    return result


def check_reader_source(root):
    root = Path(root)
    if _read(root / "index.html") != render_reader(root):
        raise ValueError("Reader source drift: run python reader_source.py --sync; do not edit generated index.html")


def sync_reader_source(root):
    root = Path(root)
    result = render_reader(root)
    # Validate the existing public split before replacing compatibility HTML.
    from reader_asset_split import rendered_reader_assets
    rendered_reader_assets(result)
    (root / "index.html").write_bytes(result.encode("utf-8"))


def sync_country_component(root, html):
    """Refresh ONLY the generated country component from canonical JSON exports."""
    root = Path(root)
    if not (root / SOURCE_DIR).is_dir():
        return  # lightweight legacy fixtures and pre-migration checkouts
    if html.count(COUNTRY_START) != 1 or html.count(COUNTRY_END) != 1:
        raise ValueError("Country component anchors missing or duplicated")
    start = html.index(COUNTRY_START)
    end = html.index(COUNTRY_END, start)
    content = html[start:end]
    # Never accept unrelated changes or copy them backwards into components.
    if render_reader(root, country_data=content) != html:
        raise ValueError("Reader source drift outside generated country data; sync reader source first")
    (root / SOURCE_DIR / "country-data.js").write_bytes(content.encode("utf-8"))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--sync", action="store_true")
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent)
    args = parser.parse_args()
    if args.sync:
        sync_reader_source(args.root)
    else:
        check_reader_source(args.root)
    print("Reader components and compatibility HTML verified")


if __name__ == "__main__":
    main()
