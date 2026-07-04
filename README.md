# Reliability-aware source–receiver model checks in public Y-chromosome phylogenies

This repository contains the source-data bundles, analysis scripts, tables, and figures for the manuscript "Reliability-aware source–receiver model checks in public Y-chromosome phylogenies."

The repository supports a defined model-checking target: whether specified public Y-chromosome tree observations are compatible with predefined source–receiver hypotheses under reliability-aware decision rules. The results are compatibility states for specified public-tree contrasts. They are not estimates of geographic origin, ethnic identity, population continuity, migration route, ancient presence, or population-level probability.

## Repository Contents

- `scripts/`: numbered analysis scripts, figure renderers, and archive validators.
- `source_data/`: audited source-data bundles used by the scripts and figures.
- `tables/`: reproducibility CSV tables and table notes.
- `figures/`: reproduced manuscript and supplementary figure artifacts.
- `REPRODUCIBILITY_SOURCE_MAP.md`: reproducibility map from reported figures, tables and numerical claims to the repository files that reproduce them.
- `release_manifest.csv`: file-level package manifest with hashes and interpretation boundaries.
- `manifest_sha256.csv`: repository-wide SHA-256 manifest for independent verification.
- `README_REPRODUCTION.md`: concise reproduction checklist for the release snapshot.
- `FULL_REPRODUCTION_LOG.txt`: latest full verification log.
- `VALIDATION_LOG.txt`: latest package-structure validation log.
- `DATA_USE.md`: data-use boundary for manuscript, figures, tables, source-data bundles, derived aggregate data and upstream resources.

## Reproduction Entry Point

Run the analysis verifier from the repository root:

```bash
python scripts/reproduce_all.py --verify-only
```

Then run the repository-structure validator:

```bash
python scripts/13_validate_repository_archive.py --skip-reproduction
```

To regenerate tables and figures before verification:

```bash
python scripts/reproduce_all.py
```

The expected final status is:

```text
Reproduction status: pass
Repository archive validation: pass
```

The standard verification run normally completes in under a few minutes on a current desktop system. The `figures/` directory contains both PNG and PDF artifacts.

## Data-Use Boundary

The code in `scripts/` is released under the MIT License. Repository documentation, figures, tables, source-data bundles and derived aggregate data are not relicensed by the MIT code license. They are provided for transparent manuscript reproduction and source-data verification under `DATA_USE.md`. This repository does not redistribute raw genetic sequence files, user-level public-tree records, private sample identifiers, kit numbers, usernames, email addresses, payment data, private locality annotations or restricted upstream genetic resources. The bundled Natural Earth country-boundary GeoJSON is included only for deterministic Supplementary Fig. 1 rendering and remains governed by Natural Earth's public-domain terms. Third-party public-tree, project-register and ancient-DNA resources remain governed by their source providers, cited publications and terms of use.

## Interpretation Boundary

All tables and figures should be read under the source–receiver model-checking framework described in the accompanying paper and supplementary information. Compatible states, rejection states, no-calls, and boundary states are framework-specific outputs, not direct claims about origin, identity, continuity, route, or ancient-DNA confirmation.
