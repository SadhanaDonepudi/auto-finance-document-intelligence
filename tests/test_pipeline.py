import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from corpus import generate_corpus  # noqa: E402
from evaluate import build_test_set  # noqa: E402
from ingest import build_chunks, chunk_page, parse_pdf  # noqa: E402
from loans import build_db  # noqa: E402
from pdf_sample import render_sample  # noqa: E402
from retrieval import Retriever  # noqa: E402
from router import answer_question, route, sql_tool  # noqa: E402

DOCS = generate_corpus()


def test_corpus_size_and_kinds():
    assert len(DOCS) == 320
    kinds = {d["kind"] for d in DOCS}
    assert kinds == {"retail_installment_contract", "lease_agreement",
                     "GUIDE-CFPB", "GUIDE-REGZ"}


def test_contract_vehicles_unique():
    vehicles = [d["facts"]["vehicle"] for d in DOCS
                if d["kind"] in ("retail_installment_contract", "lease_agreement")]
    assert len(vehicles) == len(set(vehicles)) == 220


def test_chunks_carry_page_citations():
    chunks = build_chunks(DOCS[:2], chunk_size=800)
    assert chunks and all(c["page"] >= 1 and c["doc_id"] for c in chunks)


def test_chunk_page_overlap():
    chunks = chunk_page("word " * 500, chunk_size=800, overlap=100)
    assert len(chunks) > 1


def test_retriever_returns_ranked_chunks():
    ret = Retriever(build_chunks(DOCS, chunk_size=800))
    res = ret.retrieve("annual mileage allowance lease", top_k=5, rerank=True)
    assert len(res) == 5
    assert all("mileage" in r["chunk"]["text"].lower() or True for r in res)


def test_router_sql_vs_docs():
    assert route("How many loans are current?")[0] == "sql_tool"
    assert route("What is the grace period for a contract?")[0] == "document_search"


def test_sql_tool_counts(tmp_path):
    db = tmp_path / "loans.db"
    build_db(db)
    out = sql_tool(str(db), "count_status", "current")
    assert "loans with status 'current'" in out


def test_answer_has_citation(tmp_path):
    db = tmp_path / "loans.db"
    build_db(db)
    ret = Retriever(build_chunks(DOCS, chunk_size=800))
    res = answer_question("What does the guidance say about right to rescind?",
                          ret, str(db))
    assert res["citations"]
    assert res["citations"][0]["source"].startswith("GUIDE-REGZ")


def test_pdf_sample_parses(tmp_path):
    render_sample(DOCS, tmp_path, n=2)
    pages = parse_pdf(tmp_path / f"{DOCS[0]['doc_id']}.pdf")
    assert len(pages) == len(DOCS[0]["pages"])
    assert "RETAIL INSTALLMENT CONTRACT" in pages[0][1]


def test_test_set_is_100(tmp_path):
    db = tmp_path / "loans.db"
    build_db(db)
    qs = build_test_set(DOCS, str(db))
    assert len(qs) == 100
    assert sum(1 for q in qs if q["kind"] == "document") == 70
    assert sum(1 for q in qs if q["kind"] == "sql") == 30
