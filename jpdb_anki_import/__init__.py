# import the main window object (mw) from aqt
from aqt import mw
# import all of the Qt GUI library
from aqt.qt import *
# import the "show info" tool from utils.py
from aqt.utils import showInfo

from . import jpdb, importer


# TODO: allow choosing by file select window
REVIEW_FILE = '/Users/luke/code/jpdb_anki_import/vocabulary-reviews.json'


def check_initial_state() -> bool:
    if not mw.col.v3_scheduler():
        showInfo('This plugin only works with Anki v3 scheduler. '
                 'Please enable this under the "Scheduling" tab under Anki general settings.')
        return False

    return True


def import_jpdb() -> None:
    if not check_initial_state():
        return

    review_file, _ = QFileDialog.getOpenFileName(
        caption='Select JPDB Review Export JSON file',
        initialFilter='JSON files (*.json)',
    )

    try:
        vocab = jpdb.Vocabulary.parse(review_file)
        imp = importer.JPDBImporter(mw.addonManager.getConfig(__name__))
        notes_created = imp.create_notes(vocab)
        showInfo(f'parsed {len(vocab)} vocabulary words from JPDB, created {notes_created} notes')
    except Exception:
        raise Exception(f'could not parse {review_file}')


action = QAction('Import from JPDB', mw)
qconnect(action.triggered, import_jpdb)
mw.form.menuTools.addAction(action)
