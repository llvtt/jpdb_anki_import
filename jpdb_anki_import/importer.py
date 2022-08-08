"""
Create Notes and Cards in Anki for JPDB vocabulary cards.
"""
import dataclasses

from anki.cards import Card
from anki.decks import DeckId
from anki.notes import Note
from anki.scheduler.v3 import CardAnswer
from aqt import mw
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
    def __init__(self, conf: config.Config):
        # TODO: validate config, e.g. cannot have same card type for EN/JP
        self.config = conf

    def create_note(self, vocab: jpdb.Vocabulary):
        note_model = mw.col.models.get(self.config.note_type_id) or mw.col.models.current()
        note = mw.col.new_note(note_model)

        if self.config.expression_field in note:
            note[self.config.expression_field] = vocab.spelling
        else:
            note.fields[0] = vocab.spelling

        if self.config.reading_field in note:
            note[self.config.reading_field] = vocab.reading
        else:
            note.fields[1] = vocab.reading
        mw.col.add_note(note, DeckId(self.config.deck_id))

        return note

    @staticmethod
    def card_state_current_next(card: Card, rating: str):
        # The following code is taken directly from the Anki v3 scheduler
        # TODO: is there a safer way to do this?
        states = mw.col._backend.get_next_card_states(card.id)
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

    def backfill_reviews(self, card: Card, reviews: list[jpdb.Review]):
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
            mw.col.sched.answer_card(card_answer)

    def backfill(self, note: Note, vocab: jpdb.Vocabulary):
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

    def create_notes(self, vocabulary):
        notes_created = 0
        for vocab in vocabulary:
            note = self.create_note(vocab)

            if note:
                notes_created += 1
                self.backfill(note, vocab)

        return notes_created

    def run(self) -> dict:
        vocabulary = jpdb.Vocabulary.parse(self.config.review_file)
        return {
            'parsed': len(vocabulary),
            'notes_created': self.create_notes(vocabulary),
        }
