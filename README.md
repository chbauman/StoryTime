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

## Screenshots

TODO

