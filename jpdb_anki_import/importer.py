"""
Create Notes and Cards in Anki for JPDB vocabulary cards.
"""
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

    def create_note(self, vocab: jpdb.Vocabulary) -> Note:
        note_model = self.anki.col.models.get(self.config.note_type_id) or self.anki.col.models.current()
        note = self.anki.col.new_note(note_model)

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

    def backfill_reviews(self, card: Card, reviews: list[jpdb.Review]) -> None:
        for review in reviews:
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
            self.anki.col.sched.answer_card(card_answer)

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

    def create_notes(self, vocabulary: list[jpdb.Vocabulary]) -> int:
        progress = aqt.qt.QProgressDialog('Importing from JPDB', 'Cancel', 0, len(vocabulary), self.anki)
        bar = aqt.qt.QProgressBar(progress)
        bar.setFormat('%v/%m')
        bar.setMaximum(len(vocabulary))
        progress.setBar(bar)
        progress.setMinimumDuration(1000)
        progress.setModal(True)

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
        stats = {
            'parsed': len(vocabulary),
            'notes_created': self.create_notes(vocabulary),
        }
        self.anki.overview.refresh()
        return stats
