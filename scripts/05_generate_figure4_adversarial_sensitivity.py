from __future__ import annotations

import argparse
import csv
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_figure4_adversarial_sensitivity"

DEFAULT_STATE_INPUT = SOURCE / "figure4_adversarial_state_metric_source.csv"
DEFAULT_LABEL_INPUT = SOURCE / "figure4_adversarial_label_metadata.csv"
DEFAULT_TABLE_OUTPUT = REPO / "tables" / "06_adversarial_sensitivity_summary.csv"
DEFAULT_PLOT_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_01_adversarial_sensitivity_plot_points.csv"
DEFAULT_ENVELOPE_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_02_matched_r1a_envelope_thresholds.csv"
DEFAULT_CONTROL_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_03_positive_control_recovery_trace.csv"

STATE_SOURCE_FILE = "source_data/core_figure4_adversarial_sensitivity/figure4_adversarial_state_metric_source.csv"
TABLE_SOURCE_FILE = "tables/06_adversarial_sensitivity_summary.csv"

TABLE_COLUMNS = [
    "branch_resolution_layer",
    "ambiguity_handling_mode",
    "source_mask",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "source_adequacy_A_s",
    "diversity_contrast_D",
    "weak_directional_compatibility",
    "matched_R1a_comparator_envelope_entry",
    "positive_controls_pass",
    "minimum_matched_R1a_source_adequacy_A_s",
    "maximum_matched_R1a_diversity_contrast_D",
    "A_s_gap_to_matched_R1a_source_receiver_envelope",
    "D_gap_to_matched_R1a_source_receiver_envelope",
    "source_adequacy_multiplier_needed",
    "additional_D_decrease_needed",
    "interpretation",
    "source_trace_file",
]

PLOT_COLUMNS = [
    "plot_order",
    "lineage_or_state",
    "branch_resolution_layer",
    "ambiguity_handling_mode",
    "source_mask",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "source_adequacy_A_s",
    "log10_source_adequacy_A_s",
    "diversity_contrast_D",
    "weak_directional_compatibility",
    "matched_R1a_comparator_envelope_entry",
    "positive_controls_pass",
    "figure_role",
    "plot_group",
    "interpretation",
    "source_summary_file",
    "claim_boundary",
]

ENVELOPE_COLUMNS = [
    "plot_order",
    "branch_resolution_layer",
    "ambiguity_handling_mode",
    "source_mask",
    "matched_R1a_comparator_envelope_rule",
    "minimum_matched_R1a_source_adequacy_A_s",
    "log10_minimum_matched_R1a_source_adequacy_A_s",
    "maximum_matched_R1a_diversity_contrast_D",
    "R_Z280_source_adequacy_A_s",
    "R_Z280_diversity_contrast_D",
    "R_M458_source_adequacy_A_s",
    "R_M458_diversity_contrast_D",
    "PH908_source_adequacy_A_s",
    "PH908_diversity_contrast_D",
    "PH908_A_s_gap_to_envelope",
    "PH908_D_gap_to_envelope",
    "PH908_enters_envelope",
    "source_summary_file",
    "claim_boundary",
]

