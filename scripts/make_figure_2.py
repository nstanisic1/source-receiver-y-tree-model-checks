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
    }
)

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "figure_2"
FIGURES = REPO / "figures"

INK = "#111827"
MUTED = "#475569"
BORDER = "#CBD5E1"
GRID = "#E2E8F0"
COMPATIBLE = "#1F5D8F"
REJECTION = "#B83B32"
FRAGILE = "#9C6200"
BLUE = "#1F5D8F"
PURPLE = "#6D4AA2"
TEAL = "#1B756F"
BROWN = "#6B3710"
NO_CALL = "#64748B"
O_BLUE = "#115C8A"

EXPECTED_STATE_COUNTS = {
    "Robust source-receiver compatible": 118,
    "Robust source-receiver rejection": 206,
    "Stable source-receiver rejection with scale-sensitive D": 87,
    "Fragile or scale-sensitive": 145,
    "No-call or underpowered": 214,
    "Broad-root deferred": 1696,
}

EXPECTED_HIGHLIGHTS = {
    "E-M81",
    "J-P58",
    "O-M119",
    "O-M122",
    "I-PH908",
    "R-M458",
    "R-Z280",
}

EXPECTED_DECISION_GATE_LABELS = [
    "Promote",
    "Demote",
    "No-call/deferred",
]

PLOT_X_MIN = -2.45
PLOT_X_MAX = 2.85
PLOT_Y_MIN = -5.8
PLOT_Y_MAX = 5.8


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def reliability_group(state: str) -> str:
    if state == "Robust source-receiver compatible":
        return "compatible"
    if state in {
        "Robust source-receiver rejection",
        "Stable source-receiver rejection with scale-sensitive D",
    }:
        return "rejection"
    if state == "Fragile or scale-sensitive":
        return "fragile"
    if state in {"No-call or underpowered", "Broad-root deferred"}:
        return "no-call/deferred"
    raise RuntimeError(f"Unexpected reliability state: {state}")


def validate_manifest() -> None:
    manifest = read_csv(SOURCE / "fig2_00_source_file_manifest.csv")
    for row in manifest:
        path = REPO / row["file_path"]
        if not path.exists():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != row["sha256"]:
            raise RuntimeError(
                f"Manifest hash mismatch for {row['file_path']}: "
                f"{observed} != {row['sha256']}"
            )
        if row["row_count"] != "not_applicable":
            observed_rows = len(read_csv(path))
            if observed_rows != int(row["row_count"]):
                raise RuntimeError(
                    f"Manifest row-count mismatch for {row['file_path']}: "
                    f"{observed_rows} != {row['row_count']}"
                )


def validate_sources(
    atlas: list[dict[str, str]],
    highlights: list[dict[str, str]],
    counts: list[dict[str, str]],
    decision_gates: list[dict[str, str]],
    claim_audit: list[dict[str, str]],
) -> None:
    if len(atlas) != 2466:
        raise RuntimeError(f"Expected 2,466 atlas rows, observed {len(atlas)}")
    if len(highlights) != 7:
        raise RuntimeError(f"Expected seven highlighted audit cards, observed {len(highlights)}")
    if {row["lineage_root"] for row in highlights} != EXPECTED_HIGHLIGHTS:
        raise RuntimeError("Highlighted audit-card set drifted")
    if any(row["audit_status"] != "Pass" for row in claim_audit):
        raise RuntimeError("Figure 2 claim-reproduction audit contains a non-pass row")

    count_lookup = {row["atlas_reliability_state"]: int(row["row_count"]) for row in counts}
    if count_lookup != EXPECTED_STATE_COUNTS:
        raise RuntimeError(f"Reliability-state counts drifted: {count_lookup}")

    if len(decision_gates) != 3:
        raise RuntimeError(f"Expected three decision-gate rows, observed {len(decision_gates)}")
    if [row["inset_label"] for row in decision_gates] != EXPECTED_DECISION_GATE_LABELS:
        raise RuntimeError("Decision-gate labels drifted")
    for row in decision_gates:
        if any(value == "" for value in row.values()):
            raise RuntimeError(f"Missing value in decision-gate row: {row}")
        if row["source_summary_file"] != "tables/03_evidence_layer_and_decision_state_definitions.csv":
            raise RuntimeError(f"Decision-gate row no longer traces to Table 3: {row}")

    duplicate_keys = len(atlas) - len(
        {(row["lineage_root"], row["source_mask"], row["receiver_mask"]) for row in atlas}
    )
    if duplicate_keys:
        raise RuntimeError(f"Duplicate broad atlas ordered hypotheses: {duplicate_keys}")

    for row in atlas:
        if any(value == "" for value in row.values()):
            raise RuntimeError(f"Missing value in atlas row: {row}")
        a_s = fnum(row, "deepest_source_adequacy_A_s")
        d_value = fnum(row, "deepest_diversity_contrast_D")
        if a_s <= 0 or not math.isfinite(a_s) or not math.isfinite(d_value):
            raise RuntimeError(f"Unplottable atlas coordinate: {row}")
        expected_call = (
            "Compatible at deepest layer" if a_s > 1 and d_value < 0 else "Rejected at deepest layer"
        )
        if row["deepest_source_receiver_call"] != expected_call:
            raise RuntimeError(f"Deepest-call logic drifted: {row}")
        expected_a_s = float(row["source_terminal_count"]) / float(row["receiver_terminal_count"])
        if abs(expected_a_s - a_s) > 1e-6:
            raise RuntimeError(f"Source-adequacy arithmetic drifted: {row}")

    for row in highlights:
        if any(value == "" for value in row.values()):
            raise RuntimeError(f"Missing value in highlighted audit card: {row}")
        a_s = fnum(row, "deepest_source_adequacy_A_s")
        d_value = fnum(row, "deepest_diversity_contrast_D")
        if a_s <= 0 or not math.isfinite(a_s) or not math.isfinite(d_value):
            raise RuntimeError(f"Unplottable highlighted coordinate: {row}")
        if row["coordinate_layer"] != "Focused predeclared contract":
            raise RuntimeError(f"Highlighted audit card is not marked predeclared: {row}")


