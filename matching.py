import re

STOPWORDS = {
    "the", "a", "an", "and", "or", "to", "of", "in", "for", "with",
    "on", "is", "are", "at", "as", "be", "this", "that", "will",
    "years", "year", "experience", "strong", "good", "ability",
}


def _keywords(text):
    words = re.findall(r"[a-zA-Z][a-zA-Z0-9+#.]*", text.lower())
    return {w for w in words if w not in STOPWORDS and len(w) > 2}


def score_match(resume_text, requirements_text):
    """Simple keyword-overlap score, 0-100. Swap this out for an LLM call later."""
    resume_kw = _keywords(resume_text)
    req_kw = _keywords(requirements_text)
    if not req_kw:
        return 0, []
    overlap = resume_kw & req_kw
    score = round(100 * len(overlap) / len(req_kw), 1)
    return min(score, 100), sorted(overlap)
