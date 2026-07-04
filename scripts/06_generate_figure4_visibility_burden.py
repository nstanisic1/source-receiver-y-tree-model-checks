from __future__ import annotations

import argparse
import csv
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_figure4_visibility_burden"

DEFAULT_RULE_INPUT = SOURCE / "figure4_primary_visibility_reversal_rule_source.csv"
DEFAULT_ADVERSARIAL_INPUT = (
    REPO
    / "source_data"
    / "core_figure4_adversarial_sensitivity"
    / "figure4_adversarial_state_metric_source.csv"
)
DEFAULT_HIGHLIGHT_INPUT = REPO / "source_data" / "core_yfull" / "source_receiver_highlight_contracts.csv"
DEFAULT_BURDEN_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_05_source_visibility_burden_trace.csv"
DEFAULT_PRIMARY_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_09_primary_visibility_bias_reversal_summary.csv"
DEFAULT_PRIMARY_TABLE_OUTPUT = REPO / "tables" / "30_figure_4_primary_visibility_bias_reversal_summary.csv"

ADVERSARIAL_TABLE_SOURCE = "tables/06_adversarial_sensitivity_summary.csv"
PRIMARY_SOURCE = "source_data/core_yfull/source_receiver_highlight_contracts.csv"

BURDEN_COLUMNS = [
    "plot_order",
    "branch_resolution_layer",
    "ambiguity_handling_mode",
    "source_mask",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "PH908_source_adequacy_A_s",
    "minimum_matched_R1a_source_adequacy_A_s",
    "PH908_A_s_gap_to_envelope",
    "source_visibility_multiplier_needed",
    "source_visibility_burden_state",
    "matched_R1a_comparator_envelope_entry",
    "positive_controls_pass",
    "interpretation",
    "source_summary_file",
    "claim_boundary",
]

PRIMARY_COLUMNS = [
    "display_order",
    "reversal_axis",
    "primary_observed_quantity",
    "threshold_target",
    "threshold_value",
    "multiplier_required",
    "added_current_source_equivalents",
    "figure_label",
    "interpretation",
    "claim_boundary",
    "source_summary_file",
]

BRANCH_LABELS = {
    "deepest_observed": "Deepest observed branch layer",
    "count_balanced_frontier": "Count-balanced frontier layer",
    "depth3_cutset": "Depth-3 cutset layer",
    "depth2_cutset": "Depth-2 cutset layer",
    "direct_child_cutset": "Direct-child cutset layer",
}

AMBIGUITY_LABELS = {
    "ambiguous_included": "Ambiguous assignments included",
    "ambiguous_excluded": "Ambiguous assignments excluded",
}

SOURCE_MASK_LABELS = {
    "all_non_balkan_non_diaspora": "All non-Balkan, non-diaspora source mask",
    "eastern_northern_western_europe": "Eastern, Northern and Western Europe source mask",
}


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


