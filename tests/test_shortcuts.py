from unittest import TestCase

from story_time.shortcuts import KEY_ESCAPE, KEY_LEFT, KEY_RIGHT, shortcut_for


class TestShortcutFor(TestCase):
    def test_ctrl_shortcuts(self):
        for letter, action in [
            ("N", "new"),
            ("S", "save"),
            ("P", "photo"),
            ("D", "date"),
            ("O", "folder"),
            ("T", "selfie"),
            ("Q", "quit"),
        ]:
            for in_text in (True, False):
                for code in (ord(letter), ord(letter.lower())):
                    assert shortcut_for(code, True, False, False, in_text) == action
            # Not without Ctrl, nor with Shift or Alt
            assert shortcut_for(ord(letter), False, False, False, False) is None
            assert shortcut_for(ord(letter), True, False, True, False) is None
            assert shortcut_for(ord(letter), True, True, False, False) is None
        assert shortcut_for(ord("X"), True, False, False, False) is None

    def test_escape_discards(self):
        for in_text in (True, False):
            assert shortcut_for(KEY_ESCAPE, False, False, False, in_text) == "discard"
        # Not combined with other keys
        assert shortcut_for(KEY_ESCAPE, True, False, False, True) is None
        assert shortcut_for(KEY_ESCAPE, False, True, False, True) is None
        assert shortcut_for(KEY_ESCAPE, False, False, True, True) is None

    def test_arrows(self):
        left, right = KEY_LEFT, KEY_RIGHT
        # Plain arrows move the cursor in the text input
        assert shortcut_for(left, False, False, False, True) is None
        assert shortcut_for(right, False, False, False, True) is None
        # Elsewhere they go through the entries
        assert shortcut_for(left, False, False, False, False) == "prev"
        assert shortcut_for(right, False, False, False, False) == "next"
        # With Alt they always do
        assert shortcut_for(left, False, True, False, True) == "prev"
        assert shortcut_for(right, False, True, False, True) == "next"
        # Ctrl+arrows (word jump) and Shift+arrows (selection) are left alone
        assert shortcut_for(left, True, False, False, True) is None
        assert shortcut_for(right, False, False, True, False) is None

    def test_other_keys(self):
        assert shortcut_for(0, True, False, False, False) is None
        assert shortcut_for(ord("a"), False, False, False, False) is None
        assert shortcut_for(1000, True, False, False, False) is None
