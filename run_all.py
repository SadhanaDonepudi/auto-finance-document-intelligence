"""Reproducible end-to-end run.

  python run_all.py

Generates the corpus + loan DB, renders a 10-doc PDF sample, builds the
TF-IDF index, runs the 100-question evaluation, runs the retrieval
experiment (chunk size x top-k x reranking), and writes outputs/.
Everything is deterministic (seed 42); README numbers come from
outputs/results.json produced by this script.
"""
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

from corpus import generate_corpus          # noqa: E402
from evaluate import build_test_set, evaluate  # noqa: E402
from ingest import build_chunks, parse_pdf  # noqa: E402
from loans import build_db                  # noqa: E402
from pdf_sample import render_sample        # noqa: E402
from retrieval import Retriever             # noqa: E402
from router import answer_question          # noqa: E402

ROOT = Path(__file__).parent


def main():
    data = ROOT / "data"
    out = ROOT / "outputs"
    data.mkdir(exist_ok=True)
    out.mkdir(exist_ok=True)

    docs = generate_corpus()
    (data / "corpus.json").write_text(json.dumps(docs, indent=1))
    n_loans = build_db(data / "loans.db")
    n_pdfs = render_sample(docs, ROOT / "data" / "sample_docs")
    # Exercise the PDF path: parse one sample PDF and check it reads.
    pdf_pages = parse_pdf(ROOT / "data" / "sample_docs" / f"{docs[0]['doc_id']}.pdf")

    questions = build_test_set(docs, data / "loans.db")

    def make_answer_fn(chunk_size, top_k, rerank):
        chunks = build_chunks(docs, chunk_size=chunk_size)
        ret = Retriever(chunks)
        return lambda q: answer_question(q, ret, str(data / "loans.db"),
                                         top_k=top_k, rerank=rerank)

    main_eval = evaluate(questions,
                         make_answer_fn(chunk_size=800, top_k=5, rerank=True))
    doc_qs = [q for q in questions if q["kind"] == "document"]

    rows = []
    for chunk_size in [400, 800, 1200]:
        for top_k in [3, 5, 10]:
            for rerank in [False, True]:
                ev = evaluate(doc_qs, make_answer_fn(chunk_size, top_k, rerank))
                wrong = 1 - ev["accuracy"]
                rows.append({"chunk_size": chunk_size, "top_k": top_k,
                             "rerank": rerank, "doc_accuracy": round(ev["accuracy"], 4),
                             "wrong_rate": round(wrong, 4),
                             "correct": ev["correct"], "n": ev["n"]})
    with open(out / "experiment.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    baseline = next(r for r in rows if r["chunk_size"] == 800
                    and r["top_k"] == 3 and not r["rerank"])
    best = min(rows, key=lambda r: r["wrong_rate"])
    reduction = ((baseline["wrong_rate"] - best["wrong_rate"])
                 / baseline["wrong_rate"] if baseline["wrong_rate"] else 0.0)

    results = {
        "documents": len(docs),
        "by_kind": {k: sum(1 for d in docs if d["kind"] == k)
                    for k in sorted({d["kind"] for d in docs})},
        "loans": n_loans,
        "pdf_sample_docs": n_pdfs,
        "pdf_sample_pages_parsed": len(pdf_pages),
        "test_set_n": len(questions),
        "doc_questions": len(doc_qs),
        "sql_questions": len(questions) - len(doc_qs),
        "accuracy": round(main_eval["accuracy"], 4),
        "correct": main_eval["correct"],
        "doc_accuracy_main": round(
            sum(1 for d in main_eval["detail"]
                if d["kind"] == "document" and d["correct"]) / len(doc_qs), 4),
        "sql_accuracy_main": round(
            sum(1 for d in main_eval["detail"]
                if d["kind"] == "sql" and d["correct"])
            / (len(questions) - len(doc_qs)), 4),
        "baseline_config": {"chunk_size": 800, "top_k": 3, "rerank": False},
        "baseline_wrong_rate": baseline["wrong_rate"],
        "best_config": {"chunk_size": best["chunk_size"], "top_k": best["top_k"],
                        "rerank": best["rerank"]},
        "best_wrong_rate": best["wrong_rate"],
        "wrong_answer_reduction": round(reduction, 4),
    }
    (out / "results.json").write_text(json.dumps(results, indent=2))
    (out / "eval_detail.json").write_text(json.dumps(main_eval["detail"], indent=1))
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
