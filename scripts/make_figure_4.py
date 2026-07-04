from __future__ import annotations

import csv
import hashlib
import math
import textwrap
from datetime import datetime
from pathlib import Path

import matplotlib as mpl

mpl.use("Agg")
mpl.rcParams.update(
    {
        "font.family": "DejaVu Sans",
        "axes.unicode_minus": False,
        "pdf.fonttype": 42,
        "ps.fonttype": 42,
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.spines.top": False,
        "axes.spines.right": False,
        "axes.edgecolor": "#1E293B",
        "axes.linewidth": 0.8,
        "xtick.color": "#1E293B",
        "ytick.color": "#1E293B",
        "text.color": "#1E293B",
        "axes.labelcolor": "#1E293B",
    }
)

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "figure_4"
FIGURES = REPO / "figures"

INK = "#111827"
MUTED = "#64748B"
BORDER = "#CBD5E1"
GRID = "#E2E8F0"
RED = "#B83B32"
BLUE = "#1F5D8F"
GREEN = "#247A3D"
AMBER = "#9C6200"
GREY = "#64748B"
LIGHT_GREY = "#F8FAFC"
PALE_RED = "#FCEAE8"
PALE_GREEN = "#E8F4EC"
PALE_BLUE = "#EAF2F8"

EXPECTED_FILES = {
    "fig4_01_adversarial_sensitivity_plot_points.csv": 10,
    "fig4_02_matched_r1a_envelope_thresholds.csv": 10,
    "fig4_03_positive_control_recovery_trace.csv": 10,
    "fig4_05_source_visibility_burden_trace.csv": 10,
    "fig4_06_equal_n_rarefaction_degradation_trace.csv": 48,
    "fig4_08_synthetic_source_visibility_degradation_trace.csv": 72,
    "fig4_09_primary_visibility_bias_reversal_summary.csv": 4,
    "fig4_04_figure4_value_validation.csv": 8,
    "fig4_07_visibility_mask_sensitivity_validation.csv": 16,
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        rows = list(reader)
    if not rows:
        raise RuntimeError(f"Empty CSV file: {path}")
    width = len(rows[0])
    malformed = [(idx, len(row)) for idx, row in enumerate(rows, 1) if len(row) != width]
    if malformed:
        raise RuntimeError(f"Malformed CSV rows in {path}: {malformed[:5]}")
    return [dict(zip(rows[0], row)) for row in rows[1:]]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def validate_manifest() -> None:
    manifest = read_csv(SOURCE / "fig4_00_source_file_manifest.csv")
    for row in manifest:
        path = REPO / row["file_path"]
        if not path.exists():
            raise FileNotFoundError(path)
        observed_hash = sha256(path)
        if observed_hash != row["sha256"]:
            raise RuntimeError(
                f"Manifest hash mismatch for {row['file_path']}: "
                f"{observed_hash} != {row['sha256']}"
            )
        if row["row_count"] != "not_applicable":
            observed_rows = len(read_csv(path))
            if observed_rows != int(row["row_count"]):
                raise RuntimeError(
                    f"Manifest row-count mismatch for {row['file_path']}: "
                    f"{observed_rows} != {row['row_count']}"
                )


def validate_sources(
    sensitivity: list[dict[str, str]],
    envelope: list[dict[str, str]],
    controls: list[dict[str, str]],
    visibility: list[dict[str, str]],
    rarefaction: list[dict[str, str]],
    synthetic: list[dict[str, str]],
    primary_reversal: list[dict[str, str]],
    audit: list[dict[str, str]],
) -> None:
    for name, expected in EXPECTED_FILES.items():
        observed = len(read_csv(SOURCE / name))
        if observed != expected:
            raise RuntimeError(f"{name} row-count drifted: {observed} != {expected}")

    if any(row["audit_status"] != "Pass" for row in audit):
        raise RuntimeError("Expanded Figure 4 value validation contains a non-pass row")
    if [row["display_order"] for row in primary_reversal] != [str(i) for i in range(1, 5)]:
        raise RuntimeError("Figure 4 primary reversal order drifted")
    expected_reversal = {
        "A_s to 1: 4.67x",
        "A_s to R1a floor: 41.6x",
        "q2 to D<0: 3.76x",
        "q2 to R1a ceiling: 30.4x",
    }
    if {row["figure_label"] for row in primary_reversal} != expected_reversal:
        raise RuntimeError("Figure 4 primary reversal labels drifted")

    if [row["plot_order"] for row in sensitivity] != [str(i) for i in range(1, 11)]:
        raise RuntimeError("Figure 4 adversarial sensitivity plot order drifted")
    if [row["plot_order"] for row in envelope] != [str(i) for i in range(1, 11)]:
        raise RuntimeError("Figure 4 envelope plot order drifted")
    if [row["plot_order"] for row in visibility] != [str(i) for i in range(1, 11)]:
        raise RuntimeError("Figure 4 visibility-burden plot order drifted")

    weak = sum(1 for row in sensitivity if row["weak_directional_compatibility"] == "Yes")
    matched = sum(1 for row in sensitivity if row["matched_R1a_comparator_envelope_entry"] == "Yes")
    control_pass = sum(1 for row in controls if row["positive_controls_pass"] == "Yes")
    if (weak, matched, control_pass) != (10, 0, 6):
        raise RuntimeError(f"Adversarial count drift: weak={weak}, matched={matched}, controls={control_pass}")

    for sensitivity_row, envelope_row, visibility_row in zip(sensitivity, envelope, visibility):
        if sensitivity_row["branch_resolution_layer"] != envelope_row["branch_resolution_layer"]:
            raise RuntimeError("Sensitivity/envelope branch layer order drifted")
        if sensitivity_row["branch_resolution_layer"] != visibility_row["branch_resolution_layer"]:
            raise RuntimeError("Sensitivity/visibility branch layer order drifted")
        if sensitivity_row["ambiguity_handling_mode"] != envelope_row["ambiguity_handling_mode"]:
            raise RuntimeError("Sensitivity/envelope ambiguity mode order drifted")
        if sensitivity_row["source_mask"] != envelope_row["source_mask"]:
            raise RuntimeError("Sensitivity/envelope source-mask order drifted")

        if not (fnum(sensitivity_row, "source_adequacy_A_s") > 1 and fnum(sensitivity_row, "diversity_contrast_D") < 0):
            raise RuntimeError(f"Weak directional compatibility geometry drifted: {sensitivity_row}")
        if envelope_row["PH908_enters_envelope"] != "No":
            raise RuntimeError(f"Unexpected PH908 envelope entry: {envelope_row}")
        multiplier = fnum(visibility_row, "source_visibility_multiplier_needed")
        expected = fnum(visibility_row, "minimum_matched_R1a_source_adequacy_A_s") / fnum(
            visibility_row, "PH908_source_adequacy_A_s"
        )
        if abs(multiplier - expected) > 1e-5 or multiplier <= 1:
            raise RuntimeError(f"Visibility-burden arithmetic drifted: {visibility_row}")

    full_score = sum(int(row["scoreable_cells"]) for row in rarefaction)
    full_positive = sum(int(row["positive_cells"]) for row in rarefaction)
    full_failed = sum(int(row["failed_cells"]) for row in rarefaction)
    if (full_positive, full_score, full_failed) != (376, 544, 168):
        raise RuntimeError("Full rarefaction grid counts drifted")
    ge30 = [row for row in rarefaction if int(row["equal_n_rarefaction_n"]) >= 30]
    ge50 = [row for row in rarefaction if int(row["equal_n_rarefaction_n"]) >= 50]
    if (sum(int(row["positive_cells"]) for row in ge30), sum(int(row["scoreable_cells"]) for row in ge30)) != (373, 408):
        raise RuntimeError("Common-n >= 30 rarefaction counts drifted")
    if (sum(int(row["positive_cells"]) for row in ge50), sum(int(row["scoreable_cells"]) for row in ge50)) != (272, 272):
        raise RuntimeError("Common-n >= 50 rarefaction counts drifted")

    if len(synthetic) != 72:
        raise RuntimeError("Synthetic degradation row count drifted")
    for row in synthetic:
        expected_as = fnum(row, "synthetic_source_terminal_count_continuous") / fnum(row, "baseline_receiver_terminal_count")
        if abs(expected_as - fnum(row, "synthetic_source_adequacy_A_s")) > 1e-6:
            raise RuntimeError(f"Synthetic A_s arithmetic drifted: {row}")
        source_country_pass = fnum(row, "synthetic_source_country_count_continuous") >= 3
        receiver_country_pass = fnum(row, "receiver_country_count") >= 3
        if row["source_country_gate_pass"] != ("Yes" if source_country_pass else "No"):
            raise RuntimeError(f"Synthetic source-country gate drifted: {row}")
        if row["receiver_country_gate_pass"] != ("Yes" if receiver_country_pass else "No"):
            raise RuntimeError(f"Synthetic receiver-country gate drifted: {row}")
        basic = (
            fnum(row, "synthetic_source_adequacy_A_s") > 1
            and fnum(row, "branch_layer_diversity_contrast_D") < 0
            and source_country_pass
            and receiver_country_pass
        )
        matched = (
            fnum(row, "synthetic_source_adequacy_A_s") >= fnum(row, "matched_R1a_A_s_floor")
            and fnum(row, "branch_layer_diversity_contrast_D") <= fnum(row, "matched_R1a_D_ceiling")
            and source_country_pass
            and receiver_country_pass
        )
        if row["basic_compatibility_state"] != ("Yes" if basic else "No"):
            raise RuntimeError(f"Synthetic basic-compatibility state drifted: {row}")
        if row["matched_R1a_comparator_state"] != ("Yes" if matched else "No"):
            raise RuntimeError(f"Synthetic matched-state drifted: {row}")
    if sum(1 for row in synthetic if row["basic_compatibility_state"] == "Yes") != 30:
        raise RuntimeError("Synthetic degradation full-grid basic-compatible count drifted")
    for fraction, expected in [("1.000000", 10), ("0.500000", 10), ("0.250000", 0)]:
        observed = sum(
            1
            for row in synthetic
            if row["source_visibility_fraction_retained"] == fraction and row["basic_compatibility_state"] == "Yes"
        )
        if observed != expected:
            raise RuntimeError(f"Synthetic degradation fraction {fraction} drifted: {observed} != {expected}")


def short_state_label(row: dict[str, str]) -> str:
    layer = row["branch_resolution_layer"]
    layer = (
        layer.replace(" branch layer", "")
        .replace(" cutset layer", "")
        .replace("Count-balanced frontier", "Count-balanced")
        .replace("Deepest observed", "Deepest")
    )
    ambiguity = "incl." if row["ambiguity_handling_mode"].endswith("included") else "excl."
    return f"{layer}, {ambiguity}"


def draw_panel_a(ax, sensitivity: list[dict[str, str]], envelope: list[dict[str, str]]) -> None:
    x_values = [math.log10(fnum(row, "source_adequacy_A_s")) for row in sensitivity]
    y_values = [fnum(row, "diversity_contrast_D") for row in sensitivity]
    x_env = [fnum(row, "log10_minimum_matched_R1a_source_adequacy_A_s") for row in envelope]
    y_env = [fnum(row, "maximum_matched_R1a_diversity_contrast_D") for row in envelope]

    ax.axhspan(min(y_values) - 0.35, 0, xmin=0.0, xmax=1.0, color=PALE_GREEN, zorder=0)
    ax.axvspan(0, max(max(x_env), max(x_values)) + 0.12, ymin=0.0, ymax=1.0, color=PALE_GREEN, alpha=0.45, zorder=0)
    ax.axvline(0, color=INK, lw=0.9, ls=":")
    ax.axhline(0, color=INK, lw=0.9, ls=":")

    for row, x, y in zip(sensitivity, x_values, y_values):
        control_pass = row["positive_controls_pass"] == "Yes"
        color = GREEN if control_pass else AMBER
        marker = "o" if control_pass else "s"
        ax.scatter(x, y, s=80, marker=marker, color=color, edgecolor="white", linewidth=1.0, zorder=5)

    ax.scatter(x_env, y_env, s=46, marker="x", color=RED, linewidth=1.5, zorder=6)

    best_idx = min(
        range(len(sensitivity)),
        key=lambda idx: fnum(sensitivity[idx], "source_visibility_multiplier_needed")
        if "source_visibility_multiplier_needed" in sensitivity[idx]
        else fnum(envelope[idx], "PH908_A_s_gap_to_envelope"),
    )
    ax.annotate(
        "nearest PH908 state\noutside envelope",
        xy=(x_values[best_idx], y_values[best_idx]),
        xytext=(0.08, -0.92),
        ha="left",
        va="center",
        fontsize=8.2,
        fontweight="bold",
        color=INK,
        arrowprops={"arrowstyle": "-", "color": INK, "lw": 0.9, "shrinkA": 4, "shrinkB": 4},
        bbox={"boxstyle": "round,pad=0.25", "fc": "white", "ec": BORDER, "lw": 0.8},
    )

    ax.text(
        0.02,
        0.86,
        "Weak directional zone",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.2,
        color=GREEN,
        fontweight="bold",
    )
    ax.text(
        0.56,
        0.075,
        "red X = state-matched\ncomparator threshold;\nnot observed PH908 state",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.0,
        color=RED,
    )

    ax.set_title("a  Adversarial mask search", loc="left", fontsize=13, fontweight="bold", pad=8)
    ax.set_xlabel(r"log$_{10}$ source adequacy $A_s$", fontsize=10.2)
    ax.set_ylabel(r"$D=\ln(q^2_{\mathrm{receiver}}/q^2_{\mathrm{source}})$", fontsize=10.2)
    ax.set_xlim(-0.02, 1.05)
    ax.set_ylim(-2.35, 0.18)
    ax.grid(color=GRID, lw=0.8)


def draw_panel_b(ax, visibility: list[dict[str, str]], primary_reversal: list[dict[str, str]]) -> None:
    rows = sorted(visibility, key=lambda row: fnum(row, "source_visibility_multiplier_needed"))
    labels = [short_state_label(row) for row in rows]
    values = [fnum(row, "source_visibility_multiplier_needed") for row in rows]
    colors = [GREEN if row["positive_controls_pass"] == "Yes" else AMBER for row in rows]
    y_positions = list(range(len(rows)))

    ax.barh(y_positions, values, color=colors, alpha=0.86, height=0.64)
    ax.axvline(1, color=INK, lw=0.9)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=8.1)
    ax.invert_yaxis()
    ax.set_xlim(0, 6.1)
    for y, value in zip(y_positions, values):
        ax.text(value + 0.07, y, f"{value:.2f}x", va="center", ha="left", fontsize=8.2, color=INK)

    ax.text(
        0.01,
        1.015,
        "1x would meet the matched R1a-comparator source-adequacy threshold",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.9,
        color=MUTED,
        clip_on=False,
    )
    primary_labels = [row["figure_label"] for row in sorted(primary_reversal, key=lambda item: int(item["display_order"]))]
    primary_labels = [
        label.replace("A_s", r"$A_s$").replace("q2", r"$q^2$").replace("D<0", r"$D<0$")
        for label in primary_labels
    ]
    primary_text = (
        "Primary-layer reversal bounds: "
        f"{primary_labels[0].replace(': ', ' ')}; "
        f"{primary_labels[2].replace(': ', ' ')}; "
        f"{primary_labels[1].replace(': ', ' ')}; "
        f"{primary_labels[3].replace(': ', ' ')}"
    )
    ax.text(
        0.01,
        -0.245,
        primary_text,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.25,
        color=MUTED,
        linespacing=1.10,
        clip_on=False,
    )
    ax.set_title("b  Source-visibility burden", loc="left", fontsize=13, fontweight="bold", pad=24)
    ax.set_xlabel("source adequacy multiplier still needed", fontsize=10.2)
    ax.grid(axis="x", color=GRID, lw=0.8)
    ax.spines["left"].set_visible(False)
    ax.tick_params(axis="y", length=0)


