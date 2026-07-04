from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "tables"
S1_SOURCE = REPO / "source_data" / "supplementary_figure_s1"

DEFAULT_BENCHMARK_INPUT = TABLES / "26_benchmark_audit_card_matrix.csv"
DEFAULT_BRANCH_INPUT = TABLES / "11_branch_unit_reliability_pass_matrix.csv"
DEFAULT_HIGHLIGHT_INPUT = TABLES / "13_source_receiver_highlight_contracts.csv"
DEFAULT_ROLE_INPUT = TABLES / "02_lineage_role_tiers.csv"
DEFAULT_SOURCE_LAYER_INPUT = TABLES / "04_source_layers_and_headline_coordinates.csv"
DEFAULT_INTEGRATED_BOUNDARY_INPUT = TABLES / "10_integrated_sensitivity_and_ancient_dna_boundary_summary.csv"
DEFAULT_S1_COMPLETION_INPUT = S1_SOURCE / "s1_18_supplementary_figure_s1_completion_audit.csv"

DEFAULT_MODEL_SUMMARY_OUTPUT = TABLES / "01_model_test_summary.csv"
DEFAULT_MAIN_TABLE_OUTPUT = TABLES / "main_table_1_source_receiver_audit_cards.csv"

MODEL_SUMMARY_COLUMNS = ["card", "model_tested", "result", "confidence", "interpretation", "limitations"]

MAIN_TABLE_COLUMNS = [
    "section",
    "display_order",
    "audit_card",
    "lineage_root",
    "evidence_role",
    "source_mask",
    "receiver_mask",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "A_s",
    "D",
    "branch_unit_status",
    "perturbation_rarefaction_or_sensitivity_status",
    "final_state",
    "reported_use",
    "claim_boundary",
    "source_files",
]

QUANTIFIED_ORDER = ["R-Z280", "R-M458", "PH908", "E-M81", "J-P58", "O-M119", "O-M122"]
BOUNDARY_ORDER = ["H-M82", "E-M2"]

BRANCH_STATUS = {
    "R-Z280": "Pass across evaluated branch-unit layers",
    "R-M458": "Pass with branch-scale sensitivity",
    "PH908": "Fail across evaluated branch-unit layers",
    "E-M81": "Scale-sensitive support",
    "J-P58": "Pass with bounded branch-scale sensitivity",
    "O-M119": "Deepest-layer pass but nondeep failures",
    "O-M122": "Scale-sensitive with multiple nondeep failures",
}

PERTURBATION_STATUS = {
    "R-Z280": "Stable comparator under the benchmark matrix; high-common-n equal-n rarefaction support is reported in Supplementary Table S5",
    "R-M458": "Scale-sensitive but retained as compatible matched comparator; high-common-n equal-n rarefaction support is reported in Supplementary Table S5",
    "PH908": "Rejected under the matched comparator framework",
    "E-M81": "Compatibility depends on branch resolution and is not promoted as universal validation",
    "J-P58": "Retained only within the stated J-M267/J1 context",
    "O-M119": "Demoted because broad-label compatibility fails branch-unit reliability checks",
    "O-M122": "Demoted because compatibility outside the main comparison set is branch-scale sensitive",
}

FINAL_STATE = {
    "R-Z280": "Compatible state; load-bearing matched comparator",
    "R-M458": "Compatible state with branch-scale caveat",
    "PH908": "Stable model rejection",
    "E-M81": "Supporting compatible state; scale-sensitive",
    "J-P58": "Supporting compatible state within J-M267/J1 context",
    "O-M119": "Fragile/support-only state",
    "O-M122": "Fragile/support-only state",
}

REPORTED_USE_OVERRIDE = {
    "PH908": "Tests whether PH908 enters the predefined matched R1a-comparator envelope; it does not",
}

EVIDENCE_ROLE = {
    "R-Z280": "Matched R1a positive comparator",
    "R-M458": "Matched R1a positive comparator",
    "PH908": "Held-out target application",
    "E-M81": "Supporting non-target comparison",
    "J-P58": "Supporting non-target comparison",
    "O-M119": "Support-only diagnostic card",
    "O-M122": "Support-only diagnostic card",
}

