# Core YFull Public-Tree Provenance and Data-Use Note

This note defines the reproducibility and data-use boundary for the YFull-derived source-receiver audit inputs in this repository.

## Reproducible analysis layer

The repository provides the aggregate source-data tables required to regenerate the YFull atlas, highlighted contracts, source-layer coordinates, figures, tables, manifests, and file-level provenance checks. These aggregate files contain branch labels, source and receiver masks, terminal-count summaries, country-count summaries, branch-count summaries, q2-derived diversity contrasts, source-adequacy values, reliability states, and claim-boundary fields.

The repository does not redistribute raw genetic sequence files, YFull user-level records, private sample identifiers, usernames, email addresses, payment information, or per-sample geographic annotations.

## Public branch-identity provenance

Lineage labels used in the repository source-data and table layer were cross-checked against the public YFullTeam/YTree GitHub snapshot `current_tree.json`, version `14.02.0`, SHA-256 `e46e840025fb60314c918bb4bf35eb31fdac8a885f2d71dde81d162417dd9df3`. The public YFullTeam/YTree GitHub snapshot is distributed under CC-BY-4.0.

The branch-identity check is recorded in `yfull_public_ytree_lineage_identity_crosswalk.csv`. In the core YFull atlas, all 84 unique lineage roots and all seven highlighted roots matched public YTree node identifiers in the tested snapshot. Across the wider repository CSV layer, lineage-style labels matched public YTree node identifiers or SNP aliases, with one nomenclature variant, `I2a-PH908`, mapped to the canonical public YTree node label `I-PH908`.

This crosswalk supports public-tree branch-identity traceability. It does not convert the derived source/receiver masks, terminal counts, diversity contrasts, or geographic annotations into raw YFull redistributions.

Country labels in the aggregate public-tree layer are treated as visibility labels rather than unbiased birthplaces or ancient locations. They may reflect self-reported earliest-known paternal ancestry, project conventions, diaspora reporting, country-level aggregation, and platform-specific disclosure rules. Cross-platform comparisons are interpreted as triangulation of direction and scoreability, not as independent population-frequency replication.

## Ethical and publication boundary

The manuscript analyses are reproduced from derived aggregate source-receiver tables. The public-tree branch labels are externally traceable, but the repository does not expose user-level YFull records or private identifiers. This preserves reproducibility of the published figures and numerical claims while avoiding redistribution of third-party user-level data.

These files support model checking under predefined source-receiver criteria. They should not be interpreted as evidence of exact geographic origin, ethnic identity, population continuity, migration route, ancient-DNA confirmation, or population-level probability.
