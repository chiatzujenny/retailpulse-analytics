"""Small artificial fixtures exercise logic; these are not the RetailPulse dataset."""

import sys
import unittest
import json
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
import retail_analytics as ra


def fixture():
    """Return six artificial transactions and four customers for edge-case tests."""
    tx = pd.DataFrame({
        "transaction_id": ["T1", "T2", "T3", "T4", "T5", "T6"],
        "customer_id": ["C1", "C1", "C2", "C2", "C3", "C3"],
        "date": ["01/01/23", "02/01/23", "01/02/23", "02/02/23", "01/03/23", "02/03/23"],
        "region": ["East", "East", "West", "West", "East", "West"],
        "product": ["Mouse", "Mouse", "Laptop", "Laptop", "Mouse", "Laptop"],
        "category": ["Accessories", "Accessories", "Computers", "Computers", "Accessories", "Computers"],
        "quantity": [1] * 6, "unit_price": [100.] * 6,
        "discount_pct": [None, 0, 10, 20, 30, 0], "revenue": [100., 100., 90., 80., 70., 100.],
        "payment_method": ["Cash", "Card", "Cash", "Card", "Cash", "Card"],
        "returned": ["FALSE", "TRUE", "FALSE", "FALSE", "TRUE", "FALSE"],
        "customer_rating": [1, None, 5, 4, None, 2],
    })
    cust = pd.DataFrame({
        "customer_id": ["C1", "C2", "C3", "C4"], "customer_name": ["A", "B", "C", "D"],
        "city": ["City"] * 4, "signup_date": ["01/01/22"] * 4,
        "age": [30] * 4, "loyalty_points": [0] * 4,
    })
    return tx, cust


class AnalyticsTests(unittest.TestCase):
    def setUp(self):
        self.raw, self.customers = fixture()
        self.tx, self.cust, self.audit = ra.prepare_data(self.raw, self.customers)

    def test_booleans_missing_values_and_formula(self):
        self.assertFalse(self.tx.iloc[0]["returned"])
        self.assertEqual(self.tx["returned"].sum(), 2)
        self.assertEqual(self.audit["missing_discounts_filled_with_zero"], 1)
        self.assertEqual(self.tx["customer_rating"].isna().sum(), 2)
        self.assertEqual(self.audit["revenue_formula_discrepancy_ids"], [])
        self.assertTrue(pd.isna(self.raw.iloc[0]["discount_pct"]))

    def test_formula_discrepancy_reported(self):
        self.raw.loc[0, "revenue"] = 101
        _, _, audit = ra.prepare_data(self.raw, self.customers)
        self.assertEqual(audit["revenue_formula_discrepancy_ids"], ["T1"])

    def test_duplicate_and_unknown_customer_rejected(self):
        duplicate = pd.concat([self.customers, self.customers.iloc[[0]]])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            ra.prepare_data(self.raw, duplicate)
        self.raw.loc[0, "customer_id"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "absent"):
            ra.prepare_data(self.raw, self.customers)

    def test_date_and_return_values_rejected(self):
        self.raw.loc[0, "date"] = "31/02/23"
        with self.assertRaisesRegex(ValueError, "date"):
            ra.prepare_data(self.raw, self.customers)
        self.raw, _ = fixture()
        self.raw.loc[0, "returned"] = "possibly"
        with self.assertRaisesRegex(ValueError, "returned"):
            ra.prepare_data(self.raw, self.customers)

    def test_no_purchase_customer_is_not_lost(self):
        summary = ra.get_customer_summary(self.tx, self.cust)
        no_purchase = summary.set_index("customer_id").loc["C4"]
        self.assertEqual(len(summary), 4)
        self.assertEqual(no_purchase["transaction_count"], 0)
        self.assertTrue(pd.isna(no_purchase["return_rate"]))
        self.assertAlmostEqual(summary["total_revenue"].sum(), self.tx["revenue"].sum())
        rfm = ra.rfm_summary(summary).set_index("customer_id")
        self.assertTrue(pd.isna(rfm.loc["C4", "RFM_score"]))

    def test_observed_rating_denominator(self):
        table = ra.rating_summary(self.tx, "region").set_index("region")
        self.assertEqual(table.loc["East", "rated_transactions"], 1)
        self.assertEqual(table.loc["East", "missing_ratings"], 2)
        self.assertEqual(table.loc["East", "low_rating_rate_among_rated"], 1)

    def test_complete_month_grid_and_undefined_growth(self):
        monthly, category = ra.monthly_summary(self.tx)
        self.assertEqual(len(monthly), 12)
        self.assertEqual(len(category), 24)
        self.assertEqual(monthly.loc[monthly["month"].eq(12), "revenue"].iloc[0], 0)
        self.assertTrue(pd.isna(monthly.loc[monthly["month"].eq(5), "mom_revenue_change"].iloc[0]))
        self.assertAlmostEqual(monthly["revenue_index"].mean(), 1)

    def test_rfm_ties_are_invariant_to_row_order(self):
        summary = ra.get_customer_summary(self.tx, self.cust)
        a = ra.rfm_summary(summary).set_index("customer_id")
        b = ra.rfm_summary(summary.sample(frac=1, random_state=7)).set_index("customer_id")
        pd.testing.assert_series_equal(a["RFM_score"].sort_index(), b["RFM_score"].sort_index())
        self.assertEqual(a.loc["C1", "F_score"], a.loc["C2", "F_score"])

    def test_discount_bounds_and_tier_boundaries(self):
        table = ra.discount_summary(self.tx)
        self.assertEqual(table["transaction_count"].sum(), 6)
        self.assertIn("(20,100]%", table["discount_band"].astype(str).tolist())
        self.assertIn("Missing discount", table["discount_band"].astype(str).tolist())
        self.assertEqual([ra.assign_tier(x) for x in [1499, 1500, 4000, 8000, 8001]], ["Bronze", "Silver", "Gold", "Gold", "Platinum"])

    def test_top_n_validation(self):
        summary = ra.get_customer_summary(self.tx, self.cust)
        for value in [0, -1, 2.5, True]:
            with self.assertRaises(ValueError):
                ra.top_n_customers(summary, value)

    def test_all_tables_reconcile(self):
        tables, diagnostic = ra.build_tables(self.tx, self.cust)
        for name in ["region_summary", "product_summary", "category_summary"]:
            self.assertAlmostEqual(tables[name]["revenue"].sum(), 540.)
            self.assertEqual(tables[name]["transaction_count"].sum(), 6)
        self.assertEqual(tables["cohort_summary"]["customer_count"].sum(), 4)
        self.assertTrue(diagnostic["repeated_customers_present"])
        self.assertGreater(diagnostic["cells_with_expected_count_below_5"], 0)

    def test_csv_to_cli_export(self):
        # Exercise real file loading, argument handling, computation and exports.
        with tempfile.TemporaryDirectory(prefix="retailpulse-test-") as temp:
            directory = Path(temp)
            self.raw.to_csv(directory / "sales_transactions.csv", index=False)
            self.customers.to_csv(directory / "customers.csv", index=False)
            script = Path(__file__).resolve().parents[1] / "src" / "main.py"
            result = subprocess.run(
                [sys.executable, str(script), "--data-dir", str(directory), "--output-dir", str(directory / "results")],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((directory / "results" / "run_summary.json").read_text())
            self.assertEqual(summary["kpis"]["transactions"], 6)
            self.assertAlmostEqual(summary["kpis"]["revenue_after_discount"], 540.)
            self.assertEqual(len(list((directory / "results").glob("*.csv"))), 17)


if __name__ == "__main__":
    unittest.main()
