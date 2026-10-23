# StoryTime

[![CI](https://github.com/chbauman/StoryTime/actions/workflows/ci.yml/badge.svg)](https://github.com/chbauman/StoryTime/actions/workflows/ci.yml)

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

## Data format

The entries are stored in one SQLite database, `story_time.sqlite`, in the data
folder; the photos are in its `Img` folder. Every entry gets a stable id and
every change is written atomically, so a crash cannot corrupt the diary.
Deleted entries stay in the database, marked as deleted, until the trash is emptied.

Diaries of older versions (one XML file per year in the `XML` folder) are taken
over once, automatically, when the folder is opened: either all entries are
imported or none. The XML files are left untouched as a backup. To get XML
files back, use `story_time.storage.export_xml`.

## Settings

The chosen data folder is stored in `settings.json` in the config folder of the
user (`~/.config/StoryTime` on Linux, `%APPDATA%\StoryTime` on Windows,
`~/Library/Application Support/StoryTime` on macOS). It survives updates of the
app. The folder of older versions (`Info.txt` in the package) is taken over
automatically. Taken photos are kept in a temporary folder until they are saved.

## Keyboard shortcuts

| Keys | Action |
| --- | --- |
| Ctrl+N | Write a new entry, or go back to reading |
| Ctrl+S | Save the entry |
| Ctrl+E | Edit the entry that is read |
| Ctrl+P | Switch between text-only and photo mode |
| Ctrl+D | Choose another date and time |
| Esc | Discard the text, image and date of the entry (can be undone) |
| Ctrl+O | Choose another data folder |
| Ctrl+T | Take a selfie with the webcam |
| Ctrl+Q | Quit |
| Alt+Left / Alt+Right | Previous (older) / next (newer) entry |
| Left / Right | Previous / next entry, if the cursor is not in the text input or the list |

The shortcuts are also shown in the tooltips of the toolbar.

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
$ mypy
```

### Code structure

The logic is kept apart from the GUI, so most of it can be tested without one:

| Module | Content | Uses wx |
| --- | --- | --- |
| `controller.py` | `DiaryController`: what happens when the user writes, reads, searches, saves... | no |
| `dates.py`, `images.py`, `folders.py`, `settings.py`, `shortcuts.py`, `texts.py` | Helpers for dates, image files, folders, settings, keys and texts | no |
| `entries.py` | The `Entry` type, filtering and grouping of entries | no |
| `sqlite_storage.py`, `storage.py` | The SQLite database with the entries, take-over and export of the old XML files | no |
| `xml_storage.py` | Reading and writing of the legacy XML files | no |
| `user_interface.py` | The main window, which shows what the controller says and passes on what the user does | yes |
| `dialogs.py`, `util.py` | The dialogs, colors, fonts and image helpers | yes |

The controller talks to the window through the small interface `View` and asks
the user through `Dialogs` (both in `controller.py`). The real ones are the
main window and `WxDialogs`, the tests of the controller use the fakes in
`tests/fakes.py`. `tests/test_pure_modules.py` checks that the modules without
wx do not import it.

The tests of the main window and of the dialogs open real windows, so on a
headless machine run them under a virtual display, e.g. with `xvfb-run`.
Tests that need a webcam are skipped if none is available.

The toolbar icons are drawn as SVG files in `story_time/Icons/src`.
After changing one, re-render the PNGs the app loads with
`python tools/render_icons.py` (needs `playwright`).

## Usage

The entries are listed on the left, grouped by month, with a search field on
top. Click an entry to read it. The first tool of the toolbar (or Ctrl+N)
switches to writing a new entry, and back. The other tools (save, photo mode,
date, selfie) are only active while writing.

**Edit** (or Ctrl+E) below an entry that is read changes its text, date and
photo; the button to discard becomes **Cancel** then, and asks first if
something was changed. **Delete** moves the entry to the trash with an Undo bar.
The **Trash** button below the list shows the trash: there an entry can be
restored or **deleted for good**, or the whole trash be emptied, which also
deletes the images that no entry uses any more. A replaced image is not deleted.

**Discard** (button or Esc) clears the text, the image and the date of the entry
that is written. **Remove image** below the image removes only the photo.
Instead of asking for confirmation, an **Undo** bar appears for a few seconds.
Leaving the page to write, or choosing an entry to read, discards a draft the
same way. Only closing the app with unsaved changes asks first.

## Screenshots

Reading an entry:

![Reading an entry](docs/screenshot.png)

Writing a new entry:

![Writing an entry](docs/screenshot_write.png)

