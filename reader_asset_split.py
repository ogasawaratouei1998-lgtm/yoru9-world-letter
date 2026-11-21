"""Build verified external reader CSS/JS without changing source test contracts.

The older monolithic index.html remains an editorial compatibility template.
GitHub Pages receives separate browser assets; their exact bytes are audited.
This is a transitional extraction until source-level component migration.
"""
from pathlib import Path


STYLE_OPEN = "<style>\n"
STYLE_CLOSE = "\n</style>"
RUNTIME_OPEN = "<script>\n'use strict';"
RUNTIME_CLOSE = "\n</script>"
STYLE_TAG = '<link rel="stylesheet" href="./assets/reader-core.css">'
RUNTIME_TAG = '<script src="./assets/reader-core.js"></script>'
ASSETS = ("assets/reader-core.css", "assets/reader-core.js")


def rendered_reader_assets(source: str) -> dict[str, bytes]:
    """Extract the main reader only; never move the embedded demonstration JSON."""
    if source.count(STYLE_OPEN) != 1 or source.count(RUNTIME_OPEN) != 1:
        raise ValueError("Reader stylesheet/runtime anchors are ambiguous")
    if source.count(STYLE_CLOSE) != 1:
        raise ValueError("Reader CSS closing tag is ambiguous")
    start = source.index(STYLE_OPEN)
    end = source.index(STYLE_CLOSE, start + len(STYLE_OPEN))
    stylesheet = source[start + len(STYLE_OPEN):end]
    if ":root{" not in stylesheet or "news-detail-mode" not in stylesheet:
        raise ValueError("Reader CSS is incomplete")
    source = source[:start] + STYLE_TAG + source[end + len(STYLE_CLOSE):]

    start = source.index(RUNTIME_OPEN)
    end = source.index(RUNTIME_CLOSE, start + len(RUNTIME_OPEN))
    runtime = source[start + len("<script>\n"):end]
    for required in ("function renderIssueGallery()", "function travelPostcardHtml(",
                     "function currentIssueCountries()", "checkPublished();"):
        if required not in runtime:
            raise ValueError("Reader runtime missing: " + required)
    source = source[:start] + RUNTIME_TAG + source[end + len(RUNTIME_CLOSE):]
    if "<script>\n'use strict';" in source or "<style>\n" in source:
        raise ValueError("Inline reader assets remain unexpectedly")
    return {
        "index.html": source.encode("utf-8"),
        ASSETS[0]: (stylesheet + "\n").encode("utf-8"),
        ASSETS[1]: (runtime + "\n").encode("utf-8"),
    }


def expected_reader_assets(root: Path) -> dict[str, bytes]:
    return rendered_reader_assets((Path(root) / "index.html").read_text(encoding="utf-8"))


def split_reader_assets(site: Path) -> None:
    """Publish the exact externalized browser bundle, fail closed on missing code."""
    site = Path(site)
    expected = expected_reader_assets(site)
    for relative, payload in expected.items():
        dest = site / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(payload)
