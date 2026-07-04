from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_branch_unit_reliability"

DEFAULT_METRIC_INPUT = SOURCE / "branch_unit_metric_source.csv"
DEFAULT_METADATA_INPUT = SOURCE / "branch_unit_contract_metadata.csv"
DEFAULT_MATRIX_OUTPUT = REPO / "tables" / "11_branch_unit_reliability_pass_matrix.csv"
DEFAULT_PIVOT_OUTPUT = REPO / "tables" / "12_branch_unit_reliability_pass_pivot_summary.csv"
DEFAULT_OVERLAY_OUTPUT = REPO / "source_data" / "figure_3" / "fig3_06_branch_unit_stability_overlay.csv"

BRANCH_ORDER = [
    ("deepest_observed", "Deepest observed branch layer"),
    ("residualized_counts", "Residualized-count branch layer"),
    ("direct_child_cutset", "Direct-child cutset layer"),
    ("depth2_cutset", "Depth-2 cutset layer"),
    ("depth3_cutset", "Depth-3 cutset layer"),
    ("count_balanced_frontier", "Count-balanced frontier layer"),
]

PIVOT_COLUMNS_BY_CODE = {
    "deepest_observed": "deepest_layer_decision",
    "residualized_counts": "residualized_count_layer_decision",
    "direct_child_cutset": "direct_child_layer_decision",
    "depth2_cutset": "depth_2_layer_decision",
    "depth3_cutset": "depth_3_layer_decision",
    "count_balanced_frontier": "count_balanced_layer_decision",
}

MATRIX_COLUMNS = [
    "comparison_contract",
    "lineage_root",
    "audit_card",
    "interpretive_role",
    "branch_resolution_layer",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "source_branch_count",
    "receiver_branch_count",
    "source_adequacy_A_s",
    "diversity_contrast_D",
    "branch_unit_decision",
    "decision_basis",
    "additional_sensitivity_evidence",
    "source_summary_file",
]

PIVOT_COLUMNS = [
    "lineage_root",
    "audit_card",
    "interpretive_role",
    "deepest_layer_decision",
    "residualized_count_layer_decision",
    "direct_child_layer_decision",
    "depth_2_layer_decision",
    "depth_3_layer_decision",
    "count_balanced_layer_decision",
    "branch_unit_pattern_summary",
    "reported_interpretation",
    "source_summary_file",
]