def draw_panel_c(ax) -> None:
    ax.axis("off")
    ax.set_title("c  Adversarial decision gate", loc="left", fontsize=13, fontweight="bold", pad=8)

    items = [
        ("Weak directional\ncompatibility", "10/10", GREEN, PALE_GREEN),
        ("State-matched\nR1a-comparator envelope", "0/10", RED, PALE_RED),
        ("Positive-control\npassing states", "6/10", BLUE, PALE_BLUE),
        ("Transparency-only\ncontrol-failing states", "4/10", AMBER, "#FFF4DE"),
    ]
    x0, y0 = 0.02, 0.68
    width, height = 0.45, 0.23
    positions = [(x0, y0), (0.53, y0), (x0, 0.36), (0.53, 0.36)]
    for (label, value, color, face), (x, y) in zip(items, positions):
        ax.add_patch(
            Rectangle(
                (x, y),
                width,
                height,
                transform=ax.transAxes,
                facecolor=face,
                edgecolor=color,
                linewidth=1.0,
                alpha=0.95,
            )
        )
        ax.text(x + 0.035, y + 0.115, value, transform=ax.transAxes, ha="left", va="center", fontsize=17, fontweight="bold", color=color)
        ax.text(x + 0.168, y + 0.115, label, transform=ax.transAxes, ha="left", va="center", fontsize=8.7, color=INK, linespacing=1.05)

    ax.annotate(
        "",
        xy=(0.50, 0.80),
        xytext=(0.47, 0.80),
        xycoords=ax.transAxes,
        arrowprops={"arrowstyle": "->", "lw": 1.1, "color": MUTED},
    )
    ax.text(
        0.02,
        0.16,
        textwrap.fill(
            "Interpretation: mask flexibility can create weak directional compatibility, but the strict matched-comparator gate remains closed.",
            width=72,
        ),
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=9.0,
        color=MUTED,
        linespacing=1.18,
    )


