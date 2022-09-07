import os
import os.path
import tempfile
import unittest

import aqt
from aqt import _run
from aqt import AnkiApp
from aqt.main import AnkiQt
from aqt.profiles import ProfileManager


class AnkiRunner:
    def __init__(self):
        self.base_directory = tempfile.TemporaryDirectory(suffix='_anki')

    def start_anki(self):
        # don't use the second instance mechanism, start a new instance every time
        def mock_second_instance(_anki):
            return False

        AnkiApp.secondInstance = mock_second_instance

        # prevent auto-updater code from running (it makes http requests)
        def mock_setup_auto_update(_anki):
            pass

        AnkiQt.setupAutoUpdate = mock_setup_auto_update

        # setup user profile in temp directory
        # ====================================

        lang = "en_US"
        name = "anonymous"

        # prevent popping up language selection dialog
        def set_default_lang(profile_manager, *_):
            profile_manager.setLang(lang)

        ProfileManager.setDefaultLang = set_default_lang
        pm = ProfileManager(base=self.base_directory.name)
        pm.setupMeta()

        # create profile no matter what (since we are starting in a unique temp directory)
        pm.create(name)

        # this needs to be called explicitly with an index
        pm.setDefaultLang(0)

        pm.name = name

        # run the app
        # ===========

        argv = ["anki", "-p", name, "-b", self.base_directory.name]
        print(f'running anki with argv={argv}')
        app = _run(argv=argv, exec=False)
        if app is None:
            raise Exception('Could not create Anki app')

        return app

    def stop_anki(self):
        # clean up what was spoiled
        aqt.mw.cleanupAndExit()

        # remove hooks added during app initialization
        from anki import hooks
        hooks._hooks = {}

        # test_nextIvl will fail on some systems if the locales are not restored
        import locale
        locale.setlocale(locale.LC_ALL, locale.getdefaultlocale())

        # cleanup base directory
        self.base_directory.cleanup()


class E2ETest(unittest.TestCase):
    anki_runner: AnkiRunner

    @classmethod
    def setUpClass(cls) -> None:
        cls.anki_runner = AnkiRunner()
        cls.anki_runner.start_anki()

        from aqt import mw
        mw.setupProfile()
        mw.col.set_v3_scheduler(True)
        cls.mw = mw

    @classmethod
    def tearDownClass(cls) -> None:
        cls.anki_runner.stop_anki()

    def setUp(self) -> None:
        # Plugin can only be imported after Anki is running.
        import jpdb_anki_import

        self.config = jpdb_anki_import.config.Config(
            review_file=os.path.join(
                os.path.dirname(__file__),
                'fixtures',
                'vocabulary-reviews.json')
        )
        self.importer = jpdb_anki_import.importer.JPDBImporter(self.config, self.mw)

    def test_import(self):
        """Test importing into a deck without notes."""
        self.importer.run()

    def test_import_with_existing_notes(self):
        """Test importing into a deck where there are already notes."""
        pass
