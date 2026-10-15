# Validation record

## Tested environment

- Python: 3.12.14
- pandas: 3.0.1
- numpy: 2.3.5
- matplotlib: 3.11.2
- nbformat: 5.11.1
- nbclient: 0.11.0
- nbconvert: 7.17.2
- ipykernel: 7.4.0
- reportlab: 4.4.9

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
