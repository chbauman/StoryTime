"""The keyboard shortcuts of the main window, without any GUI."""

from typing import Optional

# The key codes of the arrow keys and Escape, the same as `wx.WXK_LEFT`,
# `wx.WXK_RIGHT` and `wx.WXK_ESCAPE`.
KEY_LEFT = 314
KEY_RIGHT = 316
KEY_ESCAPE = 27

#: Actions of the shortcuts with Ctrl, by the letter of the key.
CTRL_SHORTCUTS = {
    "N": "new",
    "S": "save",
    "P": "upload",
    "D": "date",
    "E": "edit",
    "O": "folder",
    "T": "selfie",
    "Q": "quit",
}


def shortcut_for(
    key: int, ctrl: bool, alt: bool, shift: bool, in_text_input: bool
) -> Optional[str]:
    """Returns the name of the action of a keyboard shortcut, if there is one.

    The arrow keys are only used if the cursor is not in the text input or the
    list, as they are needed there to move around. With Alt they always work.

    Args:
        key: The key code.
        ctrl: Whether Ctrl (Cmd on macOS) is pressed.
        alt: Whether Alt is pressed.
        shift: Whether Shift is pressed.
        in_text_input: Whether the text input or the list has the keyboard focus.
    """
    if shift:
        return None
    if key == KEY_ESCAPE and not (ctrl or alt):
        return "discard"
    if ctrl and not alt and 0 < key < 256:
        return CTRL_SHORTCUTS.get(chr(key).upper())
    if key in (KEY_LEFT, KEY_RIGHT) and not ctrl and (alt or not in_text_input):
        return "prev" if key == KEY_LEFT else "next"
    return None
