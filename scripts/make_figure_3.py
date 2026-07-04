from __future__ import annotations

import csv
import hashlib
import math
import re
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


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "figure_3"
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

EXPECTED_LINEAGES = ["I-PH908", "R-Z280", "R-M458"]
LINEAGE_LABEL = {"I-PH908": "PH908", "R-Z280": "R-Z280", "R-M458": "R-M458"}
LINEAGE_COLOR = {"I-PH908": RED, "R-Z280": BLUE, "R-M458": GREEN}
EXPECTED_STABILITY_COUNTS = {
    "I-PH908": {"Pass": 0, "Fail": 6, "No-call": 0},
    "R-Z280": {"Pass": 6, "Fail": 0, "No-call": 0},
    "R-M458": {"Pass": 4, "Fail": 2, "No-call": 0},
}
EXPECTED_BRANCH_LAYERS = [
    "Deepest observed branch layer",
    "Residualized-count branch layer",
    "Direct-child cutset layer",
    "Depth-2 cutset layer",
    "Depth-3 cutset layer",
    "Count-balanced frontier layer",
]


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


def trace_row(rows: list[dict[str, str]], comparison: str) -> dict[str, str]:
    matches = [row for row in rows if row["comparison_or_calibration"] == comparison]
    if len(matches) != 1:
        raise RuntimeError(f"Expected one trace row for {comparison!r}, observed {len(matches)}")
    return matches[0]


def extract_metric(text: str, label: str) -> str:
    match = re.search(rf"{re.escape(label)}\s*=\s*([^;]+)", text)
    if not match:
        raise RuntimeError(f"Could not extract {label!r} from {text!r}")
    return match.group(1).strip()


