"""
Create Notes and Cards in Anki for JPDB vocabulary cards.
"""
from anki.cards import Card
from anki.notes import Note
from anki.scheduler.v3 import CardAnswer
from aqt import mw
from . import jpdb


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
    def __init__(self, config):
        self.note_type = config['noteType']
        self.deck_name = config['deckName']
        self.expression_field = config['expressionField']
        self.reading_field = config['readingField']

    def create_note(self, vocab: jpdb.Vocabulary):
        # TODO: something odd seems to be going on here when we add new notes
        # across _different_ decks.
        # TODO: I think this may have to do with the fact that the first field in a note is used internally by Anki as the ID.
        note_model = mw.col.models.by_name(self.note_type) or mw.col.models.current()
        note = mw.col.new_note(note_model)

        if self.expression_field in note:
            note[self.expression_field] = vocab.spelling
        else:
            note.fields[0] = vocab.spelling

        if self.reading_field in note:
            note[self.reading_field] = vocab.reading
        else:
            note.fields[1] = vocab.reading

        mw.col.add_note(note, mw.col.decks.id_for_name(self.deck_name))

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

    def backfill_reviews(self, note: Note, vocab: jpdb.Vocabulary):
        # Assume there is only 1 card
        card = note.cards()[0]

        for review in vocab.reviews:
            rating = JPDB_TO_CARD_ANSWER[review.grade]
            current_state, new_state = self.card_state_current_next(card, rating)
            card_answer = CardAnswer(
                card_id=card.id,
                current_state=current_state,
                new_state=new_state,
                rating=rating,
                answered_at_millis=review.timestamp * 1000,
                milliseconds_taken=1000,
            )
            mw.col.sched.answer_card(card_answer)

    def create_notes(self, vocabulary: list[jpdb.Vocabulary]):
        notes_created = 0
        for vocab in vocabulary:
            note = self.create_note(vocab)
            if note:
                notes_created += 1
                self.backfill_reviews(note, vocab)

        return notes_created
