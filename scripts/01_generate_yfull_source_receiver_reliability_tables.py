from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]

DEFAULT_ATLAS_INPUT = REPO / "source_data" / "core_yfull" / "source_receiver_reliability_atlas.csv"
DEFAULT_HIGHLIGHT_INPUT = REPO / "source_data" / "core_yfull" / "source_receiver_highlight_contracts.csv"
DEFAULT_ATLAS_OUTPUT = REPO / "tables" / "14_yfull_reliability_atlas_background.csv"
DEFAULT_HIGHLIGHT_OUTPUT = REPO / "tables" / "13_source_receiver_highlight_contracts.csv"


ATLAS_COLUMNS = [
    "lineage_root",
    "source_mask",
    "receiver_mask",
    "source_terminal_count",
    "receiver_terminal_count",
    "source_country_count",
    "receiver_country_count",
    "source_branch_count",
    "receiver_branch_count",
    "deepest_source_adequacy_A_s",
    "deepest_diversity_contrast_D",
    "deepest_source_receiver_call",
    "source_receiver_reliability_score",
    "atlas_reliability_state",
    "figure_source_file",
]

HIGHLIGHT_COLUMNS = [
    "focused_contract",
    "lineage_root",
    "source_mask",
    "receiver_mask",
    "region_mask_rule",
    "coordinate_layer",
    "deepest_source_adequacy_A_s",
    "deepest_diversity_contrast_D",
    "deepest_source_receiver_call",
    "nondeep_scoreable_layer_count",
    "call_flip_rate",
    "diversity_contrast_sign_flip_rate",
    "source_adequacy_gate_flip_rate",
    "scaled_diversity_contrast_range",
    "scoreability_penalty",
    "source_receiver_reliability_score",
    "atlas_display_class",
    "atlas_display_note",
    "figure_source_file",
]

REGION_LABELS = {
    "americas_indigenous_relevant": "Americas Indigenous-relevant",
    "arabia": "Arabia/West Asia",
    "balkan": "Balkans",
    "caribbean": "Caribbean",
    "central_africa": "Central Africa",
    "central_asia": "Central Asia",
    "east_africa": "East Africa",
    "east_asia": "East Asia",
    "east_europe": "Eastern Europe",
    "east_europe;east_europe_plus_russia": "Eastern Europe/Russia",
    "north_africa": "North Africa/Maghreb",
    "north_america": "North America",
    "north_europe": "Northern Europe",
    "northeast_africa": "Northeast Africa",
    "pacific_oceania": "Pacific/Oceania",
    "south_america": "South America",
    "south_asia": "South Asia",
    "southeast_asia": "Southeast Asia",
    "southern_africa": "Southern Africa",
    "west_africa": "West Africa",
    "west_asia": "West Asia",
    "west_europe": "Western Europe",
}

RELIABILITY_STATE_LABELS = {
    "broad-root deferred": "Broad-root deferred",
    "fragile or scale-sensitive": "Fragile or scale-sensitive",
    "no-call or underpowered": "No-call or underpowered",
    "robust compatible": "Robust source-receiver compatible",
    "robust rejection": "Robust source-receiver rejection",
    "stable rejection, scale-sensitive D": "Stable source-receiver rejection with scale-sensitive D",
}

REGION_RULE_LABELS = {
    "focused_fine_region": "Focused fine-region mask",
    "focused_rollup_region": "Focused roll-up region mask",
}

COORDINATE_LAYER_LABELS = {
    "focused_predeclared_contract": "Focused predeclared contract",
}

HIGHLIGHT_CONTRACT_LABELS = {
    "E_M81_NORTH_AFRICA_TO_WEST_EUROPE": "E-M81 North Africa/Maghreb-to-Western Europe supporting comparison",
    "J_P58_ARABIA_TO_NORTH_AFRICA": "J-P58 Arabia/West Asia-to-North Africa supporting comparison",
    "O_M119_EAST_ASIA_TO_SE_ASIA": "O-M119 East Asia-to-Southeast Asia support-only diagnostic",
    "O_M122_EAST_ASIA_TO_SE_ASIA": "O-M122 East Asia-to-Southeast Asia support-only diagnostic",
    "PH908_EE_RUSSIA_TO_BALKAN": "I-PH908 Eastern Europe/Russia-to-Balkans held-out test",
    "R_M458_EE_RUSSIA_TO_BALKAN": "R-M458 Eastern Europe/Russia-to-Balkans matched comparator",
    "R_Z280_EE_RUSSIA_TO_BALKAN": "R-Z280 Eastern Europe/Russia-to-Balkans matched comparator",
}

HIGHLIGHT_DISPLAY_LABELS = {
    "E_M81_NORTH_AFRICA_TO_WEST_EUROPE": "Supporting non-target comparison; scale-sensitive",
    "J_P58_ARABIA_TO_NORTH_AFRICA": "Supporting non-target comparison; scale-sensitive",
    "O_M119_EAST_ASIA_TO_SE_ASIA": "Support-only fragile diagnostic",
    "O_M122_EAST_ASIA_TO_SE_ASIA": "Support-only fragile diagnostic",
    "PH908_EE_RUSSIA_TO_BALKAN": "Stable rejection of the specified source-receiver hypothesis; scale-sensitive D",
    "R_M458_EE_RUSSIA_TO_BALKAN": "Source-receiver-compatible comparator; scale-sensitive",
    "R_Z280_EE_RUSSIA_TO_BALKAN": "Robust source-receiver-compatible comparator",
}


