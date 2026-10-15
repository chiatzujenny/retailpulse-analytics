"""Run the RetailPulse analysis when the two original CSVs are available."""

import argparse
import json
from pathlib import Path

from retail_analytics import load_data, compute_summary, build_tables


def main():
    """Load validated inputs and export tables plus machine-readable diagnostics."""
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=root / "data")
    parser.add_argument("--output-dir", type=Path, default=root / "outputs")
    parser.add_argument("--as-of", default="2023-12-31")
    args = parser.parse_args()
    try:
        tx, customers, audit = load_data(args.data_dir)
        tables, payment = build_tables(tx, customers, args.as_of)
    except (ValueError, FileNotFoundError) as exc:
        parser.exit(2, f"Input error: {exc}\n")
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, table in tables.items():
        table.to_csv(args.output_dir / f"{name}.csv", index=False)
    report = {"data_audit": audit, "kpis": compute_summary(tx), "payment_diagnostics": payment}
    # JSON null represents an undefined KPI, such as ratings when all are missing.
    def sanitize(value):
        if isinstance(value, dict):
            return {k: sanitize(v) for k, v in value.items()}
        if isinstance(value, float) and not __import__("math").isfinite(value):
            return None
        return value
    (args.output_dir / "run_summary.json").write_text(json.dumps(sanitize(report), indent=2, allow_nan=False), encoding="utf-8")
    print(f"Exported {len(tables)} tables and run_summary.json to {args.output_dir}")


if __name__ == "__main__":
    main()
