import re
import unicodedata


def grade_from_attempts(attempts: int, passed: bool) -> int:
    """Map a card's outcome to an SM-2 grade.

    ``attempts`` is the number of tries used, with 1 representing a
    first-try answer. The retry limit is a policy of the caller, not this
    function.
    """
    if not passed:
        return 1
    return 5 if attempts == 1 else 3


def check_reading(expected: str, typed: str) -> bool:
    """True if the typed kana matches the expected reading."""
    # NFKC folds half-width kana to full-width (and full-width ASCII to
    # half-width), so equivalent-looking readings compare equal.
    expected_norm = unicodedata.normalize("NFKC", expected).strip()
    typed_norm = unicodedata.normalize("NFKC", typed).strip()
    return expected_norm == typed_norm


def _normalize_meaning(s: str) -> str:
    """Fold one English meaning to a canonical form for comparison."""
    s = unicodedata.normalize("NFKC", s).strip().lower()
    s = s.rstrip(".!?,")            # drop trailing punctuation
    words = s.split()              # split() with no args also collapses whitespace
    if len(words) > 1 and words[0] in {"a", "an", "the"}:
        words = words[1:]         # drop a leading article
    return " ".join(words)


def check_meaning(expected: str, typed: str) -> bool:
    """True if the typed English matches any accepted meaning in ``expected``."""
    candidates = {_normalize_meaning(c) for c in re.split(r"[,;/]", expected)}
    candidates.discard("")        # ignore blanks from a stray separator
    return _normalize_meaning(typed) in candidates