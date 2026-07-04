from __future__ import annotations

import argparse
import csv
import math
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_parser_logbase_quality_control"

DEFAULT_HEADLINE_INPUT = SOURCE / "parser_headline_sensitivity_metric_source.csv"
DEFAULT_FAILED_ROW_INPUT = SOURCE / "parser_failed_row_audit_source.csv"
DEFAULT_RULE_INPUT = SOURCE / "parser_logbase_rule_source.csv"
DEFAULT_ADVERSARIAL_INPUT = (
    REPO / "source_data" / "core_figure4_adversarial_sensitivity" / "figure4_adversarial_state_metric_source.csv"
)
DEFAULT_LABEL_INPUT = (
    REPO / "source_data" / "core_figure4_adversarial_sensitivity" / "figure4_adversarial_label_metadata.csv"
)
DEFAULT_HEADLINE_OUTPUT = REPO / "tables" / "15_parser_headline_sensitivity.csv"
DEFAULT_FAILED_ROW_OUTPUT = REPO / "tables" / "16_parser_failed_rows_action_table.csv"
DEFAULT_LOG_BASE_OUTPUT = REPO / "tables" / "17_diversity_contrast_log_base_audit.csv"

HEADLINE_SOURCE_FILE = "source_data/core_parser_logbase_quality_control/parser_headline_sensitivity_metric_source.csv"
FAILED_ROW_SOURCE_FILE = "source_data/core_parser_logbase_quality_control/parser_failed_row_audit_source.csv"
ADVERSARIAL_SOURCE_FILE = (
    "source_data/core_figure4_adversarial_sensitivity/figure4_adversarial_state_metric_source.csv"
)

HEADLINE_COLUMNS = [
    "comparison_contract",
    "lineage_root",
    "original_source_terminal_count",
    "original_receiver_terminal_count",
    "original_source_country_count",
    "original_receiver_country_count",
    "original_source_branch_unit_count",
    "original_receiver_branch_unit_count",
    "original_source_q2",
    "original_receiver_q2",
    "original_source_adequacy_A_s",
    "original_diversity_contrast_D",
    "original_headline_decision",
    "post_exclusion_source_terminal_count",
    "post_exclusion_receiver_terminal_count",
    "post_exclusion_source_country_count",
    "post_exclusion_receiver_country_count",
    "post_exclusion_source_branch_unit_count",
    "post_exclusion_receiver_branch_unit_count",
    "post_exclusion_source_q2",
    "post_exclusion_receiver_q2",
    "post_exclusion_source_adequacy_A_s",
    "post_exclusion_diversity_contrast_D",
    "post_exclusion_headline_decision",
    "delta_source_adequacy_A_s",
    "delta_diversity_contrast_D",
    "headline_decision_changed",
    "parser_audit_interpretation",
    "source_audit_file",
]

FAILED_ROW_COLUMNS = [
    "lineage_root",
    "descendant_branch_label",
    "country",
    "parsed_terminal_count",
    "YFull_topology_check",
    "root_membership_check",
    "parent_child_consistency_check",
    "public_display_row_found",
    "private_identifier_detected",
    "parser_audit_status",
    "exclusion_reason",
    "curation_action",
    "downstream_sensitivity_check",
    "source_audit_file",
]

