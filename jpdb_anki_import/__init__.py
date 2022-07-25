# import the main window object (mw) from aqt
from aqt import mw
# import the "show info" tool from utils.py
from aqt.utils import showInfo, qconnect
# import all of the Qt GUI library
from aqt.qt import *
from . import jpdb, importer


REVIEW_FILE = '/Users/luke/code/jpdb_anki_import/vocabulary-reviews.json'
# We're going to add a menu item below. First we want to create a function to
# be called when the menu item is activated.


def import_jpdb() -> None:
    vocab = jpdb.Vocabulary.parse(REVIEW_FILE)
    notes_created = importer.create_notes(vocab)
    showInfo(f'parsed {len(vocab)} vocabulary words from JPDB, created {notes_created} notes')


# create a new menu item, "test"
action = QAction('Import from JPDB', mw)
# set it to call testFunction when it's clicked
qconnect(action.triggered, import_jpdb)
# and add it to the tools menu
mw.form.menuTools.addAction(action)
