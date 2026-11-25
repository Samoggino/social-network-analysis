#!/usr/bin/env python3
"""Replace the node circles of a Gephi SVG export with country flags.

Gephi's Preview cannot draw images inside nodes, so RenderReportGraphs.java
exports an SVG and this script post-processes it: every <circle class="id_XX">
becomes the flag of XX clipped to the same circle, with a ring in the node's
original colour (the UN subregion), and the label is moved below the node.
Flags are read from output/gephi/flags/XX.svg (downloaded from flagcdn.com by
render_report.sh) and embedded as data URIs, so the SVG is self-contained.

Usage: python3 scripts/gephi/flag_nodes.py graph.svg... (writes graph_flags.svg)
"""

from __future__ import annotations

import base64
import re
import sys
from pathlib import Path

FLAGS = Path(__file__).resolve().parents[2] / "output" / "gephi" / "flags"
CIRCLE = re.compile(r"<circle\b[^>]*?/>", re.S)
TEXT = re.compile(r"(<text\b[^>]*?>)", re.S)


def attr(tag: str, name: str) -> str:
    m = re.search(rf'\b{name}="([^"]*)"', tag)
    return m.group(1) if m else ""


def flag_uri(code: str) -> str:
    data = (FLAGS / f"{code}.svg").read_bytes()
    return "data:image/svg+xml;base64," + base64.b64encode(data).decode()


def process(svg: str) -> str:
    radius: dict[str, tuple[float, float, float]] = {}
    clips: list[str] = []

    def node(m: re.Match) -> str:
        tag = m.group(0)
        code = attr(tag, "class").removeprefix("id_")
        cx, cy, r = float(attr(tag, "cx")), float(attr(tag, "cy")), float(attr(tag, "r"))
        radius[code] = (cx, cy, r)
        ring = max(1.2, 0.18 * r)
        clips.append(f'<clipPath id="clip_{code}"><circle cx="{cx}" cy="{cy}" r="{r}"/></clipPath>')
        return (
            f'<image x="{cx - 1.5 * r}" y="{cy - r}" width="{3 * r}" height="{2 * r}" '
            f'preserveAspectRatio="xMidYMid slice" clip-path="url(#clip_{code})" '
            f'xlink:href="{flag_uri(code)}"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r - ring / 2}" fill="none" '
            f'stroke="{attr(tag, "fill")}" stroke-width="{ring}"/>'
        )

    svg = CIRCLE.sub(node, svg)

    def label(m: re.Match) -> str:
        tag = m.group(1)
        code = attr(tag, "class").removeprefix("id_")
        if code not in radius:
            return tag
        _, cy, r = radius[code]
        size = re.search(r"font-size=\"([\d.]+)\"", tag)
        offset = r + (float(size.group(1)) if size else 6.0) * 0.95
        return re.sub(r'\by="[^"]*"', f'y="{cy + offset}"', tag)

    svg = TEXT.sub(label, svg)

    # Labels now sit below the nodes: enlarge the viewBox so none is cut off.
    def pad(m: re.Match) -> str:
        x, y, w, h = map(float, m.group(1).split())
        d = 0.06 * max(w, h)
        return f'viewBox="{x - d} {y - d} {w + 2 * d} {h + 2 * d}"'

    svg = re.sub(r'viewBox="([^"]*)"', pad, svg, count=1)
    return svg.replace('<g id="edges">', "<defs>" + "".join(clips) + '</defs>\n    <g id="edges">', 1)


def main() -> int:
    for name in sys.argv[1:]:
        path = Path(name)
        out = path.with_name(path.stem + "_flags.svg")
        out.write_text(process(path.read_text(encoding="utf-8")), encoding="utf-8")
        print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
