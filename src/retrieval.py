"""TF-IDF retrieval + simple reranker.

Embedding method: TF-IDF over chunk text (scikit-learn), cosine similarity.
This is a deliberate, honest substitute for neural embeddings: no model
download, fully reproducible locally. The reranker re-scores the top
candidates with token-overlap against the query, which rewards chunks
that literally contain the question's distinguishing terms (vehicle,
fee type) rather than only sharing generic finance vocabulary.
"""
import re
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

_STOP = set("what is the of a an for in on and to how much does do".split())


def _tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in _STOP]


class Retriever:
    def __init__(self, chunks):
        self.chunks = chunks
        # Index each chunk together with its document title (standard
        # metadata enrichment): without it, a fact page that never repeats
        # the vehicle/concept name can never outrank other documents'
        # title pages, however relevant its body text is. Citations and
        # quoted text still use the chunk body only.
        self.vectorizer = TfidfVectorizer(stop_words="english", ngram_range=(1, 2))
        self.matrix = self.vectorizer.fit_transform(
            [f"{c['title']} {c['text']}" for c in chunks])

    def retrieve(self, query, top_k=5, rerank=False):
        q = self.vectorizer.transform([query])
        sims = cosine_similarity(q, self.matrix)[0]
        order = sims.argsort()[::-1]
        pool = order[: max(top_k * 4, top_k)] if rerank else order[:top_k]
        results = [{"chunk": self.chunks[i], "score": float(sims[i])} for i in pool]
        if rerank:
            qtok = set(_tokens(query))
            for r in results:
                ctok = set(_tokens(r["chunk"]["title"] + " " + r["chunk"]["text"]))
                overlap = len(qtok & ctok) / max(len(qtok), 1)
                r["score"] = 0.7 * r["score"] + 0.3 * overlap
            results.sort(key=lambda r: r["score"], reverse=True)
            results = results[:top_k]
        return results
