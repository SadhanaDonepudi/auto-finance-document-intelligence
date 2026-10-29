# Auto Finance Document Intelligence Chatbot (RAG + Agentic AI)

> ⚠️ **ALL DATA IS SYNTHETIC.** Every document in this project was
> generated programmatically from templates. Nothing here is a real
> retail installment contract, a real lease agreement, a real CFPB
> publication, or a real Regulation Z filing, and no answer from this
> chatbot is legal advice. Guidance notes are paraphrases written for
> this project, not quotations from official publications.

A retrieval-augmented chatbot over auto finance documents, with an
agentic router that sends each question to document search or to a SQL
tool over a synthetic loan portfolio, and answers with page-level
citations.

## How it works

```
src/corpus.py  (generate 320 synthetic docs, seed 42)
      → src/ingest.py   (parse text/PDF, chunk within a page)
      → src/retrieval.py (TF-IDF embeddings, cosine similarity, reranker)
      → src/router.py   (hand-rolled tool router: document_search | sql_tool)
      → extractive answer quoting the retrieved chunk(s), doc + page cited
```

- **Embeddings:** TF-IDF (scikit-learn, 1–2 grams) — a deliberate,
  reproducible substitute for neural embeddings; no model download.
  Chunks are indexed together with their document title (metadata
  enrichment), because a fact page that never repeats the vehicle or
  concept name otherwise cannot outrank other documents' title pages.
- **Router:** hand-rolled, not LangChain — the routing rules are
  explicit (see `src/router.py`), so the dependency would add nothing.
  The SQL tool is deterministic and pattern-matched over a fixed set of
  aggregates/lookups; it cannot run arbitrary queries.
- **Generation:** no LLM is called (no API key available). Answers are
  extractive: the quoted retrieved chunk, or the computed SQL result.
- **PDF path:** a 10-document sample is rendered as real PDFs
  (`data/sample_docs/`) and parsed with pypdf; `run_all.py` verifies
  the parse (3 pages for the first sample document).

## How to run

```bash
pip install -r requirements.txt
python run_all.py          # generate corpus + loan DB, evaluate, experiment
python -m pytest tests/ -q
streamlit run app.py       # chatbot UI (needs data/corpus.json from run_all.py)
```

See `docs/user_guide.md` for the non-technical guide and `docs/method.md`
for the full method.

## Results (actual run, synthetic — from `outputs/results.json`)

- **Corpus: 320 documents** — 120 retail installment contracts,
  100 lease agreements, 50 CFPB-style guidance notes, 50 Regulation
  Z-style guidance notes. Each contract/lease names a unique
  year/make/model/trim, so a question naming a vehicle is unambiguous.
- **Loan portfolio: 500 synthetic loans** (SQLite, `data/loans.db`).
- **Test set: 100 questions** generated from stored facts / database
  aggregates — 70 document, 30 SQL. Judge: SQL — expected value in the
  tool answer; document — expected value in any of the top-5 cited
  chunks (documented in `src/evaluate.py`).
- **Accuracy (main config: chunk 800, top-k 5, reranking on): 97/100
  = 97.0%** — document questions 67/70 = 95.7%, SQL questions 30/30
  = 100%. The 3 misses: 1 monthly-payment question and 2 questions on
  the same guidance concept (tolerance for APR disclosure), where
  same-topic title pages crowded the fact page out of the top 5.
- **Retrieval experiment** (chunk size × top-k × reranking, 70 document
  questions, full grid in `outputs/experiment.csv`):
  - Baseline (chunk 800, top-k 3, no reranking): wrong-answer rate
    **32.86%** (23/70 wrong).
  - Best (chunk 800, top-k 10, reranking on): wrong-answer rate
    **2.86%** (2/70 wrong).
  - **Wrong-answer reduction: 91.3%** ((32.86 − 2.86) / 32.86).
  - Reranking helped at every setting once title enrichment was in
    place; chunk 800 and 1200 give identical results because no page
    exceeds ~1,100 characters, while chunk 400 splits facts across
    chunks and scores worse.

## Resume claims vs measured results

| Resume claim | Measured here | Verdict |
|---|---|---|
| 300+ documents (contracts, leases, CFPB/Reg Z guidance) | **320 synthetic documents** (120 + 100 + 50 + 50) | ✅ Met in count; synthetic, not real filings |
| Agentic tool routing (doc search vs SQL) with page-level citations | Router implemented; every grounded answer cites doc + page (SQL answers cite the loan database) | ✅ Met |
| 88% accuracy on a 100-question test set | **97.0%** (97/100) | ⚠️ **Exceeds claim — but not comparable.** The test set is synthetic, generated from the same templates as the corpus, so questions are easier than real user questions. Treat 97% as an upper bound on this synthetic benchmark, not as expected real-world accuracy |
| Retrieval-quality testing cutting wrong answers by 40% | **91.3%** reduction (32.86% → 2.86% wrong, doc questions) | ⚠️ **Exceeds claim, same caveat.** The reduction is real on this grid, but it is measured on the same synthetic questions used to design the pipeline, and the "best" configuration was selected on that grid |
| Deployed as a Streamlit app with a user guide | `app.py` + `docs/user_guide.md` provided; **not deployed to a hosted service** — runs locally via `streamlit run app.py` | ⚠️ Partially met: app + guide exist, no public deployment |

## Caveats

- TF-IDF instead of neural embeddings; hand-rolled router instead of
  LangChain; template/extractive answering instead of an LLM — all
  stated here and in `docs/method.md`, none presented as the real thing.
- The generated corpus (`data/corpus.json`) and loan database
  (`data/loans.db`) are **not committed** — they are regenerated by
  `run_all.py`. Only the generation scripts, a 10-document PDF sample,
  outputs, specs, and docs are committed.
- Scores are optimistic by construction (synthetic questions from
  synthetic templates); a held-out, human-written question set would
  almost certainly score lower.
