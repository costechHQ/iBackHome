"""Matching a visitor's question to the best entry in knowledge.py (ADR 0006). Owner: Christopher.

Plain Python, no model: lower-case, drop stop words, strip a plural "s", then score each entry by the words it
shares with the question. A word that is rare across the entries counts for more than a common one, and a
whole keyword phrase found in the question gets a bonus. Below MIN_SCORE nothing matches and the answer is a
handoff to a person. Deterministic and instant: it can't invent a fact or be talked into a promise.
"""

import math
import re
from dataclasses import dataclass

from app.features.assistant.knowledge import ENTRIES, Entry

STOPWORDS = frozenset(
    """a an the is are was were be been am do does did done can could would should will shall may might must
    i me my mine you your yours we us our ours it its they them their he she his her this that these those
    to of in on at by for with from about as into than then so if or and but not no yes how what when where
    which who whom why please hi hello hey tell give want like get got just also any some there here
    have has had""".split()
)

MIN_SCORE = 4.0  # below this nothing matches well enough: hand off to a person
RELATED_MIN_SCORE = 3.0
RELATED_RATIO = 0.2  # a related entry must score at least this share of the best one
MAX_RELATED = 2
PHRASE_BONUS = 4.0
RAW_PHRASE_BONUS = 2.0
KEYWORD_WEIGHT = 2.0

_WORD = re.compile(r"[a-z0-9]+")


def _stem(word: str) -> str:
    if len(word) > 4 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("s") and not word.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def tokens(text: str) -> list[str]:
    """The meaningful words of `text`, lower-cased, without stop words, a plural 's' stripped."""
    words = _WORD.findall(text.lower().replace("'", "").replace("’", ""))
    return [_stem(w) for w in words if w not in STOPWORDS]


@dataclass(frozen=True)
class _Indexed:
    entry: Entry
    strong_tokens: frozenset[str]  # words that are keywords on their own
    soft_tokens: frozenset[str]  # words from multi-word keywords and from the example questions
    phrases: tuple[tuple[str, ...], ...]  # keyword phrases of two or more meaningful words
    raw_phrases: tuple[tuple[str, ...], ...]  # keyword phrases as typed, stop words and all


def _raw_words(text: str) -> tuple[str, ...]:
    return tuple(_WORD.findall(text.lower().replace("'", "").replace("’", "")))


def _build() -> tuple[tuple[_Indexed, ...], dict[str, float]]:
    indexed = []
    for entry in ENTRIES:
        strong: set[str] = set()
        soft: set[str] = set()
        phrases = []
        raw_phrases = []
        for keyword in entry.keywords:
            words = tokens(keyword)
            if len(words) == 1 and len(_raw_words(keyword)) == 1:
                strong.update(words)
            else:
                soft.update(words)
            if len(words) >= 2:
                phrases.append(tuple(words))
            raw = _raw_words(keyword)
            if len(raw) >= 2:
                raw_phrases.append(raw)
        soft.update(w for q in entry.questions for w in tokens(q))
        indexed.append(
            _Indexed(entry, frozenset(strong), frozenset(soft - strong), tuple(phrases), tuple(raw_phrases))
        )
    total = len(indexed)
    document_frequency: dict[str, int] = {}
    for item in indexed:
        for word in item.strong_tokens | item.soft_tokens:
            document_frequency[word] = document_frequency.get(word, 0) + 1
    weights = {word: 1.0 + math.log(total / df) for word, df in document_frequency.items()}
    return tuple(indexed), weights


_INDEX, _WEIGHTS = _build()


def _contains(haystack: list[str], phrase: tuple[str, ...]) -> bool:
    size = len(phrase)
    return any(tuple(haystack[i : i + size]) == phrase for i in range(len(haystack) - size + 1))


def _score(item: _Indexed, query: list[str], query_set: set[str], raw: tuple[str, ...]) -> float:
    score = 0.0
    for word in query_set:
        weight = _WEIGHTS.get(word, 0.0)
        if word in item.strong_tokens:
            score += KEYWORD_WEIGHT * weight
        elif word in item.soft_tokens:
            score += weight
    for phrase in item.phrases:
        if _contains(query, phrase):
            score += PHRASE_BONUS
    for phrase in item.raw_phrases:
        if _contains(list(raw), phrase):
            score += RAW_PHRASE_BONUS * (len(phrase) - 1)  # the longer the phrase found, the surer we are
    return score


@dataclass(frozen=True)
class Match:
    entry: Entry
    score: float


def rank(message: str) -> list[Match]:
    """Every entry that shares something with the question, best first (ties keep the file's order)."""
    query = tokens(message)
    raw = _raw_words(message)
    if not query and not raw:
        return []
    query_set = set(query)
    scored = [Match(item.entry, _score(item, query, query_set, raw)) for item in _INDEX]
    return sorted((m for m in scored if m.score > 0), key=lambda m: -m.score)


def best(message: str) -> tuple[Match | None, list[Entry]]:
    """The confident best match (None if nothing reaches MIN_SCORE) and up to two related entries."""
    ranked = rank(message)
    if not ranked or ranked[0].score < MIN_SCORE:
        return None, []
    top = ranked[0]
    related = [
        m.entry
        for m in ranked[1:]
        if not m.entry.handoff
        and m.score >= RELATED_MIN_SCORE
        and m.score >= RELATED_RATIO * top.score
        and m.entry.id != top.entry.id
    ][:MAX_RELATED]
    return top, related
