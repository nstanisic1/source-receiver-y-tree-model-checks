from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
TABLES = REPO / "tables"

DEFAULT_BENCHMARK_INPUT = TABLES / "26_benchmark_audit_card_matrix.csv"
DEFAULT_OUTPUT = TABLES / "33_source_receiver_mask_country_membership_and_boundary_rules.csv"

SOURCE_TRACE = (
    "tables/26_benchmark_audit_card_matrix.csv; "
    "source_data/core_yfull/source_receiver_highlight_contracts.csv; "
    "audited country-code recode used for the core YFull source bundle"
)

OUTPUT_COLUMNS = [
    "section",
    "display_order",
    "contract_id",
    "audit_card",
    "lineage_root",
    "evidence_role",
    "mask_role",
    "mask_label",
    "region_rule",
    "region_values",
    "country_code",
    "country_code_status",
    "reported_use",
    "source_trace",
    "claim_boundary",
]

CONTRACTS = [
    {
        "contract_id": "R_Z280_EE_RUSSIA_TO_BALKAN",
        "audit_card": "R-Z280",
        "lineage_root": "R-Z280",
        "evidence_role": "Matched R1a positive comparator",
        "source_label": "Eastern Europe/Russia",
        "receiver_label": "Balkans",
        "source_rule": "Focused roll-up region mask",
        "receiver_rule": "Focused roll-up region mask",
        "source_values": "east_europe;east_europe_plus_russia",
        "receiver_values": "balkan",
        "source_codes": ["BLR", "CZE", "EST", "HUN", "LTU", "LVA", "MDA", "POL", "RUS", "SVK", "UKR"],
        "receiver_codes": ["ALB", "BGR", "BIH", "GRC", "HRV", "MNE", "ROU", "SRB", "SVN"],
        "reported_use": "Defines the positive matched-comparator envelope for the held-out PH908 application.",
    },
    {
        "contract_id": "R_M458_EE_RUSSIA_TO_BALKAN",
        "audit_card": "R-M458",
        "lineage_root": "R-M458",
        "evidence_role": "Matched R1a positive comparator",
        "source_label": "Eastern Europe/Russia",
        "receiver_label": "Balkans",
        "source_rule": "Focused roll-up region mask",
        "receiver_rule": "Focused roll-up region mask",
        "source_values": "east_europe;east_europe_plus_russia",
        "receiver_values": "balkan",
        "source_codes": ["BLR", "CZE", "EST", "HUN", "LTU", "LVA", "MDA", "POL", "RUS", "SVK", "UKR"],
        "receiver_codes": ["ALB", "BGR", "BIH", "GRC", "HRV", "MKD", "MNE", "ROU", "SRB", "SVN"],
        "reported_use": "Calibrates the positive matched-comparator envelope while exposing branch-scale sensitivity.",
    },
    {
        "contract_id": "PH908_EE_RUSSIA_TO_BALKAN",
        "audit_card": "PH908",
        "lineage_root": "I-PH908",
        "evidence_role": "Held-out target application",
        "source_label": "Eastern Europe/Russia",
        "receiver_label": "Balkans",
        "source_rule": "Focused roll-up region mask",
        "receiver_rule": "Focused roll-up region mask",
        "source_values": "east_europe;east_europe_plus_russia",
        "receiver_values": "balkan",
        "source_codes": ["BLR", "CZE", "HUN", "LTU", "MDA", "POL", "RUS", "SVK", "UKR"],
        "receiver_codes": ["ALB", "BGR", "BIH", "GRC", "HRV", "MKD", "MNE", "ROU", "SRB"],
        "reported_use": "Tests whether PH908 enters the predefined matched R1a-comparator envelope; it does not.",
    },
    {
        "contract_id": "E_M81_NORTH_AFRICA_TO_WEST_EUROPE",
        "audit_card": "E-M81",
        "lineage_root": "E-M81",
        "evidence_role": "Supporting non-target comparison",
        "source_label": "North Africa/Maghreb",
        "receiver_label": "Western Europe",
        "source_rule": "Focused roll-up region mask",
        "receiver_rule": "Focused roll-up region mask",
        "source_values": "north_africa",
        "receiver_values": "west_europe",
        "source_codes": ["DZA", "EGY", "ESH", "LBY", "MAR", "MRT", "TUN"],
        "receiver_codes": ["BEL", "DEU", "ENG", "ESP", "FRA", "GBR", "IRL", "ITA", "PRT", "SCT"],
        "reported_use": "Provides a supporting non-target comparison under an independent source-receiver context.",
    },
    {
        "contract_id": "J_P58_ARABIA_TO_NORTH_AFRICA",
        "audit_card": "J-P58",
        "lineage_root": "J-P58",
        "evidence_role": "Supporting non-target comparison",
        "source_label": "Arabia/West Asia",
        "receiver_label": "North Africa/Maghreb",
        "source_rule": "Focused fine-region mask",
        "receiver_rule": "Focused fine-region mask",
        "source_values": "arabia",
        "receiver_values": "north_africa",
        "source_codes": ["BHR", "KWT", "OMN", "QAT", "SAU", "UAE", "YEM"],
        "receiver_codes": ["DZA", "EGY", "LBY", "MAR", "MRT", "TUN"],
        "reported_use": "Provides a supporting non-target comparison within the stated J-M267/J1 context.",
    },
    {
        "contract_id": "O_M119_EAST_ASIA_TO_SE_ASIA",
        "audit_card": "O-M119",
        "lineage_root": "O-M119",
        "evidence_role": "Support-only diagnostic card",
        "source_label": "East Asia",
        "receiver_label": "Southeast Asia",
        "source_rule": "Focused roll-up region mask",
        "receiver_rule": "Focused roll-up region mask",
        "source_values": "east_asia",
        "receiver_values": "southeast_asia;island_southeast_asia",
        "source_codes": ["CHN", "HKG", "KOR", "MAC"],
        "receiver_codes": ["IDN", "KHM", "MYS", "PHL", "SGP", "THA", "TWN", "VNM"],
        "reported_use": "Demonstrates demotion of deepest-layer compatibility when branch-unit checks do not support promotion.",
    },
    {
        "contract_id": "O_M122_EAST_ASIA_TO_SE_ASIA",
        "audit_card": "O-M122",
        "lineage_root": "O-M122",
        "evidence_role": "Support-only diagnostic card",
        "source_label": "East Asia",
        "receiver_label": "Southeast Asia",
        "source_rule": "Focused roll-up region mask",
        "receiver_rule": "Focused roll-up region mask",
        "source_values": "east_asia",
        "receiver_values": "southeast_asia;island_southeast_asia",
        "source_codes": ["CHN", "JPN", "KOR", "MNG", "PRK"],
        "receiver_codes": ["IDN", "KHM", "MMR", "MYS", "PHL", "SGP", "THA", "TWN", "VNM"],
        "reported_use": "Demonstrates demotion of deepest-layer compatibility when branch-unit checks do not support promotion.",
    },
]

