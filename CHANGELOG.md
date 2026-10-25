# Changelog

All notable changes of the app. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/). To release, rename
the section "Unreleased" to the new version with its date (see "Releasing" in
the README).

## [Unreleased]

### Added
- Entries are stored in a SQLite database (`story_time.sqlite`) with stable ids
  and atomic writes. Diaries of older versions (XML files) are taken over once,
  all or nothing, and the XML files are kept as a backup.
- Edit saved entries (text, date, image), delete them to a trash, restore them
  or delete them for good. The trash is the last item of the list.
- Undo and redo for discarding a draft or an image and for deleting and
  restoring entries.
- Discard a draft (button or Esc), remove only the image.
- Upload an image with a file dialog (Ctrl+P), besides dropping a file and taking
  one with the webcam. Click the date line to choose another date.
- Keyboard shortcuts, a list of the entries grouped by month with a search, a
  scrollable preview for long entries, texts in English and German.
- The data folder is kept in the settings of the user and survives updates.

### Changed
- New layout: logo on the left, the tools on the right, an image area that is
  always there with the buttons to add and remove an image. An entry with an
  image is a photo entry, the photo mode is gone.
- Disabled tools get their own gray icon. New logo as an SVG in the color of the
  theme, shown larger and sharper.
- Requires Python 3.12 or newer.
- The logic is separated from the GUI and tested without it. Style checks (ruff,
  black, mypy) and CI on GitHub for Python 3.12 and 3.13.

### Fixed
- The list crashed with wxPython 4.3 when it named the weekday and the month.
- Cancelling the choice of an image with the same date no longer crashes saving.
