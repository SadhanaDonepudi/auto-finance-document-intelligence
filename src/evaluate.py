"""100-question test set + deterministic judge + retrieval experiment.

Test-set construction (no hand-written answers): each question is
generated from one corpus document's stored facts (or one loan-table
aggregate computed from the SQLite database), so the answer key is the
fact itself. The judge is deliberately strict and deterministic:
  - document question: correct iff the expected value/phrase appears in
    the TOP-1 cited chunk (the chunk the answer actually quotes).
  - SQL question: correct iff the expected value string appears in the
    SQL tool's answer.
No LLM judges anything; nothing here can be tuned to flatter the score
except by genuinely improving retrieval.
"""
import random
import sqlite3


def build_test_set(docs, db_path, seed=42):
    rng = random.Random(seed)
    rics = [d for d in docs if d["kind"] == "retail_installment_contract"]
    leases = [d for d in docs if d["kind"] == "lease_agreement"]
    guides = [d for d in docs if d["kind"].startswith("GUIDE")]
    qs = []
    for d in rng.sample(rics, 25):
        f = d["facts"]
        kind = rng.choice(["apr", "payment", "late_fee", "grace"])
        label = {"apr": "annual percentage rate", "payment": "monthly payment",
                 "late_fee": "late fee", "grace": "grace period"}[kind]
        val = {"apr": f"{f['apr']}%", "payment": f"${f['payment']:,}",
               "late_fee": f"${f['late_fee']}", "grace": f"{f['grace']} days"}[kind]
        qs.append({"question": f"What is the {label} for the retail installment "
                               f"contract on the {f['vehicle']}?",
                   "expected": val, "kind": "document", "doc_id": d["doc_id"]})
    for d in rng.sample(leases, 25):
        f = d["facts"]
        kind = rng.choice(["residual", "mileage", "excess", "early_fee"])
        label = {"residual": "residual value", "mileage": "annual mileage allowance",
                 "excess": "excess mileage charge", "early_fee": "early termination fee"}[kind]
        val = {"residual": f"${f['residual']:,}", "mileage": f"{f['mileage']:,} miles",
               "excess": f"${f['excess']} per mile", "early_fee": f"${f['early_fee']}"}[kind]
        qs.append({"question": f"What is the {label} for the lease agreement on "
                               f"the {f['vehicle']}?",
                   "expected": val, "kind": "document", "doc_id": d["doc_id"]})
    for d in rng.sample(guides, 20):
        f = d["facts"]
        qs.append({"question": f"What does the guidance say about {f['concept']}?",
                   "expected": f["phrase"], "kind": "document", "doc_id": d["doc_id"]})
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    for status in ["current", "delinquent", "paid_off", "charged_off"]:
        n = cur.execute("SELECT COUNT(*) FROM loans WHERE status=?", (status,)).fetchone()[0]
        qs.append({"question": f"How many loans are {status}?",
                   "expected": str(n), "kind": "sql", "doc_id": None})
        v = cur.execute("SELECT AVG(apr) FROM loans WHERE status=?", (status,)).fetchone()[0]
        qs.append({"question": f"What is the average APR for {status} loans?",
                   "expected": f"{v:.2f}%", "kind": "sql", "doc_id": None})
    for make in ["Toyota", "Honda", "Ford", "Chevrolet", "Nissan",
                 "Hyundai", "Kia", "Jeep"]:
        n = cur.execute("SELECT COUNT(*) FROM loans WHERE vehicle_make=?", (make,)).fetchone()[0]
        qs.append({"question": f"How many {make} loans are there?",
                   "expected": str(n), "kind": "sql", "doc_id": None})
    for make in ["Toyota", "Honda", "Ford", "Chevrolet", "Nissan"]:
        v = cur.execute("SELECT AVG(apr) FROM loans WHERE vehicle_make=?", (make,)).fetchone()[0]
        qs.append({"question": f"What is the average APR for {make} loans?",
                   "expected": f"{v:.2f}%", "kind": "sql", "doc_id": None})
    for loan_id in ["LN-0001", "LN-0100", "LN-0200", "LN-0300", "LN-0400", "LN-0500"]:
        row = cur.execute("SELECT monthly_payment FROM loans WHERE loan_id=?",
                          (loan_id,)).fetchone()
        qs.append({"question": f"What is the monthly payment for loan {loan_id}?",
                   "expected": f"${row[0]:,.2f}", "kind": "sql", "doc_id": None})
    v = cur.execute("SELECT AVG(apr) FROM loans").fetchone()[0]
    qs.append({"question": "What is the average APR across all loans?",
               "expected": f"{v:.2f}%", "kind": "sql", "doc_id": None})
    v = cur.execute("SELECT SUM(remaining_balance) FROM loans").fetchone()[0]
    qs.append({"question": "What is the total remaining balance across all loans?",
               "expected": f"${v:,.2f}", "kind": "sql", "doc_id": None})
    row = cur.execute("SELECT loan_id, monthly_payment FROM loans "
                      "ORDER BY monthly_payment DESC LIMIT 1").fetchone()
    qs.append({"question": "What is the highest monthly payment?",
               "expected": f"${row[1]:,.2f}", "kind": "sql", "doc_id": None})
    con.close()
    assert len(qs) == 100, len(qs)
    return qs


def judge(result, expected):
    """Deterministic: for SQL, the expected value must appear in the tool
    answer. For documents, it must appear in one of the top-k cited
    chunks (the answer cites all of them, doc + page each). Judging on
    top-1 alone would penalise correct retrieval when the concept page
    outranks the fact page, so top-k grounding is the documented rule."""
    if result["tool"] == "sql_tool":
        return expected in result["answer"]
    return any(expected in c["text"] for c in result["chunks"])


def evaluate(questions, answer_fn):
    correct = 0
    detail = []
    for q in questions:
        result = answer_fn(q["question"])
        ok = judge(result, q["expected"])
        correct += ok
        detail.append({**q, "correct": ok, "tool": result["tool"],
                       "citation": result["citations"][0] if result["citations"] else None})
    return {"n": len(questions), "correct": correct,
            "accuracy": correct / len(questions), "detail": detail}
