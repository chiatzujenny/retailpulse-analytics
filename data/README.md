# Case data and provenance

The included files are course-provided inputs for the USC MSBA pre-program
RetailPulse educational case. Their generation process and any connection to an
actual retailer have not been established; the project makes no such claim.

- sales_transactions.csv: 150 records from 01_Week 0 Raw Data.
- customers.csv: 60 records from 03_Week 5 External.
- source_manifest.json: SHA-256 fingerprints of original and included files,
  plus a description of the transformation.

The different customers.csv in the Week 0 folder has 120 records with IDs
1001–1120; none matches the transaction IDs C001–C060. It is not used, and no
invented ID mapping has been applied.

Customer names in the included master have been replaced with Customer C001, etc.
IDs, signup dates, cities, ages, loyalty points and all transaction values are
unchanged. Public charts use IDs. These label changes do not affect the analysis.

Missing discounts remain empty in the CSV. The loader fills them with zero and
retains a flag; comparisons show them as a separate missing-discount group.
Ratings remain missing. Source revenue is retained where formula checks flag
discrepancies.

The course guide, original team notebook, personal reflections and peer
evaluations are not included. Attribution is to the course exercise; this
repository does not grant an independent license to the course materials.