SUMMARY_ROWS = [
    {
        "card": "R-Z280/R-M458",
        "model_tested": "Eastern Europe/Russia-to-Balkans source-adequacy model tested using matched R1a comparator lineages",
        "result": "Supported",
        "confidence": "High",
        "interpretation": (
            "The R1a comparator lineages recover the expected source-adequacy signal and lower diversity in the "
            "inferred receiving region, consistent with the specified Eastern Europe/Russia-to-Balkans "
            "source-adequacy model."
        ),
        "limitations": (
            "This result calibrates the test against the selected R1a comparator lineages only. It does not "
            "validate PH908, identify an exact historical source, or warrant inference about ethnic identity."
        ),
    },
    {
        "card": "PH908",
        "model_tested": "Eastern Europe/Russia-to-Balkans source-adequacy model tested in PH908",
        "result": "Not supported",
        "confidence": "High",
        "interpretation": (
            "PH908 does not meet the predefined source-adequacy threshold and does not reproduce the lower "
            "receiving-region diversity pattern observed in the matched R1a comparator lineages."
        ),
        "limitations": (
            "This result does not support the R1a-comparator source-adequacy model for PH908. It does not "
            "determine PH908 origin, chronology, population continuity, ethnic identity, or a specific "
            "alternative dispersal route."
        ),
    },
    {
        "card": "E-M81",
        "model_tested": "North Africa/Maghreb source model evaluated with an external-source comparison",
        "result": "Supported",
        "confidence": "Moderate",
        "interpretation": (
            "E-M81 is consistent with a North Africa/Maghreb source model in layers with sufficient statistical "
            "power, although support is weaker in the external-source comparison."
        ),
        "limitations": (
            "This is a supporting non-target comparison. It does not validate all E lineages, all Maghreb source "
            "models, or unrestricted transfer of the method to other phylogenetic contexts."
        ),
    },
    {
        "card": "J-P58",
        "model_tested": "West Asia/Arabia-to-North Africa source model evaluated within the J-M267/J1 phylogenetic context",
        "result": "Supported",
        "confidence": "Moderate",
        "interpretation": (
            "J-P58 meets the predefined source-adequacy criteria and shows lower diversity in the inferred "
            "receiving region under the specified focused model."
        ),
        "limitations": (
            "This result applies to J-P58 within its stated phylogenetic context. It does not generalize to "
            "J-M267/J1 as a whole or validate unrestricted source inference."
        ),
    },
    {
        "card": "O-M119/O-M122",
        "model_tested": "East Asia-to-Southeast Asia and East Asia-to-Oceania comparison models",
        "result": "Inconclusive",
        "confidence": "Low",
        "interpretation": (
            "The O-lineage comparisons show source-compatible patterns at broad public labels but reduced "
            "reliability when terminal branches are aggregated into broader units."
        ),
        "limitations": (
            "These comparisons provide diagnostic support only. They should not be interpreted as primary evidence "
            "for method portability outside the main E, J and R comparison set."
        ),
    },
    {
        "card": "H-M82/E-M2",
        "model_tested": "South Asia-to-Roma diaspora and West Africa-to-Americas comparison models",
        "result": "Inconclusive",
        "confidence": "Low",
        "interpretation": (
            "Current public phylogenetic visibility and branch resolution are insufficient to support a primary "
            "decision in these diasporic and source-visibility contexts."
        ),
        "limitations": (
            "These tests illustrate boundary conditions for the method's applicability in diasporic and "
            "source-visibility contexts. They should not be interpreted as validation successes or as "
            "source/receiver origin assignments."
        ),
    },
    {
        "card": "FTDNA Discover direct-child layer",
        "model_tested": "Public direct-child source-adequacy comparison for PH908 and the R1a comparators",
        "result": "Supported",
        "confidence": "Moderate",
        "interpretation": (
            "The public direct-child layer provides a secondary consistency check for the source-adequacy contrast "
            "between PH908 and the R1a comparators."
        ),
        "limitations": (
            "This evidence is limited to public direct-child structure and is not a full replication of "
            "terminal-branch diversity; it should not be treated as an independent substitute for the "
            "YFull-based test."
        ),
    },
    {
        "card": "Ancient-DNA directness audit",
        "model_tested": "Published pre-550 CE ancient-DNA sampling compared with PH908 branch-derived expectations",
        "result": "Inconclusive",
        "confidence": "Moderate",
        "interpretation": (
            "Published pre-550 CE ancient-DNA sampling is currently insufficiently direct to reject the PH908 "
            "branch-derived expectation."
        ),
        "limitations": (
            "This is a sampling-boundary result. It should not be interpreted as positive ancient-DNA evidence for "
            "PH908 and does not establish population continuity or geographic origin."
        ),
    },
]

