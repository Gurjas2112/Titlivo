"""Transliteration of names from Indian scripts to Latin, and search keys that match across scripts."""

import re
import unicodedata

from indic_transliteration import sanscript
from indic_transliteration.sanscript import transliterate

_SCRIPTS = [
    (re.compile(r"[ऀ-ॿ]"), sanscript.DEVANAGARI, True),
    (re.compile(r"[ಀ-೿]"), sanscript.KANNADA, False),
    (re.compile(r"[઀-૿]"), sanscript.GUJARATI, True),
]
_FOLD = {"ś": "sh", "ṣ": "sh", "ṛ": "ri", "ṅ": "n", "ñ": "n", "ḥ": "h", "ṁ": "n", "ṃ": "n"}


def detect_script(text: str) -> str | None:
    for pattern, script, _ in _SCRIPTS:
        if pattern.search(text):
            return script
    return None


def to_iso(text: str) -> str:
    """ISO 15919 transliteration (keeps diacritics). Latin text is returned unchanged."""
    for pattern, script, _ in _SCRIPTS:
        if pattern.search(text):
            return transliterate(text, script, sanscript.ISO)
    return text


def _fold(text: str) -> str:
    for k, v in _FOLD.items():
        text = text.replace(k, v)
    text = unicodedata.normalize("NFD", text)
    return "".join(c for c in text if not unicodedata.combining(c))


def to_latin(text: str) -> str:
    """Readable Latin spelling, e.g. "सुनील पाटील" → "Sunil Patil"."""
    drop_schwa = any(p.search(text) and d for p, _, d in _SCRIPTS)
    words = []
    for w in _fold(to_iso(text)).split():
        if drop_schwa and len(w) > 2 and w.endswith("a") and w[-2] not in "aeiou":
            w = w[:-1]
        words.append(w.capitalize())
    return " ".join(words)


def name_key(text: str) -> str:
    """Lower-case search key that is the same for "Sunil Patil", "sunīl pāṭīl" and "सुनील पाटील"."""
    s = to_latin(text).lower() if detect_script(text) else _fold(text).lower()
    s = s.replace("ee", "i").replace("oo", "u").replace("aa", "a").replace("th", "t")
    s = re.sub(r"([a-z])\1+", r"\1", s)
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def mask(name: str) -> str:
    """ "Sunil Patil" → "S. P****" (shown to callers without the parcels:pii scope)."""
    parts = name.split()
    if not parts:
        return ""
    if len(parts) == 1:
        return parts[0][0] + "****"
    return " ".join(p[0] + "." for p in parts[:-1]) + " " + parts[-1][0] + "****"
