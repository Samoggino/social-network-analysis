#!/usr/bin/env bash
# Put the jury and public Gephi renders side by side with titles and the
# subregion legend (ImageMagick 7). Usage: compose_report_figures.sh [dir]
set -euo pipefail
DIR="${1:-$(cd "$(dirname "$0")/../.." && pwd)/output/gephi/report}"
cd "$DIR"
FONT=DejaVu-Sans
legend() {
  local args=() ; local x=0
  while [ $# -gt 0 ]; do
    args+=(-fill "$1" -draw "circle $((x+26)),45 $((x+48)),45" -fill black -annotate +$((x+60))+62 "$2")
    x=$((x + 60 + ${#2} * 31 + 60)); shift 2
  done
  magick -size 4200x90 xc:white -font $FONT -pointsize 52 "${args[@]}" -trim -bordercolor white -border 20 legend.png
}
legend '#0072B2' 'Northern Europe' '#E69F00' 'Western Europe' '#009E73' 'Southern Europe' \
       '#CC79A7' 'Eastern Europe' '#D55E00' 'Western Asia' '#56B4E9' 'Australia' '#C8C8C8' 'Tie across subregions'
for fig in strong reciprocal; do
  for layer in jury public; do
    title=$([ $layer = jury ] && echo "Jury" || echo "Televote")
    magick "${fig}_${layer}_flags.png" -trim +repage -resize 1800x1800 -bordercolor white -border 40 \
      -background white -gravity north -splice 0x140 -font $FONT -pointsize 80 -fill black \
      -annotate +0+25 "$title" "_${fig}_${layer}.png"
  done
  magick "_${fig}_jury.png" "_${fig}_public.png" -gravity center -background white +append +repage "_${fig}_pair.png"
  # The legend follows the width of the panels, never the other way round.
  width=$(magick identify -format %w "_${fig}_pair.png")
  magick "_${fig}_pair.png" \( legend.png -resize "${width}x>" \) -gravity center -background white -append \
    -bordercolor white -border 20 -alpha remove -alpha off +repage -depth 8 "fig_${fig}_ties.png"
  rm "_${fig}_pair.png"
  rm "_${fig}_jury.png" "_${fig}_public.png"
  echo "$DIR/fig_${fig}_ties.png"
done
rm legend.png
