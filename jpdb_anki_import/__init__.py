import aqt.qt
from aqt import mw
from aqt.qt import *
from aqt.utils import showInfo

from . import jpdb, importer, config


def check_initial_state() -> bool:
    if not mw.col.v3_scheduler():
        showInfo('This plugin only works with Anki v3 scheduler. '
                 'Please enable this under the "Scheduling" tab under Anki general settings.')
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

    print("scraping config", c.scraped_jpdb_field_mapping)
    return

    try:
        imp = importer.JPDBImporter(c, mw)
        stats = imp.run()
        showInfo(f'parsed {stats["parsed"]} vocabulary words from JPDB, created {stats["notes_created"]} notes')
    except Exception:
        raise Exception(f'could not parse {c.review_file}')


action = QAction('Import from JPDB', mw)
qconnect(action.triggered, import_jpdb)
mw.form.menuTools.addAction(action)
