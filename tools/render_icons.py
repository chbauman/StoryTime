"""Renders the SVG icons in `story_time/Icons/src` to the PNGs used by the app.

Needs playwright with a chromium browser: `pip install playwright`.
Run from the repository root: `python tools/render_icons.py`.
"""

import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ICON_DIR = Path(__file__).resolve().parent.parent / "story_time" / "Icons"
SIZE = 128  #: Edge length in pixels of the rendered icons.
#: The accent color of the theme, `util.teal`. The icons are drawn in `currentColor`.
THEME_COLOR = "#0F766E"
#: Icons that are rendered larger than `SIZE`, as they are shown large.
SIZES = {"logo": 512}


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        page = browser.new_page()
        for svg in sorted((ICON_DIR / "src").glob("*.svg")):
            size = SIZES.get(svg.stem, SIZE)
            page.set_viewport_size({"width": size, "height": size})
            page.set_content(
                "<style>html,body{margin:0;background:transparent}"
                f"svg{{width:{size}px;height:{size}px;display:block;color:{THEME_COLOR}}}"
                "</style>" + svg.read_text(encoding="utf8")
            )
            out = ICON_DIR / f"{svg.stem}.png"
            page.screenshot(path=str(out), omit_background=True)
            print(f"Wrote {out}")
        browser.close()


if __name__ == "__main__":
    main()
