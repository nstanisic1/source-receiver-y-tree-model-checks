from __future__ import annotations

import csv
import hashlib
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
        "text.color": "#111827",
    }
)

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "figure_1"
FIGURES = REPO / "figures"

INK = "#111827"
MUTED = "#475569"
BORDER = "#D0D7DE"
GREY_EDGE = "#64748B"
BLUE = "#1F5D8F"
VERMILION = "#B83B32"
AMBER = "#9C6200"
GREY = "#64748B"

BLUE_SOFT = "#EAF2F8"
VERMILION_SOFT = "#F8E3E1"
AMBER_SOFT = "#FFF3D8"
GREY_SOFT = "#F8FAFC"
GREY_PANEL = "#F6F8FA"

EXPECTED_FILES = {
    "source_data/figure_1/fig1_01_framework_steps.csv",
    "source_data/figure_1/fig1_02_decision_state_matrix.csv",
    "source_data/figure_1/fig1_03_claim_tiering_matrix.csv",
    "source_data/figure_1/fig1_04_figure1_value_validation.csv",
    "source_data/figure_1/fig1_source_bundle_note.md",
}

EXPECTED_STATES = {
    "Compatible state",
    "Stable model rejection",
    "Fragile/support-only state",
    "No-call or boundary state",
}


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def validate_manifest() -> None:
    manifest = SOURCE / "fig1_00_source_file_manifest.csv"
    require(manifest.exists(), "Missing Figure 1 source manifest.")
    rows = read_csv(manifest)
    paths = {row["file_path"] for row in rows}
    require(paths == EXPECTED_FILES, f"Unexpected manifest files: {sorted(paths ^ EXPECTED_FILES)}")
    for row in rows:
        path = REPO / row["file_path"]
        require(path.exists(), f"Missing manifest dependency: {row['file_path']}")
        if row["row_count"] != "not_applicable":
            require(len(read_csv(path)) == int(row["row_count"]), f"Row-count mismatch for {row['file_path']}")
        require(sha256(path) == row["sha256"], f"SHA-256 mismatch for {row['file_path']}")


def validate_sources() -> tuple[list[dict[str, str]], list[dict[str, str]], list[dict[str, str]]]:
    validate_manifest()
    steps = read_csv(SOURCE / "fig1_01_framework_steps.csv")
    states = read_csv(SOURCE / "fig1_02_decision_state_matrix.csv")
    tiers = read_csv(SOURCE / "fig1_03_claim_tiering_matrix.csv")
    audit = read_csv(SOURCE / "fig1_04_figure1_value_validation.csv")
    note = (SOURCE / "fig1_source_bundle_note.md").read_text(encoding="utf-8")

    require(len(steps) == 6, "Figure 1 must contain six framework steps.")
    require([row["display_order"] for row in steps] == [str(i) for i in range(1, 7)], "Framework steps are not ordered 1-6.")
    require({row["state_label"] for row in states} == EXPECTED_STATES, "Decision states do not match the manuscript grammar.")
    require(len(tiers) == 5, "Claim-tiering matrix must contain five tiers.")
    require(all(row["audit_status"] == "Pass" for row in audit), "Figure 1 value validation contains a non-pass row.")

    geometry = next(row for row in steps if row["step_label"] == "geometry")["figure_body"]
    require("A_s = n_source / n_receiver" in geometry, "A_s formula missing or changed.")
    require("D = ln(q2_receiver / q2_source)" in geometry, "D natural-log formula missing or changed.")
    require("q2 = 1 / sum(p_i^2)" in geometry, "q2 Hill-order formula missing or changed.")
    require("exact geographic origin" in note, "No-origin claim boundary missing from source note.")
    require("ancient-DNA confirmation" in note, "Ancient-DNA confirmation boundary missing from source note.")

    return steps, states, tiers


def wrap_text(text: str, width: int) -> str:
    wrapped_parts = []
    for part in text.splitlines():
        if not part:
            wrapped_parts.append("")
        else:
            wrapped_parts.append("\n".join(textwrap.wrap(part, width=width, break_long_words=False)))
    return "\n".join(wrapped_parts)


def rounded_box(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    title: str,
    body: str,
    face: str,
    edge: str,
    title_color: str | None = None,
    title_size: float = 12.5,
    body_size: float = 10.0,
    body_width: int = 28,
    title_width: int | None = None,
    body_y_frac: float = 0.45,
    lw: float = 1.8,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.02,rounding_size=2.1",
        facecolor=face,
        edgecolor=edge,
        linewidth=lw,
    )
    ax.add_patch(patch)
    tx = x + 0.08 * w
    ax.text(
        tx,
        y + h - 0.22 * h,
        wrap_text(title, title_width) if title_width else title,
        ha="left",
        va="top",
        fontsize=title_size,
        color=title_color or edge,
        fontweight="bold",
        linespacing=1.02,
    )
    if body:
        ax.text(
            tx,
            y + h - body_y_frac * h,
            wrap_text(body, body_width),
            ha="left",
            va="top",
            fontsize=body_size,
            color=INK,
            linespacing=1.13,
        )


