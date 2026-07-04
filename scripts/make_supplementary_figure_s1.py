from __future__ import annotations

import csv
import hashlib
import json
import math
import textwrap
from collections import Counter
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
    }
)

import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Patch, Polygon, Rectangle


REPO = Path(__file__).resolve().parents[1]
SOURCE = REPO / "source_data" / "supplementary_figure_s1"
FIGURES = REPO / "figures"

MAP_LON_MIN = 13.2
MAP_LON_MAX = 22.2
MAP_LAT_MIN = 41.3
MAP_LAT_MAX = 46.5

INK = "#111827"
MUTED = "#475569"
BORDER = "#CBD5E1"
LAND = "#F8FAFC"
WATER = "#EFF6FF"
GREY = "#94A3B8"
PH908 = "#DC2626"
PH908_DARK = "#991B1B"
TEAL = "#0F766E"
BLUE = "#2563EB"
GREEN = "#16A34A"
VIOLET = "#7C3AED"
AMBER = "#F59E0B"

LINEAGE_COLORS = {
    "E-V13": VIOLET,
    "J2b": TEAL,
    "R1b": BLUE,
    "G2a": GREEN,
}

REGION_LABEL_POSITIONS = {
    "Bosanska Krajina": (16.20, 45.42),
    "Brda / northern Montenegro": (18.62, 42.66),
    "Stari Vlah": (20.42, 43.92),
    "Kosovo": (21.35, 42.36),
}

EXPECTED_REGIONS = set(REGION_LABEL_POSITIONS)

COUNTRY_NAMES = {
    "Albania",
    "Austria",
    "Bosnia and Herzegovina",
    "Bulgaria",
    "Croatia",
    "Greece",
    "Hungary",
    "Italy",
    "Kosovo",
    "Montenegro",
    "North Macedonia",
    "Romania",
    "Serbia",
    "Slovenia",
}


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fnum(row: dict[str, str], key: str) -> float:
    return float(row[key])


def validate_manifest() -> None:
    manifest = read_csv(SOURCE / "s1_00_source_file_manifest.csv")
    for row in manifest:
        path = SOURCE / row["source_file"]
        if not path.exists():
            raise FileNotFoundError(path)
        observed = sha256(path)
        if observed != row["sha256"]:
            raise RuntimeError(
                f"Manifest hash mismatch for {row['source_file']}: "
                f"{observed} != {row['sha256']}"
            )


