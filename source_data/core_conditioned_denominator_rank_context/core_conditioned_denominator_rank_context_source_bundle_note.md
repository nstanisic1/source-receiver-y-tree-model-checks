# Core Conditioned-Denominator Rank Context Source Bundle

This bundle contains the audited inputs used by `scripts/09_generate_conditioned_denominator_rank_context.py`.

`conditioned_denominator_metric_source.csv` records the predefined conditioned denominators, denominator root counts, denominator family counts, and PH908 rank within each denominator.

`conditioned_denominator_rank_rule_source.csv` records the formulas used to compute rank percentile and empirical rank p-value. Percentile is computed only within the specified denominator, with rank 1 represented as 100%. The empirical rank p-value is defined as PH908 rank within the denominator divided by the denominator root count.

These rows provide conditioned rank context for the held-out target application. They are not atlas-wide rarity tests, population-frequency estimates, global significance claims, geographic-origin claims, ethnic-identity claims, population-continuity claims, or migration-route claims.