LOG_BASE_COLUMNS = [
    "audit_context",
    "audited_row",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_q2",
    "receiver_q2",
    "receiver_source_q2_ratio",
    "expected_D_natural_log",
    "D_log10_reference",
    "reported_diversity_contrast_D",
    "reported_log_base",
    "log_base_audit_status",
    "log_base_interpretation",
    "source_audit_file",
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


def close_enough(left: Decimal, right: Decimal, tolerance: Decimal = Decimal("0.000001")) -> bool:
    return abs(left - right) <= tolerance


def rules_by_name(rows: list[dict[str, str]]) -> dict[str, str]:
    rules = {row["rule_name"]: row["rule_value"] for row in rows}
    required = {
        "source_adequacy_pass_threshold_A_s",
        "diversity_contrast_pass_threshold_D",
        "reported_D_log_base",
    }
    missing = required - set(rules)
    if missing:
        raise ReproducibilityError(f"Missing parser/log-base rules: {', '.join(sorted(missing))}")
    if rules["reported_D_log_base"] != "natural_log":
        raise ReproducibilityError("The reported D log-base rule must remain natural_log.")
    return rules


def adequacy(source_terminal_count: str, receiver_terminal_count: str) -> Decimal:
    return Decimal(source_terminal_count) / Decimal(receiver_terminal_count)


def diversity_contrast(source_q2: str, receiver_q2: str) -> Decimal:
    return Decimal(str(math.log(float(Decimal(receiver_q2) / Decimal(source_q2)))))


def log10_reference_from_ratio(ratio: Decimal) -> Decimal:
    return Decimal(str(math.log10(float(ratio))))


def decision(a_s: Decimal, d_value: Decimal, rules: dict[str, str]) -> str:
    return (
        "Pass"
        if a_s > Decimal(rules["source_adequacy_pass_threshold_A_s"])
        and d_value < Decimal(rules["diversity_contrast_pass_threshold_D"])
        else "Fail"
    )


def parser_interpretation(delta_a: Decimal, delta_d: Decimal, changed: str) -> str:
    if changed == "Yes":
        return "Headline decision changed after failed-row exclusion."
    if close_enough(delta_a, Decimal("0")) and close_enough(delta_d, Decimal("0")):
        return "No numerical change and no headline-decision change after failed-row exclusion."
    return "Small metric shift after failed-row exclusion; headline decision unchanged."


def generate_headline_rows(source_rows: list[dict[str, str]], rules: dict[str, str]) -> list[dict[str, str]]:
    rows = []
    for source in source_rows:
        original_a = adequacy(source["original_source_terminal_count"], source["original_receiver_terminal_count"])
        original_d = diversity_contrast(source["original_source_q2"], source["original_receiver_q2"])
        post_a = adequacy(
            source["post_exclusion_source_terminal_count"],
            source["post_exclusion_receiver_terminal_count"],
        )
        post_d = diversity_contrast(source["post_exclusion_source_q2"], source["post_exclusion_receiver_q2"])
        original_decision = decision(original_a, original_d, rules)
        post_decision = decision(post_a, post_d, rules)
        delta_a = post_a - original_a
        delta_d = post_d - original_d
        changed = "Yes" if original_decision != post_decision else "No"

        row = {field: source[field] for field in HEADLINE_COLUMNS if field in source}
        row.update(
            {
                "original_source_adequacy_A_s": decimal_6(original_a),
                "original_diversity_contrast_D": decimal_6(original_d),
                "original_headline_decision": original_decision,
                "post_exclusion_source_adequacy_A_s": decimal_6(post_a),
                "post_exclusion_diversity_contrast_D": decimal_6(post_d),
                "post_exclusion_headline_decision": post_decision,
                "delta_source_adequacy_A_s": decimal_6(delta_a),
                "delta_diversity_contrast_D": decimal_6(delta_d),
                "headline_decision_changed": changed,
                "parser_audit_interpretation": parser_interpretation(delta_a, delta_d, changed),
                "source_audit_file": HEADLINE_SOURCE_FILE,
            }
        )
        rows.append(row)
    return rows


def generate_failed_row_table(source_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for source in source_rows:
        row = {field: source[field] for field in FAILED_ROW_COLUMNS if field in source}
        row["source_audit_file"] = FAILED_ROW_SOURCE_FILE
        rows.append(row)
    return rows


def labels_by_dimension(rows: list[dict[str, str]]) -> dict[tuple[str, str], str]:
    return {(row["label_dimension"], row["label_code"]): row["descriptive_label"] for row in rows}


def label(labels: dict[tuple[str, str], str], dimension: str, code: str) -> str:
    try:
        return labels[(dimension, code)]
    except KeyError as error:
        raise ReproducibilityError(f"Missing label metadata for {dimension}: {code}") from error


def headline_log_base_rows(headline_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in headline_rows:
        ratio = Decimal(row["original_receiver_q2"]) / Decimal(row["original_source_q2"])
        expected_d = diversity_contrast(row["original_source_q2"], row["original_receiver_q2"])
        reported_d = Decimal(row["original_diversity_contrast_D"])
        if not close_enough(expected_d, reported_d):
            raise ReproducibilityError(f"Headline log-base mismatch for {row['lineage_root']}.")
        rows.append(
            {
                "audit_context": "Headline q2-component recomputation row",
                "audited_row": f"{row['lineage_root']} headline parser-sensitivity row",
                "source_terminal_count": row["original_source_terminal_count"],
                "receiver_terminal_count": row["original_receiver_terminal_count"],
                "source_q2": row["original_source_q2"],
                "receiver_q2": row["original_receiver_q2"],
                "receiver_source_q2_ratio": decimal_6(ratio),
                "expected_D_natural_log": decimal_6(expected_d),
                "D_log10_reference": decimal_6(log10_reference_from_ratio(ratio)),
                "reported_diversity_contrast_D": decimal_6(reported_d),
                "reported_log_base": "Natural log",
                "log_base_audit_status": "Pass",
                "log_base_interpretation": (
                    "Reported D matches natural-log recomputation from source and receiver q2 components."
                ),
                "source_audit_file": HEADLINE_SOURCE_FILE,
            }
        )
    return rows


def adversarial_log_base_rows(
    adversarial_rows: list[dict[str, str]], labels: dict[tuple[str, str], str]
) -> list[dict[str, str]]:
    rows = []
    for source in sorted(adversarial_rows, key=lambda item: int(item["state_order"])):
        d_value = Decimal(source["ph908_diversity_contrast_D"])
        ratio = Decimal(str(math.exp(float(d_value))))
        branch_label = label(labels, "branch_resolution", source["branch_resolution_code"])
        ambiguity_label = label(labels, "ambiguity_handling", source["ambiguity_handling_code"]).lower()
        rows.append(
            {
                "audit_context": "Adversarial sensitivity D context row",
                "audited_row": (
                    f"I-PH908 adversarial sensitivity state {source['state_order']}; "
                    f"{branch_label}; {ambiguity_label}"
                ),
                "source_terminal_count": source["ph908_source_terminal_count"],
                "receiver_terminal_count": source["ph908_receiver_terminal_count"],
                "source_q2": "Not reported in source row",
                "receiver_q2": "Not reported in source row",
                "receiver_source_q2_ratio": decimal_6(ratio),
                "expected_D_natural_log": decimal_6(d_value),
                "D_log10_reference": decimal_6(log10_reference_from_ratio(ratio)),
                "reported_diversity_contrast_D": decimal_6(d_value),
                "reported_log_base": "Natural log; context-only",
                "log_base_audit_status": "Context only; q2 components not present in source row",
                "log_base_interpretation": (
                    "Reported adversarial sensitivity-state D is in natural-log context; q2 components are not "
                    "present in this source row, so this row is not an independent q2-component recomputation."
                ),
                "source_audit_file": ADVERSARIAL_SOURCE_FILE,
            }
        )
    return rows


def generate_log_base_rows(
    headline_rows: list[dict[str, str]],
    adversarial_rows: list[dict[str, str]],
    label_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    labels = labels_by_dimension(label_rows)
    rows = headline_log_base_rows(headline_rows)
    rows.extend(adversarial_log_base_rows(adversarial_rows, labels))
    return rows


def validate_outputs(headline_rows: list[dict[str, str]], failed_rows: list[dict[str, str]], log_rows: list[dict[str, str]]) -> None:
    if len(headline_rows) != 7:
        raise ReproducibilityError(f"Table 15 row count changed: {len(headline_rows)}")
    if sum(1 for row in headline_rows if row["headline_decision_changed"] == "Yes") != 0:
        raise ReproducibilityError("Parser headline sensitivity contains a decision change.")
    if len(failed_rows) != 2:
        raise ReproducibilityError(f"Table 16 row count changed: {len(failed_rows)}")
    if any(row["private_identifier_detected"] != "No" for row in failed_rows):
        raise ReproducibilityError("Failed-row action table contains a private-identifier flag.")
    if len(log_rows) != 17:
        raise ReproducibilityError(f"Table 17 row count changed: {len(log_rows)}")
    if sum(1 for row in log_rows if row["audit_context"] == "Headline q2-component recomputation row") != 7:
        raise ReproducibilityError("Table 17 headline q2-component audit row count changed.")
    if sum(1 for row in log_rows if row["audit_context"] == "Adversarial sensitivity D context row") != 10:
        raise ReproducibilityError("Table 17 adversarial context row count changed.")


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
    parser = argparse.ArgumentParser(description="Generate parser-sensitivity and diversity-contrast log-base QC tables.")
    parser.add_argument("--headline-input", type=Path, default=DEFAULT_HEADLINE_INPUT)
    parser.add_argument("--failed-row-input", type=Path, default=DEFAULT_FAILED_ROW_INPUT)
    parser.add_argument("--rule-input", type=Path, default=DEFAULT_RULE_INPUT)
    parser.add_argument("--adversarial-input", type=Path, default=DEFAULT_ADVERSARIAL_INPUT)
    parser.add_argument("--label-input", type=Path, default=DEFAULT_LABEL_INPUT)
    parser.add_argument("--headline-output", type=Path, default=DEFAULT_HEADLINE_OUTPUT)
    parser.add_argument("--failed-row-output", type=Path, default=DEFAULT_FAILED_ROW_OUTPUT)
    parser.add_argument("--log-base-output", type=Path, default=DEFAULT_LOG_BASE_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated parser and log-base QC tables.")
    args = parser.parse_args()

    try:
        rules = rules_by_name(read_csv(args.rule_input))
        headline_rows = generate_headline_rows(read_csv(args.headline_input), rules)
        failed_rows = generate_failed_row_table(read_csv(args.failed_row_input))
        log_rows = generate_log_base_rows(headline_rows, read_csv(args.adversarial_input), read_csv(args.label_input))
        validate_outputs(headline_rows, failed_rows, log_rows)

        if args.write:
            write_csv(args.headline_output, HEADLINE_COLUMNS, headline_rows)
            write_csv(args.failed_row_output, FAILED_ROW_COLUMNS, failed_rows)
            write_csv(args.log_base_output, LOG_BASE_COLUMNS, log_rows)

        compare("Parser headline sensitivity table", headline_rows, args.headline_output)
        compare("Parser failed-row action table", failed_rows, args.failed_row_output)
        compare("Diversity-contrast log-base audit table", log_rows, args.log_base_output)

        print(f"Parser headline sensitivity rows: {len(headline_rows)}")
        print(f"Parser failed-row action rows: {len(failed_rows)}")
        print(f"Diversity-contrast log-base audit rows: {len(log_rows)}")
        print("Parser and log-base quality-control layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Parser and log-base quality-control layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
