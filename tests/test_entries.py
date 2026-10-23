from datetime import datetime
from unittest import TestCase

from story_time.entries import Entry, filter_entries, group_by_month


class TestEntries(TestCase):
    def test_filter_entries(self):
        e1 = Entry(datetime(2020, 1, 1), "text", "Walk by the Lake")
        e2 = Entry(datetime(2020, 1, 2), "photo", "Logo sketch", "a.jpg")
        entries = [e1, e2]
        assert filter_entries(entries, "") == entries
        assert filter_entries(entries, "   ") == entries
        assert filter_entries(entries, "lake") == [e1]
        assert filter_entries(entries, "SKETCH logo") == [e2]
        assert filter_entries(entries, "lake logo") == []

    def test_group_by_month(self):
        entries = [
            Entry(datetime(2020, 3, 5), "text", "a"),
            Entry(datetime(2020, 3, 1), "text", "b"),
            Entry(datetime(2020, 1, 9), "text", "c"),
            Entry(datetime(2019, 3, 9), "text", "d"),
        ]
        groups = group_by_month(entries)
        assert [k for k, _ in groups] == [(2020, 3), (2020, 1), (2019, 3)]
        assert [[e.text for e in g] for _, g in groups] == [["a", "b"], ["c"], ["d"]]
        assert group_by_month([]) == []

    def test_first_line(self):
        assert (
            Entry(datetime(2020, 1, 1), "text", "\n\n  Hello \nWorld").first_line
            == "Hello"
        )
        assert Entry(datetime(2020, 1, 1), "text", "").first_line == ""

    def test_entries_with_the_same_content_differ_by_id(self):
        first = Entry(datetime(2020, 1, 1), "text", "Same", None, 1)
        second = Entry(datetime(2020, 1, 1), "text", "Same", None, 2)
        assert first != second
        assert first == Entry(datetime(2020, 1, 1), "text", "Same", None, 1)
        # Not stored yet
        assert Entry(datetime(2020, 1, 1), "text", "Same").id is None
