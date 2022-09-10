import dataclasses
import pathlib

import aqt


@dataclasses.dataclass
class Config:
    review_file: str = ''
    deck_id: int = 1
    note_type_id: int = 1
    reading_field: str = 'Back'
    expression_field: str = 'Front'
    jp2en_card_name: str = 'JPtoEN'
    en2jp_card_name: str = 'ENtoJP'


class ConfigGUI(aqt.qt.QDialog):
    def __init__(self, window: aqt.AnkiQt, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self._config = Config()
        self._mw = window
        self._create_form()

    @property
    def config(self):
        return self._config

    def _create_form(self):
        self._layout = aqt.qt.QFormLayout(self)
        self.setModal(True)
        self.setSizeGripEnabled(True)

        self.setWindowTitle("Import from JPDB")
        self.setAutoFillBackground(True)
        self.setLayout(self._layout)

        self._setup_review_file()
        self._setup_deck_name()
        self._setup_note_type()
        self._setup_reading_field()
        self._setup_expression_field()
        self._setup_card_names()
        self._setup_cta_buttons()

        # Trigger default values
        self._handle_note_type_changed(0)

    def _setup_card_names(self):
        def jp_en_card_selected(name):
            self._config.jp2en_card_name = name

        self._jp_card_name_input = aqt.qt.QComboBox()
        self._jp_card_name_input.setEditable(False)
        self._jp_card_name_input.currentTextChanged.connect(jp_en_card_selected)
        self._layout.addRow(
            aqt.qt.QLabel("Japanese to English Card"),
            self._jp_card_name_input,
        )

        def en_jp_card_selected(name):
            self._config.en2jp_card_name = name

        self._en_card_name_input = aqt.qt.QComboBox()
        self._en_card_name_input.setEditable(False)
        self._en_card_name_input.setDisabled(True)
        self._en_card_name_input.currentTextChanged.connect(en_jp_card_selected)

        self._use_en_cards = aqt.qt.QCheckBox()
        self._use_en_cards.setChecked(False)
        self._use_en_cards.stateChanged.connect(self._en_card_name_input.setEnabled)
        self._layout.addRow(
            aqt.qt.QLabel("Import English to Japanese cards?"),
            self._use_en_cards,
        )
        self._layout.addRow(
            aqt.qt.QLabel("English to Japanese Card"),
            self._en_card_name_input,
        )

    def _setup_review_file(self):
        def select_file():
            path, ok = aqt.qt.QFileDialog.getOpenFileUrl(
                self,
                "JPDB Vocabulary Export",
                aqt.qt.QUrl(str(pathlib.Path.home())),
                "*.json"
            )
            if not ok:
                return

            if path.isValid():
                path = path.path()
                self._selected_file_label.setText(path)
                self._config.review_file = path
                self._set_ok_enabled(True)

        button = aqt.qt.QPushButton("Open")
        button.clicked.connect(select_file)
        self._selected_file_label = aqt.qt.QLabel("Select JPDB review JSON file")
        self._layout.addRow(button, self._selected_file_label)

    def _set_ok_enabled(self, enabled):
        ok = self._buttons.button(aqt.qt.QDialogButtonBox.StandardButton.Ok)
        ok.setEnabled(enabled)

    def _setup_cta_buttons(self):
        self._buttons = aqt.qt.QDialogButtonBox()
        self._buttons.setStandardButtons(
            aqt.qt.QDialogButtonBox.StandardButton.Ok | aqt.qt.QDialogButtonBox.StandardButton.Cancel)
        self._set_ok_enabled(False)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)
        self._layout.addRow(self._buttons)

    def _setup_deck_name(self):
        self._decks = self._mw.col.decks.all_names_and_ids(include_filtered=False)
        self._config.deck_id = self._decks[0].id

        def handle_deck_selected(index):
            self._config.deck_id = self._decks[index].id

        deck_options = [deck.name for deck in self._decks]
        deck_name_input = aqt.qt.QComboBox()
        deck_name_input.setEditable(False)
        deck_name_input.insertItems(0, deck_options)
        deck_name_input.currentIndexChanged.connect(handle_deck_selected)
        self._layout.addRow(
            aqt.qt.QLabel("Deck name"),
            deck_name_input,
        )

    def _setup_note_type(self):
        self._note_types = self._mw.col.models.all_names_and_ids()
        self._config.note_type_id = self._note_types[0].id

        note_type_options = [model.name for model in self._note_types]
        note_type_input = aqt.qt.QComboBox()
        note_type_input.setEditable(False)
        note_type_input.insertItems(0, note_type_options)
        note_type_input.currentIndexChanged.connect(self._handle_note_type_changed)
        self._layout.addRow(
            aqt.qt.QLabel("Note type"),
            note_type_input,
        )

    def _handle_note_type_changed(self, index):
        self._config.note_type_id = self._note_types[index].id
        model = self._mw.col.models.get(self._config.note_type_id)

        field_names = self._mw.col.models.field_names(model)
        self._reading_field_input.clear()
        self._reading_field_input.addItems(field_names)
        self._reading_field_input.setEnabled(bool(field_names))
        self._expression_field_input.clear()
        self._expression_field_input.addItems(field_names)
        self._expression_field_input.setEnabled(bool(field_names))

        card_templates = [template['name'] for template in model.get('tmpls', [])]
        self._en_card_name_input.clear()
        self._en_card_name_input.addItems(card_templates)
        self._en_card_name_input.setEnabled(
            bool(card_templates) and self._use_en_cards.isChecked())
        self._jp_card_name_input.clear()
        self._jp_card_name_input.setEnabled(bool(card_templates))
        self._jp_card_name_input.addItems(card_templates)

    def _setup_reading_field(self):
        def handle_reading_field_selected(name):
            self._config.reading_field = name

        self._reading_field_input = aqt.qt.QComboBox()
        self._reading_field_input.currentTextChanged.connect(handle_reading_field_selected)
        self._layout.addRow(
            aqt.qt.QLabel("Reading field"),
            self._reading_field_input,
        )

    def _setup_expression_field(self):
        def handle_expression_field_changed(name):
            self._config.expression_field = name

        self._expression_field_input = aqt.qt.QComboBox()
        self._expression_field_input.currentTextChanged.connect(handle_expression_field_changed)
        self._layout.addRow(
            aqt.qt.QLabel("Expression field"),
            self._expression_field_input,
        )