def validate_sources(
    ancient: list[dict[str, str]],
    relics: list[dict[str, str]],
    visibility: list[dict[str, str]],
    candidates: list[dict[str, str]],
    bands: list[dict[str, str]],
    claims: list[dict[str, str]],
    derivation: list[dict[str, str]],
) -> None:
    visible = [row for row in ancient if row["s1_visible_comparator"] == "Yes"]
    unique_all = {(row["site_or_location"], row["latitude"], row["longitude"]) for row in ancient}
    unique_visible = {
        (row["site_or_location"], row["latitude"], row["longitude"]) for row in visible
    }

    expected_counts = {
        "ancient rows": (len(ancient), 475),
        "visible comparator rows": (len(visible), 146),
        "unique ancient-DNA site/coordinate pairs": (len(unique_all), 100),
        "unique visible site/coordinate pairs": (len(unique_visible), 57),
        "PH908 relic-footprint localities": (len(relics), 11),
        "direct negative controls": (
            sum(row["strict_direct_negative_control"] == "Yes" for row in candidates),
            0,
        ),
        "value validation failures": (
            sum(row["audit_status"] != "Pass" for row in claims),
            0,
        ),
        "relic-footprint derivation rows": (len(derivation), 10),
        "relic-footprint derivation failures": (
            sum(row["audit_status"] != "Pass" for row in derivation),
            0,
        ),
    }
    for label, (observed, expected) in expected_counts.items():
        if observed != expected:
            raise RuntimeError(f"{label} expected {expected}, observed {observed}")

    if any(row["terminal_branch"] == "Y283553" for row in relics):
        raise RuntimeError("Ambiguous Y283553 is present in the relic-footprint layer")

    focus_counts = Counter(row["lineage_focus"] for row in visible)
    for lineage, expected in {"E-V13": 2, "J2b": 56, "R1b": 63, "G2a": 25}.items():
        if focus_counts[lineage] != expected:
            raise RuntimeError(f"{lineage} visible count drifted: {focus_counts[lineage]}")

    region_counts = Counter(row["branch_region"] for row in relics)
    for region, expected in {
        "Bosanska Krajina": 3,
        "Brda / northern Montenegro": 2,
        "Kosovo": 4,
        "Stari Vlah": 2,
    }.items():
        if region_counts[region] != expected:
            raise RuntimeError(f"{region} relic count drifted: {region_counts[region]}")

    if sum(fnum(row, "elevation_m") >= 500 for row in relics) != 7:
        raise RuntimeError("PH908 >=500 m count drifted")
    if sum(fnum(row, "elevation_m") >= 800 for row in relics) != 4:
        raise RuntimeError("PH908 >=800 m count drifted")

    if len(visibility) != 4:
        raise RuntimeError("Regional visibility table must contain four rows")
    if len(bands) != 12:
        raise RuntimeError("Elevation-band summary must contain twelve rows")
    if not any(row["derivation_component"] == "Interpretive boundary" for row in derivation):
        raise RuntimeError("Relic-footprint derivation trace lacks the interpretive boundary row")
    if not any(row["derivation_component"] == "Parent-or-anchor age gate" for row in derivation):
        raise RuntimeError("Relic-footprint derivation trace lacks the parent-or-anchor age-gate row")

    if {row["region"] for row in candidates} != EXPECTED_REGIONS:
        raise RuntimeError("Direct-negative-control candidate regions drifted")
    if {row["region"] for row in visibility} != EXPECTED_REGIONS:
        raise RuntimeError("Visibility-region table drifted")

    for label, rows in {"ancient": ancient, "relics": relics}.items():
        for row in rows:
            lon = fnum(row, "longitude")
            lat = fnum(row, "latitude")
            if not (MAP_LON_MIN <= lon <= MAP_LON_MAX and MAP_LAT_MIN <= lat <= MAP_LAT_MAX):
                raise RuntimeError(f"{label} point outside plotted map bounds: {row}")


def iter_polygons(geometry: dict) -> list[list[list[float]]]:
    if not geometry:
        return []
    kind = geometry.get("type")
    coords = geometry.get("coordinates") or []
    if kind == "Polygon":
        return [coords]
    if kind == "MultiPolygon":
        return coords
    return []


def draw_boundaries(ax) -> None:
    geo_path = SOURCE / "geodata" / "s1_10_natural_earth_admin0_countries.geojson"
    geo = json.loads(geo_path.read_text(encoding="utf-8"))
    for feature in geo["features"]:
        props = feature.get("properties", {})
        names = {
            str(props.get(key))
            for key in ("ADMIN", "NAME", "name", "NAME_LONG", "SOVEREIGNT", "BRK_NAME")
            if props.get(key)
        }
        if not names.intersection(COUNTRY_NAMES):
            continue
        for polygon in iter_polygons(feature.get("geometry") or {}):
            if not polygon:
                continue
            exterior = polygon[0]
            xs = [pt[0] for pt in exterior]
            ys = [pt[1] for pt in exterior]
            if (
                max(xs) < MAP_LON_MIN
                or min(xs) > MAP_LON_MAX
                or max(ys) < MAP_LAT_MIN
                or min(ys) > MAP_LAT_MAX
            ):
                continue
            ax.fill(xs, ys, facecolor="white", edgecolor=BORDER, lw=0.55, zorder=1)


