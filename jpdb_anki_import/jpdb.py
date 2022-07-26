import dataclasses
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
    en_jp_reviews: list[Review] = dataclasses.field(default_factory=list)
    jp_en_reviews: list[Review] = dataclasses.field(default_factory=list)

    @classmethod
    def parse(cls, filename):
        with open(filename, 'rb') as review_file:
            reviews = json.load(review_file)

        by_vid = {}
        for vocab in reviews.get('cards_vocabulary_en_jp', []):
            by_vid[vocab['vid']] = cls(
                vid=vocab['vid'],
                spelling=vocab['spelling'],
                reading=vocab['reading'],
                en_jp_reviews=cls._build_reviews(vocab['reviews'])
            )

        for vocab in reviews.get('cards_vocabulary_jp_en', []):
            vid = vocab['vid']
            if vid in by_vid:
                by_vid[vid].jp_en_reviews = cls._build_reviews(vocab['reviews'])
            else:
                by_vid = cls(
                    vid=vocab['vid'],
                    spelling=vocab['spelling'],
                    reading=vocab['reading'],
                    jp_en_reviews=cls._build_reviews(vocab['reviews'])
                )

        return list(by_vid.values())

    @staticmethod
    def _build_reviews(reviews) -> list[Review]:
        return sorted((Review.from_dict(r) for r in reviews), key=lambda x: x.timestamp)
