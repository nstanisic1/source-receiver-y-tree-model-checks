from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "tables"
FIG4_SOURCE = REPO / "source_data" / "figure_4"

DEFAULT_SENSITIVITY_INPUT = TABLES / "06_adversarial_sensitivity_summary.csv"
DEFAULT_DIRECTNESS_INPUT = TABLES / "19_direct_negative_control_eligibility_audit.csv"
DEFAULT_FIG4_CLAIM_AUDIT = FIG4_SOURCE / "fig4_07_visibility_mask_sensitivity_validation.csv"
DEFAULT_POSITIVE_CONTROL_TRACE = FIG4_SOURCE / "fig4_03_positive_control_recovery_trace.csv"
DEFAULT_OUTPUT = TABLES / "10_integrated_sensitivity_and_ancient_dna_boundary_summary.csv"

OUTPUT_COLUMNS = [
    "panel",
    "case",
    "comparator_or_predefined_criterion",
    "observed_result",
    "interpretation_or_limitation",
    "claim_boundary",
]

REGION_ORDER = ["Bosanska Krajina", "Brda / northern Montenegro", "Stari Vlah", "Kosovo"]

DIRECTNESS_LIMITATIONS = {
    "Bosanska Krajina": "The cross-border proxy does not satisfy the same sampling-territory criterion",
    "Brda / northern Montenegro": "The nearby proxy does not satisfy the elevation-matching criterion",
    "Stari Vlah": "No published proxy is identified within the predefined 75-km distance threshold",
    "Kosovo": "The corridor proxy does not satisfy the same sampling-territory criterion",
}

DIRECTNESS_BOUNDARY = (
    "Absence from currently published ancient-DNA sampling is not treated as direct negative evidence "
    "for PH908 in this setting"
)


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


def require_audit(audit_rows: list[dict[str, str]], audit_id: str, observed_value: str) -> None:
    matches = [row for row in audit_rows if row["audit_id"] == audit_id]
    if len(matches) != 1:
        raise ReproducibilityError(f"Missing or duplicated Figure 4 value-validation row: {audit_id}")
    row = matches[0]
    if row["audit_status"] != "Pass" or row["observed_value"] != observed_value:
        raise ReproducibilityError(
            f"Figure 4 value-validation row failed or drifted: {audit_id} observed {row['observed_value']}"
        )


def validate_parent_layers(
    sensitivity_rows: list[dict[str, str]],
    directness_rows: list[dict[str, str]],
    fig4_audit_rows: list[dict[str, str]],
    positive_control_rows: list[dict[str, str]],
) -> None:
    if len(sensitivity_rows) != 10:
        raise ReproducibilityError(f"Adversarial sensitivity row count changed: {len(sensitivity_rows)}")
    if sum(row["weak_directional_compatibility"] == "Yes" for row in sensitivity_rows) != 10:
        raise ReproducibilityError("Weak directional compatibility count changed.")
    if sum(row["matched_R1a_comparator_envelope_entry"] == "Yes" for row in sensitivity_rows) != 0:
        raise ReproducibilityError("Matched R1a-comparator envelope entry count changed.")
    if sum(row["positive_controls_pass"] == "Yes" for row in sensitivity_rows) != 6:
        raise ReproducibilityError("Positive-control-passing adversarial state count changed.")

    require_audit(fig4_audit_rows, "fig4_weak_directional_compatibility_count", "10/10")
    require_audit(fig4_audit_rows, "fig4_matched_envelope_entry_count", "0/10")
    require_audit(fig4_audit_rows, "fig4_positive_control_recovery_count", "6/10")

    if len(positive_control_rows) != 10:
        raise ReproducibilityError(f"Positive-control trace row count changed: {len(positive_control_rows)}")
    passing = [row for row in positive_control_rows if row["positive_controls_pass"] == "Yes"]
    if len(passing) != 6:
        raise ReproducibilityError(f"Positive-control trace pass count changed: {len(passing)}")
    if any(row["R_Z280_expected_source_receiver_state"] != "Recovered" for row in passing):
        raise ReproducibilityError("R-Z280 recovery drifted in positive-control-passing states.")
    if any(row["R_M458_expected_source_receiver_state"] != "Recovered" for row in passing):
        raise ReproducibilityError("R-M458 recovery drifted in positive-control-passing states.")

    observed_regions = [row["region"] for row in directness_rows]
    if observed_regions != REGION_ORDER:
        raise ReproducibilityError(f"Direct-negative-control region order changed: {observed_regions}")
    if any(row["strict_direct_negative_control"] != "No" for row in directness_rows):
        raise ReproducibilityError("At least one direct-negative-control region now passes all criteria.")


def clean_site_name(value: str) -> str:
    text = value.replace(" (Croatia)", "").strip()
    if text == "Zavojane-Ravca, Velika Gomila":
        return "Zavojane-Ravca Velika Gomila"
    if text.startswith("Shkrel"):
        return "Shkrel"
    if text.startswith("Doclea Bjelovine"):
        return "Doclea Bjelovine"
    if text.startswith("Buchinci-Skopje"):
        return "Buchinci-Skopje"
    return text


