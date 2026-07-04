# Reproduction Checklist

This file gives the concise release reproduction route for the archived release snapshot.

## Inputs

The numbered CSV tables in `tables/` and source-data bundles in `source_data/` are the authoritative reproducibility inputs. The repository does not redistribute third-party user-level YFull records, private sample identifiers, raw sequence files, usernames, email addresses, payment information or per-sample geographic annotations.

## Verification

From the repository root, run:

```bash
python scripts/reproduce_all.py --verify-only
python scripts/13_validate_repository_archive.py --skip-reproduction
```

Expected final status:

```text
Reproduction status: pass
Repository archive validation: pass
```

## Regeneration

To regenerate the numbered analysis outputs and figures before verification, run:

```bash
python scripts/reproduce_all.py
python scripts/13_validate_repository_archive.py --skip-reproduction
```

The figure renderers write PNG and PDF artifacts to `figures/`.

## Supplementary Tables

The numbered CSV files in `tables/` are the authoritative supplementary table sources in this repository.

## Interpretation Boundary

The pipeline reproduces source–receiver model checks for specified public-tree observations. It does not infer exact geographic origin, ethnic identity, population continuity, migration route, ancient-DNA confirmation or population-level probability.
