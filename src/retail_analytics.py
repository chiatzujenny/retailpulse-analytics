"""RetailPulse portfolio revision of a USC pre-program team notebook.

All return/low-rating rates are fractions (0 to 1). Revenue is the supplied
after-discount transaction amount; it is not profit or verified net-of-refund
revenue. The source CSVs are required for actual case results.
"""

from pathlib import Path
import math

import numpy as np
import pandas as pd


TRANSACTION_COLUMNS = {
    "transaction_id", "customer_id", "date", "region", "product", "category",
    "quantity", "unit_price", "discount_pct", "revenue", "payment_method",
    "returned", "customer_rating",
}
CUSTOMER_COLUMNS = {
    "customer_id", "customer_name", "city", "signup_date", "age", "loyalty_points",
}


def _require_columns(frame, columns, name):
    """Raise an actionable error if required columns are absent."""
    missing = set(columns) - set(frame.columns)
    if missing:
        raise ValueError(f"{name}: missing columns: {', '.join(sorted(missing))}")


def _numeric(series, name, allow_missing=False):
    """Convert numbers without silently turning malformed values into NaN."""
    result = pd.to_numeric(series, errors="coerce")
    if (series.notna() & result.isna()).any():
        raise ValueError(f"{name}: contains nonnumeric values")
    if not allow_missing and result.isna().any():
        raise ValueError(f"{name}: missing values are not allowed")
    if not np.isfinite(result.dropna().to_numpy(dtype=float)).all():
        raise ValueError(f"{name}: infinite values are not allowed")
    return result


def _dates(series, name):
    """Parse the DD/MM/YY format documented in the course data dictionary."""
    if pd.api.types.is_datetime64_any_dtype(series):
        result = pd.to_datetime(series)
    else:
        result = pd.to_datetime(series, format="%d/%m/%y", errors="coerce")
    if result.isna().any():
        raise ValueError(f"{name}: missing/invalid date; expected DD/MM/YY")
    return result


def prepare_data(transactions, customers):
    """Validate and clean copies of the source tables, returning (tx, cust, audit).

    Missing discounts become zero, as specified by the course dictionary.
    Missing ratings remain missing. Duplicate IDs, unmatched customers, invalid
    values and malformed dates raise errors. Formula differences and unusual
    chronology are reported for investigation rather than silently overwritten.
    """
    _require_columns(transactions, TRANSACTION_COLUMNS, "transactions")
    _require_columns(customers, CUSTOMER_COLUMNS, "customers")
    tx, cust = transactions.copy(), customers.copy()
    if tx.empty or cust.empty:
        raise ValueError("Both input tables must contain at least one row")
    for frame, key, label in [
        (tx, "transaction_id", "transactions"),
        (cust, "customer_id", "customers"),
    ]:
        if frame[key].isna().any() or frame[key].astype(str).str.strip().eq("").any():
            raise ValueError(f"{label}: missing {key}")
        if frame[key].duplicated().any():
            raise ValueError(f"{label}: duplicate {key}; resolve before analysis")
    for name in ["customer_id", "region", "product", "category", "payment_method"]:
        if tx[name].isna().any() or tx[name].astype(str).str.strip().eq("").any():
            raise ValueError(f"transactions: missing {name}")
    for name in ["customer_id", "transaction_id", "region", "product", "category", "payment_method"]:
        tx[name] = tx[name].astype(str).str.strip()
    cust["customer_id"] = cust["customer_id"].astype(str).str.strip()
    if tx["transaction_id"].duplicated().any() or cust["customer_id"].duplicated().any():
        raise ValueError("Whitespace normalization produced duplicate IDs")
    for name in ["quantity", "unit_price", "revenue"]:
        tx[name] = _numeric(tx[name], name)
        if tx[name].lt(0).any():
            raise ValueError(f"{name}: negative values are not supported in this case")
    if tx["quantity"].le(0).any() or tx["quantity"].mod(1).ne(0).any():
        raise ValueError("quantity must contain positive integers")
    missing_discounts = int(tx["discount_pct"].isna().sum())
    tx["discount_was_missing"] = tx["discount_pct"].isna()
    tx["discount_pct"] = _numeric(tx["discount_pct"], "discount_pct", True).fillna(0)
    if not tx["discount_pct"].between(0, 100).all():
        raise ValueError("discount_pct must be between 0 and 100")
    tx["customer_rating"] = _numeric(tx["customer_rating"], "customer_rating", True)
    ratings = tx["customer_rating"].dropna()
    if not ratings.between(1, 5).all() or ratings.mod(1).ne(0).any():
        raise ValueError("Observed customer_rating must be an integer from 1 to 5")
    # astype(bool) would incorrectly convert the nonempty string 'FALSE' to True.
    returned = tx["returned"].astype(str).str.strip().str.lower()
    if not returned.isin(["true", "false"]).all():
        raise ValueError("returned must contain TRUE/FALSE or boolean values")
    tx["returned"] = returned.map({"true": True, "false": False}).astype(bool)
    tx["date"] = _dates(tx["date"], "date")
    cust["signup_date"] = _dates(cust["signup_date"], "signup_date")
    if not tx["customer_id"].isin(cust["customer_id"]).all():
        raise ValueError("Transactions reference customer IDs absent from customers.csv")
    joined = tx.merge(cust[["customer_id", "signup_date"]], on="customer_id", validate="many_to_one")
    expected = tx["quantity"] * tx["unit_price"] * (1 - tx["discount_pct"] / 100)
    discrepancy = (tx["revenue"] - expected).abs().gt(0.01 + 1e-9)
    tx["formula_revenue_with_imputed_discount"] = expected.round(2)
    tx["revenue_formula_difference"] = (tx["revenue"] - expected).round(2)
    tx["revenue_formula_mismatch"] = discrepancy
    audit = {
        "transactions": len(tx), "customers": len(cust),
        "missing_discounts_filled_with_zero": missing_discounts,
        "missing_ratings_preserved": int(tx["customer_rating"].isna().sum()),
        "revenue_formula_discrepancy_ids": tx.loc[discrepancy, "transaction_id"].tolist(),
        "revenue_formula_difference_total": round(float((tx["revenue"] - expected)[discrepancy].sum()), 2),
        "transactions_before_signup": int(joined["date"].lt(joined["signup_date"]).sum()),
        "transaction_date_min": tx["date"].min().date().isoformat(),
        "transaction_date_max": tx["date"].max().date().isoformat(),
        "join_preserves_transaction_count": len(joined) == len(tx),
    }
    return tx, cust, audit


