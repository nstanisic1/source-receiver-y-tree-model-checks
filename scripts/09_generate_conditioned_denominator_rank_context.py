from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "core_conditioned_denominator_rank_context"

DEFAULT_METRIC_INPUT = SOURCE / "conditioned_denominator_metric_source.csv"
DEFAULT_RULE_INPUT = SOURCE / "conditioned_denominator_rank_rule_source.csv"
DEFAULT_OUTPUT = REPO / "tables" / "07_conditioned_denominator_summary.csv"

SOURCE_SUMMARY_FILE = "source_data/core_conditioned_denominator_rank_context/conditioned_denominator_metric_source.csv"

OUTPUT_COLUMNS = [
    "conditioned_denominator",
    "denominator_root_count",
    "denominator_family_count",
    "PH908_rank_within_denominator",
    "PH908_rank_percentile_within_denominator",
    "within_denominator_empirical_rank_p",
    "conditioned_rank_interpretation",
    "source_summary_file",
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
        writer = csv.DictWriter(handle, fieldnames=fieldnames, quoting=csv.QUOTE_ALL, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def decimal_6(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP))


def percentile_1(value: Decimal | str) -> str:
    return str(Decimal(value).quantize(Decimal("0.1"), rounding=ROUND_HALF_UP))


def validate_rule_source(rows: list[dict[str, str]]) -> None:
    required = {"rank_percentile_within_denominator", "within_denominator_empirical_rank_p"}
    observed = {row["rule_name"] for row in rows}
    missing = required - observed
    if missing:
        raise ReproducibilityError(f"Missing conditioned-denominator rule rows: {', '.join(sorted(missing))}")
    formulas = {row["rule_name"]: row["rule_formula"] for row in rows}
    if "PH908_rank_within_denominator / denominator_root_count" not in formulas[
        "within_denominator_empirical_rank_p"
    ]:
        raise ReproducibilityError("Empirical rank p-value formula drifted.")


def generate_rows(metric_rows: list[dict[str, str]]) -> list[dict[str, str]]:
    rows = []
    for source in sorted(metric_rows, key=lambda item: int(item["denominator_order"])):
        denominator_count = Decimal(source["denominator_root_count"])
        family_count = Decimal(source["denominator_family_count"])
        rank = Decimal(source["PH908_rank_within_denominator"])
        if denominator_count <= 0:
            raise ReproducibilityError(f"Invalid denominator count at row {source['denominator_order']}.")
        if family_count <= 0:
            raise ReproducibilityError(f"Invalid family count at row {source['denominator_order']}.")
        if rank < 1 or rank > denominator_count:
            raise ReproducibilityError(f"Invalid PH908 rank at row {source['denominator_order']}.")

        percentile = Decimal("100") * (denominator_count - rank + Decimal("1")) / denominator_count
        empirical_p = rank / denominator_count
        interpretation = (
            "PH908 ranks first within this predefined conditioned denominator"
            if rank == 1
            else "PH908 rank is reported within this predefined conditioned denominator"
        )
        rows.append(
            {
                "conditioned_denominator": source["conditioned_denominator"],
                "denominator_root_count": str(int(denominator_count)),
                "denominator_family_count": str(int(family_count)),
                "PH908_rank_within_denominator": str(int(rank)),
                "PH908_rank_percentile_within_denominator": percentile_1(percentile),
                "within_denominator_empirical_rank_p": decimal_6(empirical_p),
                "conditioned_rank_interpretation": interpretation,
                "source_summary_file": SOURCE_SUMMARY_FILE,
            }
        )
    return rows


def validate_outputs(rows: list[dict[str, str]]) -> None:
    if len(rows) != 7:
        raise ReproducibilityError(f"Table 7 row count changed: {len(rows)}")
    if any(row["PH908_rank_within_denominator"] != "1" for row in rows):
        raise ReproducibilityError("At least one conditioned denominator no longer has PH908 at rank 1.")
    expected_counts = ["34", "28", "18", "18", "6", "14", "18"]
    observed_counts = [row["denominator_root_count"] for row in rows]
    if observed_counts != expected_counts:
        raise ReproducibilityError(f"Conditioned denominator counts changed: {observed_counts}")


def compare(generated: list[dict[str, str]], existing_path: Path) -> None:
    existing = read_csv(existing_path)
    if generated == existing:
        return
    if len(generated) != len(existing):
        raise ReproducibilityError(
            f"Conditioned-denominator table row count mismatch: generated {len(generated)}; existing {len(existing)}"
        )
    for index, (left, right) in enumerate(zip(generated, existing), start=1):
        differences = [field for field in OUTPUT_COLUMNS if left.get(field) != right.get(field)]
        if differences:
            raise ReproducibilityError(
                f"Conditioned-denominator table mismatch at row {index}: {', '.join(differences[:6])}"
            )
    raise ReproducibilityError("Conditioned-denominator table mismatch detected.")


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate conditioned-denominator rank context table.")
    parser.add_argument("--metric-input", type=Path, default=DEFAULT_METRIC_INPUT)
    parser.add_argument("--rule-input", type=Path, default=DEFAULT_RULE_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--write", action="store_true", help="Write generated conditioned-denominator table.")
    args = parser.parse_args()

    try:
        validate_rule_source(read_csv(args.rule_input))
        rows = generate_rows(read_csv(args.metric_input))
        validate_outputs(rows)
        if args.write:
            write_csv(args.output, OUTPUT_COLUMNS, rows)
        compare(rows, args.output)
        print(f"Conditioned-denominator rows: {len(rows)}")
        print("Conditioned-denominator rank context layer: pass")
        return 0
    except ReproducibilityError as error:
        print("Conditioned-denominator rank context layer: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
