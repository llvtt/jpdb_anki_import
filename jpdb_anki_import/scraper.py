#!/usr/bin/env python
import dataclasses
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

from typing import Optional, List

from . import jpdb

# vendor dependencies
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'vendor'))
import bs4


MAX_RETRIES = 5


@dataclasses.dataclass
class Word:
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
        return ''.join(self._japanese_strings(tag)).strip()

    @property
    def _headers(self) -> dict:
        # TODO: this can probably be cleaned up a little bit
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

    def _word_soup(self, word: jpdb.Vocabulary) -> bs4.BeautifulSoup:
        encoded_spelling = urllib.parse.quote(word.spelling, encoding='utf-8')
        encoded_reading = urllib.parse.quote(word.reading, encoding='utf-8')
        url = f"https://jpdb.io/vocabulary/{word.vid}/{encoded_spelling}/{encoded_reading}?lang=english#a"
        request = urllib.request.Request(
            url=url,
            method='GET',
            headers=self._headers,
        )
        for i in range(MAX_RETRIES+1):
            try:
                with urllib.request.urlopen(request) as response:
                    return bs4.BeautifulSoup(response.read(), 'html.parser')
            except urllib.error.URLError:
                if i == MAX_RETRIES:
                    raise
                time.sleep(2**i)
        # This should not be reachable
        raise ParseError("Failed to contact JPDB")

    def lookup_word(self, word: jpdb.Vocabulary) -> Word:
        soup = self._word_soup(word)

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
            notes = "".join(str(element) for element in custom_meaning.contents).strip()
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
            glossary=glossary,
            notes=notes,
            sentence=sentence,
        )
