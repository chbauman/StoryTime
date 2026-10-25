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


def main() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=os.environ.get("CHROMIUM_PATH") or None
        )
        page = browser.new_page(viewport={"width": SIZE, "height": SIZE})
        for svg in sorted((ICON_DIR / "src").glob("*.svg")):
            page.set_content(
                "<style>html,body{margin:0;background:transparent}"
                f"svg{{width:{SIZE}px;height:{SIZE}px;display:block;color:{THEME_COLOR}}}"
                "</style>" + svg.read_text(encoding="utf8")
            )
            out = ICON_DIR / f"{svg.stem}.png"
            page.screenshot(path=str(out), omit_background=True)
            print(f"Wrote {out}")
        browser.close()


if __name__ == "__main__":
    main()
