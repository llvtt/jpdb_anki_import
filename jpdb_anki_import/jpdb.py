import datetime
import json


class Review:
    def __init__(self, timestamp, grade):
        self.grade = grade
        self.timestamp = datetime.datetime.fromtimestamp(timestamp)

    @classmethod
    def from_dict(cls, d):
        return cls(timestamp=d['timestamp'], grade=d['grade'])

    def __repr__(self):
        return f"Review('{self.grade}', {self.timestamp})"


class Vocabulary:
    def __init__(self, vid, spelling, reading, reviews):
        self.vid = vid
        self.spelling = spelling
        self.reading = reading
        self.reviews = self._build_reviews(reviews)

    @classmethod
    def from_dict(cls, d):
        return cls(vid=d['vid'], spelling=d['spelling'], reading=d['reading'], reviews=d['reviews'])

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

    def __repr__(self):
        return f"Vocabulary({self.vid}, '{self.spelling}', '{self.reading}', {self.reviews})"


def main():
    vocab = Vocabulary.parse('../vocabulary-reviews.json')
    vocab.sort(key=lambda x: x.spelling)
    for v in vocab:
        print(v)


if __name__ == '__main__':
    main()
