# Core YFull Source Bundle

This bundle contains the audited upstream YFull reliability inputs used by `scripts/01_generate_yfull_source_receiver_reliability_tables.py` to generate Tables 13 and 14.

`source_receiver_reliability_atlas.csv` is the broad ordered source-receiver atlas input. `source_receiver_highlight_contracts.csv` is the predeclared highlighted-contract input. The script converts these inputs into the table vocabulary, applies the fixed six-decimal rounding convention, and verifies exact agreement with the current clean repository tables.

`yfull_public_ytree_lineage_identity_crosswalk.csv` records public-tree branch-identity traceability against the YFullTeam/YTree GitHub snapshot. It is a lineage-label provenance file only; it does not contain raw YFull user-level records, private sample identifiers, raw genetic sequence files, or per-sample geographic annotations.

These files are upstream aggregate analysis inputs, not raw public-tree extraction files. They support reproducibility of the YFull atlas and highlighted-contract table layer only. They are not evidence of exact geographic origin, ethnic identity, population continuity, migration route, ancient-DNA confirmation, or population-level probability.