class ReproducibilityError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ReproducibilityError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decimal_6(value: str) -> str:
    return str(Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def label(mapping: dict[str, str], value: str, field: str) -> str:
    if value not in mapping:
        raise ReproducibilityError(f"Unrecognized {field}: {value}")
    return mapping[value]


def deepest_call(value: str, atlas: bool) -> str:
    if value == "True":
        return "Compatible at deepest layer" if atlas else "Compatible"
    if value == "False":
        return "Rejected at deepest layer" if atlas else "Rejected"
    raise ReproducibilityError(f"Unrecognized deepest-call value: {value}")


def generate_atlas_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    for row in read_csv(path):
        rows.append(
            {
                "lineage_root": row["root"],
                "source_mask": label(REGION_LABELS, row["source_region"], "source region"),
                "receiver_mask": label(REGION_LABELS, row["receiver_region"], "receiver region"),
                "source_terminal_count": row["source_n"],
                "receiver_terminal_count": row["receiver_n"],
                "source_country_count": row["source_country_count"],
                "receiver_country_count": row["receiver_country_count"],
                "source_branch_count": row["source_branch_count"],
                "receiver_branch_count": row["receiver_branch_count"],
                "deepest_source_adequacy_A_s": decimal_6(row["deepest_A_s"]),
                "deepest_diversity_contrast_D": decimal_6(row["deepest_D"]),
                "deepest_source_receiver_call": deepest_call(row["deepest_call"], atlas=True),
                "source_receiver_reliability_score": decimal_6(row["source_receiver_reliability_score"]),
                "atlas_reliability_state": label(RELIABILITY_STATE_LABELS, row["display_class"], "reliability state"),
                "figure_source_file": "source_receiver_reliability_atlas.csv",
            }
        )
    return rows


def generate_highlight_rows(path: Path) -> list[dict[str, str]]:
    rows = []
    for row in read_csv(path):
        contract = row["contract"]
        rows.append(
            {
                "focused_contract": label(HIGHLIGHT_CONTRACT_LABELS, contract, "focused contract"),
                "lineage_root": row["root"],
                "source_mask": label(REGION_LABELS, row["source_region"], "source region"),
                "receiver_mask": label(REGION_LABELS, row["receiver_region"], "receiver region"),
                "region_mask_rule": label(REGION_RULE_LABELS, row["region_rule"], "region rule"),
                "coordinate_layer": label(COORDINATE_LAYER_LABELS, row["coordinate_layer"], "coordinate layer"),
                "deepest_source_adequacy_A_s": decimal_6(row["deepest_A_s"]),
                "deepest_diversity_contrast_D": decimal_6(row["deepest_D"]),
                "deepest_source_receiver_call": deepest_call(row["deepest_call"], atlas=False),
                "nondeep_scoreable_layer_count": row["nondeep_scoreable_count"],
                "call_flip_rate": decimal_6(row["call_flip_rate"]),
                "diversity_contrast_sign_flip_rate": decimal_6(row["D_sign_flip_rate"]),
                "source_adequacy_gate_flip_rate": decimal_6(row["A_gate_flip_rate"]),
                "scaled_diversity_contrast_range": decimal_6(row["D_range_scaled"]),
                "scoreability_penalty": decimal_6(row["scoreability_penalty"]),
                "source_receiver_reliability_score": decimal_6(row["source_receiver_reliability_score"]),
                "atlas_display_class": label(HIGHLIGHT_DISPLAY_LABELS, contract, "display class"),
                "atlas_display_note": "Overlaid on broad atlas for reliability context",
                "figure_source_file": "source_receiver_highlight_contracts.csv",
            }
        )
    return rows


def compare(label_name: str, generated: list[dict[str, str]], existing_path: Path) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"{label_name} row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        if left != right:
            fields = sorted(set(left) | set(right))
            differences = [field for field in fields if left.get(field) != right.get(field)]
            shown = ", ".join(differences[:5])
            raise ReproducibilityError(f"{label_name} mismatch at row {index}: {shown}")
    raise ReproducibilityError(f"{label_name} mismatch detected")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate repository YFull source-receiver reliability tables from audited upstream inputs."
    )
    parser.add_argument("--atlas-input", type=Path, default=DEFAULT_ATLAS_INPUT)
    parser.add_argument("--highlight-input", type=Path, default=DEFAULT_HIGHLIGHT_INPUT)
    parser.add_argument("--atlas-output", type=Path, default=DEFAULT_ATLAS_OUTPUT)
    parser.add_argument("--highlight-output", type=Path, default=DEFAULT_HIGHLIGHT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated tables to the output paths.")
    args = parser.parse_args()

    try:
        atlas_rows = generate_atlas_rows(args.atlas_input)
        highlight_rows = generate_highlight_rows(args.highlight_input)

        if args.write:
            write_csv(args.atlas_output, ATLAS_COLUMNS, atlas_rows)
            write_csv(args.highlight_output, HIGHLIGHT_COLUMNS, highlight_rows)

        compare("YFull atlas background table", atlas_rows, args.atlas_output)
        compare("Highlighted focused-contract table", highlight_rows, args.highlight_output)

        print(f"YFull atlas background rows: {len(atlas_rows)}")
        print(f"Highlighted focused-contract rows: {len(highlight_rows)}")
        print("Core YFull source-receiver reliability tables: pass")
        return 0
    except ReproducibilityError as error:
        print("Core YFull source-receiver reliability tables: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
