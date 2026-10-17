"""Add an original SVG rectangle to the exact FH synthetic font; host only."""

import hashlib
import sys
from pathlib import Path

from fontTools import __version__
from fontTools.ttLib import TTFont, newTable
from fontTools.ttLib.tables.S_V_G_ import SVGDocument

BASE_SHA256 = "cdd254e7aec2ce13f35942b815da8374d8b0f36a61ef99ba4a4519c2dda81b97"


def main():
    if __version__ != "4.60.1":
        raise SystemExit("Use fonttools==4.60.1")
    source, destination = map(Path, sys.argv[1:])
    if hashlib.sha256(source.read_bytes()).hexdigest() != BASE_SHA256:
        raise SystemExit("Expected the original FH geometric font")
    svg = Path(__file__).with_name("glyph.svg").read_text()
    with TTFont(source, recalcTimestamp=False) as font:
        table = newTable("SVG ")
        table.docList = [SVGDocument(svg, 2, 2, False)]
        font["SVG "] = table
        font.save(destination)


if __name__ == "__main__":
    main()
