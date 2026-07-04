from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parents[1]

ANALYSIS_SCRIPTS = [
    ("Core YFull source-receiver reliability tables", "scripts/01_generate_yfull_source_receiver_reliability_tables.py"),
    ("Source-layer and headline-coordinate table", "scripts/02_generate_source_layer_headline_coordinates.py"),
    ("Branch-unit reliability tables and Figure 3 overlay", "scripts/03_generate_branch_unit_reliability_tables.py"),
    ("Figure 3 specificity/calibration table and trace", "scripts/04_generate_figure3_specificity_calibration.py"),
    ("Parser and log-base quality-control tables", "scripts/08_generate_parser_and_log_base_quality_controls.py"),
    ("Conditioned-denominator rank context table", "scripts/09_generate_conditioned_denominator_rank_context.py"),
    ("Figure 4 adversarial sensitivity table and traces", "scripts/05_generate_figure4_adversarial_sensitivity.py"),
    ("Figure 4 visibility-burden tables and traces", "scripts/06_generate_figure4_visibility_burden.py"),
    ("Figure 4 rarefaction and synthetic degradation controls", "scripts/07_generate_figure4_rarefaction_and_degradation.py"),
    ("Supplementary Figure S1 visibility-gap quantification", "scripts/10_generate_supplementary_figure_s1_visibility_gap.py"),
    ("Integrated sensitivity and ancient-DNA boundary summary", "scripts/11_generate_integrated_boundary_summary.py"),
    ("Main Table 1 source-receiver audit summaries", "scripts/12_generate_main_table_1_audit_summaries.py"),
    ("Source-receiver mask country-membership table", "scripts/14_generate_source_receiver_mask_country_membership.py"),
]

FIGURE_SCRIPTS = [
    ("Figure 1", "scripts/make_figure_1.py"),
    ("Figure 2", "scripts/make_figure_2.py"),
    ("Figure 3", "scripts/make_figure_3.py"),
    ("Figure 4", "scripts/make_figure_4.py"),
    ("Supplementary Figure S1", "scripts/make_supplementary_figure_s1.py"),
]

PROVENANCE_TABLES = [
    "tables/29_figure_1_reliability_framework_provenance.csv",
    "tables/23_figure_2_yfull_reliability_atlas_provenance.csv",
    "tables/24_figure_3_ph908_r1a_source_receiver_contrast_provenance.csv",
    "tables/25_figure_4_visibility_mask_sensitivity_provenance.csv",
    "tables/20_supplementary_figure_s1_visibility_map_provenance.csv",
]


class ReproductionError(RuntimeError):
    pass


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv_strict(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    if not rows:
        raise ReproductionError(f"Empty CSV file: {path.relative_to(REPO)}")
    width = len(rows[0])
    malformed = [(idx, len(row)) for idx, row in enumerate(rows, 1) if len(row) != width]
    if malformed:
        shown = "; ".join(f"row {idx} has {row_width}" for idx, row_width in malformed[:5])
        raise ReproductionError(f"Malformed CSV structure in {path.relative_to(REPO)}: {shown}")
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def csv_data_row_count(path: Path) -> int:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return max(sum(1 for _ in csv.reader(handle)) - 1, 0)


def declared_feature_or_row_count(path: Path) -> int:
    if path.suffix.lower() == ".geojson":
        data = json.loads(path.read_text(encoding="utf-8"))
        features = data.get("features")
        if not isinstance(features, list):
            raise ReproductionError(f"GeoJSON lacks a feature list: {path.relative_to(REPO)}")
        return len(features)
    return csv_data_row_count(path)


def resolve_manifest_dependency(manifest: Path, value: str) -> Path:
    candidates = [REPO / value, manifest.parent / value]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]


def validate_csv_shapes() -> int:
    checked = 0
    for root in [REPO / "tables", REPO / "source_data"]:
        for path in sorted(root.rglob("*.csv")):
            read_csv_strict(path)
            checked += 1
    return checked