def decimal_3(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def display_multiplier(value: Decimal) -> str:
    if value < Decimal("10"):
        return str(value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return str(value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def close_enough(left: Decimal, right: Decimal, tolerance: Decimal = Decimal("0.000001")) -> bool:
    return abs(left - right) <= tolerance


def label(mapping: dict[str, str], code: str, dimension: str) -> str:
    if code not in mapping:
        raise ReproducibilityError(f"Missing {dimension} label for {code}.")
    return mapping[code]


def contract_by_root(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row["root"]: row for row in rows}


def validate_adversarial_row(row: dict[str, str]) -> None:
    ph908_a = decimal_value(row, "ph908_source_adequacy_A_s")
    threshold_a = decimal_value(row, "minimum_matched_r1a_source_adequacy_A_s")
    gap = threshold_a - ph908_a
    multiplier = threshold_a / ph908_a
    if not close_enough(gap, decimal_value(row, "source_adequacy_gap_to_matched_r1a_envelope")):
        raise ReproducibilityError(f"Adversarial A_s gap mismatch at state {row['state_order']}.")
    if not close_enough(multiplier, decimal_value(row, "source_adequacy_multiplier_needed")):
        raise ReproducibilityError(f"Adversarial source-visibility multiplier mismatch at state {row['state_order']}.")


def generate_burden_rows(adversarial_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in sorted(adversarial_rows, key=lambda item: int(item["state_order"])):
        validate_adversarial_row(row)
        multiplier = Decimal(row["source_adequacy_multiplier_needed"])
        state = (
            "Positive-control-passing visibility-burden trace"
            if row["positive_controls_pass"] == "Yes"
            else "Control-failing transparency trace"
        )
        rows.append(
            {
                "plot_order": row["state_order"],
                "branch_resolution_layer": label(BRANCH_LABELS, row["branch_resolution_code"], "branch-resolution"),
                "ambiguity_handling_mode": label(AMBIGUITY_LABELS, row["ambiguity_handling_code"], "ambiguity-handling"),
                "source_mask": label(SOURCE_MASK_LABELS, row["source_mask_key"], "source-mask"),
                "source_terminal_count": row["ph908_source_terminal_count"],
                "receiver_terminal_count": row["ph908_receiver_terminal_count"],
                "source_country_count": row["ph908_source_country_count"],
                "receiver_country_count": row["ph908_receiver_country_count"],
                "PH908_source_adequacy_A_s": decimal_6(row["ph908_source_adequacy_A_s"]),
                "minimum_matched_R1a_source_adequacy_A_s": decimal_6(
                    row["minimum_matched_r1a_source_adequacy_A_s"]
                ),
                "PH908_A_s_gap_to_envelope": decimal_6(row["source_adequacy_gap_to_matched_r1a_envelope"]),
                "source_visibility_multiplier_needed": decimal_6(multiplier),
                "source_visibility_burden_state": state,
                "matched_R1a_comparator_envelope_entry": row["matched_r1a_comparator_envelope_entry"],
                "positive_controls_pass": row["positive_controls_pass"],
                "interpretation": (
                    f"At this adversarial state, PH908 would need {decimal_3(multiplier)}-fold higher source "
                    "adequacy to reach the matched R1a-comparator source-adequacy threshold; this is a "
                    "visibility-burden calculation, not a population-size estimate."
                ),
                "source_summary_file": ADVERSARIAL_TABLE_SOURCE,
                "claim_boundary": (
                    "Source-visibility burden trace only; not a correction for public-tree bias, not a "
                    "population-size estimate, and not evidence of geographic origin, ethnic identity, "
                    "population continuity, or migration route."
                ),
            }
        )
    return rows


def threshold_value(rule: dict[str, str], contracts: dict[str, dict[str, str]]) -> Decimal:
    rule_name = rule["threshold_rule"]
    if rule_name == "fixed_value_1":
        return Decimal("1")
    if rule_name == "fixed_value_0":
        return Decimal("0")
    r1a_rows = [contracts[root.strip()] for root in rule["threshold_lineage_group"].split(";")]
    if rule_name == "minimum_matched_r1a_source_adequacy_A_s":
        return min(Decimal(row["deepest_A_s"]) for row in r1a_rows)
    if rule_name == "maximum_matched_r1a_diversity_contrast_D":
        return max(Decimal(row["deepest_D"]) for row in r1a_rows)
    raise ReproducibilityError(f"Unrecognized threshold rule: {rule_name}")


def primary_observed_quantity(rule: dict[str, str], contracts: dict[str, dict[str, str]]) -> Decimal:
    observed = contracts[rule["observed_lineage_root"]]
    if rule["reversal_axis"] == "source adequacy A_s":
        return Decimal(observed["deepest_A_s"])
    if rule["reversal_axis"] == "source diversity q2":
        return Decimal(observed["deepest_D"])
    raise ReproducibilityError(f"Unrecognized reversal axis: {rule['reversal_axis']}")


def primary_multiplier(axis: str, observed: Decimal, threshold: Decimal) -> Decimal:
    if axis == "source adequacy A_s":
        return threshold / observed
    if axis == "source diversity q2":
        return Decimal(str(math.exp(float(observed - threshold))))
    raise ReproducibilityError(f"Unrecognized reversal axis: {axis}")


def primary_interpretation(rule: dict[str, str], multiplier_text: str) -> str:
    if rule["reversal_axis"] == "source diversity q2":
        return rule["interpretation_rule"].replace("would need to increase", f"would need to increase by more than {multiplier_text}-fold")
    return rule["interpretation_rule"].replace("would need a source-side expansion", f"would need a {multiplier_text}-fold source-side expansion")


def generate_primary_rows(rule_rows: list[dict[str, str]], contracts: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for rule in sorted(rule_rows, key=lambda item: int(item["display_order"])):
        observed = primary_observed_quantity(rule, contracts)
        threshold = threshold_value(rule, contracts)
        multiplier = primary_multiplier(rule["reversal_axis"], observed, threshold)
        added = multiplier - Decimal("1")
        multiplier_text = display_multiplier(multiplier)
        rows.append(
            {
                "display_order": rule["display_order"],
                "reversal_axis": rule["reversal_axis"],
                "primary_observed_quantity": decimal_6(observed),
                "threshold_target": rule["threshold_target"],
                "threshold_value": decimal_6(threshold),
                "multiplier_required": multiplier_text,
                "added_current_source_equivalents": display_multiplier(added),
                "figure_label": f"{rule['figure_label_prefix']}: {multiplier_text}x",
                "interpretation": primary_interpretation(rule, multiplier_text),
                "claim_boundary": (
                    "Visibility-bias reversal bound only; not a population-size estimate, bias correction, "
                    "geographic-origin claim, ethnic-identity claim, continuity claim, or migration-route claim."
                ),
                "source_summary_file": PRIMARY_SOURCE,
            }
        )
    return rows


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
        description="Generate Figure 4 source-visibility burden and primary visibility-reversal summaries."
    )
    parser.add_argument("--rule-input", type=Path, default=DEFAULT_RULE_INPUT)
    parser.add_argument("--adversarial-input", type=Path, default=DEFAULT_ADVERSARIAL_INPUT)
    parser.add_argument("--highlight-input", type=Path, default=DEFAULT_HIGHLIGHT_INPUT)
    parser.add_argument("--burden-output", type=Path, default=DEFAULT_BURDEN_OUTPUT)
    parser.add_argument("--primary-output", type=Path, default=DEFAULT_PRIMARY_OUTPUT)
    parser.add_argument("--primary-table-output", type=Path, default=DEFAULT_PRIMARY_TABLE_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated Figure 4 visibility-burden outputs.")
    args = parser.parse_args()

    try:
        adversarial_rows = read_csv(args.adversarial_input)
        rule_rows = read_csv(args.rule_input)
        contracts = contract_by_root(read_csv(args.highlight_input))

        burden_rows = generate_burden_rows(adversarial_rows)
        primary_rows = generate_primary_rows(rule_rows, contracts)

        if args.write:
            write_csv(args.burden_output, BURDEN_COLUMNS, burden_rows, quote_all=False)
            write_csv(args.primary_output, PRIMARY_COLUMNS, primary_rows, quote_all=False)
            write_csv(args.primary_table_output, PRIMARY_COLUMNS, primary_rows, quote_all=False)

        compare("Figure 4 source-visibility burden trace", burden_rows, args.burden_output)
        compare("Figure 4 primary visibility-bias reversal source", primary_rows, args.primary_output)
        compare("Figure 4 primary visibility-bias reversal table", primary_rows, args.primary_table_output)

        print(f"Figure 4 source-visibility burden rows: {len(burden_rows)}")
        print(f"Figure 4 primary visibility-reversal rows: {len(primary_rows)}")
        print("Figure 4 visibility-burden layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Figure 4 visibility-burden layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