def aggregate_synthetic_degradation(synthetic: list[dict[str, str]]) -> tuple[list[str], list[str], dict[tuple[str, str], tuple[int, int]]]:
    layer_order = [
        "Deepest observed branch layer",
        "Residualized-count branch layer",
        "Direct-child cutset layer",
        "Depth-2 cutset layer",
        "Depth-3 cutset layer",
        "Count-balanced frontier layer",
    ]
    fraction_order = ["1.000000", "0.750000", "0.500000", "0.250000", "0.125000", "0.100000"]
    values: dict[tuple[str, str], tuple[int, int]] = {}
    for layer in layer_order:
        for fraction in fraction_order:
            rows = [
                row
                for row in synthetic
                if row["branch_resolution_layer"] == layer and row["source_visibility_fraction_retained"] == fraction
            ]
            compatible = sum(1 for row in rows if row["basic_compatibility_state"] == "Yes")
            values[(layer, fraction)] = (compatible, len(rows))
    return layer_order, fraction_order, values


def aggregate_rarefaction(rarefaction: list[dict[str, str]]) -> list[tuple[int, int, int]]:
    by_n: dict[int, list[int]] = {}
    for row in rarefaction:
        n = int(row["equal_n_rarefaction_n"])
        if n not in by_n:
            by_n[n] = [0, 0]
        by_n[n][0] += int(row["positive_cells"])
        by_n[n][1] += int(row["scoreable_cells"])
    return [(n, values[0], values[1]) for n, values in sorted(by_n.items())]