def callout(
    ax,
    plotted: dict[str, tuple[float, float, str]],
    root: str,
    label: str,
    xytext: tuple[float, float],
    ha: str,
) -> None:
    x, y, color = plotted[root]
    ax.annotate(
        label,
        xy=(x, y),
        xytext=xytext,
        textcoords="data",
        ha=ha,
        va="center",
        fontsize=9.4,
        fontweight="bold",
        color=color,
        arrowprops={
            "arrowstyle": "-",
            "color": color,
            "lw": 1.0,
            "shrinkA": 5,
            "shrinkB": 5,
        },
        bbox={
            "boxstyle": "round,pad=0.32",
            "fc": "white",
            "ec": color,
            "lw": 0.9,
            "alpha": 0.96,
        },
        zorder=8,
    )


def draw_sidebar(
    ax,
    counts: list[dict[str, str]],
    decision_gates: list[dict[str, str]],
    total_contracts: int,
) -> None:
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.axis("off")

    state_style = [
        ("Robust source-receiver compatible", "Robust compatible", COMPATIBLE, "o"),
        ("Robust source-receiver rejection", "Robust rejection", REJECTION, "x"),
        ("Stable source-receiver rejection with scale-sensitive D", "Stable rejection\n(scale-sensitive D)", REJECTION, "x"),
        ("Fragile or scale-sensitive", "Fragile / scale-sensitive", FRAGILE, "^"),
        ("No-call or underpowered", "No-call / underpowered", NO_CALL, "s"),
        ("Broad-root deferred", "Broad-root deferred", NO_CALL, "s"),
    ]
    count_lookup = {row["atlas_reliability_state"]: int(row["row_count"]) for row in counts}

    ax.text(0.0, 0.985, "b  Atlas state counts", ha="left", va="top", fontsize=12.2, fontweight="bold", color=INK)
    ax.text(
        0.0,
        0.942,
        f"{total_contracts:,} ordered source–receiver hypotheses",
        ha="left",
        va="top",
        fontsize=8.7,
        color=MUTED,
    )

    y = 0.885
    for state, label, color, marker in state_style:
        count = count_lookup[state]
        marker_lw = 1.35 if marker == "x" else 1.0
        ax.scatter(0.025, y - 0.008, s=36, marker=marker, color=color, alpha=0.86, linewidths=marker_lw)
        ax.text(0.065, y, label, ha="left", va="top", fontsize=8.35, color=INK, linespacing=1.05)
        ax.text(0.985, y, f"{count:,}", ha="right", va="top", fontsize=8.7, fontweight="bold", color=INK)
        y -= 0.082 if "\n" in label else 0.063

    ax.plot([0.0, 1.0], [0.470, 0.470], color=BORDER, lw=0.8)

    ax.text(0.0, 0.432, "c  Decision gate", ha="left", va="top", fontsize=12.2, fontweight="bold", color=INK)
    ax.text(
        0.0,
        0.390,
        "Figure-reading grammar, not additional evidence",
        ha="left",
        va="top",
        fontsize=8.1,
        color=MUTED,
    )

    gate_colors = {
        "Promote": COMPATIBLE,
        "Demote": FRAGILE,
        "No-call/deferred": NO_CALL,
    }
    gate_short = {
        "Promote": "load-bearing eligible",
        "Demote": "support or boundary only",
        "No-call/deferred": "abstain",
    }
    gate_markers = {
        "Promote": "o",
        "Demote": "^",
        "No-call/deferred": "s",
    }
    y = 0.320
    for row in decision_gates:
        label = row["inset_label"]
        color = gate_colors[label]
        ax.add_patch(
            FancyBboxPatch(
                (0.0, y - 0.064),
                1.0,
                0.066,
                boxstyle="round,pad=0.006,rounding_size=0.014",
                facecolor="#F8FAFC",
                edgecolor=BORDER,
                linewidth=0.65,
            )
        )
        ax.scatter(0.035, y - 0.024, s=31, marker=gate_markers[label], color=color, linewidths=1.0)
        ax.text(0.080, y - 0.005, label, ha="left", va="top", fontsize=8.35, fontweight="bold", color=color)
        ax.text(0.080, y - 0.034, gate_short[label], ha="left", va="top", fontsize=7.65, color=INK)
        y -= 0.083

    ax.text(
        0.0,
        0.030,
        "Directional compatibility alone is not sufficient for promotion.",
        ha="left",
        va="bottom",
        fontsize=7.05,
        color=MUTED,
        wrap=True,
    )


