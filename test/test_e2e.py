import csv
import os
import os.path
import tempfile
import unittest

import aqt
from aqt import AnkiApp, _run
from aqt.main import AnkiQt
from aqt.profiles import ProfileManager


# Much of this is credit to the test setup/teardown in the AwesomeTTS project:
# https://github.com/AwesomeTTS/awesometts-anki-addon
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

        # The plugin requires a profile for import and only works with the v3 scheduler.
        aqt.mw.setupProfile()
        aqt.mw.col.set_v3_scheduler(True)

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

    @classmethod
    def tearDownClass(cls) -> None:
        cls.anki_runner.stop_anki()

    def setUp(self) -> None:
        # Plugin can only be imported after Anki is running.
        import jpdb_anki_import
        self.module = jpdb_anki_import

        self.config = self.module.config.Config(
            review_file=self.fixture_path('reviews.json'))
        self.importer = self.module.importer.JPDBImporter(self.config, aqt.mw)

        with open(self.fixture_path('review-history.csv'), 'r') as csvfile:
            self.review_history = sorted(tuple(review) for review in csv.reader(csvfile))

    def tearDown(self) -> None:
        # TODO: this may not be sufficient, since these tests also modify Anki's revlog.
        aqt.mw.col.decks.current().clear()

    @staticmethod
    def fixture_path(filename):
        return os.path.join(os.path.dirname(__file__), 'fixtures', filename)

    @staticmethod
    def review_log():
        return sorted(
            # Match expected types from self.review_history.
            (sfld, str(rid))
            for sfld, rid in aqt.mw.col.db.execute(
                'select notes.sfld, revlog.id from notes '
                'inner join cards on cards.nid = notes.id '
                'inner join revlog on revlog.cid = cards.id'
            ))

    def test_import(self):
        """Test importing into a deck without notes."""
        self.importer.run()
        self.assertEqual(self.review_history, self.review_log())

    def test_reimport(self):
        """Test importing the same set of reviews twice."""
        self.importer.run()
        self.importer.run()
        self.assertEqual(self.review_history, self.review_log())

    def test_update_reviews(self):
        """Test import into a deck where there are already notes."""
        self.importer.run()

        aqt.mw.col.db.commit()
        importer = self.module.importer.JPDBImporter(
            self.module.config.Config(review_file=self.fixture_path('updated-reviews.json')),
            aqt.mw)
        importer.run()

        with open(self.fixture_path('updated-review-history.csv'), 'r') as csvfile:
            review_history = sorted(tuple(review) for review in csv.reader(csvfile))

        self.assertEqual(len(review_history), len(self.review_log()))
        self.assertEqual(review_history, self.review_log())
