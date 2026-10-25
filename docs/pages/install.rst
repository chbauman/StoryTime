============
Installation
============

StoryTime needs Python 3.12 or newer. It works completely offline. To install
it with everything it needs (wxPython and OpenCV), run:

.. code-block:: bash

    pip install story-time

and start it with:

.. code-block:: bash

    story-time

The entries are kept in the data folder you choose at the first start, in the
file ``story_time.sqlite`` with the photos in the folder ``Img``. There is no
backup included, so copy that folder from time to time.

Development
===========

To work on the app, install it in editable mode with the development tools
and run the checks and the tests:

.. code-block:: bash

    pip install -e ".[dev]"
    ruff check . && black --check . && mypy
    pytest tests

The tests of the windows and dialogs open real windows, so on a machine
without a display run them with ``xvfb-run``.
