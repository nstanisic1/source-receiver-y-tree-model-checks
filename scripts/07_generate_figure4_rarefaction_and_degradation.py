from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_figure4_rarefaction_degradation"

DEFAULT_RAREFACTION_INPUT = SOURCE / "figure4_equal_n_rarefaction_metric_source.csv"
DEFAULT_FRACTION_INPUT = SOURCE / "figure4_synthetic_visibility_fraction_design.csv"
DEFAULT_RULE_INPUT = SOURCE / "figure4_rarefaction_degradation_rule_source.csv"
DEFAULT_BRANCH_INPUT = REPO / "tables" / "11_branch_unit_reliability_pass_matrix.csv"
DEFAULT_BENCHMARK_INPUT = REPO / "tables" / "26_benchmark_audit_card_matrix.csv"
DEFAULT_RAREFACTION_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_06_equal_n_rarefaction_degradation_trace.csv"
DEFAULT_SYNTHETIC_OUTPUT = REPO / "source_data" / "figure_4" / "fig4_08_synthetic_source_visibility_degradation_trace.csv"
DEFAULT_SYNTHETIC_TABLE_OUTPUT = REPO / "tables" / "28_figure_4_synthetic_source_visibility_degradation_trace.csv"

RAREFACTION_SOURCE_FILE = (
    "source_data/core_figure4_rarefaction_degradation/figure4_equal_n_rarefaction_metric_source.csv"
)
SYNTHETIC_SOURCE_FILES = (
    "tables/11_branch_unit_reliability_pass_matrix.csv; "
    "tables/26_benchmark_audit_card_matrix.csv; "
    "source_data/core_figure4_rarefaction_degradation/figure4_synthetic_visibility_fraction_design.csv; "
    "source_data/core_figure4_rarefaction_degradation/figure4_rarefaction_degradation_rule_source.csv"
)

R1A_COMPARATOR_ORDER = ["R-Z280", "R-M458"]
BRANCH_LAYER_ORDER = [
    "Deepest observed branch layer",
    "Residualized-count branch layer",
    "Direct-child cutset layer",
    "Depth-2 cutset layer",
    "Depth-3 cutset layer",
    "Count-balanced frontier layer",
]

RAREFACTION_COLUMNS = [
    "plot_order",
    "source_layer",
    "matched_R1a_comparator",
    "boundary_context",
    "equal_n_rarefaction_n",
    "scoreable_cells",
    "positive_cells",
    "failed_cells",
    "positive_fraction",
    "adequacy_power_state",
    "interpretation",
    "source_file",
    "claim_boundary",
]

SYNTHETIC_COLUMNS = [
    "scenario_order",
    "matched_R1a_comparator",
    "branch_resolution_layer",
    "degradation_mode",
    "source_visibility_fraction_retained",
    "source_visibility_loss_percent",
    "baseline_source_terminal_count",
    "baseline_receiver_terminal_count",
    "synthetic_source_terminal_count_continuous",
    "baseline_source_country_count",
    "synthetic_source_country_count_continuous",
    "receiver_country_count",
    "source_country_gate_pass",
    "receiver_country_gate_pass",
    "synthetic_source_adequacy_A_s",
    "branch_layer_diversity_contrast_D",
    "source_adequacy_gate_A_s",
    "matched_R1a_A_s_floor",
    "matched_R1a_D_ceiling",
    "PH908_reference_A_s",
    "PH908_reference_D",
    "source_adequacy_gate_fraction_retained",
    "PH908_A_s_equivalent_fraction_retained",
    "basic_compatibility_state",
    "matched_R1a_comparator_state",
    "PH908_like_A_s_state",
    "decision_state",
    "interpretation",
    "source_files",
    "claim_boundary",
]


class ReproducibilityError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ReproducibilityError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decimal_value(row: dict[str, str], field: str) -> Decimal:
    return Decimal(row[field])