def load_data(data_dir):
    """Read both original CSVs from a configurable local directory and validate."""
    data_dir = Path(data_dir)
    paths = [data_dir / "sales_transactions.csv", data_dir / "customers.csv"]
    for path in paths:
        if not path.is_file():
            raise FileNotFoundError(f"Required source CSV not found: {path}")
    return prepare_data(pd.read_csv(paths[0]), pd.read_csv(paths[1]))


def compute_summary(tx):
    """Return transaction-level KPIs; average ratings use observed responses only."""
    return {
        "transactions": int(len(tx)),
        "purchasing_customers": int(tx["customer_id"].nunique()),
        "revenue_after_discount": float(tx["revenue"].sum()),
        "average_transaction_value": float(tx["revenue"].mean()),
        "return_count": int(tx["returned"].sum()),
        "return_rate": float(tx["returned"].mean()),
        "average_observed_rating": float(tx["customer_rating"].mean()),
        "rating_response_rate": float(tx["customer_rating"].notna().mean()),
    }


def assign_tier(revenue):
    """Retain course thresholds: >8000 / >=4000 / >=1500 / lower."""
    if pd.isna(revenue) or not math.isfinite(float(revenue)) or float(revenue) < 0:
        raise ValueError("Tier revenue must be a finite nonnegative number")
    return "Platinum" if revenue > 8000 else "Gold" if revenue >= 4000 else "Silver" if revenue >= 1500 else "Bronze"


def get_customer_summary(tx, cust, as_of="2023-12-31"):
    """Build metrics for every registered customer, including those with no orders.

    No-order customers have zero revenue/count, but undefined averages/return
    rates. These are not filled with zero. as_of is a case snapshot, not today.
    """
    as_of = pd.Timestamp(as_of)
    if tx["date"].gt(as_of).any() or cust["signup_date"].gt(as_of).any():
        raise ValueError("as_of precedes a transaction or customer signup")
    metrics = tx.groupby("customer_id").agg(
        total_revenue=("revenue", "sum"), transaction_count=("transaction_id", "count"),
        average_transaction_value=("revenue", "mean"), return_count=("returned", "sum"),
        return_rate=("returned", "mean"), average_observed_rating=("customer_rating", "mean"),
        rated_transactions=("customer_rating", "count"), unique_products=("product", "nunique"),
        last_transaction_date=("date", "max"),
    ).reset_index()
    result = cust.merge(metrics, on="customer_id", how="left", validate="one_to_one")
    for column in ["total_revenue", "transaction_count", "return_count", "rated_transactions", "unique_products"]:
        result[column] = result[column].fillna(0)
    for column in ["transaction_count", "return_count", "rated_transactions", "unique_products"]:
        result[column] = result[column].astype(int)
    result["days_since_signup"] = (as_of - result["signup_date"]).dt.days
    result["recency_days"] = (as_of - result["last_transaction_date"]).dt.days
    result["signup_cohort"] = result["signup_date"].dt.to_period("Q").astype(str)
    result["customer_tier"] = result["total_revenue"].map(assign_tier)
    return result


