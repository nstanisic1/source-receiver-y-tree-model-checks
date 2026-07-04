# Core Parser and Log-Base Quality-Control Source Bundle

This bundle contains the audited inputs used by `scripts/08_generate_parser_and_log_base_quality_controls.py`.

`parser_headline_sensitivity_metric_source.csv` records original and post-exclusion headline parser-sensitivity metrics. The generator recomputes source adequacy, diversity contrast, pass/fail decisions, deltas, and interpretation fields for Table 15.

`parser_failed_row_audit_source.csv` records the two public-display rows that failed manual topology or root-membership checks. The generator converts this source into the failed-row action table, Table 16.

`parser_logbase_rule_source.csv` records the source-adequacy, diversity-contrast, and log-base conventions used by the generator. The reported convention is `D = ln(q2_receiver/q2_source)`. The log10 field in Table 17 is a reference contrast only.

The log-base audit directly recomputes headline `D` from source and receiver q2 components. Adversarial sensitivity rows are context checks because q2 components are not present in the adversarial state source rows.

These files support calculation reproducibility and parser-quality transparency. They do not demonstrate exhaustive parser correctness and do not provide evidence of geographic origin, ethnic identity, population continuity, migration route, ancient-DNA confirmation, or population-level probability.
