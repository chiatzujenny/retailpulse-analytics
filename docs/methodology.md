# Metric definitions and revision notes

## Data and provenance

This is a USC MSBA pre-program team educational case. The validated inputs contain
150 transactions, 60 registered customers and 53 purchasers. The transactions cover
2023-01-01 through 2023-12-29; the snapshot date is 2023-12-31.

The matching master is the Week 5 External customers.csv, not the incompatible
Week 0 customer file. All 150 transactions match without row expansion. The original
notebook's revenue, returns and signup-cohort summaries have been reproduced.
Customer names are replaced with ID-based labels in public inputs. The manifest
records source and included SHA-256 fingerprints; analytical fields are unchanged.

This is a retrospective, AI-assisted portfolio revision after the original
coursework. It is not represented as code entirely present in the class submission.

## Definitions

| Metric | Definition and scope |
|---|---|
| Revenue | Sum of supplied after-discount revenue; refund treatment unverified |
| Average transaction value | Mean revenue per unique transaction record |
| Return rate | Returned transaction records / all transaction records in the segment |
| Mean observed rating | Mean nonmissing rating, without imputation |
| Low-rating rate | Observed ratings below 3 / all observed ratings in the segment |
| Rating response rate | Rated transaction records / all transaction records |
| Customer revenue | Recorded revenue within the supplied 2023 observation window |
| Signup cohort | Calendar quarter of signup; comparison of window revenue and transactions |
| Recency | Days from last observed purchase to the stated snapshot |
| RFM score | Sum of three 1–5 heuristic scores using average percentile ranks |
| Monthly revenue index | Month revenue / mean revenue over the 12-month calendar grid |

Rate columns are fractions from 0 to 1, formatted as percentages in the notebook.
No-purchase customers remain in cohort denominators with zero revenue/counts and
undefined averages/return rates. Their RFM scores remain missing.

Equal R/F/M values receive equal component scores. Component bins need not have
equal customer counts. Recency is reversed so smaller values get higher scores;
frequency and monetary ranks rise with value. Scores are equally weighted. Ties
in the display order use revenue then customer ID; this does not alter scores.

## Missingness and formula exceptions

Five discounts are missing. Loading follows the course rule of filling with zero,
but retains discount_was_missing and separates those rows from confirmed 0%
transactions in comparisons.

Four missing-discount records fail the revenue formula by more than $0.01:
TXN1008, TXN1073, TXN1074 and TXN1120. Their aggregate supplied revenue is $261.77
below quantity × unit_price × (1 - imputed_discount / 100). Source revenue is not
overwritten. The discrepancy is not a measured loss, nor proof of an accounting
error; original discount information is needed.

Eight ratings remain missing. Low-rating proportions use observed responses,
with both rated and missing counts disclosed. The prior customer-mean imputation
was removed because it treats estimated values as actual feedback.

Nine transactions precede signup. Signup may mean loyalty enrollment rather than
first purchase, so these rows remain and are flagged. Cohort comparisons describe
2023 activity among signup groups, not post-signup retention or lifetime value.

## Other changes from the original notebook

- Parse both dates with the documented DD/MM/YY format and reject malformed values.
- Verify primary keys, join cardinality and unmatched IDs.
- Normalize TRUE/FALSE explicitly rather than relying on truthiness of strings.
- Reindex every category to all 12 months. Missing records are zero recorded
  activity, not proof that the business had no activity.
- Plot transaction counts and revenue as separate quantities; distinguish
  transaction share from revenue share and encode returns in scatter plots.
- Compare regional totals alongside transaction counts and average values.
- Preserve RFM ties rather than breaking them by input row order.

## Payment-method interpretation

The original table has nonreturned/returned counts: Cash 38/1, Credit Card 29/5,
Debit Card 32/1 and PayPal 32/12. Three of eight expected cell counts are below five:
approximately 4.94, 4.31 and 4.18. Repeated customer purchases also complicate the
independent-observation assumption. The original asymptotic chi-square p-value
around 0.00183 is not used as a standalone significance verdict.

See [SciPy's official test documentation](https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2_contingency.html).
The revision reports descriptive differences and diagnostics. An inferential
extension would need an appropriate sampling unit and a method addressing both
sparsity and customer dependence.

## Limits for business decisions

- Returns, low ratings and non-purchase do not establish churn.
- Costs and refund amounts are unavailable; profit and margin are not estimated.
- Product mix, prices and customer selection may explain discount-band differences.
  No causal discount effect is estimated.
- Small subgroup denominators accompany percentages.
- Signup cohorts are not retention curves or customer lifetime values.
- One sparse calendar year does not establish recurring seasonality.
- Recommendations are proposed investigations; no commercial intervention or
  realized business impact has been measured.
