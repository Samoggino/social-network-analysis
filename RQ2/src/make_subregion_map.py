"""Map of the 45 voting countries coloured by UN M49 subregion.

Reads the subregions from RQ2/processed_data/tables/country_attributes_rq2.csv
and draws them on Natural Earth 1:50m country borders, in a Lambert azimuthal
equal-area projection centred on Europe (as EPSG:3035) so that shapes and areas
are not stretched. The borders are
downloaded once into ~/.cache/eurovision-sna/ (or pass --geojson PATH).

Output: RQ2/figures/rq2/rq2_subregion_map.{png,pdf}
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import urllib.request
from collections import defaultdict
from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib.patches import Patch, Polygon

ROOT = Path(__file__).resolve().parents[1]
ATTRIBUTES = ROOT / "processed_data" / "tables" / "country_attributes_rq2.csv"
FIGURES_DIR = ROOT / "figures" / "rq2"

NE_URL = (
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/"
    "v5.1.2/geojson/ne_50m_admin_0_countries.geojson"
)
NE_CACHE = Path.home() / ".cache" / "eurovision-sna" / "ne_50m_admin_0_countries.geojson"
M49_URL = "https://unstats.un.org/unsd/methodology/m49/"

# Okabe-Ito, colour-blind safe.
COLORS = {
    "Northern Europe": "#0072B2",
    "Western Europe": "#E69F00",
    "Southern Europe": "#009E73",
    "Eastern Europe": "#CC79A7",
    "Western Asia": "#D55E00",
    "Australia and New Zealand": "#56B4E9",
}
OTHER = "#e6e6e6"
EDGE = "#ffffff"

# Projection centres (lon, lat): Europe as in EPSG:3035, Australia for the inset.
EUROPE_CENTRE = (10.0, 52.0)
AUSTRALIA_CENTRE = (134.0, -27.0)
# The main frame fits every study country except Russia (clipped) and Australia.
# Only polygons whose centroid falls in this lon/lat box count, which leaves out
# overseas territories (French Guiana, Reunion, Canaries, Azores, Svalbard).
FRAME_EXCLUDE = {"RU", "AU"}
FRAME_BOX = (-26.0, 52.0, 29.0, 72.0)
FRAME_PAD = 0.03

# Countries too small to see at this scale: drawn as a dot as well.
SMALL = {"SM", "MT", "LU"}

# Label positions where the polygon centroid is a poor choice.
LABEL_AT = {
    "RU": (42.0, 57.0), "NO": (9.0, 61.5), "SE": (15.5, 62.5), "FI": (26.0, 63.0),
    "GB": (-1.8, 52.8), "FR": (2.4, 46.6), "HR": (15.6, 45.4), "GR": (22.0, 39.6),
    "IT": (12.8, 42.8), "DK": (9.2, 56.1), "SM": (13.9, 43.5), "MT": (14.4, 35.2),
    "LU": (5.0, 49.3), "CY": (33.2, 34.25), "IL": (34.9, 31.0), "ME": (19.1, 42.5),
    "MK": (21.7, 41.6), "BA": (17.8, 44.2), "SI": (14.8, 46.1), "AL": (20.0, 40.9),
    "NL": (5.6, 52.3), "BE": (4.6, 50.6), "CH": (8.2, 46.8), "AT": (14.0, 47.6),
    "AZ": (47.6, 40.4), "AM": (44.9, 40.2), "GE": (43.6, 42.2), "MD": (28.5, 47.2),
    "IS": (-18.7, 64.9),
}


def load_subregions() -> dict[str, str]:
    with ATTRIBUTES.open(encoding="utf-8-sig", newline="") as handle:
        return {row["country"]: row["region"] for row in csv.DictReader(handle)}


def load_borders(path: Path | None) -> dict:
    if path is None:
        path = NE_CACHE
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            urllib.request.urlretrieve(NE_URL, path)
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


# Natural Earth draws de facto borders and puts Crimea in Russia; the UN
# (and the M49 classification used here) treat it as part of Ukraine.
CRIMEA = (32.0, 36.8, 44.0, 46.3)


def assign_crimea_to_ukraine(borders: dict) -> None:
    features = {f["properties"]["ISO_A2_EH"]: f for f in borders["features"]}
    russia, ukraine = features["RU"]["geometry"], features["UA"]["geometry"]
    lon0, lon1, lat0, lat1 = CRIMEA
    keep, moved = [], []
    for polygon in russia["coordinates"]:
        _, x, y = ring_area_centroid(polygon[0])
        (moved if lon0 <= x <= lon1 and lat0 <= y <= lat1 else keep).append(polygon)
    if not moved:
        return
    russia["coordinates"] = keep
    if ukraine["type"] == "Polygon":
        ukraine["type"], ukraine["coordinates"] = "MultiPolygon", [ukraine["coordinates"]]
    ukraine["coordinates"].extend(moved)


def laea(lon: float, lat: float, centre: tuple[float, float]) -> tuple[float, float]:
    """Lambert azimuthal equal-area projection on the unit sphere."""
    lam, phi = math.radians(lon - centre[0]), math.radians(lat)
    phi0 = math.radians(centre[1])
    cos_c = math.sin(phi0) * math.sin(phi) + math.cos(phi0) * math.cos(phi) * math.cos(lam)
    k = math.sqrt(2 / max(1 + cos_c, 1e-9))
    x = k * math.cos(phi) * math.sin(lam)
    y = k * (math.cos(phi0) * math.sin(phi) - math.sin(phi0) * math.cos(phi) * math.cos(lam))
    return x, y


def rings(geometry: dict) -> list[list[list[float]]]:
    """Exterior rings of a Polygon/MultiPolygon (holes are irrelevant here)."""
    if geometry["type"] == "Polygon":
        return [geometry["coordinates"][0]]
    return [polygon[0] for polygon in geometry["coordinates"]]


def ring_area_centroid(ring: list[list[float]]) -> tuple[float, float, float]:
    area = cx = cy = 0.0
    for (x0, y0), (x1, y1) in zip(ring, ring[1:] + ring[:1]):
        cross = x0 * y1 - x1 * y0
        area += cross
        cx += (x0 + x1) * cross
        cy += (y0 + y1) * cross
    area /= 2
    if area == 0:
        return 0.0, ring[0][0], ring[0][1]
    return abs(area), cx / (6 * area), cy / (6 * area)


def laea_dist(lon: float, lat: float, centre) -> float:
    """Angular distance (radians) from the projection centre."""
    phi, phi0 = math.radians(lat), math.radians(centre[1])
    lam = math.radians(lon - centre[0])
    cos_c = math.sin(phi0) * math.sin(phi) + math.cos(phi0) * math.cos(phi) * math.cos(lam)
    return math.acos(max(-1.0, min(1.0, cos_c)))


def frame(borders: dict, codes, centre, box) -> tuple[float, ...]:
    """Projected bounding box of the given countries' polygons inside `box`."""
    xs, ys = [], []
    for feature in borders["features"]:
        code = feature["properties"]["ISO_A2_EH"]
        if code not in codes:
            continue
        for ring in rings(feature["geometry"]):
            _, clon, clat = ring_area_centroid(ring)
            if not (box[0] <= clon <= box[1] and box[2] <= clat <= box[3]):
                continue
            for lon, lat in ring:
                x, y = laea(lon, lat, centre)
                xs.append(x)
                ys.append(y)
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    pad = FRAME_PAD * max(x1 - x0, y1 - y0)
    return x0 - pad, x1 + pad, y0 - pad, y1 + pad


