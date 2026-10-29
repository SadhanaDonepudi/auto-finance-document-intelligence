"""Streamlit chatbot UI (run: streamlit run app.py).

No LLM is called. Answers are extractive: the router sends the question
to document search (TF-IDF + reranking) or to the SQL tool, and the
answer quotes the retrieved chunks with document + page citations.
See docs/user_guide.md for the non-technical guide.
"""
import json
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from ingest import build_chunks  # noqa: E402
from retrieval import Retriever  # noqa: E402
from router import answer_question  # noqa: E402

ROOT = Path(__file__).parent


@st.cache_resource
def load():
    docs = json.loads((ROOT / "data" / "corpus.json").read_text())
    retriever = Retriever(build_chunks(docs, chunk_size=800))
    return retriever


st.title("Auto Finance Document Assistant")
st.write("Ask about synthetic auto finance documents or the synthetic loan "
         "portfolio. Every grounded answer cites its document and page. "
         "All documents are synthetic — none are real contracts or filings.")
retriever = load()
question = st.text_input("Your question",
                         placeholder="e.g. What is the late fee for the lease "
                         "agreement on the 2023 Toyota Camry?")
if st.button("Ask") and question:
    result = answer_question(question, retriever, str(ROOT / "data" / "loans.db"))
    st.write(f"**Tool used:** {result['tool']}")
    st.write(result["answer"])
    st.write("**Citations**")
    for c in result["citations"]:
        if "page" in c:
            st.write(f"- {c['source']} (page {c['page']}) — {c['title']}")
        else:
            st.write(f"- {c['source']} — {c['detail']}")
