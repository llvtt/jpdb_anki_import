"""
Create Notes and Cards in Anki for JPDB vocabulary cards.
"""
from typing import Optional

import aqt
import aqt.qt
from anki.cards import Card
from anki.decks import DeckId
from anki.notes import Note
from anki.scheduler.v3 import CardAnswer

from . import jpdb, config

JPDB_TO_CARD_ANSWER = {
    'okay': CardAnswer.GOOD,
    'known': CardAnswer.GOOD,
    'unknown': CardAnswer.AGAIN,
    'hard': CardAnswer.HARD,
    'something': CardAnswer.AGAIN,
    'fail': CardAnswer.AGAIN,
    'nothing': CardAnswer.AGAIN,
    'easy': CardAnswer.EASY,
}


class JPDBImporter:
    def __init__(self, conf: config.Config, anki: aqt.AnkiQt):
        self.config = conf
        self.anki = anki

    def _create_progress_dialog(self, message, steps):
        dialog = aqt.qt.QProgressDialog(message, 'Cancel', 0, steps, self.anki)
        bar = aqt.qt.QProgressBar(dialog)
        bar.setFormat('%v/%m')
        bar.setMaximum(steps)
        dialog.setBar(bar)
        dialog.setMinimumDuration(1000)
        dialog.setModal(True)
        return dialog

    def create_note(self, vocab: jpdb.Vocabulary) -> Note:
        note = self.anki.col.new_note(self._note_model)

        if self.config.expression_field in note:
            note[self.config.expression_field] = vocab.spelling
        else:
            note.fields[0] = vocab.spelling

        if self.config.reading_field in note:
            note[self.config.reading_field] = vocab.reading
        else:
            note.fields[1] = vocab.reading
        self.anki.col.add_note(note, DeckId(self.config.deck_id))

        return note

    def card_state_current_next(self, card: Card, rating: str) -> (CardAnswer, CardAnswer):
        # The following code is taken directly from the Anki v3 scheduler
        states = self.anki.col._backend.get_next_card_states(card.id)
        if rating == CardAnswer.AGAIN:
            new_state = states.again
        elif rating == CardAnswer.HARD:
            new_state = states.hard
        elif rating == CardAnswer.GOOD:
            new_state = states.good
        elif rating == CardAnswer.EASY:
            new_state = states.easy
        else:
            raise Exception("invalid rating")

        return states.current, new_state

    @staticmethod
    def _slice_reviews(reviews: list[jpdb.Review], since: Optional[int] = None) -> list[jpdb.Review]:
        if since is None:
            return reviews

        for i, review in enumerate(reviews):
            # `since` is in milliseconds
            if review.timestamp * 1000 > since:
                return reviews[i:]

        return []

    def backfill_reviews(self, card: Card, reviews: list[jpdb.Review], since: Optional[int] = None) -> None:
        for review in self._slice_reviews(reviews, since):
            rating = JPDB_TO_CARD_ANSWER[review.grade]
            current_state, new_state = self.card_state_current_next(card, rating)
            card_answer = CardAnswer(
                card_id=card.id,
                current_state=current_state,
                new_state=new_state,
                rating=rating,
                answered_at_millis=review.timestamp * 1000,
                # Arbitrary
                milliseconds_taken=1000,
            )
            try:
                self.anki.col.sched.answer_card(card_answer)
            except Exception as e:
                print(f'could not rate card {card.id}; state: {current_state}; reason: {e}')

    def backfill(self, note: Note, vocab: jpdb.Vocabulary) -> None:
        jp_en_card = None
        en_jp_card = None
        for card in note.cards():
            template_name = card.template()['name']
            if template_name == self.config.jp2en_card_name:
                jp_en_card = card
            elif template_name == self.config.en2jp_card_name:
                en_jp_card = card

        if en_jp_card:
            self.backfill_reviews(en_jp_card, vocab.en_jp_reviews)

        # Always fill in JP->EN cards, otherwise what's the point.
        if jp_en_card:
            self.backfill_reviews(jp_en_card, vocab.jp_en_reviews)
        else:
            # Fall back to assuming the first card for the note is the JP->EN card.
            self.backfill_reviews(note.cards()[0], vocab.jp_en_reviews)

    def update_notes(self, vocabulary: list[jpdb.Vocabulary]) -> set[str]:
        deck_cards = list(self.anki.col.find_cards(f'did:{self.config.deck_id}'))
        progress = self._create_progress_dialog('Updating notes from JPDB history', len(deck_cards))
        vocabulary_by_spelling = {v.spelling: v for v in vocabulary}
        updated_vocabulary = set()

        for index, card_id in enumerate(deck_cards):
            progress.setValue(index)
            if progress.wasCanceled():
                break

            card = Card(self.anki.col, card_id)
            note = card.note()
            note_expression = note[self.config.expression_field]

            # Is there a JPDB review for this note?
            vocab = vocabulary_by_spelling.get(note_expression)
            if not vocab:
                continue

            # Figure out if we're doing JP => EN or EN => JP.
            try:
                card_name = self._note_model["tmpls"][card.ord]
            except IndexError:
                continue
            else:
                reviews_for_card = vocab.jp_en_reviews
                if card_name == self.config.en2jp_card_name:
                    reviews_for_card = vocab.en_jp_reviews

            # Find the latest review for the card.
            latest_review = self.anki.col.db.scalar(
                'select revlog.id from revlog '
                'inner join cards on revlog.cid = cards.id '
                'where cards.id = ? '
                'order by revlog.id desc '
                'limit 1',
                card.id)

            reviews = self._slice_reviews(reviews_for_card, latest_review)
            self.backfill_reviews(card, reviews)
            updated_vocabulary.add(note_expression)

        progress.setValue(len(deck_cards))

        return updated_vocabulary

    @property
    def _note_model(self):
        return self.anki.col.models.get(self.config.note_type_id) or self.anki.col.models.current()

    def create_notes(self, vocabulary: list[jpdb.Vocabulary]) -> int:
        progress = self._create_progress_dialog('Importing new notes from JPDB', len(vocabulary))

        notes_created = 0
        for i, vocab in enumerate(vocabulary):
            progress.setValue(i)
            if progress.wasCanceled():
                break

            note = self.create_note(vocab)

            if note:
                notes_created += 1
                self.backfill(note, vocab)

        progress.setValue(len(vocabulary))

        return notes_created

    def run(self) -> dict:
        vocabulary = jpdb.Vocabulary.parse(self.config.review_file)
        updated = self.update_notes(vocabulary)
        created = self.create_notes([v for v in vocabulary if v.spelling not in updated])
        stats = {
            'parsed': len(vocabulary),
            'notes_updated': len(updated),
            'notes_created': created,
        }
        self.anki.overview.refresh()
        return stats