AMBIGUOUS_COUNTRY_RULES = {
    "AUS": "Modern diaspora-heavy and Oceania-adjacent country code.",
    "AZE": "Caucasus and West Asia boundary country code.",
    "CAN": "Modern diaspora-heavy country code.",
    "CYP": "Mediterranean and West Asia boundary country code.",
    "EGY": "North Africa, Northeast Africa and West Asia boundary country code.",
    "GEO": "Caucasus and West Asia boundary country code.",
    "IDN": "Island Southeast Asia and Oceania-adjacent boundary country code.",
    "KAZ": "Europe-adjacent steppe and Central Asia boundary country code.",
    "NZL": "Modern diaspora-heavy and Pacific-adjacent country code.",
    "RUS": "Country-level Russia cannot distinguish European Russia from Siberia or North Asia.",
    "TUR": "Europe and West Asia boundary country code.",
    "USA": "Modern diaspora-heavy country code.",
}

BOUNDARY_CONTEXTS = [
    {
        "audit_card": "H-M82",
        "lineage_root": "H-M82",
        "source_label": "South Asia",
        "receiver_label": "Roma diaspora / Europe",
        "evidence_role": "Boundary/no-call card",
        "reason": "Diaspora and founder structure prevent a load-bearing primary source-receiver decision.",
    },
    {
        "audit_card": "E-M2",
        "lineage_root": "E-M2",
        "source_label": "West Africa",
        "receiver_label": "Americas / diaspora receiver",
        "evidence_role": "Boundary/no-call card",
        "reason": "Diaspora structure and source visibility prevent a load-bearing primary source-receiver decision.",
    },
]