def arrow(ax, x1: float, y1: float, x2: float, y2: float, rad: float = 0.0, lw: float = 2.0) -> None:
    ax.add_patch(
        FancyArrowPatch(
            (x1, y1),
            (x2, y2),
            arrowstyle="-|>",
            mutation_scale=15,
            linewidth=lw,
            color="#667085",
            connectionstyle=f"arc3,rad={rad}",
            shrinkA=3.0,
            shrinkB=3.5,
        )
    )


def save_figure(fig: plt.Figure) -> None:
    FIGURES.mkdir(parents=True, exist_ok=True)
    png = FIGURES / "Figure_1_reliability_aware_source_receiver_audit_framework.png"
    pdf = FIGURES / "Figure_1_reliability_aware_source_receiver_audit_framework.pdf"
    metadata = {
        "Title": "Figure 1 reliability-aware source–receiver model-checking framework",
        "Author": "Reliability-aware source–receiver model-checking reproduction script",
        "Subject": "Figure 1 source–receiver model-checking framework",
        "Keywords": "Figure 1, source–receiver model checking, reliability audit, claim tiering",
        "CreationDate": datetime(2026, 7, 2, 0, 0, 0),
        "ModDate": datetime(2026, 7, 2, 0, 0, 0),
    }
    fig.savefig(png, dpi=300, bbox_inches="tight", facecolor="white")
    fig.savefig(pdf, bbox_inches="tight", facecolor="white", metadata=metadata)
    plt.close(fig)
    print(f"Wrote {png}")
    print(f"Wrote {pdf}")


def draw_panel_label(ax, x: float, y: float, label: str, title: str) -> None:
    ax.text(x, y, label, ha="left", va="top", fontsize=13.2, fontweight="bold", color=INK)
    ax.text(x + 2.8, y, title, ha="left", va="top", fontsize=13.2, fontweight="bold", color=INK)


def workflow_card(
    ax,
    x: float,
    y: float,
    w: float,
    h: float,
    heading: str,
    lines: list[str],
    edge: str,
    face: str,
) -> None:
    patch = FancyBboxPatch(
        (x, y),
        w,
        h,
        boxstyle="round,pad=0.012,rounding_size=0.85",
        facecolor=face,
        edgecolor=edge,
        linewidth=1.25,
    )
    ax.add_patch(patch)
    title_lines = heading.count("\n") + 1
    body_y = y + h - 5.7 - max(0, title_lines - 1) * 1.4
    ax.text(
        x + 1.4,
        y + h - 2.2,
        heading,
        ha="left",
        va="top",
        fontsize=9.9,
        fontweight="bold",
        color=edge,
        linespacing=1.05,
    )
    ax.text(x + 1.4, body_y, "\n".join(lines), ha="left", va="top", fontsize=8.4, color=INK, linespacing=1.08)


def workflow_arrow(ax, x1: float, y: float, x2: float) -> None:
    ax.add_patch(
        FancyArrowPatch(
            (x1, y),
            (x2, y),
            arrowstyle="-|>",
            mutation_scale=11,
            linewidth=1.05,
            color=GREY_EDGE,
            shrinkA=2.0,
            shrinkB=2.0,
        )
    )