def convex_hull(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    ordered = sorted(set(points))
    if len(ordered) <= 2:
        return ordered

    def cross(o: tuple[float, float], a: tuple[float, float], b: tuple[float, float]) -> float:
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])

    lower: list[tuple[float, float]] = []
    for point in ordered:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], point) <= 0:
            lower.pop()
        lower.append(point)
    upper: list[tuple[float, float]] = []
    for point in reversed(ordered):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], point) <= 0:
            upper.pop()
        upper.append(point)
    return lower[:-1] + upper[:-1]


def draw_map(ax, ancient: list[dict[str, str]], relics: list[dict[str, str]]) -> None:
    ax.set_facecolor(WATER)
    ax.set_xlim(MAP_LON_MIN, MAP_LON_MAX)
    ax.set_ylim(MAP_LAT_MIN, MAP_LAT_MAX)
    ax.set_aspect("equal", adjustable="box")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor(BORDER)
        spine.set_linewidth(0.8)

    draw_boundaries(ax)

    hull = convex_hull([(fnum(row, "longitude"), fnum(row, "latitude")) for row in relics])
    if len(hull) >= 3:
        ax.add_patch(
            Polygon(
                hull,
                closed=True,
                facecolor="#FEE2E2",
                edgecolor=PH908,
                lw=1.2,
                alpha=0.30,
                zorder=2,
            )
        )

    background = [row for row in ancient if row["s1_visible_comparator"] == "No"]
    ax.scatter(
        [fnum(row, "longitude") for row in background],
        [fnum(row, "latitude") for row in background],
        s=11,
        color=GREY,
        alpha=0.34,
        linewidth=0,
        zorder=4,
    )

    for lineage, color in LINEAGE_COLORS.items():
        rows = [row for row in ancient if row["lineage_focus"] == lineage and row["s1_visible_comparator"] == "Yes"]
        ax.scatter(
            [fnum(row, "longitude") for row in rows],
            [fnum(row, "latitude") for row in rows],
            s=34,
            marker="o",
            facecolor=color,
            edgecolor="white",
            linewidth=0.55,
            alpha=0.94,
            zorder=6,
        )

    ax.scatter(
        [fnum(row, "longitude") for row in relics],
        [fnum(row, "latitude") for row in relics],
        s=88,
        marker="X",
        facecolor=PH908,
        edgecolor="white",
        linewidth=0.85,
        alpha=0.96,
        zorder=8,
    )

    region_counts = Counter(row["branch_region"] for row in relics)
    high_counts = Counter(row["branch_region"] for row in relics if fnum(row, "elevation_m") >= 500)
    for region, (lon, lat) in REGION_LABEL_POSITIONS.items():
        rows = [row for row in relics if row["branch_region"] == region]
        if not rows:
            continue
        cx = sum(fnum(row, "longitude") for row in rows) / len(rows)
        cy = sum(fnum(row, "latitude") for row in rows) / len(rows)
        ax.plot([cx, lon], [cy, lat], color=PH908, lw=0.65, alpha=0.65, zorder=9)
        label = f"{region}\n{region_counts[region]} relic-footprint localities;\n{high_counts[region]} >=500 m"
        ax.text(
            lon,
            lat,
            label,
            ha="center",
            va="center",
            fontsize=7.4,
            color=PH908_DARK,
            linespacing=1.18,
            bbox={
                "facecolor": "white",
                "edgecolor": BORDER,
                "alpha": 0.94,
                "boxstyle": "round,pad=0.26",
                "lw": 0.6,
            },
            zorder=10,
        )

    legend_items = [
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=GREY, markeredgecolor=GREY, markersize=5, alpha=0.55, label="Other period-relevant ancient-DNA point"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=VIOLET, markeredgecolor="white", markersize=6, label="E-V13 comparator"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=TEAL, markeredgecolor="white", markersize=6, label="J2b comparator"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=BLUE, markeredgecolor="white", markersize=6, label="R1b comparator"),
        Line2D([0], [0], marker="o", linestyle="None", markerfacecolor=GREEN, markeredgecolor="white", markersize=6, label="G2a comparator"),
        Line2D([0], [0], marker="X", linestyle="None", markerfacecolor=PH908, markeredgecolor="white", markersize=8, label="branch-derived PH908 relic-footprint locality"),
        Patch(facecolor="#FEE2E2", edgecolor=PH908, alpha=0.30, label="branch-derived PH908 relic-footprint convex hull"),
    ]
    ax.legend(
        handles=legend_items,
        loc="lower left",
        bbox_to_anchor=(0.012, 0.012),
        frameon=True,
        facecolor="white",
        edgecolor=BORDER,
        framealpha=0.94,
        fontsize=7.0,
        ncol=2,
        columnspacing=0.65,
        handletextpad=0.4,
    )

    ax.text(
        0.985,
        0.016,
        "Convex hull is a plotting envelope, not an ancient territory or frequency surface.",
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=7.1,
        color=MUTED,
        bbox={"facecolor": "white", "edgecolor": BORDER, "alpha": 0.92, "boxstyle": "round,pad=0.28", "lw": 0.6},
        zorder=20,
    )


