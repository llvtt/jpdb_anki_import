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
        # TODO: validate config, e.g. cannot have same card type for EN/JP
        self.note_type = config['noteType']
        self.deck_name = config['deckName']
        self.expression_field = config['expressionField']
        self.reading_field = config['readingField']
        self.jp_en_card_name = config['japaneseToEnglishCardName']
        self.en_jp_card_name = config['englishToJapaneseCardName']

        # Used to track index of card template for JP=>EN and EN=>JP cards, respectively.
        self.jp_en_ord = None
        self.en_jp_ord = None

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
            if template_name == self.jp_en_card_name:
                jp_en_card = card
            elif template_name == self.en_jp_card_name:
                en_jp_card = card

        if en_jp_card:
            self.backfill_reviews(en_jp_card, vocab.en_jp_reviews)

        # Always fill in JP->EN cards, otherwise what's the point.
        if jp_en_card:
            self.backfill_reviews(jp_en_card, vocab.jp_en_reviews)
        else:
            # Fall back to assuming the first card for the note is the JP->EN card.
            self.backfill_reviews(note.cards()[0], vocab.jp_en_reviews)

    # def find_card_templates(self, note):
    #     if self.en_jp_ord is not None or self.jp_en_ord is not None:
    #         return
    #
    #     note_templates = note.note_type().get('tmpls', [])
    #     for tmpl in note_templates:
    #         try:
    #             template_name = tmpl['name']
    #             if template_name == self.en_jp_card_name:
    #                 self.en_jp_ord = tmpl['ord']
    #             elif template_name == self.jp_en_card_name:
    #                 self.jp_en_ord = tmpl['ord']
    #         except (TypeError, KeyError):
    #             pass

    def create_notes(self, vocabulary: list[jpdb.Vocabulary]):
        notes_created = 0
        for vocab in vocabulary:
            note = self.create_note(vocab)

            if note:
                notes_created += 1
                self.backfill(note, vocab)

        return notes_created