CONTROL_COLUMNS = [
    "plot_order",
    "branch_resolution_layer",
    "ambiguity_handling_mode",
    "source_mask",
    "positive_controls_pass",
    "R_Z280_source_adequacy_A_s",
    "R_Z280_diversity_contrast_D",
    "R_Z280_expected_source_receiver_state",
    "R_M458_source_adequacy_A_s",
    "R_M458_diversity_contrast_D",
    "R_M458_expected_source_receiver_state",
    "control_interpretation",
    "load_bearing_status",
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


def decimal_value(row: dict[str, str], field: str) -> Decimal:
    return Decimal(row[field])


def decimal_6(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def log10_6(value: Decimal | str) -> str:
    return f"{math.log10(float(value)):.6f}"


def close_enough(left: Decimal, right: Decimal, tolerance: Decimal = Decimal("0.000001")) -> bool:
    return abs(left - right) <= tolerance


def labels_by_dimension(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    return {(row["label_dimension"], row["label_code"]): row["descriptive_label"] for row in rows}


def label(labels: dict[tuple[str, str], str], dimension: str, code: str) -> str:
    try:
        return labels[(dimension, code)]
    except KeyError as error:
        raise ReproducibilityError(f"Missing label metadata for {dimension}:{code}") from error


def yes_no(value: bool) -> str:
    return "Yes" if value else "No"


def recovered_state(a_s: Decimal, d_value: Decimal) -> str:
    return "Recovered" if a_s > Decimal("1") and d_value < Decimal("0") else "Not recovered"


def expected_bool(row: dict[str, str], field: str) -> bool:
    value = row[field]
    if value == "Yes":
        return True
    if value == "No":
        return False
    raise ReproducibilityError(f"Expected Yes/No in {field}; observed {value}")


def validate_state_row(row: dict[str, str]) -> None:
    ph908_a = decimal_value(row, "ph908_source_adequacy_A_s")
    ph908_d = decimal_value(row, "ph908_diversity_contrast_D")
    z280_a = decimal_value(row, "R_Z280_source_adequacy_A_s")
    z280_d = decimal_value(row, "R_Z280_diversity_contrast_D")
    m458_a = decimal_value(row, "R_M458_source_adequacy_A_s")
    m458_d = decimal_value(row, "R_M458_diversity_contrast_D")
    min_a = min(z280_a, m458_a)
    max_d = max(z280_d, m458_d)
    a_gap = min_a - ph908_a
    d_gap = ph908_d - max_d
    multiplier = min_a / ph908_a
    additional_d = d_gap if d_gap > 0 else Decimal("0")
    weak = ph908_a > Decimal("1") and ph908_d < Decimal("0")
    envelope = a_gap <= 0 and d_gap <= 0
    controls_pass = recovered_state(z280_a, z280_d) == "Recovered" and recovered_state(m458_a, m458_d) == "Recovered"

    checks = [
        (min_a, decimal_value(row, "minimum_matched_r1a_source_adequacy_A_s"), "minimum matched R1a A_s"),
        (max_d, decimal_value(row, "maximum_matched_r1a_diversity_contrast_D"), "maximum matched R1a D"),
        (a_gap, decimal_value(row, "source_adequacy_gap_to_matched_r1a_envelope"), "A_s gap"),
        (d_gap, decimal_value(row, "diversity_contrast_gap_to_matched_r1a_envelope"), "D gap"),
        (multiplier, decimal_value(row, "source_adequacy_multiplier_needed"), "source-adequacy multiplier"),
        (additional_d, decimal_value(row, "additional_diversity_decrease_needed"), "additional D decrease"),
    ]
    for expected, observed, label_text in checks:
        if not close_enough(expected, observed):
            raise ReproducibilityError(f"{label_text} mismatch at state {row['state_order']}.")
    if weak != expected_bool(row, "weak_directional_compatibility"):
        raise ReproducibilityError(f"Weak directional compatibility mismatch at state {row['state_order']}.")
    if envelope != expected_bool(row, "matched_r1a_comparator_envelope_entry"):
        raise ReproducibilityError(f"Matched R1a envelope mismatch at state {row['state_order']}.")
    if controls_pass != expected_bool(row, "positive_controls_pass"):
        raise ReproducibilityError(f"Positive-control status mismatch at state {row['state_order']}.")


def interpretation(row: dict[str, str]) -> str:
    if expected_bool(row, "matched_r1a_comparator_envelope_entry"):
        return "PH908 enters the matched state-specific R1a-comparator envelope under this adversarial mask."
    if expected_bool(row, "positive_controls_pass"):
        return (
            "Weak directional compatibility only; PH908 does not enter the matched state-specific "
            "R1a-comparator envelope under a positive-control-passing adversarial mask."
        )
    return "Weak directional compatibility only; this mask is not positive-control-passing and is not treated as load-bearing evidence."


def plot_group(row: dict[str, str]) -> str:
    if expected_bool(row, "positive_controls_pass"):
        return "Positive-control-passing weak directional compatibility"
    return "Control-failing weak directional compatibility retained for transparency"


def load_bearing_status(row: dict[str, str]) -> str:
    if expected_bool(row, "positive_controls_pass"):
        return "Eligible for load-bearing adversarial interpretation if other matched-envelope criteria passed"
    return "Retained for transparency but not load-bearing because positive controls fail"


def control_interpretation(row: dict[str, str]) -> str:
    if expected_bool(row, "positive_controls_pass"):
        return "R-Z280 and R-M458 recover the expected source-receiver-compatible state under this configuration."
    return "At least one matched R1a comparator does not recover the expected state under this configuration."


def base_fields(row: dict[str, str], labels: dict[tuple[str, str], str]) -> dict[str, str]:
    return {
        "branch_resolution_layer": label(labels, "branch_resolution", row["branch_resolution_code"]),
        "ambiguity_handling_mode": label(labels, "ambiguity_handling", row["ambiguity_handling_code"]),
        "source_mask": label(labels, "source_mask", row["source_mask_key"]),
    }


def generate_table_rows(rows: list[dict[str, str]], labels: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    output = []
    for row in sorted(rows, key=lambda item: int(item["state_order"])):
        base = base_fields(row, labels)
        output.append(
            {
                **base,
                "source_terminal_count": row["ph908_source_terminal_count"],
                "receiver_terminal_count": row["ph908_receiver_terminal_count"],
                "source_country_count": row["ph908_source_country_count"],
                "receiver_country_count": row["ph908_receiver_country_count"],
                "source_adequacy_A_s": decimal_6(row["ph908_source_adequacy_A_s"]),
                "diversity_contrast_D": decimal_6(row["ph908_diversity_contrast_D"]),
                "weak_directional_compatibility": row["weak_directional_compatibility"],
                "matched_R1a_comparator_envelope_entry": row["matched_r1a_comparator_envelope_entry"],
                "positive_controls_pass": row["positive_controls_pass"],
                "minimum_matched_R1a_source_adequacy_A_s": decimal_6(row["minimum_matched_r1a_source_adequacy_A_s"]),
                "maximum_matched_R1a_diversity_contrast_D": decimal_6(row["maximum_matched_r1a_diversity_contrast_D"]),
                "A_s_gap_to_matched_R1a_source_receiver_envelope": decimal_6(row["source_adequacy_gap_to_matched_r1a_envelope"]),
                "D_gap_to_matched_R1a_source_receiver_envelope": decimal_6(row["diversity_contrast_gap_to_matched_r1a_envelope"]),
                "source_adequacy_multiplier_needed": decimal_6(row["source_adequacy_multiplier_needed"]),
                "additional_D_decrease_needed": decimal_6(row["additional_diversity_decrease_needed"]),
                "interpretation": interpretation(row),
                "source_trace_file": STATE_SOURCE_FILE,
            }
        )
    return output


def generate_plot_rows(rows: list[dict[str, str]], labels: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    output = []
    for row in sorted(rows, key=lambda item: int(item["state_order"])):
        base = base_fields(row, labels)
        output.append(
            {
                "plot_order": row["state_order"],
                "lineage_or_state": "I-PH908 adversarial sensitivity state",
                **base,
                "source_terminal_count": row["ph908_source_terminal_count"],
                "receiver_terminal_count": row["ph908_receiver_terminal_count"],
                "source_country_count": row["ph908_source_country_count"],
                "receiver_country_count": row["ph908_receiver_country_count"],
                "source_adequacy_A_s": decimal_6(row["ph908_source_adequacy_A_s"]),
                "log10_source_adequacy_A_s": log10_6(row["ph908_source_adequacy_A_s"]),
                "diversity_contrast_D": decimal_6(row["ph908_diversity_contrast_D"]),
                "weak_directional_compatibility": row["weak_directional_compatibility"],
                "matched_R1a_comparator_envelope_entry": row["matched_r1a_comparator_envelope_entry"],
                "positive_controls_pass": row["positive_controls_pass"],
                "figure_role": "Held-out PH908 adversarial stress-test point",
                "plot_group": plot_group(row),
                "interpretation": interpretation(row),
                "source_summary_file": TABLE_SOURCE_FILE,
                "claim_boundary": (
                    "Weak directional compatibility state only; not load-bearing unless the matched R1a-comparator "
                    "envelope criteria are met, and not evidence of geographic origin, ethnic identity, population "
                    "continuity, or migration route."
                ),
            }
        )
    return output


def generate_envelope_rows(rows: list[dict[str, str]], labels: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    output = []
    envelope_rule = (
        "Within-state envelope requires PH908 A_s to meet or exceed the less stringent matched R1a comparator "
        "A_s threshold and D to meet or fall below the less stringent matched R1a comparator D threshold."
    )
    for row in sorted(rows, key=lambda item: int(item["state_order"])):
        base = base_fields(row, labels)
        output.append(
            {
                "plot_order": row["state_order"],
                **base,
                "matched_R1a_comparator_envelope_rule": envelope_rule,
                "minimum_matched_R1a_source_adequacy_A_s": decimal_6(row["minimum_matched_r1a_source_adequacy_A_s"]),
                "log10_minimum_matched_R1a_source_adequacy_A_s": log10_6(row["minimum_matched_r1a_source_adequacy_A_s"]),
                "maximum_matched_R1a_diversity_contrast_D": decimal_6(row["maximum_matched_r1a_diversity_contrast_D"]),
                "R_Z280_source_adequacy_A_s": decimal_6(row["R_Z280_source_adequacy_A_s"]),
                "R_Z280_diversity_contrast_D": decimal_6(row["R_Z280_diversity_contrast_D"]),
                "R_M458_source_adequacy_A_s": decimal_6(row["R_M458_source_adequacy_A_s"]),
                "R_M458_diversity_contrast_D": decimal_6(row["R_M458_diversity_contrast_D"]),
                "PH908_source_adequacy_A_s": decimal_6(row["ph908_source_adequacy_A_s"]),
                "PH908_diversity_contrast_D": decimal_6(row["ph908_diversity_contrast_D"]),
                "PH908_A_s_gap_to_envelope": decimal_6(row["source_adequacy_gap_to_matched_r1a_envelope"]),
                "PH908_D_gap_to_envelope": decimal_6(row["diversity_contrast_gap_to_matched_r1a_envelope"]),
                "PH908_enters_envelope": row["matched_r1a_comparator_envelope_entry"],
                "source_summary_file": TABLE_SOURCE_FILE,
                "claim_boundary": (
                    "Matched R1a-comparator envelope threshold only; comparator recovery calibrates the stress test "
                    "and does not identify PH908 geographic origin, ethnic identity, population continuity, or migration route."
                ),
            }
        )
    return output


def generate_control_rows(rows: list[dict[str, str]], labels: dict[tuple[str, str], str]) -> list[dict[str, str]]:
    output = []
    for row in sorted(rows, key=lambda item: int(item["state_order"])):
        base = base_fields(row, labels)
        z280_a = decimal_value(row, "R_Z280_source_adequacy_A_s")
        z280_d = decimal_value(row, "R_Z280_diversity_contrast_D")
        m458_a = decimal_value(row, "R_M458_source_adequacy_A_s")
        m458_d = decimal_value(row, "R_M458_diversity_contrast_D")
        output.append(
            {
                "plot_order": row["state_order"],
                **base,
                "positive_controls_pass": row["positive_controls_pass"],
                "R_Z280_source_adequacy_A_s": decimal_6(z280_a),
                "R_Z280_diversity_contrast_D": decimal_6(z280_d),
                "R_Z280_expected_source_receiver_state": recovered_state(z280_a, z280_d),
                "R_M458_source_adequacy_A_s": decimal_6(m458_a),
                "R_M458_diversity_contrast_D": decimal_6(m458_d),
                "R_M458_expected_source_receiver_state": recovered_state(m458_a, m458_d),
                "control_interpretation": control_interpretation(row),
                "load_bearing_status": load_bearing_status(row),
                "source_summary_file": TABLE_SOURCE_FILE,
                "claim_boundary": (
                    "Positive-control recovery trace only; it calibrates the adversarial stress test and is not evidence "
                    "of PH908 origin, ethnic identity, population continuity, or migration route."
                ),
            }
        )
    return output


def compare(label_text: str, generated: list[dict[str, str]], existing_path: Path) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"{label_text} row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        if left != right:
            fields = sorted(set(left) | set(right))
            differences = [field for field in fields if left.get(field) != right.get(field)]
            raise ReproducibilityError(f"{label_text} mismatch at row {index}: {', '.join(differences[:5])}")
    raise ReproducibilityError(f"{label_text} mismatch detected")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Figure 4 adversarial sensitivity Table 6 and source-data files."
    )
    parser.add_argument("--state-input", type=Path, default=DEFAULT_STATE_INPUT)
    parser.add_argument("--label-input", type=Path, default=DEFAULT_LABEL_INPUT)
    parser.add_argument("--table-output", type=Path, default=DEFAULT_TABLE_OUTPUT)
    parser.add_argument("--plot-output", type=Path, default=DEFAULT_PLOT_OUTPUT)
    parser.add_argument("--envelope-output", type=Path, default=DEFAULT_ENVELOPE_OUTPUT)
    parser.add_argument("--control-output", type=Path, default=DEFAULT_CONTROL_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated Figure 4 adversarial outputs.")
    args = parser.parse_args()

    try:
        state_rows = read_csv(args.state_input)
        labels = labels_by_dimension(read_csv(args.label_input))
        for row in state_rows:
            validate_state_row(row)

        table_rows = generate_table_rows(state_rows, labels)
        plot_rows = generate_plot_rows(state_rows, labels)
        envelope_rows = generate_envelope_rows(state_rows, labels)
        control_rows = generate_control_rows(state_rows, labels)

        if args.write:
            write_csv(args.table_output, TABLE_COLUMNS, table_rows, quote_all=True)
            write_csv(args.plot_output, PLOT_COLUMNS, plot_rows, quote_all=False)
            write_csv(args.envelope_output, ENVELOPE_COLUMNS, envelope_rows, quote_all=False)
            write_csv(args.control_output, CONTROL_COLUMNS, control_rows, quote_all=False)

        compare("Figure 4 adversarial stress-test summary", table_rows, args.table_output)
        compare("Figure 4 adversarial plot points", plot_rows, args.plot_output)
        compare("Figure 4 matched R1a envelope thresholds", envelope_rows, args.envelope_output)
        compare("Figure 4 positive-control recovery trace", control_rows, args.control_output)

        print(f"Figure 4 adversarial state rows: {len(table_rows)}")
        print("Figure 4 adversarial sensitivity layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Figure 4 adversarial sensitivity layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
