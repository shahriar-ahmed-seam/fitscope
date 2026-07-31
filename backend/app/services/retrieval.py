"""Voyage AI embeddings + reranking, with a local fallback.

The fallback (TF-IDF cosine over character/word n-grams) exists so the product
still returns a defensible ranking if the embedding provider is unreachable, and
so the eval harness can be run offline.
"""

from __future__ import annotations

import asyncio
import logging
import math
import re
import time
from collections import Counter, deque
from itertools import pairwise

import httpx

from .. import db
from ..config import settings
from .textkit import sha

log = logging.getLogger("fitscope.retrieval")

EMBED_BATCH = 96


def configured() -> bool:
    return bool(settings.voyage_api_key.strip())


class RateLimited(RuntimeError):
    """The provider quota is exhausted and waiting would exceed the budget."""


class _TokenBucket:
    """Process-wide request shaper.

    Voyage's free tier allows 3 requests per minute. Firing one reranker call per
    requirement would burn that in a single analysis, so calls queue here and
    give up quickly (falling back to local scoring) instead of stacking retries.
    """

    def __init__(self) -> None:
        self._stamps: deque[float] = deque()
        self._lock = asyncio.Lock()

    def _prune(self, now: float) -> None:
        while self._stamps and now - self._stamps[0] > 60.0:
            self._stamps.popleft()

    async def acquire(self, max_wait: float) -> None:
        deadline = time.monotonic() + max_wait
        while True:
            async with self._lock:
                now = time.monotonic()
                self._prune(now)
                limit = max(settings.voyage_requests_per_minute, 1)
                if len(self._stamps) < limit:
                    self._stamps.append(now)
                    return
                wait_for = 60.0 - (now - self._stamps[0]) + 0.05
            if time.monotonic() + wait_for > deadline:
                raise RateLimited(
                    f"provider quota exhausted; next slot in {wait_for:.1f}s"
                )
            await asyncio.sleep(min(wait_for, 1.0))


_bucket = _TokenBucket()


async def _voyage_post(path: str, payload: dict, operation: str) -> dict:
    headers = {
        "Authorization": f"Bearer {settings.voyage_api_key}",
        "Content-Type": "application/json",
    }
    url = f"{settings.voyage_base_url.rstrip('/')}/{path}"
    started = time.perf_counter()
    last: Exception | None = None
    for attempt in range(2):
        await _bucket.acquire(settings.voyage_max_wait_seconds)
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code == 429:
                raise RateLimited("voyage 429: " + resp.text[:120])
            if resp.status_code >= 500:
                raise httpx.HTTPStatusError(
                    f"upstream {resp.status_code}", request=resp.request, response=resp
                )
            resp.raise_for_status()
            body = resp.json()
            await db.log_usage(
                "voyage",
                payload.get("model", ""),
                operation,
                {"total_tokens": (body.get("usage") or {}).get("total_tokens", 0)},
                int((time.perf_counter() - started) * 1000),
            )
            return body
        except RateLimited:
            raise
        except Exception as exc:
            last = exc
            if attempt == 1:
                raise
            log.warning("voyage retry (%s): %s", operation, exc)
            await asyncio.sleep(0.6)
    raise RuntimeError(str(last))


# --------------------------------------------------------------------------- #
# Local fallback vectoriser
# --------------------------------------------------------------------------- #

_TOKEN = re.compile(r"[a-z0-9+#.]+")

_STOP = {
    "a", "an", "and", "or", "the", "of", "to", "in", "on", "at", "for", "with", "by", "as", "is",
    "are", "be", "been", "will", "you", "your", "our", "we", "they", "it", "its", "this", "that",
    "these", "those", "have", "has", "had", "using", "use", "used", "such", "including", "etc",
    "able", "must", "should", "would", "can", "could", "not", "but", "from", "into", "over",
    "than", "then", "there", "their", "them", "who", "what", "which", "when", "while",
    "experience", "experienced", "years", "year", "strong", "solid", "good", "excellent", "least",
    "knowledge", "skills", "skill", "ability", "work", "working", "role", "job", "candidate",
    "plus", "preferred", "required", "require", "requires", "familiarity", "understanding",
    "hands", "proven", "track", "record", "well", "very", "highly", "more", "other", "across",
    "within", "also", "each", "any", "all", "some", "one", "two", "new", "like", "e.g", "i.e",
}

_STEM_SUFFIXES = (
    "ations", "ation", "ising", "izing", "ised", "ized", "ing", "ers", "er", "es", "s",
)


def _stem(word: str) -> str:
    if len(word) <= 4 or any(ch.isdigit() for ch in word):
        return word
    for suffix in _STEM_SUFFIXES:
        if word.endswith(suffix) and len(word) - len(suffix) >= 4:
            return word[: -len(suffix)]
    return word


def _words(text: str) -> list[str]:
    return [
        _stem(w.strip("."))
        for w in _TOKEN.findall(text.lower())
        if w not in _STOP and len(w.strip(".")) > 1
    ]


def _tokens(text: str) -> list[str]:
    words = _words(text)
    return [*words, *(f"{a}_{b}" for a, b in pairwise(words))]


def _tfidf_matrix(texts: list[str]) -> list[dict[str, float]]:
    docs = [Counter(_tokens(t)) for t in texts]
    df: Counter[str] = Counter()
    for doc in docs:
        df.update(doc.keys())
    n = max(len(docs), 1)
    vectors: list[dict[str, float]] = []
    for doc in docs:
        vec: dict[str, float] = {}
        for term, count in doc.items():
            idf = math.log((n + 1) / (df[term] + 0.5)) + 1.0
            vec[term] = (1 + math.log(count)) * idf
        norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
        vectors.append({k: v / norm for k, v in vec.items()})
    return vectors