class ReproducibilityError(RuntimeError):
    pass


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise ReproducibilityError(f"Required input not found: {path}")
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=OUTPUT_COLUMNS, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def country_status(code: str) -> str:
    if code in AMBIGUOUS_COUNTRY_RULES:
        return "Included in the scored mask when explicitly specified; evaluated in the conservative ambiguity audit."
    return "Included in the scored mask."


def contract_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    order = 1
    boundary = (
        "Country-code membership for a predefined model-checking mask only; not subnational placement, "
        "geographic origin, ethnic identity, population continuity, migration route, or population frequency."
    )
    for contract in CONTRACTS:
        for mask_role in ["source", "receiver"]:
            codes = contract[f"{mask_role}_codes"]
            for code in codes:
                rows.append(
                    {
                        "section": "Scored focused contract country membership",
                        "display_order": f"{order:03d}",
                        "contract_id": contract["contract_id"],
                        "audit_card": contract["audit_card"],
                        "lineage_root": contract["lineage_root"],
                        "evidence_role": contract["evidence_role"],
                        "mask_role": mask_role,
                        "mask_label": contract[f"{mask_role}_label"],
                        "region_rule": contract[f"{mask_role}_rule"],
                        "region_values": contract[f"{mask_role}_values"],
                        "country_code": code,
                        "country_code_status": country_status(code),
                        "reported_use": contract["reported_use"],
                        "source_trace": SOURCE_TRACE,
                        "claim_boundary": boundary,
                    }
                )
                order += 1
    return rows


def ambiguous_rule_rows(start_order: int) -> list[dict[str, str]]:
    rows = []
    boundary = (
        "Ambiguous-country sensitivity rule only; exclusion from the conservative audit is not evidence about "
        "geographic origin, ethnic identity, population continuity, migration route, or population frequency."
    )
    for offset, code in enumerate(sorted(AMBIGUOUS_COUNTRY_RULES), start=start_order):
        rows.append(
            {
                "section": "Ambiguous or corridor-adjacent country-code rule",
                "display_order": f"{offset:03d}",
                "contract_id": "all_scored_contracts_ambiguous_country_audit",
                "audit_card": "All scored focused contracts",
                "lineage_root": "multiple",
                "evidence_role": "Conservative ambiguity sensitivity rule",
                "mask_role": "exclusion_rule",
                "mask_label": "Conservative ambiguous-country exclusion",
                "region_rule": "Country-level ambiguity audit",
                "region_values": "spanning_or_diaspora_heavy_country_codes",
                "country_code": code,
                "country_code_status": AMBIGUOUS_COUNTRY_RULES[code],
                "reported_use": "Tests whether focused decisions depend on country codes with spanning or diaspora-heavy geography.",
                "source_trace": SOURCE_TRACE,
                "claim_boundary": boundary,
            }
        )
    return rows


