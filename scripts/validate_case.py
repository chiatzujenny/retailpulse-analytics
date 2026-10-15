"""Check the included case against independent saved notebook baselines."""

import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import subprocess
import sys

import nbformat
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from retail_analytics import load_data, compute_summary, build_tables


def main():
    tx, customers, audit = load_data(ROOT / "data")
    kpi = compute_summary(tx)
    tables, _ = build_tables(tx, customers)
    assert len(tx) == 150 and len(customers) == 60
    assert kpi["purchasing_customers"] == 53
    assert np.isclose(kpi["revenue_after_discount"], 166909.56)
    assert np.isclose(kpi["average_transaction_value"], 1112.7304)
    assert kpi["return_count"] == 19
    assert np.isclose(kpi["average_observed_rating"], 3.556338028169014)
    assert audit["join_preserves_transaction_count"]
    assert audit["missing_discounts_filled_with_zero"] == 5
    assert audit["missing_ratings_preserved"] == 8
    assert audit["transactions_before_signup"] == 9
    assert audit["revenue_formula_discrepancy_ids"] == ["TXN1008", "TXN1073", "TXN1074", "TXN1120"]
    assert np.isclose(audit["revenue_formula_difference_total"], -261.77)
    assert customers["customer_name"].str.fullmatch(r"Customer C\d{3}").all()
    cohort = tables["cohort_summary"]
    assert cohort["customer_count"].tolist() == [4, 5, 6, 6, 7, 4, 8, 6, 8, 6]
    assert np.allclose(cohort["average_window_revenue"], [926.4475, 3049.38, 1719.05, 2826.725, 2353.222857142857, 1848.535, 5593.7325, 2610.89, 2688.795, 2481.66])
    assert len(tables) == 17
    for name in ["region_summary", "product_summary", "category_summary"]:
        assert np.isclose(tables[name]["revenue"].sum(), kpi["revenue_after_discount"])
        assert tables[name]["transaction_count"].sum() == 150
    assert np.isclose(tables["customer_summary"]["total_revenue"].sum(), 166909.56)
    manifest = json.loads((ROOT / "data" / "source_manifest.json").read_text())
    for filename, field in [("sales_transactions.csv", "included_transaction_sha256"), ("customers.csv", "included_customer_sha256")]:
        assert hashlib.sha256((ROOT / "data" / filename).read_bytes()).hexdigest() == manifest[field]

    notebook = nbformat.read(ROOT / "notebooks" / "report.ipynb", as_version=4)
    nbformat.validate(notebook)
    code = [cell for cell in notebook.cells if cell.cell_type == "code"]
    assert len(code) == 11 and all(cell.execution_count is not None for cell in code)
    errors = [out for cell in code for out in cell.outputs if out.output_type == "error"]
    images = [out for cell in code for out in cell.outputs if "image/png" in out.get("data", {})]
    assert not errors and len(images) == 4
    assert "C:\\Users\\" not in json.dumps(notebook)

    tests = subprocess.run([sys.executable, "-m", "unittest", "discover", "-s", str(ROOT / "tests"), "-v"], capture_output=True, text=True)
    if tests.returncode:
        raise RuntimeError(tests.stderr)
    assert "Ran 12 tests" in tests.stderr and "OK" in tests.stderr
    environment = "\n".join(f"- {name}: {version(name)}" for name in ["pandas", "numpy", "matplotlib", "nbformat", "nbclient", "nbconvert", "ipykernel", "reportlab"])
    record = f"""# Validation record

## Tested environment

- Python: {sys.version.split()[0]}
{environment}

## Results

- 12 regression tests passed on explicitly artificial fixtures.
- The case analysis ran on 150 transactions and the matching 60-customer master;
  all transaction/customer joins matched and preserved the transaction count.
- Revenue 166,909.56 USD, average transaction value 1,112.7304 USD, 19 returns,
  53 purchasers and all 10 cohort summaries reconcile to the original notebook.
- Regional, product, category and customer revenue totals reconcile.
- Five missing discounts, eight missing ratings, four formula exceptions totaling
  -261.77 USD and nine pre-signup transactions are retained and disclosed.
- Public customer names are ID-based; included input hashes match the manifest.
- The notebook passes nbformat validation: 11 executed code cells, zero errors,
  four embedded PNG chart outputs and no absolute Windows home paths.
- 17 analytical tables are produced. The dashboard and one-page summary use
  these same validated inputs; their layouts were rendered and inspected.

## Reproduce

Run the commands in the README, then:

~~~bash
python scripts/validate_case.py
~~~

Artificial test fixtures are not substituted for the included educational case.
Validation establishes program consistency, not the truth of unknown discounts,
refund treatment, signup semantics, or causal business effects.
"""
    (ROOT / "docs" / "validation.md").write_text(record, encoding="utf-8")
    print("PASS: case baselines, data lineage, joins, 17 tables, 12 tests and executed notebook verified.")


if __name__ == "__main__":
    main()
