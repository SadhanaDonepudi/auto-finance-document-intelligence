"""Synthetic corpus generation.

ALL documents are synthetic, generated from templates with a fixed seed.
They are NOT real CFPB or Regulation Z filings, NOT real contracts, and
contain no real borrower, lender, or vehicle-owner data. Names are
pseudonymous IDs (e.g. Borrower B-0142); vehicles are make/model/year
combinations drawn from a fixed list and assigned to synthetic contracts.

Layout: 320 documents
  - 120 retail installment contracts (RIC)
  - 100 lease agreements (LEASE)
  -  50 CFPB-style consumer guidance notes (GUIDE-CFPB)
  -  50 Regulation Z-style disclosure guidance notes (GUIDE-REGZ)

Each document is stored as a JSON record with a list of pages (strings),
so page-level citations are exact. A small sample is also rendered as
PDF (see pdf_sample.py) to exercise the PDF-parsing path.
"""
import json
import random
from pathlib import Path

MAKES_MODELS = [
    ("Toyota", "Camry"), ("Toyota", "RAV4"), ("Honda", "Civic"),
    ("Honda", "Accord"), ("Ford", "F-150"), ("Ford", "Escape"),
    ("Chevrolet", "Silverado"), ("Chevrolet", "Equinox"),
    ("Nissan", "Altima"), ("Nissan", "Sentra"), ("Hyundai", "Elantra"),
    ("Hyundai", "Tucson"), ("Kia", "Sportage"), ("Kia", "Forte"),
    ("Jeep", "Grand Cherokee"), ("Subaru", "Outback"),
]
YEARS = [2021, 2022, 2023, 2024]

# Guidance facts: (concept, canonical answer phrase, body sentence)
CFPB_GUIDANCE = [
    ("complaint process",
     "submit a complaint to the Consumer Financial Protection Bureau",
     "A consumer who believes a lender misled them about loan terms may "
     "submit a complaint to the Consumer Financial Protection Bureau, which "
     "forwards the complaint to the company for a response."),
    ("debt collection contact",
     "a debt collector may not contact you at an inconvenient time",
     "Under federal guidance, a debt collector may not contact you at an "
     "inconvenient time, such as before 8 a.m. or after 9 p.m., unless you agree."),
    ("credit report dispute",
     "dispute errors on your credit report in writing",
     "Consumers should dispute errors on your credit report in writing to the "
     "credit reporting company and keep copies of everything sent."),
    ("auto loan shopping",
     "compare offers from at least three lenders",
     "Guidance for shoppers: compare offers from at least three lenders and "
     "compare the annual percentage rate, not only the monthly payment."),
    ("add-on products",
     "add-on products are optional",
     "Dealer add-on products are optional. A lender may not require you to buy "
     "gap insurance or a service contract as a condition of the loan unless "
     "the product is required by the contract terms disclosed to you."),
]
REGZ_GUIDANCE = [
    ("right to rescind",
     "three business days",
     "For certain loans secured by a consumer's principal dwelling, the "
     "borrower has a right to rescind within three business days of signing, "
     "receiving the required disclosures, or receiving notice of the right, "
     "whichever occurs last."),
    ("annual percentage rate disclosure",
     "annual percentage rate must be disclosed",
     "The annual percentage rate must be disclosed prominently so a borrower "
     "can compare the cost of credit across lenders on a common basis."),
    ("finance charge definition",
     "finance charge is the dollar amount the credit will cost",
     "The finance charge is the dollar amount the credit will cost, including "
     "interest and certain other charges imposed by the creditor as a "
     "condition of the extension of credit."),
    ("periodic statement",
     "periodic statement for each billing cycle",
     "For open-end credit, the creditor must send a periodic statement for "
     "each billing cycle in which an account balance or transaction occurred."),
    ("tolerance for APR disclosure",
     "one-eighth of one percentage point",
     "The disclosed annual percentage rate is considered accurate if it is "
     "within one-eighth of one percentage point of the actual rate for "
     "regular transactions."),
]


def _ric_doc(rng, idx, vehicle):
    make, model, year, trim = vehicle
    apr = round(rng.uniform(3.9, 14.9), 2)
    term = rng.choice([36, 48, 60, 72])
    amount = rng.randint(12000, 45000)
    payment = round(amount * (1 + apr / 100 * term / 12) / term, 2)
    finance_charge = round(payment * term - amount, 2)
    late_fee = rng.choice([25, 30, 35, 40])
    grace = rng.choice([10, 15])
    total_payments = round(payment * term, 2)
    vehicle = f"{year} {make} {model} {trim}"  # unique per contract: see generate_corpus
    boiler = [
        "The buyer acknowledges receipt of a copy of this contract and of all "
        "disclosures required by applicable law before signing.",
        "All payments must be made by the due date shown on the payment schedule, "
        "and any payment received after that date may be treated as late.",
        "The seller may assign this contract, and the buyer will be notified of "
        "any assignment and of where future payments must be sent.",
    ]
    pages = [
        f"RETAIL INSTALLMENT CONTRACT {idx:03d} (SYNTHETIC - NOT A REAL CONTRACT). "
        f"Buyer Borrower B-{rng.randint(1000, 9999)} agrees to purchase a {vehicle} "
        f"from a synthetic dealer. Amount financed: ${amount:,}. "
        f"Annual percentage rate: {apr}%. Finance charge: ${finance_charge:,}. "
        f"Amount of payments: ${total_payments:,}. Total of payments: ${total_payments:,}. "
        + " ".join(boiler),
        f"PAYMENT SCHEDULE. The buyer will make {term} monthly payments of ${payment:,} each, "
        f"beginning one month after signing. The annual percentage rate of {apr}% applies to "
        f"the unpaid balance. If a payment is more than {grace} days late, a late fee of "
        f"${late_fee} applies. The grace period is {grace} days. Prepayment is permitted "
        f"without penalty under this synthetic contract. " + " ".join(boiler),
        f"DEFAULT AND REMEDIES. Failure to make a scheduled payment when due, or breach of "
        f"any other term, is an event of default. The seller may pursue remedies permitted "
        f"by applicable law, including repossession after required notice. The buyer must "
        f"maintain insurance on the {vehicle} for the full term of {term} months. "
        f"This document is synthetic and is used only to test document retrieval. "
        + " ".join(boiler),
    ]
    facts = {"apr": apr, "term": term, "payment": payment,
             "late_fee": late_fee, "grace": grace, "amount": amount,
             "vehicle": vehicle, "finance_charge": finance_charge}
    return {"doc_id": f"RIC-{idx:03d}", "kind": "retail_installment_contract",
            "title": f"Retail Installment Contract {idx:03d} - {vehicle}",
            "pages": pages, "facts": facts}