def short_site(text: str, width: int = 30) -> str:
    for separator in (" (", ","):
        if separator in text:
            text = text.split(separator, 1)[0]
            break
    if len(text) <= width:
        return text
    if len(text) <= width:
        return text
    return text[: max(width - 3, 0)].rstrip() + "..."


def draw_directness_table(
    ax,
    visibility: list[dict[str, str]],
    candidates: list[dict[str, str]],
) -> None:
    ax.set_axis_off()
    ax.text(0.0, 1.03, "Direct negative-control eligibility", fontsize=11.5, fontweight="bold", color=INK, transform=ax.transAxes)
    ax.text(
        0.0,
        0.965,
        "Each nearest proxy is contextual unless distance, elevation, and sampling-territory criteria all pass.",
        fontsize=7.5,
        color=MUTED,
        transform=ax.transAxes,
    )

    by_region = {row["region"]: row for row in candidates}
    regions = ["Bosanska Krajina", "Brda / northern Montenegro", "Stari Vlah", "Kosovo"]
    columns = [
        ("Region", 0.00, 0.25),
        ("n localities", 0.26, 0.34),
        ("within 75 km", 0.35, 0.52),
        ("nearest identified proxy", 0.53, 0.78),
        ("limiting criterion", 0.79, 1.00),
    ]
    top = 0.875
    row_h = 0.185
    ax.add_patch(Rectangle((0, top), 1.0, 0.075, facecolor="#F8FAFC", edgecolor=BORDER, lw=0.7, transform=ax.transAxes))
    for label, x0, x1 in columns:
        ax.text((x0 + x1) / 2, top + 0.038, label, ha="center", va="center", fontsize=7.1, fontweight="bold", color=INK, transform=ax.transAxes)

    for i, region in enumerate(regions):
        y = top - (i + 1) * row_h
        fill = "white" if i % 2 == 0 else "#F8FAFC"
        ax.add_patch(Rectangle((0, y), 1.0, row_h, facecolor=fill, edgecolor=BORDER, lw=0.55, transform=ax.transAxes))
        vrow = next(row for row in visibility if row["region"] == region)
        crow = by_region[region]
        fail = crow["failed_directness_basis"]
        if crow["within_75_km"] == "No":
            limit = "distance"
        elif crow["elevation_matched_within_75_km"] == "No":
            limit = "elevation"
        elif crow["same_sampling_territory_within_75_km"] == "No":
            limit = "sampling territory"
        else:
            limit = "not applicable"
        proxy = f"{short_site(crow['nearest_identified_proxy_site'], 31)}\n{crow['nearest_identified_proxy_lineage']}, {crow['nearest_identified_proxy_km']} km"
        within = f"all {vrow['all_ancient_dna_rows_within_75_km']}\nvisible {vrow['visible_comparator_rows_within_75_km']}"
        texts = [
            (region, 0.012, "left", 7.0, INK),
            (vrow["footprint_locality_count"], 0.30, "center", 7.2, INK),
            (within, 0.435, "center", 7.0, INK),
            (proxy, 0.655, "center", 6.8, INK),
            (textwrap.fill(limit, 15), 0.895, "center", 7.0, PH908_DARK),
        ]
        for text, x, ha, size, color in texts:
            ax.text(x, y + row_h / 2, text, ha=ha, va="center", fontsize=size, color=color, linespacing=1.18, transform=ax.transAxes)
        if len(fail) < 1:
            raise RuntimeError(f"Missing failed directness basis for {region}")

    ax.text(
        0.0,
        0.02,
        "Result: no listed region supplies a strict direct negative control under the predefined criteria.",
        fontsize=7.4,
        color=MUTED,
        transform=ax.transAxes,
    )