def top_n_customers(summary, n=10):
    """Return up to n customers ordered by revenue, with stable ID tie-breaking."""
    if isinstance(n, bool) or not isinstance(n, int) or n <= 0:
        raise ValueError("n must be a positive integer")
    return summary.sort_values(["total_revenue", "customer_id"], ascending=[False, True]).head(n)


def segment_summary(tx, column):
    """Compare segment revenue, counts and returns; report denominators explicitly."""
    _require_columns(tx, [column, "revenue", "returned", "transaction_id"], "transactions")
    table = tx.groupby(column, observed=True, dropna=False).agg(
        revenue=("revenue", "sum"), transaction_count=("transaction_id", "count"),
        average_transaction_value=("revenue", "mean"), return_count=("returned", "sum"),
        return_rate=("returned", "mean"), rated_transactions=("customer_rating", "count"),
        average_observed_rating=("customer_rating", "mean"),
    ).reset_index()
    total = table["revenue"].sum()
    table["revenue_share"] = table["revenue"] / total if total else np.nan
    return table.sort_values(["revenue", column], ascending=[False, True]).reset_index(drop=True)


def cohort_summary(customers):
    """Compare signup cohorts within the observation window, not lifetime retention."""
    return customers.groupby("signup_cohort").agg(
        customer_count=("customer_id", "count"),
        average_window_revenue=("total_revenue", "mean"),
        average_window_transactions=("transaction_count", "mean"),
    ).reset_index()


def discount_summary(tx):
    """Describe discount bands; differences are associations, not causal effects."""
    data = tx.copy()
    data["discount_band"] = pd.cut(
        data["discount_pct"], bins=[-1e-9, 0, 10, 20, 100],
        labels=["0%", "(0,10]%", "(10,20]%", "(20,100]%"], include_lowest=True,
    ).astype("object")
    # Zero-imputation is retained for the course loading rule, but unknown
    # discounts are not represented as confirmed zero-discount transactions.
    data.loc[data["discount_was_missing"], "discount_band"] = "Missing discount"
    data["discount_band"] = pd.Categorical(data["discount_band"], categories=[
        "0%", "(0,10]%", "(10,20]%", "(20,100]%", "Missing discount",
    ], ordered=True)
    return data.groupby("discount_band", observed=True).agg(
        transaction_count=("transaction_id", "count"),
        average_transaction_value=("revenue", "mean"), average_quantity=("quantity", "mean"),
        return_count=("returned", "sum"), return_rate=("returned", "mean"),
        average_observed_rating=("customer_rating", "mean"), rated_transactions=("customer_rating", "count"),
    ).reset_index()


def rating_summary(tx, column):
    """Use only observed ratings in the low-rating denominator; preserve missingness."""
    data = tx.copy()
    data["low_rating"] = data["customer_rating"].lt(3) & data["customer_rating"].notna()
    table = data.groupby(column, observed=True).agg(
        transaction_count=("transaction_id", "count"), rated_transactions=("customer_rating", "count"),
        low_rating_count=("low_rating", "sum"), average_observed_rating=("customer_rating", "mean"),
    ).reset_index()
    table["missing_ratings"] = table["transaction_count"] - table["rated_transactions"]
    table["low_rating_rate_among_rated"] = table["low_rating_count"] / table["rated_transactions"].replace(0, np.nan)
    return table


def monthly_summary(tx, year=2023):
    """Report all 12 calendar months, including zero-record months, for a stated year.

    The index describes the supplied observation window. One year does not
    establish recurring seasonality. Missing calendar-month records are treated
    as zero recorded activity, not verified zero business activity.
    """
    if not tx["date"].dt.year.eq(year).all():
        raise ValueError("Monthly comparison requires one explicit calendar year")
    data = tx.assign(month=tx["date"].dt.month)
    table = data.groupby("month").agg(
        revenue=("revenue", "sum"), transaction_count=("transaction_id", "count"),
    ).reindex(range(1, 13), fill_value=0).rename_axis("month").reset_index()
    table["average_transaction_value"] = table["revenue"] / table["transaction_count"].replace(0, np.nan)
    table["revenue_change"] = table["revenue"].diff()
    table["mom_revenue_change"] = table["revenue"].diff() / table["revenue"].shift().replace(0, np.nan)
    mean = table["revenue"].mean()
    table["revenue_index"] = table["revenue"] / mean if mean else np.nan
    categories = pd.MultiIndex.from_product([sorted(data["category"].unique()), range(1, 13)], names=["category", "month"])
    category = data.groupby(["category", "month"])["revenue"].sum().reindex(categories, fill_value=0).reset_index()
    means = category.groupby("category")["revenue"].transform("mean").replace(0, np.nan)
    category["revenue_index"] = category["revenue"] / means
    return table, category