def draw_decision_matrix(ax, states: list[dict[str, str]]) -> None:
    state_by_label = {row["state_label"]: row for row in states}
    rows = [
        (
            "Compatible state",
            "source adequate; receiver branch-depleted",
            "stable",
            "load-bearing eligible",
            BLUE,
            BLUE_SOFT,
            "o",
        ),
        (
            "Stable model rejection",
            "specified geometry fails",
            "stable",
            "diagnostic negative",
            VERMILION,
            VERMILION_SOFT,
            "X",
        ),
        (
            "Fragile/support-only state",
            "direction only or scale-sensitive",
            "unstable or bounded",
            "supporting only",
            AMBER,
            AMBER_SOFT,
            "^",
        ),
        (
            "No-call or boundary state",
            "insufficient or boundary data",
            "unscoreable",
            "no claim",
            GREY,
            GREY_SOFT,
            "s",
        ),
    ]
    col_x = [5.2, 31.8, 57.2, 77.4]
    col_w = [24.0, 22.5, 17.4, 17.8]
    headers = ["State", "Geometry / scoreability", "Reliability status", "Claim role"]
    y_top = 39.3
    row_h = 6.9

    for x, w, header in zip(col_x, col_w, headers):
        ax.text(x, y_top + 3.05, header, ha="left", va="center", fontsize=9.0, fontweight="bold", color=MUTED)
        ax.plot([x, x + w], [y_top + 1.55, y_top + 1.55], color=BORDER, lw=0.9)

    for idx, (state_label, geometry, reliability, claim, color, face, marker) in enumerate(rows):
        y = y_top - (idx + 1) * row_h
        row_center = y - 0.35 + (row_h - 0.4) / 2
        ax.add_patch(
            FancyBboxPatch(
                (4.2, y - 0.35),
                91.4,
                row_h - 0.4,
                boxstyle="round,pad=0.006,rounding_size=0.45",
                facecolor=face,
                edgecolor=BORDER,
                linewidth=0.7,
            )
        )
        ax.scatter(6.4, row_center, s=62, marker=marker, color=color, edgecolor="white", linewidth=0.8, zorder=4)
        ax.text(
            8.2,
            row_center,
            state_by_label[state_label]["short_label"],
            ha="left",
            va="center",
            fontsize=9.1,
            fontweight="bold",
            color=color,
        )
        ax.text(col_x[1], row_center, geometry, ha="left", va="center", fontsize=8.35, color=INK)
        ax.text(col_x[2], row_center, reliability, ha="left", va="center", fontsize=8.35, color=INK)
        ax.text(col_x[3], row_center, claim, ha="left", va="center", fontsize=8.35, color=INK)


def draw_figure() -> None:
    steps, states, tiers = validate_sources()
    step_by_label = {row["step_label"]: row for row in steps}

    fig, ax = plt.subplots(figsize=(15.8, 8.2))
    ax.set_xlim(0, 100)
    ax.set_ylim(0, 100)
    ax.axis("off")

    ax.text(4.2, 95.0, "Reliability-aware source–receiver model-checking framework", fontsize=19.0, fontweight="bold", color=INK)
    ax.text(
        4.2,
        91.7,
        "Pre-specified source–receiver hypotheses in public Y trees are scored as compatibility states, not origin states.",
        fontsize=11.7,
        color=MUTED,
    )
    ax.plot([4.2, 95.8], [88.6, 88.6], color=BORDER, lw=0.9)

    draw_panel_label(ax, 4.2, 84.0, "a", "Workflow for a specified source–receiver hypothesis")
    workflow_card(
        ax,
        4.2,
        61.9,
        19.6,
        15.4,
        "Pre-specified\nsource–receiver hypothesis",
        ["lineage root", "source mask", "receiver mask", "boundary exclusions"],
        GREY,
        GREY_SOFT,
    )
    workflow_card(
        ax,
        28.5,
        61.9,
        19.6,
        15.4,
        "Public Y-tree observations",
        ["branch-country labels", "terminal visibility", "country-level visibility"],
        GREY,
        GREY_SOFT,
    )
    workflow_card(
        ax,
        52.8,
        61.9,
        19.6,
        15.4,
        "Geometry",
        [
            r"$A_s = n_{\mathrm{source}}/n_{\mathrm{receiver}}$",
            r"$D = \ln(q^2_{\mathrm{receiver}}/q^2_{\mathrm{source}})$",
            r"$q^2 = 1/\sum p_i^2$",
        ],
        BLUE,
        BLUE_SOFT,
    )
    workflow_card(
        ax,
        77.1,
        61.9,
        18.7,
        15.4,
        "Reliability gates",
        ["branch-unit sensitivity", "country perturbation", "rarefaction/minimum-data", "no-call rules"],
        AMBER,
        AMBER_SOFT,
    )
    workflow_arrow(ax, 23.8, 69.6, 28.5)
    workflow_arrow(ax, 48.1, 69.6, 52.8)
    workflow_arrow(ax, 72.4, 69.6, 77.1)

    ax.text(
        4.2,
        56.4,
        "Claim discipline: load-bearing, supporting, diagnostic negative, boundary/no-call and unsupported uses remain separated.",
        ha="left",
        va="top",
        fontsize=9.1,
        color=MUTED,
    )
    ax.plot([4.2, 95.8], [52.4, 52.4], color=BORDER, lw=0.9)

    draw_panel_label(ax, 4.2, 48.2, "b", "Decision-state matrix")
    draw_decision_matrix(ax, states)

    ax.text(
        4.2,
        4.7,
        "Boundary: outputs are model-checking states for specified public-tree observations; origin, ethnic identity, continuity, route and ancient presence remain outside the framework's inference.",
        fontsize=8.2,
        color=MUTED,
    )

    save_figure(fig)


if __name__ == "__main__":
    draw_figure()
