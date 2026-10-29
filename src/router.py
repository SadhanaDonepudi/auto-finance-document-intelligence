"""Agentic router with tool calling.

This is a hand-rolled router, NOT LangChain: LangChain was not needed
once the routing rules were explicit, and adding it would have added a
dependency without changing behaviour. The pattern is the same one
agentic frameworks use: the router classifies the question, selects one
tool, calls it with structured arguments, and returns the tool result
plus the routing decision for auditability.

Tools:
  - document_search: TF-IDF retrieval over the synthetic corpus.
  - sql_tool: deterministic, pattern-matched queries over the synthetic
    SQLite loan table. This is NOT free-form NL-to-SQL: the tool only
    executes a fixed set of aggregate/lookup templates (count, average
    APR, total balance, max payment, lookup by loan id / status / make).
    Anything outside those templates is routed to document search, so
    the SQL tool can never run an arbitrary query.
"""
import re
import sqlite3

SQL_PATTERNS = [
    # Specific patterns first: the generic "average apr ... loans"
    # pattern would otherwise swallow "average APR across all loans".
    (re.compile(r"average apr across all"), "avg_apr_all"),
    (re.compile(r"total remaining balance"), "total_balance"),
    (re.compile(r"highest monthly payment"), "max_payment"),
    (re.compile(r"loan (ln-\d+)"), "loan_by_id"),
    (re.compile(r"how many loans are (\w+)"), "count_status"),
    (re.compile(r"how many (\w+) loans"), "count_make"),
    (re.compile(r"average apr .*?(\w+) loans"), "avg_apr_status"),
    (re.compile(r"loans? (?:that are|with status) (\w+)"), "count_status"),
]


def route(question):
    """Return (tool_name, argument_dict)."""
    q = question.lower()
    for pattern, name in SQL_PATTERNS:
        m = pattern.search(q)
        if m:
            return "sql_tool", {"intent": name,
                                "arg": m.group(1) if m.groups() else None}
    return "document_search", {}


def sql_tool(db_path, intent, arg):
    con = sqlite3.connect(db_path)
    cur = con.cursor()
    try:
        if intent == "count_status":
            n = cur.execute("SELECT COUNT(*) FROM loans WHERE status=?",
                            (arg,)).fetchone()[0]
            return f"There are {n} loans with status '{arg}'."
        if intent == "count_make":
            n = cur.execute("SELECT COUNT(*) FROM loans WHERE vehicle_make=?",
                            (arg.capitalize(),)).fetchone()[0]
            return f"There are {n} {arg.capitalize()} loans."
        if intent == "avg_apr_status":
            v = cur.execute("SELECT AVG(apr) FROM loans WHERE status=?",
                            (arg,)).fetchone()[0]
            if v is None:  # arg may be a vehicle make, not a status
                v = cur.execute("SELECT AVG(apr) FROM loans WHERE vehicle_make=?",
                                (arg.capitalize(),)).fetchone()[0]
            if v is None:
                return f"No loans found for '{arg}'."
            return f"The average APR for {arg} loans is {v:.2f}%."
        if intent == "avg_apr_all":
            v = cur.execute("SELECT AVG(apr) FROM loans").fetchone()[0]
            return f"The average APR across all loans is {v:.2f}%."
        if intent == "total_balance":
            v = cur.execute("SELECT SUM(remaining_balance) FROM loans").fetchone()[0]
            return f"The total remaining balance across all loans is ${v:,.2f}."
        if intent == "max_payment":
            row = cur.execute("SELECT loan_id, monthly_payment FROM loans "
                              "ORDER BY monthly_payment DESC LIMIT 1").fetchone()
            return f"The highest monthly payment is ${row[1]:,.2f} (loan {row[0]})."
        if intent == "loan_by_id":
            row = cur.execute("SELECT * FROM loans WHERE loan_id=?",
                              (arg.upper(),)).fetchone()
            if not row:
                return f"No loan found with id {arg.upper()}."
            return (f"Loan {row[0]}: {row[3]} {row[1]} {row[2]}, principal "
                    f"${row[4]:,.2f}, APR {row[5]}%, {row[6]} months, "
                    f"payment ${row[7]:,.2f}, remaining ${row[8]:,.2f}, "
                    f"status {row[9]}.")
        return "SQL tool: intent not recognised."
    finally:
        con.close()


def answer_question(question, retriever, db_path, top_k=5, rerank=True):
    """Route, call the tool, and return a dict with answer + citations."""
    tool, args = route(question)
    if tool == "sql_tool":
        return {"tool": tool, "answer": sql_tool(db_path, args["intent"], args["arg"]),
                "citations": [{"source": "synthetic loan database (SQLite)",
                               "detail": f"{args['intent']} {args['arg'] or ''}".strip()}],
                "chunks": []}
    results = retriever.retrieve(question, top_k=top_k, rerank=rerank)
    if not results:
        return {"tool": tool, "answer": "No relevant document found.",
                "citations": [], "chunks": []}
    top = results[0]["chunk"]
    answer = (f"According to {top['doc_id']} (page {top['page']}): "
              f"{top['text'][:600]}")
    citations = [{"source": r["chunk"]["doc_id"], "page": r["chunk"]["page"],
                  "title": r["chunk"]["title"]} for r in results]
    return {"tool": tool, "answer": answer, "citations": citations,
            "chunks": [r["chunk"] for r in results]}
