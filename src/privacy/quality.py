"""Phase-1 quality filters: minimum length + English-only review text."""

from __future__ import annotations

import re

from langdetect import DetectorFactory, LangDetectException, detect_langs

# Deterministic langdetect across runs
DetectorFactory.seed = 0

MIN_WORDS = 8
EN_MIN_PROB = 0.70

# Letters outside Latin (Devanagari, Arabic, CJK, Cyrillic, etc.)
NON_LATIN_RE = re.compile(
    r"[\u0400-\u04FF\u0600-\u06FF\u0900-\u097F\u0980-\u09FF"
    r"\u0A00-\u0A7F\u0A80-\u0AFF\u0B00-\u0B7F\u0B80-\u0BFF"
    r"\u0C00-\u0C7F\u0C80-\u0CFF\u0D00-\u0D7F\u0D80-\u0DFF"
    r"\u0E00-\u0E7F\u0E80-\u0EFF\u0F00-\u0FFF"
    r"\u3040-\u30FF\u3400-\u9FFF\uAC00-\uD7AF]"
)

WORD_RE = re.compile(r"[A-Za-z']+")

# Common romanized Hindi / Hinglish tokens (India Play feed)
HINGLISH_TOKENS = frozenset(
    {
        "hai",
        "hain",
        "nahi",
        "nahin",
        "nahiin",
        "accha",
        "achha",
        "acche",
        "achhe",
        "bahut",
        "bhut",
        "bohot",
        "theek",
        "thik",
        "magar",
        "lekin",
        "kuch",
        "kuchh",
        "jyada",
        "zyada",
        "sawal",
        "jawab",
        "paisa",
        "paise",
        "karna",
        "karta",
        "karte",
        "karo",
        "karlo",
        "raha",
        "rahi",
        "rahe",
        "rahata",
        "dekho",
        "dekha",
        "sabhi",
        "sab",
        "bilkul",
        "matlab",
        "kyunki",
        "kyun",
        "kya",
        "kaise",
        "kaisa",
        "kaisi",
        "acha",
        "bura",
        "buri",
        "sahi",
        "galat",
        "bhai",
        "yaar",
        "mujhe",
        "mujhko",
        "tumhe",
        "aap",
        "aapka",
        "apka",
        "mera",
        "meri",
        "mere",
        "unki",
        "unka",
        "uska",
        "uski",
        "isko",
        "usko",
        "karne",
        "kehte",
        "kehta",
        "kehti",
        "bolta",
        "bolti",
        "bolte",
        "chahiye",
        "chahie",
        "zarurat",
        "jarurat",
        "samajh",
        "samajhta",
        "samajhti",
        "dikkat",
        "kaam",
        "thoda",
        "thodi",
        "krta",
        "krte",
        "krna",
        "nhi",
        "bht",
        "badiya",
        "badhiya",
        "zabardast",
        "shukriya",
        "dhanyavad",
        "namaste",
    }
)


def word_count(text: str) -> int:
    """Count whitespace-separated tokens (matches operator 'words' intuition)."""
    return len(text.split())


def _hinglish_ratio(text: str) -> tuple[int, float]:
    tokens = WORD_RE.findall(text.lower())
    if not tokens:
        return 0, 0.0
    hits = sum(1 for t in tokens if t in HINGLISH_TOKENS)
    return hits, hits / len(tokens)


def looks_english(text: str) -> bool:
    """
    True only when review body is English.

    Drops: non-Latin scripts, clear non-English (langdetect), and heavy Hinglish.
    """
    stripped = text.strip()
    if not stripped:
        return False

    if NON_LATIN_RE.search(stripped):
        return False

    hits, ratio = _hinglish_ratio(stripped)
    if hits >= 3 or (hits >= 2 and ratio >= 0.25):
        return False

    try:
        langs = detect_langs(stripped)
    except LangDetectException:
        return False
    if not langs:
        return False

    top = langs[0]
    return top.lang == "en" and top.prob >= EN_MIN_PROB


def passes_quality(text: str, *, min_words: int = MIN_WORDS) -> bool:
    """Keep review if it has enough words and is English."""
    if word_count(text) < min_words:
        return False
    return looks_english(text)