OVERLAY_COLUMNS = [
    "display_order",
    "lineage_root",
    "audit_card",
    "figure3_role",
    "comparison_framework",
    "branch_resolution_order",
    "branch_resolution_layer",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "source_branch_count",
    "receiver_branch_count",
    "source_adequacy_A_s",
    "diversity_contrast_D",
    "branch_unit_decision",
    "stability_dot_class",
    "pattern_summary",
    "reported_interpretation",
    "additional_sensitivity_evidence_status",
    "source_matrix_file",
    "source_pivot_file",
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


def decimal_6(value: str) -> str:
    return str(Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def metadata_by_contract(path: Path) -> dict[str, dict[str, str]]:
    rows = read_csv(path)
    return {row["comparison_contract_id"]: row for row in rows}


def branch_label(code: str) -> str:
    for branch_code, label in BRANCH_ORDER:
        if branch_code == code:
            return label
    raise ReproducibilityError(f"Unrecognized branch-unit code: {code}")


def branch_order(code: str) -> int:
    for index, (branch_code, _) in enumerate(BRANCH_ORDER, start=1):
        if branch_code == code:
            return index
    raise ReproducibilityError(f"Unrecognized branch-unit code: {code}")


def decision_basis(row: dict[str, str]) -> str:
    state = row["branch_unit_state"]
    if state == "Pass":
        return "Predefined pass criterion met for this branch-resolution layer."
    if state == "Fail":
        return row["decision_basis"] or "A_s <= 1 or D >= 0"
    if state == "No-call":
        return "Residualized-count layer is not scoreable under the predefined branch-unit scoreability rules."
    raise ReproducibilityError(f"Unrecognized branch-unit state: {state}")


def additional_evidence(row: dict[str, str]) -> str:
    parts = []
    if row["rarefaction_median_D"]:
        parts.append(f"rarefaction median D = {decimal_6(row['rarefaction_median_D'])}")
    if row["rarefaction_p975_D"]:
        parts.append(f"rarefaction p97.5 D = {decimal_6(row['rarefaction_p975_D'])}")
    if row["permutation_p"]:
        parts.append(f"permutation p = {decimal_6(row['permutation_p'])}")
    if row["leave_one_country_min_D"]:
        parts.append(f"leave-one-country minimum D = {decimal_6(row['leave_one_country_min_D'])}")
    if row["leave_one_country_preserves_direction"]:
        parts.append(f"leave-one-country direction preserved = {row['leave_one_country_preserves_direction']}")
    return "; ".join(parts) if parts else "not reported in source metric row"


def generate_matrix_rows(metric_rows: list[dict[str, str]], metadata: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for row in metric_rows:
        meta = metadata[row["comparison_contract_id"]]
        rows.append(
            {
                "comparison_contract": meta["comparison_contract"],
                "lineage_root": row["lineage_root"],
                "audit_card": row["audit_card"],
                "interpretive_role": meta["interpretive_role"],
                "branch_resolution_layer": branch_label(row["branch_unit_code"]),
                "source_terminal_count": row["source_terminal_count"],
                "receiver_terminal_count": row["receiver_terminal_count"],
                "source_country_count": row["source_country_count"],
                "receiver_country_count": row["receiver_country_count"],
                "source_branch_count": row["source_branch_count"],
                "receiver_branch_count": row["receiver_branch_count"],
                "source_adequacy_A_s": decimal_6(row["source_adequacy_A_s"]),
                "diversity_contrast_D": decimal_6(row["diversity_contrast_D"]),
                "branch_unit_decision": row["branch_unit_state"],
                "decision_basis": decision_basis(row),
                "additional_sensitivity_evidence": additional_evidence(row),
                "source_summary_file": "source_data/core_branch_unit_reliability/branch_unit_metric_source.csv; source_data/core_branch_unit_reliability/branch_unit_contract_metadata.csv",
            }
        )
    return rows


def generate_pivot_rows(metric_rows: list[dict[str, str]], metadata: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    grouped: dict[str, dict[str, str]] = {}
    for row in metric_rows:
        grouped.setdefault(row["comparison_contract_id"], {})[row["branch_unit_code"]] = row["branch_unit_state"]

    rows = []
    for contract_id, decisions in grouped.items():
        meta = metadata[contract_id]
        output = {
            "lineage_root": meta["lineage_root"],
            "audit_card": meta["audit_card"],
            "interpretive_role": meta["interpretive_role"],
            "branch_unit_pattern_summary": meta["pattern_summary"],
            "reported_interpretation": meta["reported_interpretation"],
            "source_summary_file": "source_data/core_branch_unit_reliability/branch_unit_metric_source.csv; source_data/core_branch_unit_reliability/branch_unit_contract_metadata.csv",
        }
        for code, _ in BRANCH_ORDER:
            output[PIVOT_COLUMNS_BY_CODE[code]] = decisions[code]
        rows.append(output)
    return rows


def generate_overlay_rows(metric_rows: list[dict[str, str]], metadata: dict[str, dict[str, str]]) -> list[dict[str, str]]:
    included = {"PH908_EE_RUSSIA_TO_BALKAN": 1, "R_Z280_EE_RUSSIA_TO_BALKAN": 2, "R_M458_EE_RUSSIA_TO_BALKAN": 3}
    rows = []
    display_order = 1
    for contract_id in sorted(included, key=lambda value: included[value]):
        meta = metadata[contract_id]
        contract_rows = [row for row in metric_rows if row["comparison_contract_id"] == contract_id]
        contract_rows.sort(key=lambda row: branch_order(row["branch_unit_code"]))
        for row in contract_rows:
            rows.append(
                {
                    "display_order": str(display_order),
                    "lineage_root": row["lineage_root"],
                    "audit_card": row["audit_card"],
                    "figure3_role": meta["figure3_role"],
                    "comparison_framework": "Eastern Europe/Russia-to-Balkans PH908/R1a source-receiver geometry",
                    "branch_resolution_order": str(branch_order(row["branch_unit_code"])),
                    "branch_resolution_layer": branch_label(row["branch_unit_code"]),
                    "source_terminal_count": row["source_terminal_count"],
                    "receiver_terminal_count": row["receiver_terminal_count"],
                    "source_country_count": row["source_country_count"],
                    "receiver_country_count": row["receiver_country_count"],
                    "source_branch_count": row["source_branch_count"],
                    "receiver_branch_count": row["receiver_branch_count"],
                    "source_adequacy_A_s": decimal_6(row["source_adequacy_A_s"]),
                    "diversity_contrast_D": decimal_6(row["diversity_contrast_D"]),
                    "branch_unit_decision": row["branch_unit_state"],
                    "stability_dot_class": row["branch_unit_state"],
                    "pattern_summary": meta["pattern_summary"],
                    "reported_interpretation": meta["figure3_interpretation"],
                    "additional_sensitivity_evidence_status": "No rarefaction or additional sensitivity field is reported for this row in Table 11.",
                    "source_matrix_file": "tables/11_branch_unit_reliability_pass_matrix.csv",
                    "source_pivot_file": "tables/12_branch_unit_reliability_pass_pivot_summary.csv",
                    "claim_boundary": "Branch-unit stability overlay only; not confidence or rarefaction evidence and not evidence of geographic origin, ethnic identity, population continuity, or migration route.",
                }
            )
            display_order += 1
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
        description="Generate branch-unit reliability tables and the Figure 3 stability overlay."
    )
    parser.add_argument("--metric-input", type=Path, default=DEFAULT_METRIC_INPUT)
    parser.add_argument("--metadata-input", type=Path, default=DEFAULT_METADATA_INPUT)
    parser.add_argument("--matrix-output", type=Path, default=DEFAULT_MATRIX_OUTPUT)
    parser.add_argument("--pivot-output", type=Path, default=DEFAULT_PIVOT_OUTPUT)
    parser.add_argument("--overlay-output", type=Path, default=DEFAULT_OVERLAY_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated branch-unit outputs.")
    args = parser.parse_args()

    try:
        metric_rows = read_csv(args.metric_input)
        metadata = metadata_by_contract(args.metadata_input)
        matrix_rows = generate_matrix_rows(metric_rows, metadata)
        pivot_rows = generate_pivot_rows(metric_rows, metadata)
        overlay_rows = generate_overlay_rows(metric_rows, metadata)

        if args.write:
            write_csv(args.matrix_output, MATRIX_COLUMNS, matrix_rows, quote_all=True)
            write_csv(args.pivot_output, PIVOT_COLUMNS, pivot_rows, quote_all=True)
            write_csv(args.overlay_output, OVERLAY_COLUMNS, overlay_rows, quote_all=False)

        compare("Branch-unit reliability pass matrix", matrix_rows, args.matrix_output)
        compare("Branch-unit reliability pivot summary", pivot_rows, args.pivot_output)
        compare("Figure 3 branch-unit stability overlay", overlay_rows, args.overlay_output)

        print(f"Branch-unit reliability matrix rows: {len(matrix_rows)}")
        print(f"Branch-unit reliability pivot rows: {len(pivot_rows)}")
        print(f"Figure 3 branch-unit stability overlay rows: {len(overlay_rows)}")
        print("Branch-unit reliability layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Branch-unit reliability layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
