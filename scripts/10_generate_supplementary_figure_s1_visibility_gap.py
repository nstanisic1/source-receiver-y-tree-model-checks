from __future__ import annotations

import argparse
import csv
import math
import random
import statistics
import sys
from collections import Counter
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "supplementary_figure_s1"
TABLES = REPO / "tables"

ROW_LEVEL_INPUT = SOURCE / "s1_05_row_level_elevation_source_data.csv"
UNIQUE_SITE_INPUT = SOURCE / "s1_06_unique_site_elevation_source_data.csv"
DIRECTNESS_INPUT = SOURCE / "s1_04_direct_negative_control_candidate_trace.csv"

DEFAULT_BAND_OUTPUT = SOURCE / "s1_07_elevation_band_summary.csv"
DEFAULT_EFFECT_OUTPUT = SOURCE / "s1_08_elevation_effect_size_tests.csv"
DEFAULT_EXACT_OUTPUT = SOURCE / "s1_09_elevation_threshold_exact_tests.csv"
DEFAULT_TABLE_OUTPUT = TABLES / "09_ancient_dna_visibility_gap_quantification.csv"

CLAIM_BOUNDARY = (
    "Elevation and visibility source row for Supplementary Figure S1 only; not evidence of PH908 "
    "presence, PH908 absence, geographic origin, ethnic identity, population continuity, or migration route."
)
TABLE_METHOD_NOTE = (
    "Unique sites/localities. Period-relevant ancient-DNA sites are dated 2500 BCE-550 CE. "
    "PH908 relic-footprint localities are the fixed 11-row Supplementary Figure S1 target "
    "layer derived from branch-map rows passing parent-or-anchor age >=1400 ybp; s1_19 "
    "documents the age-gated upstream layer, Y283553 exclusion, and plotted-layer reconciliation."
)
BAND_METHOD_NOTE = (
    "Unique sites/localities; period-relevant ancient-DNA sites are dated 2500 BCE-550 CE; "
    "PH908 relic-footprint localities use the predefined 11-row branch-derived relic-footprint "
    "layer retained after parent-or-anchor age >=1400 ybp and documented in s1_19."
)
SCOPE_NOTE = (
    "Period-relevant grey ancient-DNA layer uses 2500 BCE-550 CE; visible E-V13/J2b/R1b/G2a "
    "layer uses the same period window."
)

ROW_TO_UNIQUE_LAYER = {
    "Period-relevant ancient-DNA sample rows": "Period-relevant ancient-DNA sites",
    "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sample rows": (
        "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites"
    ),
    "Branch-derived PH908 relic-footprint locality rows": "Branch-derived PH908 relic-footprint localities",
}

ROW_LAYER_ORDER = [
    "Period-relevant ancient-DNA sample rows",
    "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sample rows",
    "Branch-derived PH908 relic-footprint locality rows",
]
UNIQUE_LAYER_ORDER = [
    "Period-relevant ancient-DNA sites",
    "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites",
    "Branch-derived PH908 relic-footprint localities",
]
TABLE_LAYER_ORDER = [
    "Period-relevant ancient-DNA sites",
    "Branch-derived PH908 relic-footprint localities",
    "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites",
]
BAND_ORDER = ["0-199 m", "200-499 m", "500-799 m", ">=800 m"]
THRESHOLDS = [500, 600, 800]

BAND_COLUMNS = [
    "evidence_layer",
    "elevation_band",
    "site_count",
    "total_sites",
    "site_share",
    "method_note",
    "claim_boundary",
]
EFFECT_COLUMNS = [
    "unit",
    "comparison",
    "n_ph908",
    "n_comparator",
    "median_ph908_m",
    "median_comparator_m",
    "mean_ph908_m",
    "mean_comparator_m",
    "median_difference_ph908_minus_comparator_m",
    "cliffs_delta",
    "permutation_p_two_sided_median_difference",
    "interpretation",
    "scope_note",
    "claim_boundary",
]
EXACT_COLUMNS = [
    "comparison",
    "threshold_m",
    "ph908_high_sites",
    "ph908_total_sites",
    "comparator_high_sites",
    "comparator_total_sites",
    "ph908_high_share",
    "comparator_high_share",
    "fisher_two_sided_p",
    "interpretation",
    "claim_boundary",
]
TABLE_COLUMNS = [
    "evidence_layer",
    "total_comparison_units",
    "units_at_or_above_500_m",
    "share_at_or_above_500_m",
    "units_at_or_above_800_m",
    "share_at_or_above_800_m",
    "method_or_limitation_note",
    "source_summary_file",
]


