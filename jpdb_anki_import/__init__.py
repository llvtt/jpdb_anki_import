import aqt.qt
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

from . import config, importer, scraper


def check_initial_state() -> bool:
    if not mw.col.v3_scheduler():
        showInfo(
            "This plugin only works with Anki v3 scheduler. "
            'Please enable this under the "Scheduling" tab under Anki general settings.'
        )
        return False

    return True


def import_jpdb() -> None:
    if not check_initial_state():
        return

    option_dialog = config.ConfigGUI(mw)
    if option_dialog.exec() == aqt.qt.QDialog.DialogCode.Accepted:
        c = option_dialog.config
    else:
        return

    jpdb_scraper = None
    if c.jpdb_cookie and c.scraped_jpdb_field_mapping:
        jpdb_scraper = scraper.JPDBScraper(c.jpdb_cookie)

    try:
        imp = importer.JPDBImporter(c, mw, jpdb_scraper)
        stats = imp.run()
        showInfo(
            f'parsed {stats["parsed"]} vocabulary words from JPDB, created {stats["notes_created"]} notes'
        )
    except Exception as e:
        raise Exception(f"Could not import {c.review_file}") from e


action = QAction("Import from JPDB", mw)
qconnect(action.triggered, import_jpdb)
mw.form.menuTools.addAction(action)