def decimal_6(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def decimal_3(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def decimal_1(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def close_enough(left: Decimal, right: Decimal, tolerance: Decimal = Decimal("0.000001")) -> bool:
    return abs(left - right) <= tolerance


def rule_values(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    rules = {row["rule_name"]: Decimal(row["rule_value"]) for row in rows}
    required = {
        "source_adequacy_gate_A_s",
        "diversity_contrast_gate_D",
        "source_country_visibility_minimum",
        "receiver_country_visibility_minimum",
    }
    missing = required - set(rules)
    if missing:
        raise ReproducibilityError(f"Missing rule values: {', '.join(sorted(missing))}")
    return rules


def benchmark_values(rows: list[dict[str, str]]) -> dict[str, Decimal]:
    by_root = {row["lineage_root"]: row for row in rows}
    required = {"R-Z280", "R-M458", "I-PH908"}
    missing = required - set(by_root)
    if missing:
        raise ReproducibilityError(f"Missing benchmark rows: {', '.join(sorted(missing))}")

    r1a_rows = [by_root[root] for root in R1A_COMPARATOR_ORDER]
    return {
        "matched_R1a_A_s_floor": min(decimal_value(row, "deepest_source_adequacy_A_s") for row in r1a_rows),
        "matched_R1a_D_ceiling": max(decimal_value(row, "deepest_diversity_contrast_D") for row in r1a_rows),
        "PH908_reference_A_s": decimal_value(by_root["I-PH908"], "deepest_source_adequacy_A_s"),
        "PH908_reference_D": decimal_value(by_root["I-PH908"], "deepest_diversity_contrast_D"),
        "R-Z280_deepest_A_s": decimal_value(by_root["R-Z280"], "deepest_source_adequacy_A_s"),
        "R-M458_deepest_A_s": decimal_value(by_root["R-M458"], "deepest_source_adequacy_A_s"),
    }


def branch_rows_by_key(rows: list[dict[str, str]], benchmarks: list[dict[str, str]]) -> dict[tuple[str, str], dict[str, str]]:
    benchmark_by_root = {row["lineage_root"]: row for row in benchmarks}
    selected = {}
    for row in rows:
        root = row["lineage_root"]
        layer = row["branch_resolution_layer"]
        if root not in R1A_COMPARATOR_ORDER:
            continue
        if layer not in BRANCH_LAYER_ORDER:
            continue
        benchmark = benchmark_by_root[root]
        for field in [
            "source_terminal_count",
            "receiver_terminal_count",
            "source_country_count",
            "receiver_country_count",
        ]:
            if row[field] != benchmark[field]:
                raise ReproducibilityError(f"Comparator {root} {field} differs between Table 11 and Table 26.")
        selected[(root, layer)] = row

    expected = {(root, layer) for root in R1A_COMPARATOR_ORDER for layer in BRANCH_LAYER_ORDER}
    missing = expected - set(selected)
    if missing:
        shown = "; ".join(f"{root} {layer}" for root, layer in sorted(missing))
        raise ReproducibilityError(f"Missing R1a branch-unit rows: {shown}")
    return selected


def generate_rarefaction_rows(source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for source in sorted(source_rows, key=lambda item: int(item["plot_order"])):
        scoreable = int(source["scoreable_cells"])
        positive = int(source["positive_cells"])
        if scoreable <= 0:
            raise ReproducibilityError(f"Non-positive scoreable cell count at row {source['plot_order']}.")
        if positive < 0 or positive > scoreable:
            raise ReproducibilityError(f"Invalid positive cell count at row {source['plot_order']}.")

        failed = scoreable - positive
        if positive == 0:
            state = "No scoreable cells positive"
        elif positive == scoreable:
            state = "All scoreable cells positive"
        else:
            state = "Mixed low-common-n sensitivity"

        n = source["equal_n_rarefaction_n"]
        rows.append(
            {
                "plot_order": source["plot_order"],
                "source_layer": source["source_layer"],
                "matched_R1a_comparator": source["matched_R1a_comparator"],
                "boundary_context": source["boundary_context"],
                "equal_n_rarefaction_n": n,
                "scoreable_cells": str(scoreable),
                "positive_cells": str(positive),
                "failed_cells": str(failed),
                "positive_fraction": decimal_6(Decimal(positive) / Decimal(scoreable)),
                "adequacy_power_state": state,
                "interpretation": (
                    f"At equal-n {n}, {positive}/{scoreable} scoreable cells remain positive in this boundary "
                    "context; this is an adequacy and power sensitivity check, not a universal all-grid pass."
                ),
                "source_file": RAREFACTION_SOURCE_FILE,
                "claim_boundary": (
                    "Equal-n rarefaction sensitivity only; failures at lower common-n are interpreted as power "
                    "or denominator limits, not broad reversal and not evidence of geographic origin, ethnic "
                    "identity, population continuity, or migration route."
                ),
            }
        )
    return rows


def generate_synthetic_rows(
    branch_rows: dict[tuple[str, str], dict[str, str]],
    fractions: list[dict[str, str]],
    rules: dict[str, Decimal],
    benchmarks: dict[str, Decimal],
) -> list[dict[str, str]]:
    rows = []
    scenario = 1
    fraction_rows = sorted(fractions, key=lambda item: int(item["degradation_order"]))
    for comparator in R1A_COMPARATOR_ORDER:
        for layer in BRANCH_LAYER_ORDER:
            branch = branch_rows[(comparator, layer)]
            source_terminals = decimal_value(branch, "source_terminal_count")
            receiver_terminals = decimal_value(branch, "receiver_terminal_count")
            source_countries = decimal_value(branch, "source_country_count")
            receiver_countries = decimal_value(branch, "receiver_country_count")
            diversity = decimal_value(branch, "diversity_contrast_D")
            baseline_a = source_terminals / receiver_terminals
            source_gate_fraction = receiver_terminals / source_terminals
            ph908_fraction = benchmarks["PH908_reference_A_s"] / baseline_a

            for fraction_row in fraction_rows:
                fraction = decimal_value(fraction_row, "source_visibility_fraction_retained")
                expected_loss = (Decimal("1") - fraction) * Decimal("100")
                if not close_enough(expected_loss, decimal_value(fraction_row, "source_visibility_loss_percent")):
                    raise ReproducibilityError(
                        f"Visibility-loss percentage mismatch at design row {fraction_row['degradation_order']}."
                    )

                synthetic_source = source_terminals * fraction
                synthetic_countries = source_countries * fraction
                synthetic_a = synthetic_source / receiver_terminals
                source_country_pass = synthetic_countries >= rules["source_country_visibility_minimum"]
                receiver_country_pass = receiver_countries >= rules["receiver_country_visibility_minimum"]
                basic = (
                    synthetic_a > rules["source_adequacy_gate_A_s"]
                    and diversity < rules["diversity_contrast_gate_D"]
                    and source_country_pass
                    and receiver_country_pass
                )
                matched = (
                    synthetic_a >= benchmarks["matched_R1a_A_s_floor"]
                    and diversity <= benchmarks["matched_R1a_D_ceiling"]
                    and source_country_pass
                    and receiver_country_pass
                )
                ph908_like = synthetic_a <= benchmarks["PH908_reference_A_s"]

                if not source_country_pass or not receiver_country_pass:
                    decision_state = "no-call after degradation because source-country visibility falls below threshold"
                elif not basic:
                    decision_state = "rejected after degradation"
                elif matched:
                    decision_state = "matched R1a-comparator compatible after degradation"
                else:
                    decision_state = "basic compatible after degradation but outside the matched R1a-comparator envelope"

                rows.append(
                    {
                        "scenario_order": f"{scenario:03d}",
                        "matched_R1a_comparator": comparator,
                        "branch_resolution_layer": layer,
                        "degradation_mode": (
                            "deterministic source-terminal and source-country thinning with audited branch-layer collapse"
                        ),
                        "source_visibility_fraction_retained": decimal_6(fraction),
                        "source_visibility_loss_percent": decimal_3(expected_loss),
                        "baseline_source_terminal_count": str(int(source_terminals)),
                        "baseline_receiver_terminal_count": str(int(receiver_terminals)),
                        "synthetic_source_terminal_count_continuous": decimal_6(synthetic_source),
                        "baseline_source_country_count": str(int(source_countries)),
                        "synthetic_source_country_count_continuous": decimal_6(synthetic_countries),
                        "receiver_country_count": str(int(receiver_countries)),
                        "source_country_gate_pass": "Yes" if source_country_pass else "No",
                        "receiver_country_gate_pass": "Yes" if receiver_country_pass else "No",
                        "synthetic_source_adequacy_A_s": decimal_6(synthetic_a),
                        "branch_layer_diversity_contrast_D": decimal_6(diversity),
                        "source_adequacy_gate_A_s": decimal_6(rules["source_adequacy_gate_A_s"]),
                        "matched_R1a_A_s_floor": decimal_6(benchmarks["matched_R1a_A_s_floor"]),
                        "matched_R1a_D_ceiling": decimal_6(benchmarks["matched_R1a_D_ceiling"]),
                        "PH908_reference_A_s": decimal_6(benchmarks["PH908_reference_A_s"]),
                        "PH908_reference_D": decimal_6(benchmarks["PH908_reference_D"]),
                        "source_adequacy_gate_fraction_retained": decimal_6(source_gate_fraction),
                        "PH908_A_s_equivalent_fraction_retained": decimal_6(ph908_fraction),
                        "basic_compatibility_state": "Yes" if basic else "No",
                        "matched_R1a_comparator_state": "Yes" if matched else "No",
                        "PH908_like_A_s_state": "Yes" if ph908_like else "No",
                        "decision_state": decision_state,
                        "interpretation": (
                            f"{comparator} under {layer} with {decimal_1(fraction * Decimal('100'))}% source "
                            f"visibility retained gives synthetic A_s={decimal_3(synthetic_a)} and "
                            f"D={decimal_3(diversity)}; decision state: {decision_state}."
                        ),
                        "source_files": SYNTHETIC_SOURCE_FILES,
                        "claim_boundary": (
                            "Synthetic degradation control for matched R1a comparators only; deterministic thinning "
                            "is an operating-characteristic stress test, not a population-size estimate or evidence "
                            "of geographic origin, ethnic identity, population continuity, chronology, or migration route."
                        ),
                    }
                )
                scenario += 1
    return rows


def validate_summary_counts(rarefaction_rows: list[dict[str, str]], synthetic_rows: list[dict[str, str]]) -> None:
    if len(rarefaction_rows) != 48:
        raise ReproducibilityError(f"Rarefaction row count mismatch: {len(rarefaction_rows)}")
    full_positive = sum(int(row["positive_cells"]) for row in rarefaction_rows)
    full_scoreable = sum(int(row["scoreable_cells"]) for row in rarefaction_rows)
    full_failed = sum(int(row["failed_cells"]) for row in rarefaction_rows)
    if (full_positive, full_scoreable, full_failed) != (376, 544, 168):
        raise ReproducibilityError("Rarefaction full-grid summary counts changed.")
    ge50 = [row for row in rarefaction_rows if int(row["equal_n_rarefaction_n"]) >= 50]
    if (sum(int(row["positive_cells"]) for row in ge50), sum(int(row["scoreable_cells"]) for row in ge50)) != (
        272,
        272,
    ):
        raise ReproducibilityError("Rarefaction common-n >= 50 summary counts changed.")

    if len(synthetic_rows) != 72:
        raise ReproducibilityError(f"Synthetic degradation row count mismatch: {len(synthetic_rows)}")
    full_basic = sum(1 for row in synthetic_rows if row["basic_compatibility_state"] == "Yes")
    if full_basic != 30:
        raise ReproducibilityError(f"Synthetic degradation basic-compatible count changed: {full_basic}")
    for fraction, expected in [("1.000000", 10), ("0.500000", 10), ("0.250000", 0)]:
        observed = sum(
            1
            for row in synthetic_rows
            if row["source_visibility_fraction_retained"] == fraction and row["basic_compatibility_state"] == "Yes"
        )
        if observed != expected:
            raise ReproducibilityError(f"Synthetic degradation fraction {fraction} changed: {observed} != {expected}")


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
            raise ReproducibilityError(f"{label_text} mismatch at row {index}: {', '.join(differences[:6])}")
    raise ReproducibilityError(f"{label_text} mismatch detected.")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate Figure 4 equal-n rarefaction and synthetic visibility-degradation traces."
    )
    parser.add_argument("--rarefaction-input", type=Path, default=DEFAULT_RAREFACTION_INPUT)
    parser.add_argument("--fraction-input", type=Path, default=DEFAULT_FRACTION_INPUT)
    parser.add_argument("--rule-input", type=Path, default=DEFAULT_RULE_INPUT)
    parser.add_argument("--branch-input", type=Path, default=DEFAULT_BRANCH_INPUT)
    parser.add_argument("--benchmark-input", type=Path, default=DEFAULT_BENCHMARK_INPUT)
    parser.add_argument("--rarefaction-output", type=Path, default=DEFAULT_RAREFACTION_OUTPUT)
    parser.add_argument("--synthetic-output", type=Path, default=DEFAULT_SYNTHETIC_OUTPUT)
    parser.add_argument("--synthetic-table-output", type=Path, default=DEFAULT_SYNTHETIC_TABLE_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated Figure 4 rarefaction/degradation outputs.")
    args = parser.parse_args()

    try:
        rarefaction_source = read_csv(args.rarefaction_input)
        fraction_source = read_csv(args.fraction_input)
        rules = rule_values(read_csv(args.rule_input))
        branch_input = read_csv(args.branch_input)
        benchmark_input = read_csv(args.benchmark_input)

        benchmarks = benchmark_values(benchmark_input)
        branch_rows = branch_rows_by_key(branch_input, benchmark_input)
        rarefaction_rows = generate_rarefaction_rows(rarefaction_source)
        synthetic_rows = generate_synthetic_rows(branch_rows, fraction_source, rules, benchmarks)
        validate_summary_counts(rarefaction_rows, synthetic_rows)

        if args.write:
            write_csv(args.rarefaction_output, RAREFACTION_COLUMNS, rarefaction_rows)
            write_csv(args.synthetic_output, SYNTHETIC_COLUMNS, synthetic_rows)
            write_csv(args.synthetic_table_output, SYNTHETIC_COLUMNS, synthetic_rows)

        compare("Figure 4 equal-n rarefaction trace", rarefaction_rows, args.rarefaction_output)
        compare("Figure 4 synthetic degradation source trace", synthetic_rows, args.synthetic_output)
        compare("Figure 4 synthetic degradation numbered table", synthetic_rows, args.synthetic_table_output)

        print(f"Figure 4 equal-n rarefaction rows: {len(rarefaction_rows)}")
        print(f"Figure 4 synthetic degradation rows: {len(synthetic_rows)}")
        print("Figure 4 rarefaction/degradation layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Figure 4 rarefaction/degradation layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