class ReproducibilityError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ReproducibilityError(f"Required input not found: {path.relative_to(REPO)}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decimal_fmt(value: float | Decimal | str, places: str) -> str:
    return str(Decimal(str(value)).quantize(Decimal(places), rounding=ROUND_HALF_UP))


def elevation(row: dict[str, str]) -> float:
    return float(row["elevation_m"])


def rows_for_layer(rows: list[dict[str, str]], layer: str) -> list[dict[str, str]]:
    return [row for row in rows if row["evidence_layer"] == layer]


def values_for_layer(rows: list[dict[str, str]], layer: str) -> list[float]:
    return [elevation(row) for row in rows_for_layer(rows, layer)]


def validate_source_rows(row_rows: list[dict[str, str]], unique_rows: list[dict[str, str]]) -> None:
    observed_row_layers = Counter(row["evidence_layer"] for row in row_rows)
    expected_row_layers = {
        "Period-relevant ancient-DNA sample rows": 475,
        "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sample rows": 146,
        "Branch-derived PH908 relic-footprint locality rows": 11,
    }
    if observed_row_layers != expected_row_layers:
        raise ReproducibilityError(f"Row-level S1 layer counts changed: {dict(observed_row_layers)}")

    observed_unique_layers = Counter(row["evidence_layer"] for row in unique_rows)
    expected_unique_layers = {
        "Period-relevant ancient-DNA sites": 100,
        "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites": 57,
        "Branch-derived PH908 relic-footprint localities": 11,
    }
    if observed_unique_layers != expected_unique_layers:
        raise ReproducibilityError(f"Unique-site S1 layer counts changed: {dict(observed_unique_layers)}")

    if any(row["sample_or_terminal"] == "Y283553" for row in row_rows + unique_rows):
        raise ReproducibilityError("Ambiguous Y283553 is present in the elevation source layer.")

    row_lookup = set()
    terminal_lookup = set()
    for row in row_rows:
        mapped_layer = ROW_TO_UNIQUE_LAYER[row["evidence_layer"]]
        row_lookup.add((mapped_layer, row["site_or_locality"], row["region"], row["elevation_m"], row["elevation_band"]))
        terminal_lookup.add((mapped_layer, row["sample_or_terminal"], row["region"], row["elevation_m"], row["elevation_band"]))

    for row in unique_rows:
        layer = row["evidence_layer"]
        if layer == "Branch-derived PH908 relic-footprint localities":
            key = (layer, row["sample_or_terminal"], row["region"], row["elevation_m"], row["elevation_band"])
            if key not in terminal_lookup:
                raise ReproducibilityError(f"PH908 unique-site row lacks row-level support: {row['sample_or_terminal']}")
            continue
        key = (layer, row["site_or_locality"], row["region"], row["elevation_m"], row["elevation_band"])
        if key not in row_lookup:
            raise ReproducibilityError(f"Unique ancient-DNA site row lacks row-level support: {row['site_or_locality']}")


def generate_band_summary(unique_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    counts = Counter((row["evidence_layer"], row["elevation_band"]) for row in unique_rows)
    totals = Counter(row["evidence_layer"] for row in unique_rows)
    for layer in UNIQUE_LAYER_ORDER:
        total = totals[layer]
        if total <= 0:
            raise ReproducibilityError(f"No unique-site rows for layer: {layer}")
        for band in BAND_ORDER:
            count = counts[(layer, band)]
            rows.append(
                {
                    "evidence_layer": layer,
                    "elevation_band": band,
                    "site_count": str(count),
                    "total_sites": str(total),
                    "site_share": decimal_fmt(Decimal(count) / Decimal(total), "0.0000"),
                    "method_note": BAND_METHOD_NOTE,
                    "claim_boundary": CLAIM_BOUNDARY,
                }
            )
    return rows


def cliffs_delta(left: list[float], right: list[float]) -> float:
    greater = 0
    lesser = 0
    for left_value in left:
        for right_value in right:
            if left_value > right_value:
                greater += 1
            elif left_value < right_value:
                lesser += 1
    return (greater - lesser) / (len(left) * len(right))


def permutation_p_median_difference(
    left: list[float], right: list[float], iterations: int = 20000, seed: int = 20260602
) -> tuple[float, float]:
    observed = statistics.median(left) - statistics.median(right)
    combined = list(left) + list(right)
    left_count = len(left)
    rng = random.Random(seed)
    more_extreme = 0
    for _ in range(iterations):
        rng.shuffle(combined)
        permuted_left = combined[:left_count]
        permuted_right = combined[left_count:]
        if abs(statistics.median(permuted_left) - statistics.median(permuted_right)) >= abs(observed):
            more_extreme += 1
    return observed, (more_extreme + 1) / (iterations + 1)


def effect_row(unit: str, ph908_values: list[float], comparator_values: list[float], comparator_label: str) -> dict[str, str]:
    difference, p_value = permutation_p_median_difference(ph908_values, comparator_values)
    return {
        "unit": unit,
        "comparison": f"Branch-derived PH908 relic-footprint localities vs {comparator_label}",
        "n_ph908": str(len(ph908_values)),
        "n_comparator": str(len(comparator_values)),
        "median_ph908_m": decimal_fmt(statistics.median(ph908_values), "0.0"),
        "median_comparator_m": decimal_fmt(statistics.median(comparator_values), "0.0"),
        "mean_ph908_m": decimal_fmt(statistics.mean(ph908_values), "0.0"),
        "mean_comparator_m": decimal_fmt(statistics.mean(comparator_values), "0.0"),
        "median_difference_ph908_minus_comparator_m": decimal_fmt(difference, "0.0"),
        "cliffs_delta": decimal_fmt(cliffs_delta(ph908_values, comparator_values), "0.000"),
        "permutation_p_two_sided_median_difference": decimal_fmt(p_value, "0.00000"),
        "interpretation": "Strong highland shift; mechanism support only, not lineage confirmation",
        "scope_note": SCOPE_NOTE,
        "claim_boundary": CLAIM_BOUNDARY,
    }


def generate_effect_size_tests(row_rows: list[dict[str, str]], unique_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    row_ph908 = values_for_layer(row_rows, "Branch-derived PH908 relic-footprint locality rows")
    site_ph908 = values_for_layer(unique_rows, "Branch-derived PH908 relic-footprint localities")
    return [
        effect_row(
            "Row-level observations",
            row_ph908,
            values_for_layer(row_rows, "Period-relevant ancient-DNA sample rows"),
            "period-relevant ancient-DNA sites",
        ),
        effect_row(
            "Row-level observations",
            row_ph908,
            values_for_layer(row_rows, "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sample rows"),
            "visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites",
        ),
        effect_row(
            "Unique sites/localities",
            site_ph908,
            values_for_layer(unique_rows, "Period-relevant ancient-DNA sites"),
            "period-relevant ancient-DNA sites",
        ),
        effect_row(
            "Unique sites/localities",
            site_ph908,
            values_for_layer(unique_rows, "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites"),
            "visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites",
        ),
    ]


def fisher_two_sided(a: int, b: int, c: int, d: int) -> float:
    total = a + b + c + d
    row_one = a + b
    row_two = c + d
    column_one = a + c

    def log_comb(n: int, k: int) -> float:
        return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)

    def probability(x: int) -> float:
        return math.exp(log_comb(row_one, x) + log_comb(row_two, column_one - x) - log_comb(total, column_one))

    lower = max(0, column_one - row_two)
    upper = min(row_one, column_one)
    observed = probability(a)
    return sum(probability(x) for x in range(lower, upper + 1) if probability(x) <= observed + 1e-15)


def exact_row(ph908_values: list[float], comparator_values: list[float], comparator_label: str, threshold: int) -> dict[str, str]:
    ph908_high = sum(value >= threshold for value in ph908_values)
    comparator_high = sum(value >= threshold for value in comparator_values)
    ph908_total = len(ph908_values)
    comparator_total = len(comparator_values)
    p_value = fisher_two_sided(
        ph908_high,
        ph908_total - ph908_high,
        comparator_high,
        comparator_total - comparator_high,
    )
    return {
        "comparison": f"Branch-derived PH908 relic-footprint localities vs {comparator_label}",
        "threshold_m": str(threshold),
        "ph908_high_sites": str(ph908_high),
        "ph908_total_sites": str(ph908_total),
        "comparator_high_sites": str(comparator_high),
        "comparator_total_sites": str(comparator_total),
        "ph908_high_share": decimal_fmt(Decimal(ph908_high) / Decimal(ph908_total), "0.0000"),
        "comparator_high_share": decimal_fmt(Decimal(comparator_high) / Decimal(comparator_total), "0.0000"),
        "fisher_two_sided_p": decimal_fmt(p_value, "0.000001"),
        "interpretation": "Mechanism support only; not lineage confirmation",
        "claim_boundary": CLAIM_BOUNDARY,
    }


def generate_exact_tests(unique_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    ph908_values = values_for_layer(unique_rows, "Branch-derived PH908 relic-footprint localities")
    comparisons = [
        (
            "period-relevant ancient-DNA sites",
            values_for_layer(unique_rows, "Period-relevant ancient-DNA sites"),
        ),
        (
            "visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites",
            values_for_layer(unique_rows, "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites"),
        ),
    ]
    rows = []
    for label, comparator_values in comparisons:
        for threshold in THRESHOLDS:
            rows.append(exact_row(ph908_values, comparator_values, label, threshold))
    return rows


def generate_visibility_gap_table(
    unique_rows: list[dict[str, str]], directness_rows: list[dict[str, str]]
) -> list[dict[str, str]]:
    rows = []
    for layer in TABLE_LAYER_ORDER:
        values = values_for_layer(unique_rows, layer)
        total = len(values)
        above_500 = sum(value >= 500 for value in values)
        above_800 = sum(value >= 800 for value in values)
        rows.append(
            {
                "evidence_layer": layer,
                "total_comparison_units": str(total),
                "units_at_or_above_500_m": str(above_500),
                "share_at_or_above_500_m": decimal_fmt(Decimal(above_500) / Decimal(total), "0.000000"),
                "units_at_or_above_800_m": str(above_800),
                "share_at_or_above_800_m": decimal_fmt(Decimal(above_800) / Decimal(total), "0.000000"),
                "method_or_limitation_note": TABLE_METHOD_NOTE,
                "source_summary_file": "source_data/supplementary_figure_s1/s1_07_elevation_band_summary.csv",
            }
        )

    if any(row["strict_direct_negative_control"] == "Yes" for row in directness_rows):
        raise ReproducibilityError(
            "Strict direct negative-control candidate elevations require explicit source rows before Table 9 can be regenerated."
        )
    total_candidates = len(directness_rows)
    rows.append(
        {
            "evidence_layer": "Strict direct negative-control candidates",
            "total_comparison_units": str(total_candidates),
            "units_at_or_above_500_m": "0",
            "share_at_or_above_500_m": "0.000000",
            "units_at_or_above_800_m": "0",
            "share_at_or_above_800_m": "0.000000",
            "method_or_limitation_note": (
                "Strict direct negative-control candidates among named nearest comparator regions; "
                "evaluated using the predefined directness criteria."
            ),
            "source_summary_file": "source_data/supplementary_figure_s1/s1_04_direct_negative_control_candidate_trace.csv",
        }
    )
    return rows


def compare(generated: list[dict[str, str]], existing_path: Path, columns: list[str], label: str) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(f"{label} row count mismatch: generated {len(generated)}; existing {len(existing)}")
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        differences = [field for field in columns if left.get(field) != right.get(field)]
        if differences:
            raise ReproducibilityError(f"{label} mismatch at row {index}: {', '.join(differences[:6])}")
    raise ReproducibilityError(f"{label} mismatch detected.")


def validate_outputs(
    bands: list[dict[str, str]],
    effects: list[dict[str, str]],
    exact: list[dict[str, str]],
    table_rows: list[dict[str, str]],
) -> None:
    if len(bands) != 12:
        raise ReproducibilityError(f"Elevation-band row count changed: {len(bands)}")
    if len(effects) != 4:
        raise ReproducibilityError(f"Elevation effect-size row count changed: {len(effects)}")
    if len(exact) != 6:
        raise ReproducibilityError(f"Elevation exact-test row count changed: {len(exact)}")
    if len(table_rows) != 4:
        raise ReproducibilityError(f"Table 9 row count changed: {len(table_rows)}")

    expected_table_counts = {
        "Period-relevant ancient-DNA sites": ("100", "8", "1"),
        "Branch-derived PH908 relic-footprint localities": ("11", "7", "4"),
        "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites": ("57", "5", "1"),
        "Strict direct negative-control candidates": ("4", "0", "0"),
    }
    for row in table_rows:
        expected = expected_table_counts[row["evidence_layer"]]
        observed = (
            row["total_comparison_units"],
            row["units_at_or_above_500_m"],
            row["units_at_or_above_800_m"],
        )
        if observed != expected:
            raise ReproducibilityError(f"Visibility-gap count drifted for {row['evidence_layer']}: {observed}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Supplementary Figure S1 elevation and visibility-gap quantification tables."
    )
    parser.add_argument("--row-level-input", type=Path, default=ROW_LEVEL_INPUT)
    parser.add_argument("--unique-site-input", type=Path, default=UNIQUE_SITE_INPUT)
    parser.add_argument("--directness-input", type=Path, default=DIRECTNESS_INPUT)
    parser.add_argument("--band-output", type=Path, default=DEFAULT_BAND_OUTPUT)
    parser.add_argument("--effect-output", type=Path, default=DEFAULT_EFFECT_OUTPUT)
    parser.add_argument("--exact-output", type=Path, default=DEFAULT_EXACT_OUTPUT)
    parser.add_argument("--table-output", type=Path, default=DEFAULT_TABLE_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated S1 elevation and visibility tables.")
    args = parser.parse_args()

    try:
        row_rows = read_csv(args.row_level_input)
        unique_rows = read_csv(args.unique_site_input)
        directness_rows = read_csv(args.directness_input)
        validate_source_rows(row_rows, unique_rows)

        bands = generate_band_summary(unique_rows)
        effects = generate_effect_size_tests(row_rows, unique_rows)
        exact = generate_exact_tests(unique_rows)
        table_rows = generate_visibility_gap_table(unique_rows, directness_rows)
        validate_outputs(bands, effects, exact, table_rows)

        if args.write:
            write_csv(args.band_output, BAND_COLUMNS, bands)
            write_csv(args.effect_output, EFFECT_COLUMNS, effects)
            write_csv(args.exact_output, EXACT_COLUMNS, exact)
            write_csv(args.table_output, TABLE_COLUMNS, table_rows)

        compare(bands, args.band_output, BAND_COLUMNS, "S1 elevation-band summary")
        compare(effects, args.effect_output, EFFECT_COLUMNS, "S1 elevation effect-size tests")
        compare(exact, args.exact_output, EXACT_COLUMNS, "S1 elevation threshold exact tests")
        compare(table_rows, args.table_output, TABLE_COLUMNS, "Table 9 visibility-gap quantification")

        print(f"S1 unique-site rows: {len(unique_rows)}")
        print(f"S1 elevation-band rows: {len(bands)}")
        print(f"S1 effect-size rows: {len(effects)}")
        print(f"S1 exact-test rows: {len(exact)}")
        print("Supplementary Figure S1 visibility-gap layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Supplementary Figure S1 visibility-gap layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