def validate_manifest() -> None:
    manifest = read_csv(SOURCE / "fig3_00_source_file_manifest.csv")
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
    headline: list[dict[str, str]],
    primary: list[dict[str, str]],
    supporting: list[dict[str, str]],
    trace: list[dict[str, str]],
    claim_audit: list[dict[str, str]],
    stability: list[dict[str, str]],
) -> None:
    if len(headline) != 9:
        raise RuntimeError(f"Expected nine headline rows, observed {len(headline)}")
    if len(primary) != 3:
        raise RuntimeError(f"Expected three primary YFull rows, observed {len(primary)}")
    if len(supporting) != 6:
        raise RuntimeError(f"Expected six supporting-layer rows, observed {len(supporting)}")
    if len(trace) != 9:
        raise RuntimeError(f"Expected nine specificity/calibration rows, observed {len(trace)}")
    if len(claim_audit) != 18:
        raise RuntimeError(f"Expected eighteen value-validation rows, observed {len(claim_audit)}")
    if len(stability) != 18:
        raise RuntimeError(f"Expected eighteen branch-unit stability rows, observed {len(stability)}")
    if any(row["audit_status"] != "Pass" for row in claim_audit):
        raise RuntimeError("Figure 3 claim-reproduction audit contains a non-pass row")

    if [row["lineage_root"] for row in primary] != EXPECTED_LINEAGES:
        raise RuntimeError("Primary YFull lineage order drifted")
    if {row["lineage_root"] for row in supporting} != set(EXPECTED_LINEAGES):
        raise RuntimeError("Supporting-layer lineage set drifted")

    primary_lookup = {row["lineage_root"]: row for row in primary}
    ph908 = primary_lookup["I-PH908"]
    if not (fnum(ph908, "source_adequacy_A_s") < 1 and fnum(ph908, "terminal_ln_Q2_contrast_D") > 0):
        raise RuntimeError("PH908 primary YFull rejection pattern drifted")
    for lineage in ("R-Z280", "R-M458"):
        row = primary_lookup[lineage]
        if not (fnum(row, "source_adequacy_A_s") > 1 and fnum(row, "terminal_ln_Q2_contrast_D") < 0):
            raise RuntimeError(f"{lineage} primary YFull comparator pattern drifted")

    by_layer = {(row["lineage_root"], row["evidence_layer"]): row for row in supporting}
    for lineage in EXPECTED_LINEAGES:
        hras = by_layer[(lineage, "HRAS/YSEQ")]
        if lineage == "I-PH908":
            expected = fnum(hras, "source_adequacy_A_s") < 1 and fnum(hras, "terminal_ln_Q2_contrast_D") > 0
        else:
            expected = fnum(hras, "source_adequacy_A_s") > 1 and fnum(hras, "terminal_ln_Q2_contrast_D") < 0
        if not expected:
            raise RuntimeError(f"{lineage} HRAS/YSEQ direction drifted")

        ftdna = by_layer[(lineage, "FTDNA Discover")]
        if ftdna["terminal_ln_Q2_contrast_D"] != "":
            raise RuntimeError(f"{lineage} FTDNA row unexpectedly contains terminal D")
        if not ftdna["bounded_direct_child_D_not_terminal_Q2"].startswith("not comparable:"):
            raise RuntimeError(f"{lineage} FTDNA row is not marked bounded/not comparable")

    stability_by_lineage = {lineage: [] for lineage in EXPECTED_LINEAGES}
    for row in stability:
        lineage = row["lineage_root"]
        if lineage not in stability_by_lineage:
            raise RuntimeError(f"Unexpected lineage in stability overlay: {lineage}")
        if row["branch_unit_decision"] != row["stability_dot_class"]:
            raise RuntimeError(f"Stability dot class drifted: {row}")
        if not row["additional_sensitivity_evidence_status"].startswith("No rarefaction"):
            raise RuntimeError(f"Unexpected rarefaction/confidence wording in stability row: {row}")
        stability_by_lineage[lineage].append(row)
    for lineage, rows in stability_by_lineage.items():
        rows.sort(key=lambda item: int(item["branch_resolution_order"]))
        observed_layers = [row["branch_resolution_layer"] for row in rows]
        if observed_layers != EXPECTED_BRANCH_LAYERS:
            raise RuntimeError(f"{lineage} branch-layer order drifted: {observed_layers}")
        counts = {"Pass": 0, "Fail": 0, "No-call": 0}
        for row in rows:
            counts[row["branch_unit_decision"]] += 1
        if counts != EXPECTED_STABILITY_COUNTS[lineage]:
            raise RuntimeError(f"{lineage} branch-unit count drifted: {counts}")

    separation = trace_row(trace, "Observed PH908 versus negative-control margin separation")
    auroc = trace_row(trace, "AUROC in tested comparison grid")
    permutation = trace_row(trace, "Matched-block permutation test")
    t95 = trace_row(trace, "T95 empirical nearest-rank threshold")
    if float(extract_metric(separation["observed_result"], "minimum observed separation gap")) <= 0:
        raise RuntimeError("Observed separation gap is not positive")
    if float(extract_metric(auroc["observed_result"], "PH908-versus-negative-control margin AUROC")) < 1:
        raise RuntimeError("AUROC drifted below the audited complete-separation value")
    if float(extract_metric(permutation["observed_result"], "block permutation p-value")) > 0.05:
        raise RuntimeError("Permutation support drifted above 0.05")
    if extract_metric(t95["observed_result"], "Negative-control flagged count") != "6/136":
        raise RuntimeError("Preferred T95 negative-control flagging drifted")
    if extract_metric(t95["observed_result"], "PH908 pass count") != "136/136":
        raise RuntimeError("Preferred T95 PH908 recovery drifted")


