#!/usr/bin/env bash
# Render the report network figures with the installed Gephi (toolkit, no GUI).
# Needs output/2016-2026_{jury,public}_{nodes,edges}.csv from
# `python3 scripts/build_graph.py --aggregate --edge-weight per_opportunity`,
# a JDK and an X/Wayland display (Gephi's PNG export does not run headless).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
GEPHI_HOME="${GEPHI_HOME:-/usr/share/gephi}"
OUT="${1:-$ROOT/output/gephi/report}"
BUILD="$(mktemp -d)"; trap 'rm -rf "$BUILD"' EXIT
PY="${PYTHON:-$ROOT/.venv/bin/python}"   # env locale (vedi .envrc), non il Python di sistema
CP=$(find "$GEPHI_HOME"/gephi/modules "$GEPHI_HOME"/platform/{lib,core,modules} \
       -maxdepth 2 -name '*.jar' -not -path '*/locale/*' -printf '%p:')

"$PY" "$ROOT/scripts/gephi/make_report_graphs.py" "$OUT"
javac -cp "$CP" -d "$BUILD" "$ROOT/scripts/gephi/RenderReportGraphs.java"
java -cp "$BUILD:$CP" RenderReportGraphs "$OUT" \
  "$OUT"/strong_jury.gexf "$OUT"/strong_public.gexf \
  "$OUT"/reciprocal_jury.gexf "$OUT"/reciprocal_public.gexf 2>/dev/null

# Flags as node icons (Gephi Preview cannot draw images): cache, then SVG post-processing.
mkdir -p "$ROOT/output/gephi/flags"
for code in $(cut -d, -f1 "$ROOT/output/2016-2026_jury_nodes.csv" | tail -n +2 | tr -d '\r'); do
  [ -s "$ROOT/output/gephi/flags/$code.svg" ] || \
    curl -sfL -o "$ROOT/output/gephi/flags/$code.svg" "https://flagcdn.com/${code,,}.svg"
done
for name in strong_jury strong_public reciprocal_jury reciprocal_public; do
  "$PY" "$ROOT/scripts/gephi/flag_nodes.py" "$OUT/$name.svg" >/dev/null
  rsvg-convert -w 2400 -b white -o "$OUT/${name}_flags.png" "$OUT/${name}_flags.svg"
done
"$ROOT/scripts/gephi/compose_report_figures.sh" "$OUT"
