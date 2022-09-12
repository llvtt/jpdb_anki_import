"""Modify review exports from JPDB to create test fixtures."""
import csv
import json
import os.path

VOCAB_LIMIT = 50


def with_sorted_reviews(vocab_entry):
    vocab_entry['reviews'].sort(key=lambda r: r['timestamp'])
    return vocab_entry


def create_smaller_review_file(vocab):
    """Pare down review file to just a few words to limit file size."""
    en_reviews = {v['vid']: with_sorted_reviews(v) for v in vocab['cards_vocabulary_en_jp']}
    jp_reviews = {v['vid']: with_sorted_reviews(v) for v in vocab['cards_vocabulary_jp_en']}
    smaller_jp_reviews = []
    smaller_en_reviews = []

    # Try to find some vocabulary that has both EN/JP reviews.
    for vid, review in en_reviews.items():
        if len(smaller_jp_reviews) >= VOCAB_LIMIT:
            break

        jp_review = jp_reviews.get(vid)
        if jp_review:
            smaller_en_reviews.append(review)
            smaller_jp_reviews.append(jp_review)

    # Try to fill the rest with JP reviews if necessary.
    for vid, review in jp_reviews.items():
        if len(smaller_jp_reviews) >= VOCAB_LIMIT:
            break

        if vid not in en_reviews:
            smaller_jp_reviews.append(review)

    return {
        'cards_vocabulary_en_jp': smaller_jp_reviews,
        'cards_vocabulary_jp_en': smaller_en_reviews,
    }


def create_previous_review_file(vocab):
    """Create another review file that mocks a set of reviews made at an earlier time."""

    def remove_reviews(lang_vocab):
        # Remove some words.
        pruned = lang_vocab[:-3]

        for lv in pruned:
            # Assume there are more than 3 reviews for at least some vocabulary.
            lv['reviews'] = lv['reviews'][:3]

        return pruned

    return {
        'cards_vocabulary_en_jp': remove_reviews(vocab['cards_vocabulary_en_jp']),
        'cards_vocabulary_jp_en': remove_reviews(vocab['cards_vocabulary_jp_en']),
    }


def revlog_entries(vocab):
    """Create expected revlog entries for the vocabulary."""
    records = []
    # records.extend(
    #     (v['spelling'], review['timestamp'] * 1000)
    #     for v in vocab['cards_vocabulary_en_jp']
    #     for review in v['reviews']
    # )
    records.extend(
        (v['spelling'], review['timestamp'] * 1000)
        for v in vocab['cards_vocabulary_jp_en']
        for review in v['reviews']
    )
    records.sort()
    return records


def main():
    fixtures_directory = os.path.join(
        os.path.realpath(os.path.dirname(__file__)), os.pardir, 'test', 'fixtures')

    with open('reviews.json', 'r') as review_file:
        vocabulary = json.load(review_file)

    smaller_vocabulary = create_smaller_review_file(vocabulary)
    previous_vocabulary = create_previous_review_file(smaller_vocabulary)

    with open(os.path.join(fixtures_directory, 'updated-reviews.json'), 'w') as review_file:
        json.dump(smaller_vocabulary, review_file)

    with open(os.path.join(fixtures_directory, 'reviews.json'), 'w') as review_file:
        json.dump(previous_vocabulary, review_file)

    with open(os.path.join(fixtures_directory, 'review-history.csv'), 'w') as history_file:
        csv.writer(history_file).writerows(revlog_entries(previous_vocabulary))

    with open(os.path.join(fixtures_directory, 'updated-review-history.csv'), 'w') as history_file:
        csv.writer(history_file).writerows(revlog_entries(smaller_vocabulary))


if __name__ == '__main__':
    main()
