from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_headline_coordinates"

DEFAULT_LAYER_INPUT = SOURCE / "evidence_layer_definitions.csv"
DEFAULT_YFULL_INPUT = REPO / "tables" / "13_source_receiver_highlight_contracts.csv"
DEFAULT_HRAS_INPUT = SOURCE / "hras_yseq_branch_resolved_metric_source.csv"
DEFAULT_FTDNA_INPUT = SOURCE / "ftdna_discover_direct_child_metric_source.csv"
DEFAULT_OUTPUT = REPO / "tables" / "04_source_layers_and_headline_coordinates.csv"

OUTPUT_COLUMNS = [
    "section",
    "item",
    "context",
    "source-adequacy_A_s",
    "terminal_ln(Q2)_contrast_D",
    "bounded_direct-child_D_not_terminal_Q2",
    "status_or_limitation",
]

LINEAGE_ORDER = ["I-PH908", "R-Z280", "R-M458"]

YFULL_STATUS = {
    "I-PH908": "Stable rejection of the specified source-receiver hypothesis under predefined criteria; D is scale-sensitive",
    "R-Z280": "Source-receiver-compatible comparator under predefined criteria",
    "R-M458": "Source-receiver-compatible comparator under predefined criteria; D is scale-sensitive",
}

HRAS_STATUS = {
    "I-PH908": "Supporting branch-resolved comparison",
    "R-Z280": "Supporting branch-resolved comparison",
    "R-M458": "Supporting branch-resolved comparison",
}

FTDNA_STATUS = {
    "I-PH908": "Bounded direct-child source-adequacy support only; direct-child D is not terminal Q2 D",
    "R-Z280": "Bounded direct-child source-adequacy support only; direct-child D is not terminal Q2 D",
    "R-M458": "Bounded direct-child source-adequacy support only; direct-child D is not terminal Q2 D",
}


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


def decimal_3(value: str) -> str:
    return str(Decimal(value).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def by_lineage(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    keyed = {row["lineage_root"]: row for row in rows}
    missing = [lineage for lineage in LINEAGE_ORDER if lineage not in keyed]
    if missing:
        raise ReproducibilityError(f"Missing lineage rows: {', '.join(missing)}")
    return keyed


def generate_layer_rows(layer_input: Path) -> list[dict[str, str]]:
    rows = []
    for row in read_csv(layer_input):
        rows.append(
            {
                "section": row["section"],
                "item": row["item"],
                "context": row["context"],
                "source-adequacy_A_s": "",
                "terminal_ln(Q2)_contrast_D": "",
                "bounded_direct-child_D_not_terminal_Q2": "",
                "status_or_limitation": row["status_or_limitation"],
            }
        )
    return rows


def generate_yfull_rows(yfull_input: Path) -> list[dict[str, str]]:
    keyed = by_lineage(read_csv(yfull_input))
    rows = []
    for lineage in LINEAGE_ORDER:
        row = keyed[lineage]
        rows.append(
            {
                "section": "Headline coordinate",
                "item": lineage,
                "context": "YFull primary comparison: Eastern Europe/Russia-to-Balkans",
                "source-adequacy_A_s": decimal_3(row["deepest_source_adequacy_A_s"]),
                "terminal_ln(Q2)_contrast_D": decimal_3(row["deepest_diversity_contrast_D"]),
                "bounded_direct-child_D_not_terminal_Q2": "",
                "status_or_limitation": YFULL_STATUS[lineage],
            }
        )
    return rows


def generate_hras_rows(hras_input: Path) -> list[dict[str, str]]:
    keyed = by_lineage(read_csv(hras_input))
    rows = []
    for lineage in LINEAGE_ORDER:
        row = keyed[lineage]
        rows.append(
            {
                "section": "Headline coordinate",
                "item": lineage,
                "context": "HRAS/YSEQ supporting comparison: Balkans-Eastern Europe contrast",
                "source-adequacy_A_s": decimal_3(row["source_adequacy_A_s"]),
                "terminal_ln(Q2)_contrast_D": decimal_3(row["diversity_contrast_D"]),
                "bounded_direct-child_D_not_terminal_Q2": "",
                "status_or_limitation": HRAS_STATUS[lineage],
            }
        )
    return rows


def generate_ftdna_rows(ftdna_input: Path) -> list[dict[str, str]]:
    keyed = by_lineage(read_csv(ftdna_input))
    rows = []
    for lineage in LINEAGE_ORDER:
        row = keyed[lineage]
        rows.append(
            {
                "section": "Headline coordinate",
                "item": lineage,
                "context": "FTDNA Discover bounded comparison: Balkans-Eastern Europe contrast",
                "source-adequacy_A_s": decimal_3(row["source_adequacy_A_s"]),
                "terminal_ln(Q2)_contrast_D": "",
                "bounded_direct-child_D_not_terminal_Q2": f"not comparable: {decimal_3(row['direct_child_D_not_terminal_Q2'])}",
                "status_or_limitation": FTDNA_STATUS[lineage],
            }
        )
    return rows


def compare(generated: list[dict[str, str]], existing_path: Path) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"Table 4 row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        if left != right:
            fields = sorted(set(left) | set(right))
            differences = [field for field in fields if left.get(field) != right.get(field)]
            raise ReproducibilityError(f"Table 4 mismatch at row {index}: {', '.join(differences[:5])}")
    raise ReproducibilityError("Table 4 mismatch detected")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate the repository source-layer and headline-coordinate table."
    )
    parser.add_argument("--layer-input", type=Path, default=DEFAULT_LAYER_INPUT)
    parser.add_argument("--yfull-input", type=Path, default=DEFAULT_YFULL_INPUT)
    parser.add_argument("--hras-input", type=Path, default=DEFAULT_HRAS_INPUT)
    parser.add_argument("--ftdna-input", type=Path, default=DEFAULT_FTDNA_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write the generated Table 4 output.")
    args = parser.parse_args()

    try:
        rows = (
            generate_layer_rows(args.layer_input)
            + generate_yfull_rows(args.yfull_input)
            + generate_hras_rows(args.hras_input)
            + generate_ftdna_rows(args.ftdna_input)
        )
        if args.write:
            write_csv(args.output, rows)
        compare(rows, args.output)
        print(f"Source-layer and headline-coordinate rows: {len(rows)}")
        print("Source-layer and headline-coordinate table: pass")
        return 0
    except ReproducibilityError as error:
        print("Source-layer and headline-coordinate table: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
