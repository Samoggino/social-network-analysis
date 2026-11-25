"""Country flags for the matplotlib figures.

Flags are PNGs from flagcdn.com (160 px wide), downloaded once into
``output/flags/`` (not versioned). Country codes are the ISO 3166 alpha-2 codes
used everywhere in the project.

Helpers:

* ``flag_ticks(ax, codes, axis)`` puts a small flag next to every tick label;
* ``flag_markers(ax, xs, ys, codes, ...)`` draws round flags as markers
  (scatter plots, network nodes), optionally with a coloured ring.
"""

from __future__ import annotations

import urllib.request
from functools import lru_cache
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.offsetbox import AnnotationBbox, OffsetImage

CACHE = Path(__file__).resolve().parents[1] / "output" / "flags"
URL = "https://flagcdn.com/w160/{code}.png"


def flag_path(code: str) -> Path:
    path = CACHE / f"{code.upper()}.png"
    if not path.exists():
        CACHE.mkdir(parents=True, exist_ok=True)
        with urllib.request.urlopen(URL.format(code=code.lower()), timeout=30) as response:
            path.write_bytes(response.read())
    return path


@lru_cache(maxsize=None)
def flag_image(code: str, round_: bool = False) -> np.ndarray:
    """RGBA array of the flag; ``round_`` crops the centre square to a disc."""
    image = plt.imread(flag_path(code))
    if image.dtype != np.float32 and image.max() > 1:
        image = image / 255.0
    if image.shape[2] == 3:
        image = np.dstack([image, np.ones(image.shape[:2])])
    if not round_:
        return image
    h, w = image.shape[:2]
    side = min(h, w)
    top, left = (h - side) // 2, (w - side) // 2
    square = image[top:top + side, left:left + side].copy()
    yy, xx = np.mgrid[:side, :side]
    centre = (side - 1) / 2
    square[..., 3] *= ((yy - centre) ** 2 + (xx - centre) ** 2 <= (side / 2) ** 2)
    return square


def _box(code: str, height_pt: float, round_: bool) -> OffsetImage:
    image = flag_image(code, round_)
    # OffsetImage draws one pixel per point at zoom 1 (dpi-corrected).
    return OffsetImage(image, zoom=height_pt / image.shape[0])


def flag_ticks(ax, codes, axis: str = "x", height_pt: float = 6.0, gap_pt: float = 2.0) -> None:
    """Add a flag between the axis and each tick label.

    The tick labels are pushed out by the width of the flag, so both stay
    readable. ``codes`` must follow the order of the ticks.
    """
    ticks = ax.get_xticks() if axis == "x" else ax.get_yticks()
    tick_len = plt.rcParams[f"{axis}tick.major.size"]
    # Flags have different proportions (CH 1:1, GB 2:1): leave room for the widest.
    widest = max(flag_image(c).shape[1] / flag_image(c).shape[0] for c in codes) * height_pt
    room = height_pt if axis == "x" else widest
    ax.tick_params(axis=axis, pad=room + 2 * gap_pt)
    for tick, code in zip(ticks, codes):
        if axis == "x":
            xy, coords, offset, align = (tick, 0), ("data", "axes fraction"), (0, -tick_len - gap_pt), (0.5, 1.0)
        else:
            xy, coords, offset, align = (0, tick), ("axes fraction", "data"), (-tick_len - gap_pt, 0), (1.0, 0.5)
        ax.add_artist(AnnotationBbox(
            _box(code, height_pt, False), xy, xycoords=coords, xybox=offset,
            boxcoords="offset points", box_alignment=align, frameon=False,
            annotation_clip=False, zorder=5,
        ))


def flag_markers(ax, xs, ys, codes, diameter_pt=18.0, ring=None, ring_pt=2.0,
                 labels: bool = True, fontsize: float = 7.0, zorder: float = 4) -> None:
    """Round flags at data coordinates.

    ``diameter_pt`` may be a scalar or one value per point; ``ring`` is None,
    one colour string, or one colour per point. With ``labels`` the country code is written below the flag.
    """
    n = len(codes)
    diameters = np.broadcast_to(np.asarray(diameter_pt, dtype=float), (n,))
    rings = [ring] * n if ring is None or isinstance(ring, str) else list(ring)
    for x, y, code, d, colour in zip(xs, ys, codes, diameters, rings):
        if colour is not None:
            # A ring drawn as a marker, so its size is in points like the flag.
            ax.plot([x], [y], "o", markersize=d + 2 * ring_pt, color=colour,
                     markeredgewidth=0, zorder=zorder - 0.1)
        ax.add_artist(AnnotationBbox(
            _box(code, d, True), (x, y), frameon=False, zorder=zorder, annotation_clip=False,
        ))
        if labels:
            ax.annotate(code, (x, y), xytext=(0, -(d / 2 + ring_pt + fontsize * 0.7)),
                        textcoords="offset points", ha="center", va="center",
                        fontsize=fontsize, fontweight="bold", color="#222222", zorder=zorder + 0.1)

