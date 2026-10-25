"""Writes the logo of the app as `story_time/Icons/src/logo.svg`.

The shape is the "fancy triangle" of https://github.com/chbauman/SVGIcons
(`my_tria.py`): a triangle whose sides are cut by the corners of a smaller,
rotated triangle. It is drawn in `currentColor`, so `render_icons.py` gives it
the color of the theme.

Run from the repository root: `python tools/make_logo.py`.
"""

import math
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent / "story_time" / "Icons" / "src"

SIDE = 300.0  #: Side length of the main triangle.
INNER_RATIO = 0.43  #: Side length of the inner triangle relative to the main one.
INNER_ANGLE = 54.0  #: Rotation of the inner triangle in degrees.
CUT_START = 0.3  #: Where on a side the cut starts, as a fraction of the side.
CUT_END = 0.4  #: Where on a side the cut ends, as a fraction from the far corner.


def triangle(side: float, rotation: float = 0.0) -> list[tuple[float, float]]:
    """The corners of an upright isosceles triangle around the origin."""
    to_corner = 0.5 / math.cos(math.radians(30))
    below = math.sqrt(0.75) - to_corner
    corners = [(-0.5, -below), (0.5, -below), (0.0, to_corner)]
    angle = math.radians(rotation)
    cos, sin = math.cos(angle), math.sin(angle)
    return [
        (side * (cos * x - sin * y), side * (sin * x + cos * y)) for x, y in corners
    ]


def logo_path() -> str:
    main = triangle(SIDE)
    inner = triangle(INNER_RATIO * SIDE, -INNER_ANGLE)
    points = []
    previous = main[-1]
    for k, corner in enumerate(main):
        side = (corner[0] - previous[0], corner[1] - previous[1])
        points += [
            (previous[0] + CUT_START * side[0], previous[1] + CUT_START * side[1]),
            inner[(k + 1) % 3],
            (
                previous[0] + (1 - CUT_END) * side[0],
                previous[1] + (1 - CUT_END) * side[1],
            ),
            corner,
        ]
        previous = corner
    # The y axis of SVG points down
    path = " ".join(f"{x:.1f},{-y:.1f}" for x, y in points)
    return f"M{path}Z"


def main() -> None:
    svg = (
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-200 -200 400 400" '
        'width="400" height="400" fill="currentColor">\n'
        f'  <path d="{logo_path()}"/>\n'
        "</svg>\n"
    )
    (OUT / "logo.svg").write_text(svg, encoding="utf8")
    print(f"Wrote {OUT / 'logo.svg'}")


if __name__ == "__main__":
    main()
