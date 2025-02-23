#!/usr/bin/env python
import argparse
import csv
import dataclasses
import functools
import itertools
import json
import os
import pathlib
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from typing import Optional, List, cast

# vendor dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vendor'))
import bs4

# e.g. sid=XXXXXX
COOKIE = os.getenv("JPDB_COOKIE")

MAX_RETRIES = 3


@dataclasses.dataclass
class Word:
    spelling: str
    reading: Optional[str]
    glossary: str
    notes: Optional[str]
    sentence: Optional[str]

    def as_dict(self):
        return dataclasses.asdict(self)


class ParseError(Exception):
    pass


def strings_to_html_list(strings: List[str]) -> str:
    pattern = re.compile(r"^\d\. ")
    elements = (
        f"<li>{re.sub(pattern, '', element)}</li>"
        for element in strings
    )
    return f"<ol>{''.join(elements)}</ol>"


class JPDBScraper:
    def __init__(self, cookie):
        self._session_cookie = cookie
        self._http_client = None
        self._logged_in = False

    def _japanese_strings(self, tag_with_text):
        """Yield substrings of the japanese text markup without furigana."""
        for child in tag_with_text.children:
            if isinstance(child, str):
                yield child
            elif child.name == 'rt':
                # Furigana
                pass
            else:
                yield from self._japanese_strings(child)

    def _strip_furigana(self, tag):
        """Return text content of the tag without furigana."""
        return ''.join(self._japanese_strings(tag))

    @property
    def _headers(self) -> dict:
        return {
            "authority": "jpdb.io",
            "sec-ch-ua": "^^",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "^^",
            "upgrade-insecure-requests": "1",
            "dnt": "1",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36",
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
            "sec-fetch-site": "same-origin",
            "sec-fetch-mode": "navigate",
            "sec-fetch-user": "?1",
            "sec-fetch-dest": "document",
            "accept-language": "ja,en-GB;q=0.9,en;q=0.8",
            "cookie": self._session_cookie,
            "if-none-match": "^^",
        }

    def _word_soup(self, spelling) -> bs4.BeautifulSoup:
        encoded_spelling = urllib.parse.quote(spelling, encoding='utf-8')
        url = f"https://jpdb.io/search?q={encoded_spelling}&lang=english#a"
        request = urllib.request.Request(
            url=url,
            method='GET',
            headers=self._headers,
        )
        for i in range(MAX_RETRIES+1):
            try:
                with urllib.request.urlopen(request) as response:
                    return bs4.BeautifulSoup(response.read(), 'html.parser')
            except urllib.error.HTTPError as e:
                if i == MAX_RETRIES:
                    raise
                if e.status == 429:
                    time.sleep(i**2)
                    continue
        # This should not be reachable
        raise ParseError("Failed to contact JPDB")

    def lookup_word(self, spelling) -> Word:
        soup = self._word_soup(spelling)

        # reading
        accent_section = soup.find('div', class_='subsection-pitch-accent')
        reading = None
        if isinstance(accent_section, bs4.element.Tag):
            accent_content = accent_section.find('div', class_='subsection')
            if accent_content:
                # There may be multiple pitch accents listed.
                reading = cast(bs4.element.Tag, accent_content.contents[0]).contents[0].text

        # meanings
        meanings = soup.find('div', class_='subsection-meanings')
        if not isinstance(meanings, bs4.element.Tag):
            raise ParseError("could not find subsection-meanings")

        definitions = [
            " ".join(meaning.strings)
            for meaning in meanings.find_all('div', class_='description')
        ]

        # part of speech
        pos_section = meanings.find('div', class_='part-of-speech')
        if not isinstance(pos_section, bs4.element.Tag):
            raise ParseError("could not find part-of-speech section")
        pos_list = [pos.text for pos in pos_section.children]

        # custom definition (may not be present)
        custom_meaning = meanings.find('div', class_='custom-meaning')
        if custom_meaning:
            notes = "".join(str(element) for element in custom_meaning.contents)
        else:
            notes = None

        # custom sentence (may not be present)
        sentence_section = soup.find('div', class_='card-sentence')
        if sentence_section:
            sentence = self._strip_furigana(sentence_section)
        else:
            sentence = None

        # Combine parts of speech and definitions into the glossary field.
        pos = ", ".join(pos_list)
        definitions = strings_to_html_list(definitions)
        glossary = f'<div class="glossary"><p class="pos">{pos}</p>{definitions}</div>'

        return Word(
            spelling=spelling,
            reading=reading,
            glossary=glossary,
            notes=notes,
            sentence=sentence,
        )


@functools.cache
def scraper():
    return JPDBScraper(COOKIE)


def collect_words(words: List[str]):
    lookup = []
    for i, word in enumerate(words, 1):
        print(f"({i}/{len(words)}) looking up word {word}")
        lookup.append(scraper().lookup_word(word))
        time.sleep(1)

    return lookup


def build_csv(words: List[Word], output_filename: str) -> None:
    pathlib.Path(output_filename).parent.mkdir(parents=True, exist_ok=True)
    with open(output_filename, "wt") as csvfile:
        writer = csv.DictWriter(
            csvfile,
            fieldnames=[field.name for field in dataclasses.fields(Word)]
        )
        writer.writeheader()

        for word in words:
            writer.writerow(dataclasses.asdict(word))


def review_words(jpdb_reviews: dict) -> List[str]:
    return list({
        entry["spelling"] for entry in itertools.chain(
            jpdb_reviews["cards_vocabulary_jp_en"],
            jpdb_reviews["cards_vocabulary_en_jp"],
        )
    })


def create_reviews_csv(review_file: str, prev_review_file: Optional[str], output: str, limit: Optional[int]):
    with open(review_file) as f:
        reviews = json.load(f)

    words = review_words(reviews)

    if prev_review_file:
        with open(prev_review_file) as pf:
            previous_reviews = json.load(pf)
        words -= review_words(previous_reviews)

    lookup = collect_words(words[:limit])
    build_csv(lookup, output)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--review-file",
        "-r",
        help="JPDB review file JSON",
        type=str,
        default="review.json",
    )
    parser.add_argument(
        "--prev-review-file",
        "-p",
        help="Previous JPDB review file JSON. Words already present in this file won't be "
             "included in the final output.",
        type=str,
        required=False,
    )
    parser.add_argument(
        "--output",
        "-o",
        help="Output file",
        type=str,
        default="jpdb_anki_reviews.csv",
    )
    parser.add_argument(
        "--limit",
        help="Maximum words to look up (useful for testing)",
        type=int,
        required=False,
    )

    args = parser.parse_args()
    create_reviews_csv(
        review_file=args.review_file,
        prev_review_file=args.prev_review_file,
        output=args.output,
        limit=args.limit,
    )
