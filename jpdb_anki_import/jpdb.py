import dataclasses
import datetime
import json


@dataclasses.dataclass
class Review:
    grade: str
    timestamp: int

    @classmethod
    def from_dict(cls, d):
        return cls(timestamp=d['timestamp'], grade=d['grade'])


@dataclasses.dataclass
class Vocabulary:
    vid: int
    spelling: str
    reading: str
    reviews: list[Review]

    @classmethod
    def from_dict(cls, d):
        return cls(
            vid=d['vid'],
            spelling=d['spelling'],
            reading=d['reading'],
            reviews=cls._build_reviews(d['reviews']),
        )

    @classmethod
    def parse(cls, filename):
        with open(filename, 'rb') as review_file:
            reviews = json.load(review_file)

        en_reviews = [cls.from_dict(v) for v in reviews['cards_vocabulary_en_jp']]
        jp_reviews = [cls.from_dict(v) for v in reviews['cards_vocabulary_jp_en']]

        # merge together but keep reviews only from jp => en
        by_vid = {v.vid: v for v in jp_reviews}
        for v in en_reviews:
            if v.vid not in by_vid:
                # Add a new vocab word with blank reviews.
                by_vid[v.vid] = cls(
                    vid=int(v.vid),
                    spelling=v.spelling,
                    reading=v.reading,
                    reviews=[]
                )

        return list(by_vid.values())

    @staticmethod
    def _build_reviews(reviews):
        return sorted((Review.from_dict(r) for r in reviews), key=lambda x: x.timestamp)


def main():
    vocab = Vocabulary.parse('../vocabulary-reviews.json')
    vocab.sort(key=lambda x: x.spelling)
    for v in vocab:
        print(v)


if __name__ == '__main__':
    main()
