# Method

## Corpus
320 synthetic documents generated from templates (seed 42): 120 retail
installment contracts, 100 lease agreements, 50 CFPB-style guidance
notes, 50 Regulation Z-style guidance notes. Guidance notes are
paraphrases written for this project — they are not quotations from,
and must not be mistaken for, official publications.

## Pipeline
`corpus.py` (generate) → `ingest.py` (parse, chunk within a page,
800 chars default, 100 overlap) → `retrieval.py` (TF-IDF, scikit-learn,
1–2 grams, cosine similarity; optional reranker = 0.7 × cosine +
0.3 × query-token overlap) → `router.py` (hand-rolled tool router:
document_search or sql_tool over SQLite) → extractive answer quoting
the retrieved chunk with doc + page citation.

## Evaluation
100 questions generated from stored facts / database aggregates
(`evaluate.py`): 70 document, 30 SQL. Judge: SQL — expected value in
the tool answer; document — expected value in any of the top-k cited
chunks. The retrieval experiment varies chunk size (400/800/1200),
top-k (3/5/10), and reranking on/off on the 70 document questions.
Baseline for the wrong-answer reduction is chunk 800 / top-k 3 /
no reranking; the "best" configuration is the one with the lowest
wrong-answer rate in that grid, whatever it is.

## Honest substitutions
- TF-IDF instead of neural embeddings (no model download, reproducible).
- Hand-rolled router instead of LangChain (routing rules are explicit).
- Template/extractive answering instead of an LLM (no API key available).
