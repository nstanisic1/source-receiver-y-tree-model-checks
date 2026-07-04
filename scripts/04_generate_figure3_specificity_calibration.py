from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_figure3_specificity_calibration"

DEFAULT_MARGIN_INPUT = SOURCE / "figure3_margin_permutation_metric_source.csv"
DEFAULT_CALIBRATION_INPUT = SOURCE / "figure3_threshold_calibration_source.csv"
DEFAULT_METADATA_INPUT = SOURCE / "figure3_specificity_calibration_row_metadata.csv"
DEFAULT_TABLE_OUTPUT = REPO / "tables" / "05_matched_r1a_comparator_calibration_summary.csv"
DEFAULT_TRACE_OUTPUT = REPO / "source_data" / "figure_3" / "fig3_04_specificity_and_calibration_trace.csv"

TABLE_COLUMNS = [
    "section",
    "comparison_or_calibration",
    "observed_result",
    "interpretation",
    "limitation",
    "source_trace_file",
]

TRACE_COLUMNS = [
    "display_order",
    "section",
    "comparison_or_calibration",
    "observed_result",
    "interpretation",
    "limitation",
    "source_trace_file",
    "source_summary_file",
    "claim_boundary",
]


class ReproducibilityError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ReproducibilityError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]], quote_all: bool) -> None:
    quoting = csv.QUOTE_ALL if quote_all else csv.QUOTE_MINIMAL
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=quoting, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decimal_6(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def decimal_rate(numerator: str, denominator: str) -> Decimal:
    return Decimal(numerator) / Decimal(denominator)


def close_enough(left: Decimal, right: Decimal, tolerance: Decimal = Decimal("1e-15")) -> bool:
    return abs(left - right) <= tolerance


def metric_values(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    return {row["metric"]: Decimal(row["observed_value"]) for row in rows}


def calibration_values(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["calibration"]: row for row in rows}


def require_metric(metrics: dict[str, Decimal], key: str) -> Decimal:
    if key not in metrics:
        raise ReproducibilityError(f"Missing metric source value: {key}")
    return metrics[key]


def require_calibration(calibrations: dict[str, dict[str, str]], key: str) -> dict[str, str]:
    if key not in calibrations:
        raise ReproducibilityError(f"Missing calibration source row: {key}")
    return calibrations[key]


def validate_sources(metrics: dict[str, Decimal], calibrations: dict[str, dict[str, str]]) -> None:
    auroc = require_metric(metrics, "PH908_vs_negative_control_margin_AUROC")
    if auroc < 0 or auroc > 1:
        raise ReproducibilityError("AUROC must fall within [0, 1].")

    matched_blocks = require_metric(metrics, "matched_block_pair_count")
    if matched_blocks != Decimal("136"):
        raise ReproducibilityError("Matched block pair count must equal 136 for the audited Figure 3 grid.")

    linear_threshold = require_metric(metrics, "negative_control_T95_margin_threshold_linear_quantile")
    empirical_threshold = require_metric(metrics, "negative_control_T95_margin_threshold_empirical_nearest_rank")

    for key, row in calibrations.items():
        negative_rate = decimal_rate(row["negative_control_flagged_count"], row["negative_control_row_count"])
        ph908_rate = decimal_rate(row["PH908_pass_count"], row["PH908_row_count"])
        if not close_enough(negative_rate, Decimal(row["empirical_negative_control_flag_rate"])):
            raise ReproducibilityError(f"Negative-control rate mismatch for {key}.")
        if not close_enough(ph908_rate, Decimal(row["empirical_PH908_pass_rate"])):
            raise ReproducibilityError(f"PH908 recovery rate mismatch for {key}.")

    linear = require_calibration(calibrations, "specificity_calibrated_T95_linear_quantile_threshold")
    empirical = require_calibration(calibrations, "specificity_calibrated_T95_empirical_nearest_rank_threshold")
    if Decimal(linear["margin_threshold"]) != linear_threshold:
        raise ReproducibilityError("Linear T95 threshold mismatch between metric and calibration sources.")
    if Decimal(empirical["margin_threshold"]) != empirical_threshold:
        raise ReproducibilityError("Empirical nearest-rank T95 threshold mismatch between metric and calibration sources.")
    if Decimal(empirical["empirical_negative_control_flag_rate"]) >= Decimal("0.05"):
        raise ReproducibilityError("Preferred empirical T95 negative-control flag rate must be below 0.05.")
    if empirical["PH908_pass_count"] != empirical["PH908_row_count"]:
        raise ReproducibilityError("Preferred empirical T95 row must preserve all PH908 rows.")


def threshold_text(row: dict[str, str]) -> str:
    return (
        f"Negative-control flagged count = {row['negative_control_flagged_count']}/{row['negative_control_row_count']}; "
        f"empirical negative-control flag rate = {decimal_6(row['empirical_negative_control_flag_rate'])}; "
        f"PH908 pass count = {row['PH908_pass_count']}/{row['PH908_row_count']}; "
        f"empirical PH908 pass rate = {decimal_6(row['empirical_PH908_pass_rate'])}; "
        f"margin threshold = {decimal_6(row['margin_threshold'])}"
    )


def observed_result(
    metadata: dict[str, str],
    metrics: dict[str, Decimal],
    calibrations: dict[str, dict[str, str]],
) -> str:
    kind = metadata["row_kind"]
    key = metadata["metric_or_calibration_key"]

    if kind == "margin_minimum_gap":
        ph908 = require_metric(metrics, "minimum_PH908_margin")
        control = require_metric(metrics, "maximum_negative_control_margin")
        gap = ph908 - control
        return (
            f"Minimum PH908 margin = {decimal_6(ph908)}; "
            f"maximum negative-control margin = {decimal_6(control)}; "
            f"minimum observed separation gap = {decimal_6(gap)}"
        )
    if kind == "margin_median_gap":
        ph908 = require_metric(metrics, "median_PH908_margin")
        control = require_metric(metrics, "median_negative_control_margin")
        gap = ph908 - control
        return (
            f"Median PH908 margin = {decimal_6(ph908)}; "
            f"median negative-control margin = {decimal_6(control)}; "
            f"median separation gap = {decimal_6(gap)}"
        )
    if kind == "margin_auroc":
        return f"PH908-versus-negative-control margin AUROC = {decimal_6(require_metric(metrics, 'PH908_vs_negative_control_margin_AUROC'))}"
    if kind == "matched_block_permutation":
        return (
            f"Matched block pair count = {int(require_metric(metrics, 'matched_block_pair_count'))}; "
            f"mean paired block margin difference = {decimal_6(require_metric(metrics, 'mean_paired_block_margin_difference'))}; "
            f"block permutation p-value = {decimal_6(require_metric(metrics, 'block_permutation_p_value'))}"
        )
    if kind == "threshold_calibration":
        return threshold_text(require_calibration(calibrations, key))
    if kind == "preferred_threshold_calibration":
        row = require_calibration(calibrations, key)
        return (
            f"Negative-control flagging = {row['negative_control_flagged_count']}/{row['negative_control_row_count']}; "
            f"PH908 recovery = {row['PH908_pass_count']}/{row['PH908_row_count']}; "
            f"threshold margin = {decimal_6(row['margin_threshold'])}"
        )
    raise ReproducibilityError(f"Unrecognized row kind: {kind}")


def generate_table_rows(
    metadata_rows: list[dict[str, str]],
    metrics: dict[str, Decimal],
    calibrations: dict[str, dict[str, str]],
) -> list[dict[str, str]]:
    rows = []
    for row in sorted(metadata_rows, key=lambda item: int(item["display_order"])):
        rows.append(
            {
                "section": row["section"],
                "comparison_or_calibration": row["comparison_or_calibration"],
                "observed_result": observed_result(row, metrics, calibrations),
                "interpretation": row["interpretation"],
                "limitation": row["limitation"],
                "source_trace_file": row["source_trace_file"],
            }
        )
    return rows


def generate_trace_rows(table_rows: list[dict[str, str]], metadata_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    metadata_by_order = {
        int(row["display_order"]): row for row in sorted(metadata_rows, key=lambda item: int(item["display_order"]))
    }
    rows = []
    for index, table_row in enumerate(table_rows, start=1):
        metadata = metadata_by_order[index]
        output = {
            "display_order": str(index),
            **table_row,
            "source_summary_file": "tables/05_matched_r1a_comparator_calibration_summary.csv",
            "claim_boundary": metadata["claim_boundary"],
        }
        rows.append(output)
    return rows


def compare(label: str, generated: list[dict[str, str]], existing_path: Path) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"{label} row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        if left != right:
            fields = sorted(set(left) | set(right))
            differences = [field for field in fields if left.get(field) != right.get(field)]
            raise ReproducibilityError(f"{label} mismatch at row {index}: {', '.join(differences[:5])}")
    raise ReproducibilityError(f"{label} mismatch detected")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Figure 3 specificity/calibration Table 5 and trace source data."
    )
    parser.add_argument("--margin-input", type=Path, default=DEFAULT_MARGIN_INPUT)
    parser.add_argument("--calibration-input", type=Path, default=DEFAULT_CALIBRATION_INPUT)
    parser.add_argument("--metadata-input", type=Path, default=DEFAULT_METADATA_INPUT)
    parser.add_argument("--table-output", type=Path, default=DEFAULT_TABLE_OUTPUT)
    parser.add_argument("--trace-output", type=Path, default=DEFAULT_TRACE_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated specificity/calibration outputs.")
    args = parser.parse_args()

    try:
        metrics = metric_values(read_csv(args.margin_input))
        calibrations = calibration_values(read_csv(args.calibration_input))
        metadata_rows = read_csv(args.metadata_input)
        validate_sources(metrics, calibrations)

        table_rows = generate_table_rows(metadata_rows, metrics, calibrations)
        trace_rows = generate_trace_rows(table_rows, metadata_rows)

        if args.write:
            write_csv(args.table_output, TABLE_COLUMNS, table_rows, quote_all=True)
            write_csv(args.trace_output, TRACE_COLUMNS, trace_rows, quote_all=False)

        compare("Figure 3 specificity and robustness summary", table_rows, args.table_output)
        compare("Figure 3 specificity/calibration trace", trace_rows, args.trace_output)

        print(f"Figure 3 specificity/calibration summary rows: {len(table_rows)}")
        print(f"Figure 3 specificity/calibration trace rows: {len(trace_rows)}")
        print("Figure 3 specificity/calibration layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Figure 3 specificity/calibration layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