def sparse_similarity(query: str, documents: list[str]) -> list[float]:
    """Cosine similarity over TF-IDF n-grams. Used for shortlisting only."""
    vectors = _tfidf_matrix([query, *documents])
    q = vectors[0]
    scores = []
    for vec in vectors[1:]:
        shared = set(q) & set(vec)
        scores.append(sum(q[t] * vec[t] for t in shared))
    return scores


def lexical_relevance(query: str, documents: list[str]) -> list[float]:
    """Absolute 0-1 relevance without a provider call.

    Cosine similarity alone is not usable as a coverage signal: its magnitude
    depends on document length, so thresholds calibrated for a cross-encoder
    would mislabel everything. Instead this leans on IDF-weighted *query
    recall* — what share of the requirement's informative terms the candidate
    line actually contains — which is bounded and comparable across queries.
    """
    query_terms = list(dict.fromkeys(_words(query)))
    if not query_terms:
        return [0.0] * len(documents)

    doc_word_sets = [set(_words(d)) for d in documents]
    n = max(len(documents), 1)
    idf = {
        term: math.log((n + 1) / (1 + sum(1 for s in doc_word_sets if term in s))) + 1.0
        for term in query_terms
    }
    total_idf = sum(idf.values()) or 1.0
    cosines = sparse_similarity(query, documents)

    scores: list[float] = []
    for words, cosine_score in zip(doc_word_sets, cosines, strict=False):
        recall = sum(idf[t] for t in query_terms if t in words) / total_idf
        scores.append(min(1.0, 0.72 * recall + 0.28 * min(1.0, cosine_score * 1.6)))
    return scores


# --------------------------------------------------------------------------- #
# Public API
# --------------------------------------------------------------------------- #


async def embed(texts: list[str], input_type: str = "document") -> list[list[float]] | None:
    """Embed texts. Returns None when the provider is unavailable or throttled.

    Batching matters here: the free tier allows only a handful of requests per
    minute, so an analysis embeds every requirement and every resume line in one
    request rather than one request per side.
    """
    if not texts or not configured():
        return None

    key = "emb:" + sha(settings.voyage_embed_model, input_type, *texts)
    cached = await db.cache_get(key)
    if cached:
        return cached

    vectors: list[list[float]] = []
    try:
        for start in range(0, len(texts), EMBED_BATCH):
            batch = texts[start : start + EMBED_BATCH]
            body = await _voyage_post(
                "embeddings",
                {
                    "model": settings.voyage_embed_model,
                    "input": batch,
                    "input_type": input_type,
                    "output_dimension": settings.voyage_embed_dim,
                    "truncation": True,
                },
                f"embed:{input_type}",
            )
            ordered = sorted(body.get("data", []), key=lambda d: d.get("index", 0))
            vectors.extend(item["embedding"] for item in ordered)
    except RateLimited as exc:
        log.warning("embeddings throttled, using lexical retrieval: %s", exc)
        return None
    except Exception as exc:
        log.error("embedding failed, falling back to lexical retrieval: %s", exc)
        return None

    if len(vectors) == len(texts) and len(texts) <= 200:
        await db.cache_put(key, "voyage", vectors)
    return vectors


async def embed_pairs(
    documents: list[str], queries: list[str]
) -> tuple[list[list[float]] | None, list[list[float]] | None]:
    """Embed both sides of the match in a single provider request."""
    if not documents or not queries or not configured():
        return None, None
    combined = await embed(documents + queries, "document")
    if not combined or len(combined) != len(documents) + len(queries):
        return None, None
    return combined[: len(documents)], combined[len(documents) :]


def cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=False))
    na = math.sqrt(sum(x * x for x in a)) or 1.0
    nb = math.sqrt(sum(y * y for y in b)) or 1.0
    return dot / (na * nb)


def rerank_available() -> bool:
    return configured() and settings.voyage_rerank_enabled


async def rerank(
    query: str, documents: list[str], top_k: int | None = None
) -> list[tuple[int, float]]:
    """Return [(document_index, relevance_score)] sorted best first.

    Voyage rerank scores are calibrated 0-1 relevance values, which is why they
    can drive coverage thresholds directly. The call is opt-in
    (VOYAGE_RERANK_ENABLED) because it costs one request per requirement; with a
    3 RPM key that is unaffordable, so scoring defaults to the LLM judge and this
    path exists for keys with real throughput.
    """
    if not documents:
        return []
    top_k = min(top_k or len(documents), len(documents))

    if rerank_available():
        key = "rr:" + sha(settings.voyage_rerank_model, query, *documents)
        cached = await db.cache_get(key)
        if cached:
            return [(int(i), float(s)) for i, s in cached]
        try:
            body = await _voyage_post(
                "rerank",
                {
                    "model": settings.voyage_rerank_model,
                    "query": query,
                    "documents": documents,
                    "top_k": top_k,
                    "truncation": True,
                },
                "rerank",
            )
            results = [
                (int(item["index"]), float(item["relevance_score"]))
                for item in body.get("data", [])
            ]
            results.sort(key=lambda x: x[1], reverse=True)
            await db.cache_put(key, "voyage", results)
            return results
        except RateLimited as exc:
            log.warning("rerank throttled, using lexical scores: %s", exc)
        except Exception as exc:
            log.error("rerank failed, using lexical scores: %s", exc)

    scores = lexical_relevance(query, documents)
    ranked = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)
    return ranked[:top_k]