def grouped_stability(stability: list[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    grouped: dict[str, list[dict[str, str]]] = {lineage: [] for lineage in EXPECTED_LINEAGES}
    for row in stability:
        grouped[row["lineage_root"]].append(row)
    for rows in grouped.values():
        rows.sort(key=lambda item: int(item["branch_resolution_order"]))
    return grouped


def draw_bar_panel(
    ax,
    rows: list[dict[str, str]],
    metric: str,
    title: str,
    xlabel: str,
    threshold_note: str,
) -> None:
    labels = [LINEAGE_LABEL[row["lineage_root"]] for row in rows]
    colors = [LINEAGE_COLOR[row["lineage_root"]] for row in rows]
    values = [math.log10(fnum(row, "source_adequacy_A_s")) if metric == "log10_A_s" else fnum(row, "terminal_ln_Q2_contrast_D") for row in rows]
    raw_values = [fnum(row, "source_adequacy_A_s") if metric == "log10_A_s" else fnum(row, "terminal_ln_Q2_contrast_D") for row in rows]
    y_positions = list(range(len(rows)))

    ax.axvline(0, color=GREY, linestyle=":", linewidth=1.0, zorder=1)
    ax.barh(y_positions, values, color=colors, alpha=0.88, height=0.48, zorder=3)
    ax.set_yticks(y_positions)
    ax.set_yticklabels(labels, fontsize=9.5, fontweight="bold")
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    ax.set_axisbelow(True)
    ax.set_title(title, loc="left", fontsize=11.8, fontweight="bold", color=INK, pad=16)
    ax.text(
        0.0,
        1.030,
        threshold_note,
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.5,
        color=MUTED,
    )
    ax.set_xlabel(xlabel, fontsize=9.6, color=INK)
    ax.tick_params(axis="x", labelsize=8.8)
    ax.tick_params(axis="y", length=0)

    xmin = min(values + [0])
    xmax = max(values + [0])
    pad = max(0.12, (xmax - xmin) * 0.22)
    ax.set_xlim(xmin - pad, xmax + pad)
    for y_pos, value, raw, color in zip(y_positions, values, raw_values, colors):
        text = rf"$A_s$ = {raw:.3f}" if metric == "log10_A_s" else f"D = {raw:+.3f}"
        if value >= 0:
            ax.text(value + 0.040, y_pos, text, va="center", ha="left", fontsize=8.3, color=color, fontweight="bold")
        else:
            ax.text(value + 0.050, y_pos, text, va="center", ha="left", fontsize=8.1, color="white", fontweight="bold")


def draw_stability_panel(ax, stability: list[dict[str, str]]) -> None:
    grouped = grouped_stability(stability)
    layer_labels = ["Deepest", "Residual", "Direct-child", "Depth-2", "Depth-3", "Balanced"]
    decision_style = {
        "Pass": (GREEN, "o"),
        "Fail": (RED, "X"),
        "No-call": (GREY, "s"),
    }

    ax.set_title("c  Branch-unit stability across evaluated resolution layers", loc="left", fontsize=11.8, fontweight="bold", color=INK, pad=12)
    ax.set_xlim(-0.55, 5.55)
    ax.set_ylim(-0.58, 2.58)
    ax.set_xticks(range(6))
    ax.set_xticklabels(layer_labels, fontsize=8.4)
    ax.set_yticks(range(3))
    ax.set_yticklabels([LINEAGE_LABEL[lineage] for lineage in EXPECTED_LINEAGES], fontsize=9.5, fontweight="bold")
    ax.invert_yaxis()
    ax.grid(axis="x", color=GRID, linewidth=0.7, zorder=0)
    ax.tick_params(axis="y", length=0)
    ax.tick_params(axis="x", length=0)

    for y_idx, lineage in enumerate(EXPECTED_LINEAGES):
        rows = grouped[lineage]
        ax.plot(range(6), [y_idx] * 6, color=BORDER, linewidth=1.0, zorder=1)
        for x_idx, row in enumerate(rows):
            color, marker = decision_style[row["branch_unit_decision"]]
            ax.scatter(
                x_idx,
                y_idx,
                s=145,
                marker=marker,
                color=color,
                edgecolor="white",
                linewidth=1.1,
                zorder=4,
            )
        pass_count = sum(row["branch_unit_decision"] == "Pass" for row in rows)
        fail_count = sum(row["branch_unit_decision"] == "Fail" for row in rows)
        ax.text(5.60, y_idx, f"{pass_count}/6 pass", ha="right", va="center", fontsize=8.5, color=LINEAGE_COLOR[lineage], fontweight="bold")
        if fail_count:
            ax.text(5.60, y_idx + 0.22, f"{fail_count} fail", ha="right", va="center", fontsize=7.3, color=RED)

    handles = [
        Line2D([0], [0], marker="o", linestyle="None", color="none", markerfacecolor=GREEN, markeredgecolor="white", markersize=8, label="Pass"),
        Line2D([0], [0], marker="X", linestyle="None", color="none", markerfacecolor=RED, markeredgecolor="white", markersize=8, label="Fail"),
    ]
    ax.legend(
        handles=handles,
        loc="upper left",
        bbox_to_anchor=(0.0, -0.145),
        ncols=2,
        fontsize=7.9,
        frameon=False,
        borderaxespad=0.0,
        columnspacing=1.2,
        handletextpad=0.45,
    )
    ax.text(
        0.0,
        -0.280,
        "Markers show observed pass/fail branch-unit states; no-call is defined in the decision grammar but is not observed in this contrast.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=7.3,
        color=MUTED,
    )


def draw_support_panel(ax, supporting: list[dict[str, str]], trace: list[dict[str, str]]) -> None:
    ax.axis("off")
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.text(0.0, 0.97, "d  Support and calibration context", ha="left", va="top", fontsize=11.8, fontweight="bold", color=INK)
    ax.plot([0, 1], [0.895, 0.895], color=BORDER, lw=0.8)

    by_key = {(row["lineage_root"], row["evidence_layer"]): row for row in supporting}
    ax.text(0.0, 0.820, "Bounded support layers", fontsize=8.3, color=MUTED, fontweight="bold", ha="left", va="center")
    ax.text(0.245, 0.775, r"HRAS/YSEQ $A_s$ / $D$", fontsize=8.1, color=MUTED, fontweight="bold", ha="left", va="center")
    ax.text(0.650, 0.775, r"FTDNA $A_s$ (D n/a)", fontsize=8.1, color=MUTED, fontweight="bold", ha="left", va="center")
    y = 0.705
    for lineage in EXPECTED_LINEAGES:
        color = LINEAGE_COLOR[lineage]
        hras = by_key[(lineage, "HRAS/YSEQ")]
        ftdna = by_key[(lineage, "FTDNA Discover")]
        ax.scatter(0.020, y, s=30, color=color, edgecolor="white", linewidth=0.7)
        ax.text(0.050, y, LINEAGE_LABEL[lineage], fontsize=8.2, color=INK, fontweight="bold", ha="left", va="center")
        ax.text(
            0.245,
            y,
            f"{fnum(hras, 'source_adequacy_A_s'):.3f} / {fnum(hras, 'terminal_ln_Q2_contrast_D'):+.3f}",
            fontsize=8.0,
            color=color,
            fontweight="bold",
            ha="left",
            va="center",
        )
        ax.text(0.650, y, f"{fnum(ftdna, 'source_adequacy_A_s'):.3f}; D n/a", fontsize=8.0, color=color, fontweight="bold", ha="left", va="center")
        y -= 0.070

    ax.plot([0, 1], [0.485, 0.485], color=BORDER, lw=0.8)
    separation = trace_row(trace, "Observed PH908 versus negative-control margin separation")
    auroc = trace_row(trace, "AUROC in tested comparison grid")
    permutation = trace_row(trace, "Matched-block permutation test")
    t95 = trace_row(trace, "T95 empirical nearest-rank threshold")
    separation_value = float(extract_metric(separation["observed_result"], "minimum observed separation gap"))
    auroc_value = float(extract_metric(auroc["observed_result"], "PH908-versus-negative-control margin AUROC"))
    permutation_value = float(extract_metric(permutation["observed_result"], "block permutation p-value"))
    calibration_rows = [
        ("Separation gap", f"{separation_value:.3f}", RED),
        ("AUROC", f"{auroc_value:.2f}", BLUE),
        ("Matched-block\npermutation", f"p = {permutation_value:.1e}".replace("e-0", "e-").replace("e+0", "e+"), GREEN),
        ("T95 negative-control\nflags", extract_metric(t95["observed_result"], "Negative-control flagged count"), AMBER),
    ]
    ax.text(0.0, 0.420, "Specificity/calibration trace", fontsize=8.3, color=MUTED, fontweight="bold", ha="left", va="center")
    metric_positions = [(0.0, 0.330), (0.52, 0.330), (0.0, 0.215), (0.52, 0.215)]
    for (label, value, color), (x, y0) in zip(calibration_rows, metric_positions):
        ax.plot([x, x + 0.43], [y0 + 0.045, y0 + 0.045], color=BORDER, lw=0.8)
        ax.text(x, y0 + 0.010, label, fontsize=7.4, color=MUTED, fontweight="bold", ha="left", va="center", linespacing=1.0)
        ax.text(x, y0 - 0.038, value, fontsize=8.2, color=color, fontweight="bold", ha="left", va="center")
    ax.text(
        0.0,
        0.060,
        "FTDNA is bounded direct-child source-adequacy support; calibration metrics are conditional diagnostics, not population-level false-positive rates.",
        ha="left",
        va="bottom",
        fontsize=7.3,
        color=MUTED,
        wrap=True,
    )


def draw_figure(
    primary: list[dict[str, str]],
    supporting: list[dict[str, str]],
    trace: list[dict[str, str]],
    stability: list[dict[str, str]],
) -> plt.Figure:
    fig = plt.figure(figsize=(15.8, 8.8), facecolor="white")
    gs = fig.add_gridspec(
        nrows=2,
        ncols=3,
        height_ratios=[1.0, 1.15],
        width_ratios=[1.05, 1.05, 1.18],
        left=0.070,
        right=0.965,
        bottom=0.250,
        top=0.820,
        hspace=0.46,
        wspace=0.40,
    )
    ax_a = fig.add_subplot(gs[0, 0])
    ax_b = fig.add_subplot(gs[0, 1])
    ax_c = fig.add_subplot(gs[1, 0:2])
    ax_d = fig.add_subplot(gs[:, 2])

    fig.text(
        0.070,
        0.955,
        "Matched source–receiver checks separate compatible R1a comparators from held-out PH908",
        ha="left",
        va="top",
        fontsize=17.2,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.070,
        0.915,
        "Source = Eastern Europe/Russia; receiver = Balkans.",
        ha="left",
        va="top",
        fontsize=10.3,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.070,
        0.890,
        r"Primary YFull $A_s$ and $D$ bars are shown with branch-unit stability markers and bounded support traces.",
        ha="left",
        va="top",
        fontsize=10.4,
        color=MUTED,
    )
    fig.add_artist(Line2D([0.070, 0.965], [0.865, 0.865], color=BORDER, lw=0.8))

    draw_bar_panel(
        ax_a,
        primary,
        "log10_A_s",
        "a  Source adequacy",
        r"$\log_{10}(A_s)$; labels show raw $A_s$",
        r"$A_s = 1$ threshold",
    )
    draw_bar_panel(
        ax_b,
        primary,
        "D",
        "b  Diversity contrast",
        r"$D = \ln(q^2_{\mathrm{receiver}} / q^2_{\mathrm{source}})$",
        r"$D = 0$ threshold",
    )
    draw_stability_panel(ax_c, stability)
    draw_support_panel(ax_d, supporting, trace)

    fig.text(
        0.070,
        0.125,
        "Interpretation boundary: Figure 3 tests a predefined PH908/R1a source–receiver contrast. Branch-unit markers show observed pass/fail stability across audited resolution layers; they are not rarefaction or confidence intervals.",
        ha="left",
        va="top",
        fontsize=8.8,
        color=MUTED,
    )
    fig.text(
        0.070,
        0.097,
        "The figure does not identify PH908 geographic origin, ethnic identity, population continuity, migration route, ancient-DNA confirmation, or a population-level false-positive rate.",
        ha="left",
        va="top",
        fontsize=8.8,
        color=MUTED,
    )
    footer = (
        "Sources: Source data are provided with the numbered Figure 3 source-data bundle. "
        "Primary bars use YFull rows for I-PH908, R-Z280, and R-M458; branch-unit dots derive from Tables 11 and 12; "
        "HRAS/YSEQ and FTDNA Discover values are bounded support layers; calibration values derive from Table 5."
    )
    fig.text(0.070, 0.030, textwrap.fill(footer, 215), ha="left", va="bottom", fontsize=7.2, color=MUTED, linespacing=1.12)
    return fig


def main() -> int:
    validate_manifest()
    headline = read_csv(SOURCE / "fig3_01_headline_coordinates.csv")
    primary = read_csv(SOURCE / "fig3_02_primary_yfull_plot_values.csv")
    supporting = read_csv(SOURCE / "fig3_03_supporting_layer_values.csv")
    trace = read_csv(SOURCE / "fig3_04_specificity_and_calibration_trace.csv")
    claim_audit = read_csv(SOURCE / "fig3_05_figure3_value_validation.csv")
    stability = read_csv(SOURCE / "fig3_06_branch_unit_stability_overlay.csv")
    validate_sources(headline, primary, supporting, trace, claim_audit, stability)

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig = draw_figure(primary, supporting, trace, stability)
    out = FIGURES / "Figure_3_ph908_r1a_source_receiver_contrast"
    fig.savefig(out.with_suffix(".png"), dpi=300)
    pdf_metadata = {
        "Title": "Figure 3 matched source–receiver checks",
        "Author": "Reliability-aware source–receiver model-checking reproduction script",
        "Subject": "Figure 3",
        "Keywords": "Figure 3, PH908, R-Z280, R-M458, source–receiver contrast, branch-unit stability",
        "Creator": "make_figure_3.py",
        "Producer": "matplotlib",
        "CreationDate": datetime(2026, 7, 2, 0, 0, 0),
        "ModDate": datetime(2026, 7, 2, 0, 0, 0),
    }
    fig.savefig(out.with_suffix(".pdf"), metadata=pdf_metadata)
    plt.close(fig)
    print(out.with_suffix(".png"))
    print(out.with_suffix(".pdf"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