def rfm_summary(customers):
    """Score R/F/M with average percentile ranks; identical values get equal scores.

    Equal weighting is a transparent heuristic, not a validated predictive model.
    No-purchase customers retain missing scores and an explicit status.
    """
    columns = ["customer_id", "recency_days", "transaction_count", "total_revenue"]
    table = customers[columns].copy()
    table["purchase_status"] = np.where(table["transaction_count"].gt(0), "Observed purchaser", "No observed purchases")
    active = table["transaction_count"].gt(0)
    for column, score, ascending in [
        ("recency_days", "R_score", False),
        ("transaction_count", "F_score", True),
        ("total_revenue", "M_score", True),
    ]:
        percentile = table.loc[active, column].rank(method="average", pct=True, ascending=ascending)
        table[score] = pd.Series(pd.NA, index=table.index, dtype="Int64")
        table.loc[active, score] = np.ceil(percentile * 5).clip(1, 5).astype("int64")
    table["RFM_score"] = table[["R_score", "F_score", "M_score"]].sum(axis=1, min_count=3).astype("Int64")
    return table.sort_values(["RFM_score", "total_revenue", "customer_id"], ascending=[False, False, True], na_position="last")


def payment_return_diagnostics(tx):
    """Describe returns and diagnose chi-square assumptions without claiming causality.

    No significance verdict is produced. Sparse expected counts and repeated
    customers require further study design before using an independence test.
    """
    table = pd.crosstab(tx["payment_method"], tx["returned"]).reindex(columns=[False, True], fill_value=0)
    expected = np.outer(table.sum(axis=1), table.sum(axis=0)) / table.to_numpy().sum()
    expected_table = pd.DataFrame(expected, index=table.index, columns=["expected_not_returned", "expected_returned"])
    diagnostics = {
        "cells_with_expected_count_below_5": int((expected < 5).sum()),
        "total_cells": int(expected.size),
        "repeated_customers_present": bool(tx["customer_id"].duplicated().any()),
        "interpretation": "Descriptive association only; no causal or independent-sample significance claim.",
    }
    return segment_summary(tx, "payment_method"), expected_table, diagnostics


def build_tables(tx, cust, as_of="2023-12-31"):
    """Assemble portfolio tables from validated data without modifying inputs."""
    customers = get_customer_summary(tx, cust, as_of)
    monthly, category_monthly = monthly_summary(tx, pd.Timestamp(as_of).year)
    merged = tx.merge(customers[["customer_id", "customer_tier"]], on="customer_id", how="left", validate="many_to_one")
    pivot = pd.pivot_table(tx, index="category", columns="region", values="revenue", aggfunc="sum", fill_value=0, margins=True, margins_name="Total")
    payment, expected, diagnostics = payment_return_diagnostics(tx)
    tables = {
        "customer_summary": customers,
        "top_10_customers": top_n_customers(customers),
        "region_summary": segment_summary(tx, "region"),
        "product_summary": segment_summary(tx, "product"),
        "category_summary": segment_summary(tx, "category"),
        "category_region_pivot": pivot.reset_index(),
        "cohort_summary": cohort_summary(customers),
        "discount_summary": discount_summary(tx),
        "ratings_by_region": rating_summary(tx, "region"),
        "ratings_by_product": rating_summary(tx, "product"),
        "ratings_by_customer_tier": rating_summary(merged, "customer_tier"),
        "monthly_summary": monthly,
        "category_monthly_summary": category_monthly,
        "rfm_scores": rfm_summary(customers),
        "payment_return_summary": payment,
        "payment_expected_counts": expected.reset_index(),
        "revenue_formula_checks": tx.loc[tx["revenue_formula_mismatch"], [
            "transaction_id", "quantity", "unit_price", "discount_pct",
            "discount_was_missing", "revenue", "formula_revenue_with_imputed_discount",
            "revenue_formula_difference",
        ]].copy(),
    }
    return tables, diagnostics
