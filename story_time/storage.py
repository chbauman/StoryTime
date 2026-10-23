"""Opening the entries of a diary folder, taking over old XML files and exporting.

There is no dependency on the GUI.
"""

import os
from collections import defaultdict

from story_time.entries import Entry
from story_time.folders import DataFolder
from story_time.sqlite_storage import SqliteEntryStore
from story_time.xml_storage import (
    XmlEntryStore,
    init_xml,
    insert_photo_entry,
    insert_text_entry,
)


def open_store(folder: DataFolder) -> SqliteEntryStore:
    """Opens the entries in the data folder.

    If there is no database yet, the entries that older versions stored in XML
    files are taken over. This is done once, all or nothing: the database only
    appears when it is complete. The XML files are neither changed nor removed,
    they stay as a backup.
    """
    if os.path.exists(folder.db_file):
        return SqliteEntryStore(folder.db_file)

    legacy = XmlEntryStore(folder.xml_folder).load_all()
    if not legacy:
        return SqliteEntryStore(folder.db_file)

    # Build the database next to the final one and move it in place when it is done
    building = folder.db_file + ".importing"
    if os.path.exists(building):  # The rest of an import that was interrupted
        os.remove(building)
    # Oldest first, so the ids follow the dates. The sort keeps the order of entries
    # with the same time.
    SqliteEntryStore(building).add_entries(sorted(legacy, key=lambda e: e.date_time))
    os.replace(building, folder.db_file)
    return SqliteEntryStore(folder.db_file)


def export_xml(
    entries: list[Entry], xml_folder: str, overwrite: bool = False
) -> list[str]:
    """Writes the entries as XML files, one for each year, as older versions did.

    So the diary can be read without this version of the app. The images are not
    copied, only their names are in the entries.

    Args:
        entries: The entries to write.
        xml_folder: The folder for the files, it is created if needed.
        overwrite: Whether to replace files that already exist. By default
            nothing is written if there is a file for one of the years.

    Returns:
        The paths of the files that were written.

    Raises:
        FileExistsError: If a file exists and `overwrite` is False.
    """
    by_year: dict[int, list[Entry]] = defaultdict(list)
    for entry in sorted(entries, key=lambda e: e.date_time):
        by_year[entry.date_time.year].append(entry)

    paths = {year: os.path.join(xml_folder, f"{year}.xml") for year in by_year}
    if not overwrite:
        for path in paths.values():
            if os.path.exists(path):
                raise FileExistsError(f"{path} exists, nothing was written.")

    os.makedirs(xml_folder, exist_ok=True)
    for year, year_entries in by_year.items():
        tree = init_xml("Das isch es Johr " + str(year) + ".", year)
        root = tree.getroot()
        assert root is not None
        doc = root.find("doc")
        assert doc is not None
        for entry in year_entries:
            if entry.type == "photo" and entry.photo is not None:
                insert_photo_entry(doc, entry.date_time, entry.photo, entry.text)
            else:
                insert_text_entry(doc, entry.date_time, entry.text)
        # Write to a temporary file first, so a file is never half written
        temporary = paths[year] + ".tmp"
        tree.write(temporary)
        os.replace(temporary, paths[year])
    return list(paths.values())