def draw(ax, borders: dict, subregion: dict[str, str], centre, extent,
         labels: bool) -> None:
    x0, x1, y0, y1 = extent
    for feature in borders["features"]:
        code = feature["properties"]["ISO_A2_EH"]
        color = COLORS[subregion[code]] if code in subregion else OTHER
        for ring in rings(feature["geometry"]):
            # Skip what lies far behind the projection centre (it would wrap).
            if all(laea_dist(lon, lat, centre) > 2.6 for lon, lat in ring):
                continue
            points = [laea(lon, lat, centre) for lon, lat in ring]
            ax.add_patch(Polygon(points, closed=True, facecolor=color,
                                 edgecolor=EDGE, linewidth=0.4))
        if code not in subregion:
            continue
        _, clon, clat = max(ring_area_centroid(r) for r in rings(feature["geometry"]))
        if code in SMALL:
            ax.plot(*laea(clon, clat, centre), "o", ms=5, color=color,
                    mec="#333333", mew=0.6, zorder=3)
        if labels:
            x, y = laea(*LABEL_AT.get(code, (clon, clat)), centre)
            if x0 <= x <= x1 and y0 <= y <= y1:
                ax.text(x, y, code, ha="center", va="center", fontsize=6.5,
                        color="#1a1a1a", zorder=4)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_aspect("equal")
    ax.set_xticks([])
    ax.set_yticks([])
    for spine in ax.spines.values():
        spine.set_edgecolor("#999999")
        spine.set_linewidth(0.6)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--geojson", type=Path, default=None,
                        help="Natural Earth admin-0 GeoJSON (downloaded if omitted)")
    args = parser.parse_args()

    subregion = load_subregions()
    borders = load_borders(args.geojson)
    assign_crimea_to_ukraine(borders)
    missing = set(subregion) - {f["properties"]["ISO_A2_EH"] for f in borders["features"]}
    if missing:
        raise SystemExit(f"countries missing from the borders file: {sorted(missing)}")

    extent = frame(borders, set(subregion) - FRAME_EXCLUDE, EUROPE_CENTRE, FRAME_BOX)
    width, height = extent[1] - extent[0], extent[3] - extent[2]
    fig, ax = plt.subplots(figsize=(9, 9 * height / width + 0.5))
    ax.set_facecolor("#f4f8fb")
    draw(ax, borders, subregion, EUROPE_CENTRE, extent, labels=True)

    # Australia inset, bottom-left over the Atlantic.
    inset = ax.inset_axes([0.015, 0.02, 0.2, 0.2])
    inset.set_facecolor("#f4f8fb")
    au_extent = frame(borders, {"AU"}, AUSTRALIA_CENTRE, (110.0, 155.0, -45.0, -9.0))
    draw(inset, borders, subregion, AUSTRALIA_CENTRE, au_extent, labels=False)
    inset.text(*laea(*AUSTRALIA_CENTRE, AUSTRALIA_CENTRE), "AU",
               ha="center", va="center", fontsize=6.5)

    counts = defaultdict(int)
    for region in subregion.values():
        counts[region] += 1
    handles = [Patch(facecolor=COLORS[r], edgecolor="none", label=f"{r} ({counts[r]})")
               for r in COLORS]
    handles.append(Patch(facecolor=OTHER, edgecolor="none", label="Not in the study"))
    ax.legend(handles=handles, loc="upper left", fontsize=8, frameon=True,
              framealpha=0.95, title="UN M49 subregion", title_fontsize=8.5)

    fig.text(0.5, 0.015,
             f"Subregions: UN M49 standard ({M49_URL}).\n"
             "Borders: Natural Earth 1:50m, Crimea shown as part of Ukraine. "
             "Dots mark San Marino, Malta and Luxembourg.",
             ha="center", fontsize=7, color="#444444", url=M49_URL)
    fig.tight_layout(rect=(0, 0.045, 1, 1))

    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    for ext in ("png", "pdf"):
        fig.savefig(FIGURES_DIR / f"rq2_subregion_map.{ext}", dpi=220)
    print(f"saved {FIGURES_DIR / 'rq2_subregion_map.png'} (.pdf)")


if __name__ == "__main__":
    main()