def draw_panel_d(ax, rarefaction: list[dict[str, str]], synthetic: list[dict[str, str]]) -> None:
    ax.axis("off")
    ax.set_title("d  Rarefaction and synthetic degradation controls", loc="left", fontsize=13, fontweight="bold", pad=8)

    ax.text(
        0.00,
        0.872,
        "Equal-n rarefaction",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.0,
        color=MUTED,
        fontweight="bold",
    )
    ax.text(
        0.245,
        0.872,
        "n=20: 3/136; n=30: 101/136; n>=50: 272/272 positive cells",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=7.8,
        color=INK,
    )
    ax.plot([0.00, 0.92], [0.820, 0.820], transform=ax.transAxes, color=BORDER, lw=0.8)
    ax.text(
        0.00,
        0.755,
        "Synthetic degradation: basic-compatible R1a controls / 2",
        transform=ax.transAxes,
        ha="left",
        va="center",
        fontsize=8.0,
        color=MUTED,
        fontweight="bold",
    )

    heat_ax = ax.inset_axes([0.00, 0.115, 0.92, 0.560])
    layer_order, fraction_order, values = aggregate_synthetic_degradation(synthetic)
    matrix = []
    for layer in layer_order:
        row = []
        for fraction in fraction_order:
            compatible, total = values[(layer, fraction)]
            row.append(compatible / total if total else math.nan)
        matrix.append(row)

    heat_ax.imshow(matrix, cmap=mpl.colors.LinearSegmentedColormap.from_list("fig4_degrade", ["#F7D9D6", "#FFF4DE", "#E8F4EC"]), vmin=0, vmax=1, aspect="auto")
    for yi, layer in enumerate(layer_order):
        for xi, fraction in enumerate(fraction_order):
            compatible, total = values[(layer, fraction)]
            heat_ax.text(xi, yi, f"{compatible}/{total}", ha="center", va="center", fontsize=7.8, fontweight="bold", color=INK)

    heat_ax.set_xticks(range(len(fraction_order)))
    heat_ax.set_xticklabels(["100%", "75%", "50%", "25%", "12.5%", "10%"], fontsize=7.9)
    heat_ax.set_yticks(range(len(layer_order)))
    heat_ax.set_yticklabels(["Deepest", "Residual", "Direct-child", "Depth-2", "Depth-3", "Balanced"], fontsize=7.8)
    heat_ax.set_xlabel("source visibility retained", fontsize=8.3)
    heat_ax.tick_params(length=0)
    for spine in heat_ax.spines.values():
        spine.set_visible(False)
    heat_ax.set_xticks([x - 0.5 for x in range(1, len(fraction_order))], minor=True)
    heat_ax.set_yticks([y - 0.5 for y in range(1, len(layer_order))], minor=True)
    heat_ax.grid(which="minor", color="white", linewidth=1.8)
    heat_ax.plot([3, 5], [-0.60, -0.60], color=MUTED, lw=0.8, clip_on=False)
    heat_ax.text(
        4,
        -0.88,
        "source-country gate failure -> no-call",
        ha="center",
        va="center",
        fontsize=6.7,
        color=MUTED,
        clip_on=False,
    )