BOUNDARY_MAIN_ROWS = {
    "H-M82": {
        "source_mask": "South Asia",
        "receiver_mask": "Roma diaspora / Europe",
        "perturbation": "Diaspora/founder structure and source-receiver independence limits prevent primary scoring",
        "reported_use": "Demonstrates abstention when the framework should not force a source-receiver decision",
    },
    "E-M2": {
        "source_mask": "West Africa",
        "receiver_mask": "Americas / diaspora receiver",
        "perturbation": "Diaspora structure and source-visibility limits prevent primary scoring",
        "reported_use": (
            "Demonstrates abstention when source visibility or diaspora receiver structure makes a primary decision unsafe"
        ),
    },
}


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


def by_key(rows: list[dict[str, str]], key: str) -> dict[str, dict[str, str]]:
    result = {}
    for row in rows:
        value = row[key]
        if value in result:
            raise ReproducibilityError(f"Duplicate {key} value: {value}")
        result[value] = row
    return result


def validate_parent_layers(
    benchmark_rows: list[dict[str, str]],
    branch_rows: list[dict[str, str]],
    highlight_rows: list[dict[str, str]],
    role_rows: list[dict[str, str]],
    source_layer_rows: list[dict[str, str]],
    integrated_rows: list[dict[str, str]],
    s1_completion_rows: list[dict[str, str]],
) -> None:
    benchmark = by_key(benchmark_rows, "audit_card")
    missing = set(QUANTIFIED_ORDER) - set(benchmark)
    if missing:
        raise ReproducibilityError(f"Benchmark matrix lacks quantified Table 1 cards: {sorted(missing)}")
    if len(benchmark_rows) != 7:
        raise ReproducibilityError(f"Benchmark matrix row count changed: {len(benchmark_rows)}")

    branch_cards = {row["audit_card"] for row in branch_rows}
    highlight_roots = {row["lineage_root"] for row in highlight_rows}
    for card in QUANTIFIED_ORDER:
        row = benchmark[card]
        if card not in branch_cards:
            raise ReproducibilityError(f"Branch-unit matrix lacks audit card: {card}")
        if row["lineage_root"] not in highlight_roots:
            raise ReproducibilityError(f"Highlight contracts lack lineage root: {row['lineage_root']}")

    if benchmark["R-Z280"]["deepest_source_receiver_call"] != "Compatible":
        raise ReproducibilityError("R-Z280 comparator state drifted.")
    if benchmark["R-M458"]["deepest_source_receiver_call"] != "Compatible":
        raise ReproducibilityError("R-M458 comparator state drifted.")
    if benchmark["PH908"]["deepest_source_receiver_call"] != "Rejected":
        raise ReproducibilityError("PH908 rejection state drifted.")
    if float(benchmark["PH908"]["deepest_source_adequacy_A_s"]) >= 1:
        raise ReproducibilityError("PH908 source adequacy no longer falls below the source-adequacy threshold.")
    if float(benchmark["PH908"]["deepest_diversity_contrast_D"]) <= 0:
        raise ReproducibilityError("PH908 diversity contrast no longer has the expected rejection sign.")

    role_names = {row["lineage_or_group"] for row in role_rows}
    if "H-M82" not in role_names or "E-M2" not in role_names:
        raise ReproducibilityError("Boundary/no-call role rows for H-M82 and E-M2 are required.")

    ftdna_rows = [
        row
        for row in source_layer_rows
        if row["section"] == "Headline coordinate" and row["context"].startswith("FTDNA Discover bounded comparison")
    ]
    if len(ftdna_rows) != 3:
        raise ReproducibilityError(f"FTDNA Discover bounded comparison row count changed: {len(ftdna_rows)}")
    ftdna_by_item = by_key(ftdna_rows, "item")
    if float(ftdna_by_item["I-PH908"]["source-adequacy_A_s"]) >= 1:
        raise ReproducibilityError("FTDNA PH908 source adequacy boundary changed.")
    if float(ftdna_by_item["R-Z280"]["source-adequacy_A_s"]) <= 1:
        raise ReproducibilityError("FTDNA R-Z280 source adequacy boundary changed.")
    if float(ftdna_by_item["R-M458"]["source-adequacy_A_s"]) <= 1:
        raise ReproducibilityError("FTDNA R-M458 source adequacy boundary changed.")

    ancient_rows = [row for row in integrated_rows if row["panel"] == "Ancient-DNA directness"]
    if len(ancient_rows) != 4:
        raise ReproducibilityError(f"Integrated ancient-DNA boundary row count changed: {len(ancient_rows)}")
    if any("Does not satisfy" not in row["observed_result"] for row in ancient_rows):
        raise ReproducibilityError("Ancient-DNA directness state changed.")

    completion_by_requirement = by_key(s1_completion_rows, "requirement_number")
    if completion_by_requirement["8"]["audit_status"] != "Pass":
        raise ReproducibilityError("S1 regional directness completion audit is not passing.")
    if completion_by_requirement["9"]["audit_status"] != "Pass":
        raise ReproducibilityError("S1 elevation visibility completion audit is not passing.")