def draw_elevation_panel(ax, bands: list[dict[str, str]]) -> None:
    ax.set_axis_off()
    ax.text(0.0, 1.03, "Elevation visibility of source layers", fontsize=11.5, fontweight="bold", color=INK, transform=ax.transAxes)
    ax.text(
        0.0,
        0.965,
        "Unique sites/localities; counts show how much of each source layer lies in higher-elevation bands.",
        fontsize=7.5,
        color=MUTED,
        transform=ax.transAxes,
    )

    layers = [
        "Period-relevant ancient-DNA sites",
        "Visible E-V13/J2b/R1b/G2a ancient-DNA comparator sites",
        "Branch-derived PH908 relic-footprint localities",
    ]
    labels = ["All aDNA sites", "Visible comparator sites", "PH908 relic-footprint\nlocalities"]
    band_order = ["0-199 m", "200-499 m", "500-799 m", ">=800 m"]
    colors = {"0-199 m": "#DBEAFE", "200-499 m": "#93C5FD", "500-799 m": AMBER, ">=800 m": PH908}
    lookup = {(row["evidence_layer"], row["elevation_band"]): row for row in bands}

    x0 = 0.24
    x1 = 0.94
    bar_h = 0.105
    y_positions = [0.75, 0.52, 0.29]
    for layer, label, y in zip(layers, labels, y_positions):
        total = int(lookup[(layer, "0-199 m")]["total_sites"])
        ax.text(0.0, y + bar_h / 2, f"{label}\n(n={total})", ha="left", va="center", fontsize=7.7, color=INK, linespacing=1.18, transform=ax.transAxes)
        cursor = x0
        for band_name in band_order:
            row = lookup[(layer, band_name)]
            count = int(row["site_count"])
            share = count / total
            width = (x1 - x0) * share
            ax.add_patch(
                Rectangle((cursor, y), width, bar_h, transform=ax.transAxes, facecolor=colors[band_name], edgecolor="white", lw=0.8)
            )
            if width > 0.045:
                ax.text(cursor + width / 2, y + bar_h / 2, str(count), ha="center", va="center", fontsize=7.2, color="white" if band_name == ">=800 m" else INK, transform=ax.transAxes)
            cursor += width
        ax.add_patch(Rectangle((x0, y), x1 - x0, bar_h, transform=ax.transAxes, fill=False, edgecolor=BORDER, lw=0.7))

    legend_x = 0.24
    for band_name in band_order:
        ax.add_patch(Rectangle((legend_x, 0.105), 0.035, 0.035, transform=ax.transAxes, facecolor=colors[band_name], edgecolor="white", lw=0.5))
        ax.text(legend_x + 0.043, 0.123, band_name, ha="left", va="center", fontsize=7.2, color=MUTED, transform=ax.transAxes)
        legend_x += 0.18

    highland_note = "Highland counts: >=500 m = all 8/100, visible 5/57, PH908 7/11. >=800 m = all 1/100, visible 1/57, PH908 4/11."
    ax.text(
        0.0,
        0.005,
        textwrap.fill(highland_note, 92),
        fontsize=7.25,
        color=MUTED,
        linespacing=1.16,
        transform=ax.transAxes,
    )