def generate_rows(
    sensitivity_rows: list[dict[str, str]],
    directness_rows: list[dict[str, str]],
) -> list[dict[str, str]]:
    weak_count = sum(row["weak_directional_compatibility"] == "Yes" for row in sensitivity_rows)
    matched_count = sum(row["matched_R1a_comparator_envelope_entry"] == "Yes" for row in sensitivity_rows)

    rows = [
        {
            "panel": "Adversarial sensitivity",
            "case": "PH908 weak directional compatibility",
            "comparator_or_predefined_criterion": "A_s > 1 and D < 0 under alternative source and receiver masks",
            "observed_result": f"{weak_count} weak directional compatibility states",
            "interpretation_or_limitation": (
                "Alternative masks can produce weak directional compatibility for PH908, but these states are not "
                "treated as load-bearing evidence"
            ),
            "claim_boundary": "Does not support the matched R1a-comparator source-receiver hypothesis for PH908",
        },
        {
            "panel": "Adversarial sensitivity",
            "case": "PH908 matched R1a-comparator envelope test",
            "comparator_or_predefined_criterion": "PH908 reaches the matched state-specific R1a-comparator envelope",
            "observed_result": f"{matched_count} matched-envelope entries",
            "interpretation_or_limitation": (
                "No tested mask configuration places PH908 within the matched state-specific R1a-comparator envelope"
            ),
            "claim_boundary": "Does not identify PH908 origin, continuity, ethnic identity, or an alternative dispersal route",
        },
        {
            "panel": "Adversarial sensitivity",
            "case": "R-Z280 control",
            "comparator_or_predefined_criterion": (
                "Expected source-receiver-compatible states are recovered under the same predefined adversarial "
                "sensitivity procedure"
            ),
            "observed_result": "Recovered",
            "interpretation_or_limitation": "Positive-control comparator recovers the expected source-receiver-compatible state",
            "claim_boundary": (
                "Comparator recovery calibrates the adversarial sensitivity procedure but does not imply an origin "
                "claim for PH908"
            ),
        },
        {
            "panel": "Adversarial sensitivity",
            "case": "R-M458 control",
            "comparator_or_predefined_criterion": (
                "Expected source-receiver-compatible states are recovered under the same predefined adversarial "
                "sensitivity procedure"
            ),
            "observed_result": "Recovered",
            "interpretation_or_limitation": "Positive-control comparator recovers the expected source-receiver-compatible state",
            "claim_boundary": (
                "Comparator recovery calibrates the adversarial sensitivity procedure but does not imply an origin "
                "claim for PH908"
            ),
        },
    ]

    for row in directness_rows:
        region = row["region"]
        rows.append(
            {
                "panel": "Ancient-DNA directness",
                "case": region,
                "comparator_or_predefined_criterion": (
                    "Nearest identified published ancient male-line proxy: "
                    f"{clean_site_name(row['nearest_identified_proxy_site'])}; "
                    f"{row['nearest_identified_proxy_lineage']}; {row['nearest_identified_proxy_km']} km"
                ),
                "observed_result": "Does not satisfy the predefined direct negative-control criteria",
                "interpretation_or_limitation": DIRECTNESS_LIMITATIONS[region],
                "claim_boundary": DIRECTNESS_BOUNDARY,
            }
        )
    return rows


def validate_output(rows: list[dict[str, str]]) -> None:
    if len(rows) != 8:
        raise ReproducibilityError(f"Integrated boundary row count changed: {len(rows)}")
    if [row["panel"] for row in rows].count("Adversarial sensitivity") != 4:
        raise ReproducibilityError("Adversarial sensitivity row count changed.")
    if [row["panel"] for row in rows].count("Ancient-DNA directness") != 4:
        raise ReproducibilityError("Ancient-DNA directness row count changed.")


def compare(generated: list[dict[str, str]], existing_path: Path) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"Integrated boundary table row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        differences = [field for field in OUTPUT_COLUMNS if left.get(field) != right.get(field)]
        if differences:
            raise ReproducibilityError(f"Integrated boundary table mismatch at row {index}: {', '.join(differences[:6])}")
    raise ReproducibilityError("Integrated boundary table mismatch detected.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate the integrated sensitivity and ancient-DNA boundary summary.")
    parser.add_argument("--sensitivity-input", type=Path, default=DEFAULT_SENSITIVITY_INPUT)
    parser.add_argument("--directness-input", type=Path, default=DEFAULT_DIRECTNESS_INPUT)
    parser.add_argument("--fig4-value-validation", type=Path, default=DEFAULT_FIG4_CLAIM_AUDIT)
    parser.add_argument("--positive-control-trace", type=Path, default=DEFAULT_POSITIVE_CONTROL_TRACE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated integrated boundary summary.")
    args = parser.parse_args()

    try:
        sensitivity_rows = read_csv(args.sensitivity_input)
        directness_rows = read_csv(args.directness_input)
        fig4_audit_rows = read_csv(args.fig4_value_validation)
        positive_control_rows = read_csv(args.positive_control_trace)
        validate_parent_layers(sensitivity_rows, directness_rows, fig4_audit_rows, positive_control_rows)

        rows = generate_rows(sensitivity_rows, directness_rows)
        validate_output(rows)
        if args.write:
            write_csv(args.output, OUTPUT_COLUMNS, rows)
        compare(rows, args.output)

        print(f"Integrated boundary rows: {len(rows)}")
        print("Integrated sensitivity and ancient-DNA boundary summary: pass")
        return 0
    except ReproducibilityError as error:
        print("Integrated sensitivity and ancient-DNA boundary summary: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