def generate_main_table(benchmark_rows: list[dict[str, str]], role_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    benchmark = by_key(benchmark_rows, "audit_card")
    rows = []
    for index, card in enumerate(QUANTIFIED_ORDER, start=1):
        source = benchmark[card]
        audit_card = "I2a-PH908" if card == "PH908" else card
        rows.append(
            {
                "section": "Table 1A quantified audit cards",
                "display_order": f"{index:02d}",
                "audit_card": audit_card,
                "lineage_root": source["lineage_root"],
                "evidence_role": EVIDENCE_ROLE[card],
                "source_mask": source["source_mask"],
                "receiver_mask": source["receiver_mask"],
                "source_terminal_count": source["source_terminal_count"],
                "receiver_terminal_count": source["receiver_terminal_count"],
                "source_country_count": source["source_country_count"],
                "receiver_country_count": source["receiver_country_count"],
                "A_s": source["deepest_source_adequacy_A_s"],
                "D": source["deepest_diversity_contrast_D"],
                "branch_unit_status": BRANCH_STATUS[card],
                "perturbation_rarefaction_or_sensitivity_status": PERTURBATION_STATUS[card],
                "final_state": FINAL_STATE[card],
                "reported_use": REPORTED_USE_OVERRIDE.get(card, source["reported_use"]),
                "claim_boundary": source["claim_boundary"],
                "source_files": "tables/26_benchmark_audit_card_matrix.csv; "
                "tables/11_branch_unit_reliability_pass_matrix.csv; "
                "tables/13_source_receiver_highlight_contracts.csv; "
                "tables/27_figure_4_sensitivity_design_denominator_matrix.csv",
            }
        )

    role_lookup = by_key(role_rows, "lineage_or_group")
    for index, card in enumerate(BOUNDARY_ORDER, start=8):
        if card not in role_lookup:
            raise ReproducibilityError(f"Missing boundary role row: {card}")
        boundary = BOUNDARY_MAIN_ROWS[card]
        rows.append(
            {
                "section": "Table 1B boundary/no-call audit cards",
                "display_order": f"{index:02d}",
                "audit_card": card,
                "lineage_root": card,
                "evidence_role": "Boundary/no-call card",
                "source_mask": boundary["source_mask"],
                "receiver_mask": boundary["receiver_mask"],
                "source_terminal_count": "not_scoreable",
                "receiver_terminal_count": "not_scoreable",
                "source_country_count": "not_scoreable",
                "receiver_country_count": "not_scoreable",
                "A_s": "not_scoreable",
                "D": "not_scoreable",
                "branch_unit_status": "Not scoreable as a load-bearing source-receiver contrast",
                "perturbation_rarefaction_or_sensitivity_status": boundary["perturbation"],
                "final_state": "Boundary/no-call",
                "reported_use": boundary["reported_use"],
                "claim_boundary": "No-call status is not positive evidence and not direct negative evidence for absence or origin",
                "source_files": "tables/02_lineage_role_tiers.csv; tables/01_model_test_summary.csv",
            }
        )
    return rows


def generate_model_summary() -> list[dict[str, str]]:
    return [dict(row) for row in SUMMARY_ROWS]


def validate_outputs(model_rows: list[dict[str, str]], main_rows: list[dict[str, str]]) -> None:
    if len(model_rows) != 8:
        raise ReproducibilityError(f"Model summary row count changed: {len(model_rows)}")
    if len(main_rows) != 9:
        raise ReproducibilityError(f"Main Table 1 row count changed: {len(main_rows)}")
    result_counts = {result: sum(row["result"] == result for row in model_rows) for result in {"Supported", "Not supported", "Inconclusive"}}
    if result_counts != {"Supported": 4, "Not supported": 1, "Inconclusive": 3}:
        raise ReproducibilityError(f"Model summary result counts changed: {result_counts}")
    if [row["audit_card"] for row in main_rows[:7]] != ["R-Z280", "R-M458", "I2a-PH908", "E-M81", "J-P58", "O-M119", "O-M122"]:
        raise ReproducibilityError("Main Table 1 quantified-card order changed.")


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


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Table 1 source-receiver audit summaries.")
    parser.add_argument("--benchmark-input", type=Path, default=DEFAULT_BENCHMARK_INPUT)
    parser.add_argument("--branch-input", type=Path, default=DEFAULT_BRANCH_INPUT)
    parser.add_argument("--highlight-input", type=Path, default=DEFAULT_HIGHLIGHT_INPUT)
    parser.add_argument("--role-input", type=Path, default=DEFAULT_ROLE_INPUT)
    parser.add_argument("--source-layer-input", type=Path, default=DEFAULT_SOURCE_LAYER_INPUT)
    parser.add_argument("--integrated-boundary-input", type=Path, default=DEFAULT_INTEGRATED_BOUNDARY_INPUT)
    parser.add_argument("--s1-completion-input", type=Path, default=DEFAULT_S1_COMPLETION_INPUT)
    parser.add_argument("--model-summary-output", type=Path, default=DEFAULT_MODEL_SUMMARY_OUTPUT)
    parser.add_argument("--main-table-output", type=Path, default=DEFAULT_MAIN_TABLE_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated Table 1 outputs.")
    args = parser.parse_args()

    try:
        benchmark_rows = read_csv(args.benchmark_input)
        branch_rows = read_csv(args.branch_input)
        highlight_rows = read_csv(args.highlight_input)
        role_rows = read_csv(args.role_input)
        source_layer_rows = read_csv(args.source_layer_input)
        integrated_rows = read_csv(args.integrated_boundary_input)
        s1_completion_rows = read_csv(args.s1_completion_input)

        validate_parent_layers(
            benchmark_rows,
            branch_rows,
            highlight_rows,
            role_rows,
            source_layer_rows,
            integrated_rows,
            s1_completion_rows,
        )
        model_rows = generate_model_summary()
        main_rows = generate_main_table(benchmark_rows, role_rows)
        validate_outputs(model_rows, main_rows)

        if args.write:
            write_csv(args.model_summary_output, MODEL_SUMMARY_COLUMNS, model_rows)
            write_csv(args.main_table_output, MAIN_TABLE_COLUMNS, main_rows)

        compare(model_rows, args.model_summary_output, MODEL_SUMMARY_COLUMNS, "Table 1 model-test summary")
        compare(main_rows, args.main_table_output, MAIN_TABLE_COLUMNS, "Main Table 1 audit-card matrix")

        print(f"Table 1 model summary rows: {len(model_rows)}")
        print(f"Main Table 1 audit-card rows: {len(main_rows)}")
        print("Main source-receiver audit-card summaries: pass")
        return 0
    except ReproducibilityError as error:
        print("Main source-receiver audit-card summaries: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
