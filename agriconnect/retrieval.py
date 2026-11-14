"""Document retrieval over approved supplier documents.

This slice uses a dependency-free TF-IDF + cosine-similarity index, built
per tenant from the ``chunks`` table. The public ``search()`` function is the
single seam we will swap for query embeddings + pgvector in a later update;
nothing else in the app needs to change.
"""
from __future__ import annotations
import math
import re
from collections import Counter
from functools import lru_cache
from typing import Optional

from . import config, db

_STOPWORDS = {
    "the", "a", "an", "and", "or", "of", "to", "in", "on", "for", "is", "are",
    "do", "does", "you", "your", "i", "we", "it", "this", "that", "with", "at",
    "be", "can", "how", "what", "when", "which", "my", "me", "have", "has",
    "please", "about", "any", "there", "if", "as", "by", "from", "will",
    "like", "get", "got", "need", "want", "would", "could", "should", "tell",
    "hi", "hello", "hey", "thanks", "thank", "them", "they", "their", "our",
    "was", "were", "been", "being", "so", "just", "also", "some", "am", "may",
    "per", "much", "many", "next", "week", "weeks", "day", "days",
    "set", "up", "use", "used", "using", "put", "make", "made", "take",
    "takes", "well", "one", "two", "give", "gives", "into", "out",
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _stem(t: str) -> str:
    """A tiny suffix stripper so 'returns' / 'returned' / 'return' match."""
    for suf in ("ing", "ed", "es", "s"):
        if t.endswith(suf) and len(t) - len(suf) >= 3:
            return t[: -len(suf)]
    return t


def tokenize(text: str) -> list[str]:
    toks = _TOKEN_RE.findall(text.lower())
    return [_stem(t) for t in toks if t not in _STOPWORDS and len(t) > 1]


class TenantIndex:
    """A small in-memory TF-IDF index for one tenant's document chunks."""

    def __init__(self, chunks: list[dict]):
        self.chunks = chunks
        self.doc_terms: list[Counter] = []
        df: Counter = Counter()
        for ch in chunks:
            terms = Counter(tokenize(ch["text"]))
            self.doc_terms.append(terms)
            for term in terms:
                df[term] += 1
        n = max(len(chunks), 1)
        # smoothed inverse document frequency
        self.idf = {t: math.log((n + 1) / (c + 1)) + 1.0 for t, c in df.items()}
        self.vectors = [self._vectorize(tc) for tc in self.doc_terms]
        self.norms = [math.sqrt(sum(w * w for w in v.values())) for v in self.vectors]

    def _vectorize(self, term_counts: Counter) -> dict[str, float]:
        return {t: tf * self.idf.get(t, 0.0) for t, tf in term_counts.items()}

    def search(self, query: str, top_k: int) -> list[tuple[dict, float]]:
        q_terms = Counter(tokenize(query))
        q_vec = {t: tf * self.idf.get(t, 0.0) for t, tf in q_terms.items()}
        q_norm = math.sqrt(sum(w * w for w in q_vec.values()))
        if q_norm == 0:
            return []
        scored: list[tuple[dict, float]] = []
        for i, ch in enumerate(self.chunks):
            dv = self.vectors[i]
            dnorm = self.norms[i]
            if dnorm == 0:
                continue
            # dot product over the smaller vector
            if len(q_vec) < len(dv):
                dot = sum(w * dv.get(t, 0.0) for t, w in q_vec.items())
            else:
                dot = sum(w * q_vec.get(t, 0.0) for t, w in dv.items())
            if dot <= 0:
                continue
            scored.append((ch, dot / (q_norm * dnorm)))
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:top_k]


@lru_cache(maxsize=16)
def _index_for(tenant_id: str, version: int) -> TenantIndex:
    conn = db.get_conn()
    try:
        rows = conn.execute(
            "SELECT c.id, c.text, c.ord, d.title, d.source "
            "FROM chunks c JOIN documents d ON c.document_id = d.id "
            "WHERE c.tenant_id = ? ORDER BY c.id",
            (tenant_id,),
        ).fetchall()
        return TenantIndex([dict(r) for r in rows])
    finally:
        conn.close()


def _chunk_count(tenant_id: str) -> int:
    conn = db.get_conn()
    try:
        return int(conn.execute(
            "SELECT COUNT(*) FROM chunks WHERE tenant_id = ?", (tenant_id,)
        ).fetchone()[0])
    finally:
        conn.close()


def search(tenant_id: str, query: str, top_k: Optional[int] = None) -> list[dict]:
    """Return the top supporting chunks for a query, scoped to one tenant.

    Each result: {title, source, text, score}. The index is cached and keyed
    by the tenant's chunk count so re-seeding invalidates it automatically.
    """
    top_k = top_k or config.RETRIEVAL_TOP_K
    index = _index_for(tenant_id, _chunk_count(tenant_id))
    results = index.search(query, top_k)
    return [
        {"title": ch["title"], "source": ch["source"], "text": ch["text"],
         "score": round(score, 4)}
        for ch, score in results
    ]