def validate_source_manifests() -> int:
    checked = 0
    manifests = sorted((REPO / "source_data").rglob("*manifest*.csv"))
    if not manifests:
        raise ReproductionError("No source-data manifests were found.")

    for manifest in manifests:
        rows = read_csv_strict(manifest)
        for row in rows:
            path_field = "file_path" if "file_path" in row else "source_file"
            count_field = "row_count" if "row_count" in row else "row_or_feature_count"
            if path_field not in row or count_field not in row or "sha256" not in row:
                raise ReproductionError(f"Unrecognized manifest schema: {manifest.relative_to(REPO)}")

            dependency = resolve_manifest_dependency(manifest, row[path_field])
            if not dependency.exists():
                raise ReproductionError(
                    f"Manifest dependency not found: {row[path_field]} in {manifest.relative_to(REPO)}"
                )
            observed_hash = sha256(dependency)
            if observed_hash != row["sha256"]:
                raise ReproductionError(
                    f"Manifest hash mismatch for {row[path_field]}: {observed_hash} != {row['sha256']}"
                )

            declared_count = row[count_field]
            if declared_count not in {"not_applicable", "not_applicable_note"}:
                if not declared_count.isdigit():
                    raise ReproductionError(
                        f"Non-numeric declared row or feature count in {manifest.relative_to(REPO)}: "
                        f"{row[path_field]} = {declared_count}"
                    )
                observed_count = declared_feature_or_row_count(dependency)
                if observed_count != int(declared_count):
                    raise ReproductionError(
                        f"Manifest count mismatch for {row[path_field]}: "
                        f"{observed_count} != {declared_count}"
                    )
            checked += 1
    return checked


def run_figure_scripts() -> None:
    for label, script_name in FIGURE_SCRIPTS:
        script = REPO / script_name
        if not script.exists():
            raise ReproductionError(f"Missing figure script: {script_name}")
        completed = subprocess.run(
            [sys.executable, str(script)],
            cwd=str(REPO),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stdout + "\n" + completed.stderr).strip()
            raise ReproductionError(f"{label} reproduction failed.\n{details}")
        print(f"{label}: regenerated")


def run_analysis_scripts(verify_only: bool) -> None:
    for label, script_name in ANALYSIS_SCRIPTS:
        script = REPO / script_name
        if not script.exists():
            raise ReproductionError(f"Missing analysis script: {script_name}")
        command = [sys.executable, str(script)]
        if not verify_only:
            command.append("--write")
        completed = subprocess.run(
            command,
            cwd=str(REPO),
            text=True,
            capture_output=True,
            check=False,
        )
        if completed.returncode != 0:
            details = (completed.stdout + "\n" + completed.stderr).strip()
            raise ReproductionError(f"{label} reproduction failed.\n{details}")
        action = "verified" if verify_only else "regenerated"
        print(f"{label}: {action}")


def validate_provenance_tables() -> int:
    checked = 0
    for provenance_name in PROVENANCE_TABLES:
        provenance = REPO / provenance_name
        if not provenance.exists():
            raise ReproductionError(f"Missing provenance table: {provenance_name}")
        rows = read_csv_strict(provenance)
        for row in rows:
            checks = [
                ("generation_script", "generation_script_sha256"),
                ("source_manifest", "source_manifest_sha256"),
                ("claim_audit_file", "claim_audit_sha256"),
                ("output_path", "output_sha256"),
            ]
            for path_field, hash_field in checks:
                if path_field not in row or hash_field not in row:
                    raise ReproductionError(f"Unrecognized provenance schema: {provenance_name}")
                dependency = REPO / row[path_field]
                if not dependency.exists():
                    raise ReproductionError(
                        f"Provenance dependency not found: {row[path_field]} in {provenance_name}"
                    )
                observed_hash = sha256(dependency)
                if observed_hash != row[hash_field]:
                    raise ReproductionError(
                        f"Provenance hash mismatch for {row[path_field]} in {provenance_name}: "
                        f"{observed_hash} != {row[hash_field]}"
                    )
                checked += 1
    return checked


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Regenerate analysis tables and study figures, then validate source-data manifests, "
            "CSV structure, and file-level provenance."
        )
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Validate existing source data and provenance without regenerating figures.",
    )
    args = parser.parse_args()

    print("Reliability-aware source-receiver model-checking reproduction")
    print("Repository root: archived release snapshot")

    try:
        run_analysis_scripts(args.verify_only)
        csv_count = validate_csv_shapes()
        manifest_count = validate_source_manifests()
        print(f"CSV structure: pass ({csv_count} files)")
        print(f"Source-data manifests: pass ({manifest_count} dependencies)")

        if not args.verify_only:
            run_figure_scripts()

        provenance_count = validate_provenance_tables()
        print(f"File-level provenance: pass ({provenance_count} hash checks)")
        print("Reproduction status: pass")
        return 0
    except ReproductionError as error:
        print("Reproduction status: failed", file=sys.stderr)
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
