from __future__ import annotations

from functools import lru_cache
from math import ceil
from pathlib import Path

from shared.tokens import count_tokens

KB_DIR = Path(__file__).resolve().parents[1] / "data" / "kb"


@lru_cache
def article_ids() -> list[str]:
    return sorted(p.stem for p in KB_DIR.glob("*.md"))


@lru_cache
def load_article(article_id: str) -> str:
    return (KB_DIR / f"{article_id}.md").read_text()


@lru_cache
def all_articles_blob() -> str:
    """Concatenated help-center articles for Question 1."""
    parts = []
    for aid in article_ids():
        parts.append(f"--- {aid} ---\n{load_article(aid)}\n")
    return "\n".join(parts)


@lru_cache
def expanded_help_center_blob() -> str:
    """Expanded help center for Question 2."""
    base = all_articles_blob()
    filler = (
        "## Internal routing note\n"
        "Carrier pickup windows, warehouse bin labels, and CS macro catalog. "
        "Does not change customer policy unless an article id is cited.\n"
    )
    sample = filler + "Batch 0\n" + ("-" * 40 + "\n") * 30
    per_chunk = max(1, count_tokens(sample))
    count = max(1, ceil((210_000 - count_tokens(base)) / per_chunk))
    while True:
        chunks = [base] + [filler + f"Batch {i}\n" + ("-" * 40 + "\n") * 30 for i in range(count)]
        blob = "\n".join(chunks)
        missing = 210_000 - count_tokens(blob)
        if missing <= 0:
            return blob
        count += ceil(missing / per_chunk)


def title_index(limit: int | None = 400) -> str:
    ids = article_ids()
    if limit:
        ids = ids[:limit]
    return "\n".join(f"{aid}" for aid in ids)
