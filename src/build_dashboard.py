"""Create a static portfolio dashboard from the validated RetailPulse case data."""

from pathlib import Path
import calendar

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import PercentFormatter

from retail_analytics import load_data, compute_summary, build_tables


def main():
    root = Path(__file__).resolve().parents[1]
    tx, customers, audit = load_data(root / "data")
    tables, _ = build_tables(tx, customers)
    kpis = compute_summary(tx)
    cardinal, gold, gray = "#990000", "#FFCC00", "#555555"
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 10, "axes.spines.top": False, "axes.spines.right": False, "axes.titleweight": "bold", "axes.titlecolor": cardinal})
    fig = plt.figure(figsize=(14, 10), facecolor="white")
    fig.text(.07, .95, "RETAILPULSE", fontsize=24, weight="bold", color=cardinal)
    fig.text(.07, .916, "Retail Sales & Customer Analytics | 2023 observation window", fontsize=12, color=gray)
    fig.text(.93, .95, "USC MSBA\nEducational case study", ha="right", va="top", fontsize=10, color=gray)
    metrics = [
        ("RECORDED REVENUE (USD)", f"{kpis['revenue_after_discount']:,.2f}"),
        ("TRANSACTIONS", f"{kpis['transactions']}"),
        ("PURCHASING / REGISTERED", f"{kpis['purchasing_customers']} / {len(customers)}"),
        ("RETURN RATE", f"{kpis['return_rate']:.1%}"),
    ]
    for x, (label, value) in zip([.07, .30, .53, .76], metrics):
        fig.text(x, .866, label, fontsize=9, color=gray)
        fig.text(x, .832, value, fontsize=22, color=cardinal, weight="bold")
    grid = fig.add_gridspec(2, 2, left=.09, right=.94, top=.76, bottom=.13, hspace=.52, wspace=.30)
    ax_product = fig.add_subplot(grid[0, 0])
    product = tables["product_summary"].sort_values("revenue")
    bars = ax_product.barh(product["product"], product["revenue"] / 1000, color=cardinal)
    ax_product.bar_label(bars, fmt="%.1f", padding=4, fontsize=9)
    ax_product.set(title="Product contribution", xlabel="Recorded revenue (USD thousands)")
    ax_product.set_xlim(0, product["revenue"].max() / 1000 * 1.22)
    ax_product.xaxis.grid(True, alpha=.15)
    ax_product.set_axisbelow(True)

    ax_return = fig.add_subplot(grid[0, 1])
    region = tables["region_summary"].sort_values("return_rate", ascending=False)
    bars = ax_return.bar(region["region"], region["return_rate"], color=[cardinal, gold, gold, gold], edgecolor=cardinal, linewidth=.5)
    for bar, row in zip(bars, region.itertuples()):
        ax_return.annotate(f"{row.return_rate:.1%}\n({row.return_count}/{row.transaction_count})", (bar.get_x() + bar.get_width()/2, bar.get_height()), xytext=(0,5), textcoords="offset points", ha="center", fontsize=10, bbox={"facecolor": "white", "edgecolor": "none", "pad": 1})
    ax_return.axhline(kpis["return_rate"], color=gray, linestyle="--", linewidth=1, label=f"Overall {kpis['return_rate']:.1%}")
    ax_return.yaxis.set_major_formatter(PercentFormatter(1))
    ax_return.set(title="Regional returns", ylabel="Returned / transactions", ylim=(0, .28))
    ax_return.legend(frameon=False, loc="upper right", fontsize=9)

    ax_month = fig.add_subplot(grid[1, 0])
    monthly = tables["monthly_summary"]
    ax_month.plot(monthly["month"], monthly["revenue"] / 1000, color=cardinal, marker="o", linewidth=2)
    ax_month.set(title="Monthly recorded sales", ylabel="Revenue (USD thousands)", xticks=range(1,13), xticklabels=[calendar.month_abbr[i] for i in range(1,13)])
    ax_month.tick_params(axis="x", rotation=35)
    ax_month.yaxis.grid(True, alpha=.15)
    ax_month.set_axisbelow(True)

    ax_tier = fig.add_subplot(grid[1, 1])
    tiers = tables["customer_summary"].groupby("customer_tier").agg(revenue=("total_revenue", "sum"), customers=("customer_id", "count")).reindex(["Bronze", "Silver", "Gold", "Platinum"])
    bars = ax_tier.bar(tiers.index, tiers["revenue"] / 1000, color=[gold, gold, cardinal, cardinal], edgecolor=cardinal, linewidth=.5)
    for bar, row in zip(bars, tiers.itertuples()):
        ax_tier.annotate(f"{row.revenue/1000:.1f}\n{row.customers} customers", (bar.get_x()+bar.get_width()/2, bar.get_height()), xytext=(0,5), textcoords="offset points", ha="center", fontsize=9)
    ax_tier.set(title="Customer revenue tiers", ylabel="Recorded revenue (USD thousands)", ylim=(0, tiers["revenue"].max()/1000*1.35))

    fig.text(.07, .065, "Revenue is after discount; refund treatment and costs are unknown. Monthly patterns are descriptive.", fontsize=9, color=gray)
    fig.text(.07, .042, f"Data checks: {audit['missing_discounts_filled_with_zero']} missing discounts; {audit['missing_ratings_preserved']} missing ratings; {len(audit['revenue_formula_discrepancy_ids'])} formula exceptions retained and disclosed.", fontsize=9, color=gray)
    destination = root / "outputs" / "dashboard.png"
    destination.parent.mkdir(exist_ok=True)
    fig.savefig(destination, dpi=160, facecolor="white")
    plt.close(fig)
    print(f"Created {destination.name}")


if __name__ == "__main__":
    main()