def add_legend(fig) -> None:
    handles = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor=GREEN, markeredgecolor="white", markersize=8, label="positive-control passing"),
        Line2D([0], [0], marker="s", color="none", markerfacecolor=AMBER, markeredgecolor="white", markersize=8, label="control-failing transparency state"),
        Line2D([0], [0], marker="x", color=RED, markersize=8, lw=0, label="state-matched R1a-comparator threshold"),
    ]
    fig.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.070, 0.838),
        ncol=3,
        frameon=False,
        fontsize=8.1,
        handletextpad=0.4,
        columnspacing=1.4,
    )


def render() -> tuple[Path, Path]:
    validate_manifest()
    sensitivity = read_csv(SOURCE / "fig4_01_adversarial_sensitivity_plot_points.csv")
    envelope = read_csv(SOURCE / "fig4_02_matched_r1a_envelope_thresholds.csv")
    controls = read_csv(SOURCE / "fig4_03_positive_control_recovery_trace.csv")
    visibility = read_csv(SOURCE / "fig4_05_source_visibility_burden_trace.csv")
    rarefaction = read_csv(SOURCE / "fig4_06_equal_n_rarefaction_degradation_trace.csv")
    synthetic = read_csv(SOURCE / "fig4_08_synthetic_source_visibility_degradation_trace.csv")
    primary_reversal = read_csv(SOURCE / "fig4_09_primary_visibility_bias_reversal_summary.csv")
    audit = read_csv(SOURCE / "fig4_07_visibility_mask_sensitivity_validation.csv")
    validate_sources(sensitivity, envelope, controls, visibility, rarefaction, synthetic, primary_reversal, audit)

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(15.8, 9.1), dpi=300)
    fig.text(
        0.070,
        0.952,
        "Visibility and mask-choice stress tests do not place PH908 in the matched R1a-comparator envelope",
        ha="left",
        va="top",
        fontsize=19,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.070,
        0.906,
        "Visibility-bias reversal, synthetic degradation controls, and adversarial masks are shown as model checks, not origin evidence.",
        ha="left",
        va="top",
        fontsize=11.6,
        color=MUTED,
    )
    fig.add_artist(Line2D([0.070, 0.970], [0.872, 0.872], transform=fig.transFigure, color=BORDER, lw=0.9))

    grid = fig.add_gridspec(
        2,
        2,
        left=0.070,
        right=0.970,
        top=0.760,
        bottom=0.190,
        width_ratios=[1.16, 1.0],
        height_ratios=[1.0, 0.88],
        wspace=0.28,
        hspace=0.64,
    )
    ax_a = fig.add_subplot(grid[0, 0])
    ax_b = fig.add_subplot(grid[0, 1])
    ax_c = fig.add_subplot(grid[1, 0])
    ax_d = fig.add_subplot(grid[1, 1])

    draw_panel_a(ax_a, sensitivity, envelope)
    draw_panel_b(ax_b, visibility, primary_reversal)
    draw_panel_c(ax_c)
    draw_panel_d(ax_d, rarefaction, synthetic)
    add_legend(fig)

    footer = (
        "Sources: Source data are provided with the numbered Figure 4 source-data bundle. "
        "Weak directional compatibility is A_s > 1 and D < 0; matched-envelope entry additionally requires the state-matched R1a-comparator threshold. "
        "At <=25% retained source visibility, compatible comparators fail the source-country visibility gate in the deterministic degradation control. "
        "Equal-n rarefaction summarizes power and denominator limits; visibility burden and synthetic degradation controls are operating-characteristic checks, not population-size estimates. "
        "The figure does not identify PH908 geographic origin, ethnic identity, population continuity, migration route, or any population-level probability."
    )
    fig.text(0.070, 0.078, textwrap.fill(footer, width=190), ha="left", va="bottom", fontsize=8.3, color=MUTED, linespacing=1.14)

    out = FIGURES / "Figure_4_visibility_mask_sensitivity"
    png_metadata = {
        "Title": "Figure 4 adversarial sensitivity and adequacy checks",
        "Author": "Reliability-aware source-receiver model-checking reproduction script",
        "Subject": "Figure 4 source-receiver adversarial sensitivity",
        "Keywords": "Figure 4, adversarial sensitivity, source visibility, synthetic degradation, PH908, R1a",
    }
    pdf_metadata = {
        "Title": "Figure 4 adversarial sensitivity and adequacy checks",
        "Author": "Reliability-aware source-receiver model-checking reproduction script",
        "Subject": "Figure 4 source-receiver adversarial sensitivity",
        "Keywords": "Figure 4, adversarial sensitivity, source visibility, synthetic degradation, PH908, R1a",
        "CreationDate": datetime(2026, 7, 2, 0, 0, 0),
        "ModDate": datetime(2026, 7, 2, 0, 0, 0),
    }
    png = out.with_suffix(".png")
    pdf = out.with_suffix(".pdf")
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white", metadata=png_metadata)
    fig.savefig(pdf, bbox_inches="tight", facecolor="white", metadata=pdf_metadata)
    plt.close(fig)
    return png, pdf


if __name__ == "__main__":
    png_path, pdf_path = render()
    print(f"Wrote {png_path}")
    print(f"Wrote {pdf_path}")
    print(f"PNG sha256 {sha256(png_path)}")
    print(f"PDF sha256 {sha256(pdf_path)}")
