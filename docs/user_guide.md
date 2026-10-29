# User Guide — Auto Finance Document Assistant

**Who this is for:** anyone who needs a plain-language answer from a pile
of auto finance paperwork, without reading every page.

## What it can answer
- Questions about retail installment contracts: APR, monthly payment,
  late fees, grace periods.
- Questions about lease agreements: residual value, mileage allowance,
  excess-mileage charges, early termination fees.
- General guidance questions (for example, the right to rescind).
- Questions about the loan portfolio: how many loans are current, the
  average APR, total remaining balance, a single loan's details.

## How to ask
1. Run `streamlit run app.py` and open the page it prints.
2. Type your question in plain English — include the vehicle (year,
   make, model) for contract or lease questions, e.g.
   "What is the late fee for the lease agreement on the 2023 Toyota Camry?"
3. Press **Ask**. The answer quotes the document it came from, and the
   citation underneath names the document and page number.
4. For loan questions, the citation names the loan database instead.

## How to check an answer
Every document answer shows its source document and page. If an answer
looks wrong, re-ask with more detail (vehicle, fee type) — retrieval
works best when the question names the thing being asked about.

## Important limits
- **All documents are synthetic.** Nothing here is a real contract, a
  real CFPB publication, or a real Regulation Z filing, and no answer
  here is legal advice.
- There is no AI language model behind the answers: they are extracted
  from the retrieved document text, or computed from the loan table.
- The SQL tool only answers a fixed set of portfolio questions (counts,
  averages, totals, lookups). Anything else goes to document search.