def draw_figure(
    atlas: list[dict[str, str]],
    highlights: list[dict[str, str]],
    counts: list[dict[str, str]],
    decision_gates: list[dict[str, str]],
) -> plt.Figure:
    group_style = {
        "no-call/deferred": (NO_CALL, 0.16, 16, "no-call/deferred", "s", 0.0),
        "fragile": (FRAGILE, 0.42, 24, "fragile/scale-sensitive", "^", 0.0),
        "rejection": (REJECTION, 0.56, 28, "rejection states", "x", 1.12),
        "compatible": (COMPATIBLE, 0.58, 27, "robust compatible", "o", 0.0),
    }

    for row in atlas:
        row["log10_A_s"] = math.log10(fnum(row, "deepest_source_adequacy_A_s"))
        row["D"] = fnum(row, "deepest_diversity_contrast_D")
        row["plot_group"] = reliability_group(row["atlas_reliability_state"])

    highlight_lookup = {row["lineage_root"]: row for row in highlights}

    fig = plt.figure(figsize=(15.6, 8.5))
    grid = fig.add_gridspec(
        nrows=1,
        ncols=2,
        width_ratios=[4.65, 1.18],
        left=0.065,
        right=0.965,
        bottom=0.178,
        top=0.842,
        wspace=0.070,
    )
    ax = fig.add_subplot(grid[0, 0])
    sidebar = fig.add_subplot(grid[0, 1])

    fig.text(
        0.065,
        0.858,
        "a  YFull reliability atlas",
        ha="left",
        va="bottom",
        fontsize=12.2,
        fontweight="bold",
        color=INK,
    )

    for group in ["no-call/deferred", "fragile", "rejection", "compatible"]:
        color, alpha, size, label, marker, linewidth = group_style[group]
        subset = [row for row in atlas if row["plot_group"] == group]
        scatter_kwargs = {
            "s": size,
            "c": color,
            "alpha": alpha,
            "marker": marker,
            "label": label,
            "zorder": 2,
        }
        if marker == "x":
            scatter_kwargs["linewidths"] = linewidth
        else:
            scatter_kwargs["edgecolors"] = "none"
        ax.scatter([row["log10_A_s"] for row in subset], [row["D"] for row in subset], **scatter_kwargs)

    marker_style = {
        "I-PH908": ("*", REJECTION, 230),
        "R-Z280": ("o", BLUE, 145),
        "R-M458": ("s", BLUE, 145),
        "E-M81": ("^", PURPLE, 125),
        "J-P58": ("D", BROWN, 125),
        "O-M119": ("P", TEAL, 125),
        "O-M122": ("X", O_BLUE, 125),
    }
    plotted: dict[str, tuple[float, float, str]] = {}
    for root in ["I-PH908", "R-Z280", "R-M458", "E-M81", "J-P58", "O-M119", "O-M122"]:
        row = highlight_lookup[root]
        x = math.log10(fnum(row, "deepest_source_adequacy_A_s"))
        y = fnum(row, "deepest_diversity_contrast_D")
        marker, color, size = marker_style[root]
        ax.scatter(
            x,
            y,
            s=size,
            marker=marker,
            color=color,
            edgecolor="white",
            linewidth=1.25,
            zorder=7,
        )
        plotted[root] = (x, y, color)

    callout(ax, plotted, "I-PH908", "held-out PH908\nstable rejection", (-1.48, 2.18), "right")
    callout(ax, plotted, "R-Z280", "R1a comparators\ncompatible", (1.58, -1.06), "left")
    callout(ax, plotted, "E-M81", "E-M81\nsupporting card", (0.04, -0.72), "right")
    callout(ax, plotted, "O-M119", "O cases\nsupport-only", (-0.50, -2.58), "right")
    callout(ax, plotted, "J-P58", "J-P58\nsupporting card", (1.58, -3.16), "left")

    ax.axvline(0, color=NO_CALL, linestyle=":", linewidth=1.05, zorder=1)
    ax.axhline(0, color=NO_CALL, linestyle=":", linewidth=1.05, zorder=1)
    ax.text(0.035, PLOT_Y_MAX - 0.35, r"$A_s = 1$", ha="left", va="top", fontsize=8.8, color=MUTED)
    ax.text(PLOT_X_MAX - 0.08, 0.16, r"$D = 0$", ha="right", va="bottom", fontsize=8.8, color=MUTED)
    ax.set_xlim(PLOT_X_MIN, PLOT_X_MAX)
    ax.set_ylim(PLOT_Y_MIN, PLOT_Y_MAX)
    ax.grid(True, color=GRID, linewidth=0.72, zorder=0)
    ax.set_axisbelow(True)
    ax.set_xlabel(r"$\log_{10}$ source adequacy $A_s$", fontsize=13.5, fontweight="bold", color=INK)
    ax.set_ylabel(r"$D = \ln(q^2_{\mathrm{receiver}} / q^2_{\mathrm{source}})$", fontsize=13.5, fontweight="bold", color=INK)
    ax.tick_params(axis="both", labelsize=11.2, colors=INK)
    for spine in ax.spines.values():
        spine.set_color(INK)
        spine.set_linewidth(0.95)

    draw_sidebar(sidebar, counts, decision_gates, len(atlas))

    legend = ax.legend(
        loc="lower left",
        fontsize=10.0,
        frameon=True,
        framealpha=0.96,
        edgecolor=BORDER,
        facecolor="white",
        borderpad=0.8,
    )
    for handle in legend.legend_handles:
        if isinstance(handle, Line2D):
            handle.set_alpha(0.9)

    fig.text(
        0.065,
        0.955,
        "Reliability atlas shows promotion, demotion and abstention across public Y-tree hypotheses",
        ha="left",
        va="top",
        fontsize=17.2,
        fontweight="bold",
        color=INK,
    )
    fig.text(
        0.065,
        0.915,
        "Background points define reliability context; highlighted audit cards are predeclared benchmarks; decision gates show promotion, demotion and no-call criteria.",
        ha="left",
        va="top",
        fontsize=12.0,
        color=MUTED,
    )
    fig.add_artist(Line2D([0.065, 0.965], [0.885, 0.885], color=BORDER, lw=0.8))

    footer = (
        "Sources: numbered Figure 2 source-data bundle. "
        "The plotted coordinate window is cropped for readability; full atlas coordinates are provided in the source data. "
        "Background points are broad YFull atlas source–receiver hypotheses; highlighted markers are predeclared focused audit cards, not atlas-screen discoveries. "
        "Decision-gate text summarizes predeclared promotion, demotion and no-call criteria and does not reclassify atlas rows. "
        "The figure does not classify geographic origin, ethnic identity, population continuity, migration route or population-level probability."
    )
    fig.text(
        0.065,
        0.040,
        textwrap.fill(footer, 230),
        ha="left",
        va="bottom",
        fontsize=7.5,
        color=MUTED,
        linespacing=1.16,
    )
    return fig


def main() -> int:
    validate_manifest()
    atlas = read_csv(SOURCE / "fig2_01_atlas_background_plot_points.csv")
    highlights = read_csv(SOURCE / "fig2_02_highlighted_focused_contracts.csv")
    counts = read_csv(SOURCE / "fig2_03_reliability_state_counts.csv")
    claim_audit = read_csv(SOURCE / "fig2_04_figure2_value_validation.csv")
    decision_gates = read_csv(SOURCE / "fig2_05_decision_gate_inset.csv")
    validate_sources(atlas, highlights, counts, decision_gates, claim_audit)

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig = draw_figure(atlas, highlights, counts, decision_gates)
    out = FIGURES / "Figure_2_yfull_reliability_atlas"
    fig.savefig(out.with_suffix(".png"), dpi=300)
    pdf_metadata = {
        "Title": "Figure 2 YFull reliability atlas",
        "Author": "Reliability-aware source–receiver model-checking reproduction script",
        "Subject": "Figure 2",
        "Keywords": "Figure 2, YFull, reliability atlas, source–receiver model checking",
        "Creator": "make_figure_2.py",
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
