# StoryTime

Digital diary written in python using wxPython.
Works completely offline, so there are no privacy issues.
On the other hand side, there is no backup included. 
Therefore, one has to take care of backing up the data manually.

## Installation

Can be installed using pip as follows:

```
$ pip install story-time
```

## Running

Requires python version >= 3.9.
To run it, just type the following command into
the command line:

```
$ story-time
```

## Languages

All texts of the user interface are in the catalogs in `story_time/locales`
(currently English and German). The language is taken from the system or
can be set with the environment variable `STORY_TIME_LANG`, e.g.
`STORY_TIME_LANG=de story-time`.

To add a language, copy `en.json` to `<language code>.json` and translate
the values. Keep the keys and the `{placeholders}`, missing texts fall back
to English. In the code, use `tr("some.key")` from `story_time.texts` instead
of writing texts directly.

## Development

Install the package with the development tools and run the checks:

```
$ pip install -e ".[dev]"
$ pytest tests
$ ruff check .
$ black --check .
```

The tests open GUI windows, so on a headless machine run them
under a virtual display, e.g. with `xvfb-run`.
Tests that need a webcam are skipped if none is available.

The toolbar icons are drawn as SVG files in `story_time/Icons/src`.
After changing one, re-render the PNGs the app loads with
`python tools/render_icons.py` (needs `playwright`).

## Screenshots

![StoryTime](docs/screenshot.png)

