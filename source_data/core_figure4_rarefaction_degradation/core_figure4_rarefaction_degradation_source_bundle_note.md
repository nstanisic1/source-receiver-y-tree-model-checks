# Core Figure 4 Rarefaction and Synthetic Degradation Source Bundle

This bundle contains the audited inputs used by `scripts/07_generate_figure4_rarefaction_and_degradation.py`.

`figure4_equal_n_rarefaction_metric_source.csv` records the scoreable and positive cell counts for the equal-n rarefaction sensitivity layer. The generator recomputes failed cells, positive fractions, adequacy-power states, interpretations, and the Figure 4 rarefaction trace.

`figure4_synthetic_visibility_fraction_design.csv` records the retained source-visibility fractions used for the synthetic degradation control. The generator combines these fractions with the matched R1a comparator rows in `tables/11_branch_unit_reliability_pass_matrix.csv` and the benchmark envelope values in `tables/26_benchmark_audit_card_matrix.csv` to recompute all synthetic degradation rows.

`figure4_rarefaction_degradation_rule_source.csv` records the source-adequacy, diversity-contrast, and country-visibility gates used by the generator. Rows that fall below the country-visibility gate are treated as no-calls.

The equal-n rarefaction layer is an adequacy and denominator sensitivity check. The synthetic degradation layer is a deterministic operating-characteristic stress test for matched R1a positive comparators under imposed source-terminal and source-country visibility loss. These files are not bias corrections, population-size estimates, geographic-origin claims, ethnic-identity claims, population-continuity claims, chronology claims, or migration-route claims.
