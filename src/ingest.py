"""Parsing + chunking.

Text corpus records carry explicit pages, so a chunk's page citation is
exact. PDFs (the sample set) are parsed with pypdf; page breaks in the
rendered sample correspond to the same page list, so citations agree.
Chunking is character-based with overlap, applied within a single page
so a chunk never spans two pages.
"""
import json
import re
from pathlib import Path

try:
    from pypdf import PdfReader
except ImportError:  # pragma: no cover
    PdfReader = None


def load_corpus(path):
    return json.loads(Path(path).read_text())


def parse_pdf(path):
    if PdfReader is None:
        raise RuntimeError("pypdf is not installed")
    reader = PdfReader(str(path))
    return [(i + 1, (page.extract_text() or "").strip())
            for i, page in enumerate(reader.pages)]


def chunk_page(text, chunk_size=800, overlap=100):
    """Split one page's text into overlapping character chunks."""
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]
    chunks, start = [], 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        if end >= len(text):
            break
        start = end - overlap
    return chunks


def build_chunks(docs, chunk_size=800, overlap=100):
    chunks = []
    for doc in docs:
        for page_no, page_text in enumerate(doc["pages"], start=1):
            for chunk in chunk_page(page_text, chunk_size, overlap):
                chunks.append({"doc_id": doc["doc_id"], "kind": doc["kind"],
                               "title": doc["title"], "page": page_no,
                               "text": chunk})
    return chunks
