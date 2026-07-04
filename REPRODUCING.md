# Reproducing the Analysis

This file describes the release reproduction path for the repository.

## Environment

Create an environment from `environment.yml` or install Python 3.10 or newer with Matplotlib available. The numbered table-generation scripts use the Python standard library; the figure renderers require Matplotlib.

## Full Verification

From the repository root:

```bash
python scripts/reproduce_all.py --verify-only
python scripts/13_validate_repository_archive.py --skip-reproduction
```

The first command verifies the analysis outputs, source-data manifests, file-level provenance tables, and hash consistency for reproduced figures. The second command verifies the repository file manifest and recorded hashes without rerunning the analysis verifier.

The expected final lines are:

```text
Reproduction status: pass
Repository archive validation: pass
```

## Regeneration

To regenerate the archived analysis tables and figures before verification:

```bash
python scripts/reproduce_all.py
```

The script executes the numbered analysis scripts and the figure renderers, then verifies source-data manifests and provenance hashes.

## Figure Renderers

Figures can also be rendered individually:

```bash
python scripts/make_figure_1.py
python scripts/make_figure_2.py
python scripts/make_figure_3.py
python scripts/make_figure_4.py
python scripts/make_supplementary_figure_s1.py
```

Each figure renderer validates its source-data manifest and value-validation checks before writing figure files.

## Supplementary Tables

The authoritative supplementary table sources are the numbered CSV files in `tables/`, with interpretation boundaries stated in the paired note files.

## Expected Boundaries

The reproduction pipeline tests the specified source–receiver model checks. It does not estimate exact geographic origin, ethnic identity, population continuity, migration route, ancient presence, or population-level probability.