def boundary_context_rows(start_order: int) -> list[dict[str, str]]:
    rows = []
    boundary = (
        "Boundary/no-call context only; not a scored source-receiver country-membership row and not evidence of "
        "geographic origin, ethnic identity, population continuity, migration route, or population frequency."
    )
    for offset, context in enumerate(BOUNDARY_CONTEXTS, start=start_order):
        for mask_role, label in [("source", context["source_label"]), ("receiver", context["receiver_label"])]:
            rows.append(
                {
                    "section": "Boundary/no-call context",
                    "display_order": f"{offset:03d}{'a' if mask_role == 'source' else 'b'}",
                    "contract_id": f"{context['audit_card']}_boundary_no_call_context",
                    "audit_card": context["audit_card"],
                    "lineage_root": context["lineage_root"],
                    "evidence_role": context["evidence_role"],
                    "mask_role": mask_role,
                    "mask_label": label,
                    "region_rule": "Not used as a load-bearing scored mask",
                    "region_values": "not_scoreable_as_primary_comparison",
                    "country_code": "not_applicable",
                    "country_code_status": context["reason"],
                    "reported_use": "Makes abstention visible when a load-bearing source-receiver decision is not justified.",
                    "source_trace": "tables/main_table_1_source_receiver_audit_cards.csv; tables/02_lineage_role_tiers.csv",
                    "claim_boundary": boundary,
                }
            )
    return rows


def generate_rows() -> list[dict[str, str]]:
    rows = contract_rows()
    rows.extend(ambiguous_rule_rows(len(rows) + 1))
    rows.extend(boundary_context_rows(len(rows) + 1))
    return rows


def validate_counts(rows: list[dict[str, str]], benchmark_rows: list[dict[str, str]]) -> None:
    by_contract = {row["focused_contract"]: row for row in benchmark_rows}
    for contract in CONTRACTS:
        benchmark = by_contract.get(
            {
                "R_Z280_EE_RUSSIA_TO_BALKAN": "R-Z280 Eastern Europe/Russia-to-Balkans matched comparator",
                "R_M458_EE_RUSSIA_TO_BALKAN": "R-M458 Eastern Europe/Russia-to-Balkans matched comparator",
                "PH908_EE_RUSSIA_TO_BALKAN": "I-PH908 Eastern Europe/Russia-to-Balkans held-out test",
                "E_M81_NORTH_AFRICA_TO_WEST_EUROPE": "E-M81 North Africa/Maghreb-to-Western Europe supporting comparison",
                "J_P58_ARABIA_TO_NORTH_AFRICA": "J-P58 Arabia/West Asia-to-North Africa supporting comparison",
                "O_M119_EAST_ASIA_TO_SE_ASIA": "O-M119 East Asia-to-Southeast Asia support-only diagnostic",
                "O_M122_EAST_ASIA_TO_SE_ASIA": "O-M122 East Asia-to-Southeast Asia support-only diagnostic",
            }[contract["contract_id"]]
        )
        if benchmark is None:
            raise ReproducibilityError(f"Benchmark row not found for {contract['contract_id']}")
        for mask_role in ["source", "receiver"]:
            observed = sum(
                1
                for row in rows
                if row["contract_id"] == contract["contract_id"] and row["mask_role"] == mask_role
            )
            expected = int(benchmark[f"{mask_role}_country_count"])
            if observed != expected:
                raise ReproducibilityError(
                    f"{contract['contract_id']} {mask_role} country count mismatch: {observed} != {expected}"
                )


def compare(generated: list[dict[str, str]], output: Path) -> None:
    existing = read_csv(output)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"Mask country-membership table row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        differences = [field for field in OUTPUT_COLUMNS if left.get(field) != right.get(field)]
        if differences:
            raise ReproducibilityError(
                f"Mask country-membership table mismatch at row {index}: {', '.join(differences[:6])}"
            )
    raise ReproducibilityError("Mask country-membership table mismatch detected.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate source-receiver mask country-membership table.")
    parser.add_argument("--benchmark-input", type=Path, default=DEFAULT_BENCHMARK_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated mask country-membership table.")
    args = parser.parse_args()

    try:
        rows = generate_rows()
        validate_counts(rows, read_csv(args.benchmark_input))
        if args.write:
            write_csv(args.output, rows)
        else:
            compare(rows, args.output)
        print(f"Source-receiver mask country-membership table {'written' if args.write else 'verified'}: {args.output}")
        return 0
    except ReproducibilityError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
