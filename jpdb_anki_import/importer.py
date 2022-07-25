"""
Create Notes and Cards in Anki for JPDB vocabulary cards.
"""
from anki.notes import Note
from anki.scheduler.v3 import CardAnswer
from aqt import mw
from . import jpdb


# TODO: these are just test values but should be customizable
NOTE_TYPE = 'basic'
DECK_NAME = 'Default'


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


def create_note(vocab: jpdb.Vocabulary):
    basic_model = mw.col.models.by_name(NOTE_TYPE)
    note = mw.col.new_note(basic_model)
    note.fields[0] = vocab.spelling
    note.fields[1] = vocab.reading
    mw.col.add_note(note, mw.col.decks.id_for_name(DECK_NAME))

    return note


def backfill_reviews(note: Note, vocab: jpdb.Vocabulary):
    # Assume there is only 1 card
    card = note.cards()[0]
    for review in vocab.reviews:
        # TODO: is there a safer way to do this?
        states = mw.col._backend.get_next_card_states(card.id)

        rating = JPDB_TO_CARD_ANSWER[review.grade]
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

        card_answer = CardAnswer(
            card_id=card.id,
            current_state=states.current,
            new_state=new_state,
            rating=rating,
            answered_at_millis=int(review.timestamp.timestamp() * 1000),
            milliseconds_taken=1000,
        )
        mw.col.sched.answer_card(card_answer)


def create_notes(vocabulary: list[jpdb.Vocabulary]):
    notes_created = 0
    for vocab in vocabulary:
        note = create_note(vocab)
        if create_note(vocab):
            notes_created += 1
            backfill_reviews(note, vocab)

    return notes_created


def create_model():
    # TODO: allow the user to select a model and how to map that to JPDB.
    pass
