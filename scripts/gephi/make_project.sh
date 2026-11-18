#!/usr/bin/env bash
# Build output/gephi/eurovision.gephi: one Gephi workspace per styled graph.
# Requires the GEXF files from build_graph.py + style_gexf.py, a JDK (javac)
# and Gephi installed (its libraries are used directly, no GUI).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GEPHI_HOME="${GEPHI_HOME:-/usr/share/gephi}"
OUT="${1:-$ROOT/output/gephi/eurovision.gephi}"
BUILD="$(mktemp -d)"
trap 'rm -rf "$BUILD"' EXIT

CP=$(find "$GEPHI_HOME"/gephi/modules "$GEPHI_HOME"/platform/{lib,core,modules} \
       -maxdepth 2 -name '*.jar' -not -path '*/locale/*' -printf '%p:')

# Workspace order: aggregated networks, then per edition (jury before public),
# first the readable finalists-only >=8 points version, then the full networks.
FILES=("$ROOT"/output/2016-2026_jury_styled.gexf "$ROOT"/output/2016-2026_public_styled.gexf)
for variant in _finalists_min8 ""; do
  for f in "$ROOT"/output/per-year/20??_jury${variant}_styled.gexf; do
    FILES+=("$f" "${f/_jury/_public}")
  done
done

mkdir -p "$(dirname "$OUT")"
javac -cp "$CP" -d "$BUILD" "$ROOT/scripts/gephi/MakeGephiProject.java"
java -Djava.awt.headless=true -cp "$BUILD:$CP" MakeGephiProject "$OUT" "${FILES[@]}" 2>/dev/null