def _lease_doc(rng, idx, vehicle):
    make, model, year, trim = vehicle
    vehicle = f"{year} {make} {model} {trim}"
    term = rng.choice([24, 36, 39, 48])
    payment = round(rng.uniform(249, 649), 2)
    residual = rng.randint(12000, 30000)
    mileage = rng.choice([10000, 12000, 15000])
    excess = round(rng.uniform(0.15, 0.30), 2)
    early_fee = rng.randint(300, 900)
    pages = [
        f"VEHICLE LEASE AGREEMENT {idx:03d} (SYNTHETIC - NOT A REAL LEASE). "
        f"Lessee Borrower B-{rng.randint(1000, 9999)} leases a {vehicle}. "
        f"Lease term: {term} months. Monthly lease payment: ${payment:,}. "
        f"Residual value at lease end: ${residual:,}. "
        f"The lessee must keep the {vehicle} insured and serviced as specified.",
        f"MILEAGE AND WEAR. The annual mileage allowance is {mileage:,} miles. "
        f"Excess mileage is charged at ${excess} per mile. The lessee must return the "
        f"{vehicle} in reasonable condition, allowing for normal wear. "
        f"Early termination fee: ${early_fee}. Early termination before month {term} "
        f"requires payment of the early termination fee of ${early_fee}.",
        f"END OF LEASE OPTIONS. At lease end the lessee may return the vehicle, "
        f"or purchase it for the residual value of ${residual:,}. Purchase option price "
        f"equals the residual value stated above. This document is synthetic and is used "
        f"only to test document retrieval.",
    ]
    facts = {"term": term, "payment": payment, "residual": residual,
             "mileage": mileage, "excess": excess, "early_fee": early_fee,
             "vehicle": vehicle}
    return {"doc_id": f"LEASE-{idx:03d}", "kind": "lease_agreement",
            "title": f"Lease Agreement {idx:03d} - {vehicle}",
            "pages": pages, "facts": facts}


def _guide_doc(rng, idx, kind, concept, phrase, sentence):
    topic_variant = rng.choice([
        "This guidance note explains the topic in plain language for consumers.",
        "This guidance note summarises how the rule is normally applied.",
        "This guidance note answers a frequently asked question on the topic."])
    pages = [
        f"{'CFPB-STYLE' if kind == 'GUIDE-CFPB' else 'REGULATION Z-STYLE'} GUIDANCE NOTE "
        f"{idx:03d} (SYNTHETIC - NOT AN OFFICIAL PUBLICATION). Topic: {concept}. {topic_variant}",
        f"On {concept}: {sentence} This note is a synthetic paraphrase written "
        f"for retrieval testing; it is not a quotation from any official publication.",
    ]
    return {"doc_id": f"{kind}-{idx:03d}", "kind": kind,
            "title": f"Guidance Note {idx:03d} - {concept}",
            "pages": pages, "facts": {"concept": concept, "phrase": phrase}}


def generate_corpus(seed=42):
    rng = random.Random(seed)
    # 16 models x 4 years x 4 trims = 256 unique vehicles > 220 contracts,
    # so each contract/lease names a vehicle no other document shares.
    # Without this, a question naming only a vehicle would be ambiguous.
    trims = ["LE", "SE", "XLE", "Sport"]
    vehicles = [(m, mo, y, t) for m, mo in MAKES_MODELS
                for y in YEARS for t in trims]
    rng.shuffle(vehicles)
    docs = []
    for i in range(1, 121):
        docs.append(_ric_doc(rng, i, vehicles[i - 1]))
    for i in range(1, 101):
        docs.append(_lease_doc(rng, i, vehicles[120 + i - 1]))
    for i in range(1, 51):
        concept, phrase, sentence = CFPB_GUIDANCE[(i - 1) % len(CFPB_GUIDANCE)]
        docs.append(_guide_doc(rng, i, "GUIDE-CFPB", concept, phrase, sentence))
    for i in range(1, 51):
        concept, phrase, sentence = REGZ_GUIDANCE[(i - 1) % len(REGZ_GUIDANCE)]
        docs.append(_guide_doc(rng, i, "GUIDE-REGZ", concept, phrase, sentence))
    return docs


def main():
    out = Path(__file__).resolve().parent.parent / "data" / "corpus.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    docs = generate_corpus()
    out.write_text(json.dumps(docs, indent=1))
    print(f"documents: {len(docs)}")
    from collections import Counter
    print(Counter(d["kind"] for d in docs))


if __name__ == "__main__":
    main()
