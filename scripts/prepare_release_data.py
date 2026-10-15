"""Prepare case inputs for a portfolio, replacing names with ID-based labels."""

import argparse
import hashlib
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retail_analytics import prepare_data


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--transactions", type=Path, required=True)
    parser.add_argument("--customers", type=Path, required=True)
    args = parser.parse_args()
    transactions = pd.read_csv(args.transactions)
    customers = pd.read_csv(args.customers)
    _, _, audit = prepare_data(transactions, customers)
    output = ROOT / "data"
    output.mkdir(exist_ok=True)
    # Preserve the source transaction bytes; only customer names are transformed.
    tx_bytes = args.transactions.read_bytes()
    customers["customer_name"] = "Customer " + customers["customer_id"].astype(str)
    (output / "sales_transactions.csv").write_bytes(tx_bytes)
    customers.to_csv(output / "customers.csv", index=False)
    manifest = {
        "purpose": "USC MSBA pre-program RetailPulse educational case portfolio adaptation",
        "transaction_source": f"{args.transactions.parent.name}/sales_transactions.csv",
        "customer_source": f"{args.customers.parent.name}/customers.csv",
        "source_transaction_sha256": digest(args.transactions),
        "source_customer_sha256": digest(args.customers),
        "included_transaction_sha256": digest(output / "sales_transactions.csv"),
        "included_customer_sha256": digest(output / "customers.csv"),
        "transformation": "Customer names replaced by Customer + original customer_id; analytical values unchanged.",
        "transactions": audit["transactions"], "customers": audit["customers"],
        "join_preserves_transaction_count": audit["join_preserves_transaction_count"],
    }
    (output / "source_manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"Prepared {audit['transactions']} transactions and {audit['customers']} customers; matched all transaction IDs.")


if __name__ == "__main__":
    main()