def main() -> int:
    validate_manifest()

    ancient = read_csv(SOURCE / "s1_01_ancient_dna_plotted_points.csv")
    relics = read_csv(SOURCE / "s1_02_ph908_relic_footprint_locality_points.csv")
    visibility = read_csv(SOURCE / "s1_03_visibility_directness_by_region.csv")
    candidates = read_csv(SOURCE / "s1_04_direct_negative_control_candidate_trace.csv")
    bands = read_csv(SOURCE / "s1_07_elevation_band_summary.csv")
    claims = read_csv(SOURCE / "s1_11_supplementary_figure_s1_value_validation.csv")
    derivation = read_csv(SOURCE / "s1_19_ph908_relic_footprint_derivation_trace.csv")
    validate_sources(ancient, relics, visibility, candidates, bands, claims, derivation)

    FIGURES.mkdir(parents=True, exist_ok=True)
    fig = plt.figure(figsize=(15.8, 8.2), facecolor="white")
    map_ax = fig.add_axes([0.035, 0.125, 0.55, 0.705])
    table_ax = fig.add_axes([0.62, 0.505, 0.345, 0.325])
    elev_ax = fig.add_axes([0.62, 0.125, 0.345, 0.300])

    draw_map(map_ax, ancient, relics)
    draw_directness_table(table_ax, visibility, candidates)
    draw_elevation_panel(elev_ax, bands)

    fig.text(
        0.035,
        0.968,
        "Currently published pre-550 CE ancient-DNA sampling does not yet provide\nstrict direct negative controls for branch-derived PH908 relic-footprint localities",
        ha="left",
        va="top",
        fontsize=13.2,
        fontweight="bold",
        color=INK,
        linespacing=1.08,
    )
    fig.text(
        0.035,
        0.903,
        "The map plots period-relevant ancient-DNA points retained in the curated comparison layer, visible E-V13/J2b/R1b/G2a comparators, and the branch-derived PH908 relic-footprint locality layer used for Supplementary Figure S1.",
        ha="left",
        va="top",
        fontsize=9.0,
        color=MUTED,
    )
    fig.add_artist(Line2D([0.035, 0.965], [0.870, 0.870], color=BORDER, lw=0.8))

    footer = (
        "Sources: numbered Supplementary Figure S1 source-data bundle in source_data/supplementary_figure_s1; country boundaries use the bundled Natural Earth admin-0 layer. "
        "Ancient-DNA points use the 2500 BCE-550 CE window and the plotted map bounds. "
        "The PH908 convex hull is a plotting envelope around the fixed 11-row branch-derived PH908 relic-footprint layer retained after parent-or-anchor age >=1400 ybp; s1_19 documents the age-gated upstream layer, Y283553 exclusion, and plotted-layer reconciliation. "
        "The layer is a modern branch-derived target for directness testing, not an ancient territory, migration route, ethnic map, frequency surface, origin claim, continuity claim, or ancient PH908 evidence. "
        "The figure tests coverage, directness, and ecological visibility only; it is not positive ancient-DNA evidence for PH908, direct negative evidence for PH908 absence, or a claim about origin, ethnic identity, continuity, or route."
    )
    fig.text(0.035, 0.030, textwrap.fill(footer, 185), ha="left", va="bottom", fontsize=7.35, color=MUTED, linespacing=1.2)

    out = FIGURES / "Supplementary_Figure_S1_ancient_dna_directness_visibility"
    fig.savefig(out.with_suffix(".png"), dpi=300)
    pdf_metadata = {
        "Title": "Supplementary Figure S1 ancient-DNA directness and visibility",
        "Author": "Reliability-aware source-receiver model-checking reproduction script",
        "Subject": "Supplementary Figure S1",
        "Keywords": "Supplementary Figure S1, ancient DNA, PH908, directness, visibility",
        "Creator": "make_supplementary_figure_s1.py",
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
