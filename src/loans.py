"""Synthetic loan dataset (SQLite). All rows are generated with seed 42;
no real borrowers, accounts, or balances are involved."""
import random
import sqlite3
from pathlib import Path

MAKES = ["Toyota", "Honda", "Ford", "Chevrolet", "Nissan", "Hyundai", "Kia", "Jeep"]
STATUSES = ["current", "current", "current", "delinquent", "paid_off", "charged_off"]


def build_db(path, seed=42, n=500):
    rng = random.Random(seed)
    if path.exists():
        path.unlink()
    con = sqlite3.connect(path)
    con.execute("""CREATE TABLE loans (
        loan_id TEXT PRIMARY KEY, vehicle_make TEXT, vehicle_model TEXT,
        vehicle_year INTEGER, principal REAL, apr REAL, term_months INTEGER,
        monthly_payment REAL, remaining_balance REAL, status TEXT)""")
    models = {"Toyota": ["Camry", "RAV4"], "Honda": ["Civic", "Accord"],
              "Ford": ["F-150", "Escape"], "Chevrolet": ["Silverado", "Equinox"],
              "Nissan": ["Altima", "Sentra"], "Hyundai": ["Elantra", "Tucson"],
              "Kia": ["Sportage", "Forte"], "Jeep": ["Grand Cherokee", "Wrangler"]}
    rows = []
    for i in range(1, n + 1):
        make = rng.choice(MAKES)
        principal = rng.randint(10000, 45000)
        apr = round(rng.uniform(3.5, 15.0), 2)
        term = rng.choice([36, 48, 60, 72])
        payment = round(principal * (1 + apr / 100 * term / 12) / term, 2)
        status = rng.choice(STATUSES)
        remaining = 0.0 if status == "paid_off" else round(principal * rng.uniform(0.1, 0.95), 2)
        rows.append((f"LN-{i:04d}", make, rng.choice(models[make]),
                     rng.choice([2021, 2022, 2023, 2024]), principal, apr, term,
                     payment, remaining, status))
    con.executemany("INSERT INTO loans VALUES (?,?,?,?,?,?,?,?,?,?)", rows)
    con.commit()
    con.close()
    return n


if __name__ == "__main__":
    out = Path(__file__).resolve().parent.parent / "data" / "loans.db"
    print("loans:", build_db(out))
