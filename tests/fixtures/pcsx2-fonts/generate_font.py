"""Generate original rectangular glyphs; requires host-only fonttools==4.60.1."""

import sys
from pathlib import Path

from fontTools import __version__
from fontTools.feaLib.builder import addOpenTypeFeaturesFromString
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen


def rectangle(width):
    pen = TTGlyphPen(None)
    if width:
        pen.moveTo((0, 0))
        pen.lineTo((0, 700))
        pen.lineTo((width, 700))
        pen.lineTo((width, 0))
        pen.closePath()
    return pen.glyph()


def main():
    if __version__ != "4.60.1":
        raise SystemExit("Use fonttools==4.60.1 for reproducible fixture generation")
    font = FontBuilder(1000, isTTF=True)
    names = [".notdef", "space", "A", "V", "AV"]
    font.setupGlyphOrder(names)
    font.setupCharacterMap({32: "space", 65: "A", 86: "V"})
    font.setupGlyf(dict(zip(names, map(rectangle, [300, 0, 400, 450, 800]), strict=True)))
    font.setupHorizontalMetrics(
        dict(zip(names, [(500, 0), (250, 0), (600, 0), (650, 0), (1000, 0)], strict=True))
    )
    font.setupHorizontalHeader(ascent=800, descent=-200)
    font.setupNameTable(
        {
            "familyName": "SH3 Synthetic Rectangles",
            "styleName": "Regular",
            "uniqueFontIdentifier": "SH3Rectangles-v1",
            "fullName": "SH3 Synthetic Rectangles Regular",
            "psName": "SH3SyntheticRectangles-Regular",
            "version": "Version 1.0",
        }
    )
    font.setupOS2(sTypoAscender=800, sTypoDescender=-200, usWinAscent=800, usWinDescent=200)
    font.setupPost()
    font.setupMaxp()
    addOpenTypeFeaturesFromString(
        font.font,
        """
        languagesystem DFLT dflt;
        languagesystem latn dflt;
        feature liga { sub A V by AV; } liga;
        feature kern { pos A V -80; } kern;
    """,
    )
    font.font["head"].created = 3660681600
    font.font["head"].modified = 3660681600
    font.font.recalcTimestamp = False
    font.save(Path(sys.argv[1]))


if __name__ == "__main__":
    main()
