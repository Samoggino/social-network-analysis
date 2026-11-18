#!/usr/bin/env python3
"""Build directed, weighted Eurovision vote networks (jury and televote kept
separate) and export them for Gephi.

The data rules are the same as the group's ``build_eurovision_data.py``:

* editions 2016-2026, Grand Final only (2020 was cancelled and is skipped);
* the jury and televote ("public") layers are always kept separate;
  ``total`` (jury + public) is available only on request;
* the aggregated "Rest of the World" televote (``WLD``) is excluded,
  because it is not a country;
* every ballot is validated: no self-votes, points in {0, 1-8, 10, 12},
  every national voter scores every other finalist and its positive points
  are exactly 1, 2, ..., 8, 10, 12 (58 points), jury and public voter sets
  coincide.  Any inconsistency stops the script.

Semantics of the graph
----------------------
* Node = country.  In one edition a country can be a finalist (it can
  receive points) or only a voter (eliminated in the semi-final: it votes
  in the final but cannot receive points).
* Directed edge ``A -> B`` = ``A`` awarded points to ``B``; weight = points.
* An *opportunity* is a pair (A, B) where A could vote for B: A is a
  national voter, B a finalist and A != B.  In the matrices a 0 is an
  opportunity without points, an empty cell is an impossible vote.  A 0 is
  never an edge, but it still counts in the normalised weights.

Examples
--------
The 20 annual networks (10 editions x jury/public), one GEXF each::

    python3 scripts/build_graph.py

One edition, both layers::

    python3 scripts/build_graph.py --year 2025

Only finalists (the sub-network used for reciprocity and triads in RQ1)::

    python3 scripts/build_graph.py --finalists-only

One network aggregated over 2016-2026 per layer, weighted per opportunity::

    python3 scripts/build_graph.py --aggregate --edge-weight per_opportunity

Also write the matrices and tables in the format of build_eurovision_data.py::

    python3 scripts/build_graph.py --matrices

Who voted for Italy (ego network, incoming edges), per edition::

    python3 scripts/build_graph.py --country IT --ego-mode in

The script uses only the Python standard library.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATA_DIR = PROJECT_ROOT / "dataset" / "data"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "output"

FIRST_YEAR = 2016  # first edition with separate jury and televote points
LAYERS = ("jury", "public")
SCORE_ALIASES = {
    "jury": ("jury",),
    "public": ("public",),
    "tele": ("public",),
    "televote": ("public",),
    "both": ("jury", "public"),
    "total": ("total",),
}
POINT_VALUES = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12}
BALLOT_POINTS = [1, 2, 3, 4, 5, 6, 7, 8, 10, 12]
WLD_CODE = "WLD"

FLAG_CODE_OVERRIDES = {"GB": "gb", "GB-WLS": "gb-wls"}
FLAG_URL_TEMPLATE = "https://flagcdn.com/w160/{code}.png"


# ---------------------------------------------------------------------------
# Dataset loading and validation
# ---------------------------------------------------------------------------


def resolve_data_dir(path: Path) -> Path:
    """Accept both the dataset root (``dataset-main``) and its ``data`` dir."""
    for candidate in (path, path / "data", path / "dataset-main" / "data"):
        if (candidate / "senior").is_dir():
            return candidate
    raise SystemExit(f"[error] dataset not found in {path} (expected data/senior/)")


def load_json(path: Path) -> dict:
    with path.open(encoding="utf-8-sig") as stream:
        return json.load(stream)


def load_country_names(data_dir: Path) -> dict[str, str]:
    path = data_dir / "countries.json"
    if not path.is_file():
        return {}
    return {str(code): str(name) for code, name in load_json(path).items()}


@dataclass
class Edition:
    """Validated Grand Final of one year."""

    year: int
    voters: set[str]  # national voters (WLD excluded)
    finalists: set[str]
    # (layer, source, target) -> points, for every opportunity (zeros included)
    votes: dict[tuple[str, str, str], int]

    def countries(self) -> list[str]:
        return sorted(self.voters | self.finalists)

    def opportunities(self) -> list[tuple[str, str]]:
        """Every pair (source, target) in which source could vote target."""
        return [
            (source, target)
            for source in sorted(self.voters)
            for target in sorted(self.finalists)
            if source != target
        ]

    def points(self, layer: str, source: str, target: str) -> int:
        if layer == "total":
            return self.votes["jury", source, target] + self.votes["public", source, target]
        return self.votes[layer, source, target]


def read_edition(data_dir: Path, year: int) -> Edition:
    """Read and validate one Grand Final (same checks as build_eurovision_data.py)."""
    directory = data_dir / "senior" / str(year)

    contestants: dict[int, str] = {}
    for file in sorted((directory / "contestants").glob("*/contestant.json")):
        info = load_json(file)
        if info["id"] in contestants:
            raise ValueError(f"{year}: duplicate contestant ID {info['id']}")
        contestants[info["id"]] = info["country"]
    if not contestants:
        raise ValueError(f"{year}: no contestant metadata found")

    finalists: set[str] = set()
    votes: dict[tuple[str, str, str], int] = {}
    final = load_json(directory / "rounds" / "final.json")
    for performance in final["performances"]:
        target = contestants[performance["contestantId"]]
        if target in finalists:
            raise ValueError(f"{year}: duplicate finalist {target}")
        finalists.add(target)
        seen_layers = set()
        for score in performance["scores"]:
            layer = score.get("name", "").lower()
            if layer == "tele":
                layer = "public"
            if layer not in LAYERS:
                continue  # "total" is recomputed from jury + public
            if layer in seen_layers:
                raise ValueError(f"{year}: duplicate {layer} result for {target}")
            seen_layers.add(layer)
            ballot = score["votes"]
            if sum(ballot.values()) != score["points"]:
                raise ValueError(f"{year}/{layer}/{target}: inconsistent score total")
            for source, points in ballot.items():
                if type(points) is not int or points not in POINT_VALUES:
                    raise ValueError(f"{year}/{layer}/{source}->{target}: invalid points")
                if source == target:
                    raise ValueError(f"{year}: self vote by {source}")
                key = (layer, source, target)
                if key in votes:
                    raise ValueError(f"{year}: duplicate vote {key}")
                votes[key] = points
        if seen_layers != set(LAYERS):
            raise ValueError(f"{year}: jury/public results missing for {target}")

    # Ballot checks: every national voter scores every other finalist once,
    # and its positive points are exactly the Eurovision scale (58 points).
    voters = {
        layer: {s for l, s, _ in votes if l == layer and s != WLD_CODE}
        for layer in LAYERS
    }
    if voters["jury"] != voters["public"]:
        raise ValueError(f"{year}: jury and public voter sets differ")
    for layer in LAYERS:
        for source in voters[layer]:
            targets = {t for l, s, t in votes if l == layer and s == source}
            if targets != finalists - {source}:
                raise ValueError(f"{year}/{layer}/{source}: incomplete or unexpected targets")
            positive = sorted(votes[layer, source, t] for t in targets if votes[layer, source, t] > 0)
            if positive != BALLOT_POINTS:
                raise ValueError(f"{year}/{layer}/{source}: invalid ballot distribution")

    national = {k: v for k, v in votes.items() if k[1] != WLD_CODE}
    return Edition(year=year, voters=voters["jury"], finalists=finalists, votes=national)


def select_years(data_dir: Path, year_from: int, year_to: int) -> tuple[list[int], list[int]]:
    """Return (years with a Grand Final, years in range without one)."""
    years, skipped = [], []
    for year in range(max(year_from, FIRST_YEAR), year_to + 1):
        final = data_dir / "senior" / str(year) / "rounds" / "final.json"
        if final.is_file() and (load_json(final) or {}).get("performances"):
            years.append(year)
        elif (data_dir / "senior" / str(year)).is_dir():
            skipped.append(year)  # e.g. 2020, cancelled
    return years, skipped


# ---------------------------------------------------------------------------
# Network construction
# ---------------------------------------------------------------------------


@dataclass
class EdgeStats:
    """Aggregated statistics of one ordered pair ``source -> target``."""

    weight: float = 0.0  # total points
    n_votes: int = 0  # awards with points >= min_points
    opportunities: int = 0  # editions in which source could vote target
    years: set[int] = field(default_factory=set)  # editions with an award

    @property
    def weight_mean(self) -> float:
        """Average points per award (intensity, given that the pair was chosen)."""
        return self.weight / self.n_votes if self.n_votes else 0.0

    @property
    def per_opportunity(self) -> float:
        """Average points per opportunity (zeros included)."""
        return self.weight / self.opportunities if self.opportunities else 0.0

    @property
    def frequency(self) -> float:
        """Share of the opportunities in which source awarded points to target."""
        return self.n_votes / self.opportunities if self.opportunities else 0.0


@dataclass
class Network:
    nodes: dict[str, dict[str, object]]
    edges: dict[tuple[str, str], EdgeStats]


def build_network(
    editions: list[Edition],
    layer: str,
    min_points: int,
    finalists_only: bool,
    country_names: dict[str, str],
) -> Network:
    """Aggregate one layer over the given editions.

    With ``finalists_only`` an edition contributes only the pairs between
    its finalists (non-finalists can vote but never receive points, so they
    cannot take part in reciprocal ties or cycles).
    """
    stats: dict[tuple[str, str], EdgeStats] = {}
    years_voting: defaultdict[str, set[int]] = defaultdict(set)
    years_finalist: defaultdict[str, set[int]] = defaultdict(set)
    opp_in: defaultdict[str, int] = defaultdict(int)
    opp_out: defaultdict[str, int] = defaultdict(int)

    for edition in editions:
        voters = edition.voters & edition.finalists if finalists_only else edition.voters
        for country in voters:
            years_voting[country].add(edition.year)
        for country in edition.finalists:
            years_finalist[country].add(edition.year)

        for source, target in edition.opportunities():
            if source not in voters:
                continue
            opp_out[source] += 1
            opp_in[target] += 1
            edge = stats.setdefault((source, target), EdgeStats())
            edge.opportunities += 1
            points = edition.points(layer, source, target)
            if points > 0 and points >= min_points:
                edge.weight += points
                edge.n_votes += 1
                edge.years.add(edition.year)

    edges = {pair: s for pair, s in stats.items() if s.n_votes > 0}

    nodes: dict[str, dict[str, object]] = {}
    for code in sorted(set(years_voting) | set(years_finalist)):
        flag = FLAG_CODE_OVERRIDES.get(code, code.lower())
        nodes[code] = {
            "id": code,
            "label": country_names.get(code, code),
            "code": code,
            "role": "finalist" if years_finalist[code] else "voter_only",
            "years_finalist": len(years_finalist[code]),
            "years_voting": len(years_voting[code]),
            "opportunities_in": opp_in[code],
            "opportunities_out": opp_out[code],
            "flag_url": FLAG_URL_TEMPLATE.format(code=flag),
        }
    return with_edge_totals(nodes, edges)


def with_edge_totals(nodes: dict[str, dict[str, object]], edges: dict[tuple[str, str], EdgeStats]) -> Network:
    """Return a network whose node strengths and degrees are computed on ``edges``."""
    zero = {"in_weight": 0.0, "out_weight": 0.0, "in_degree": 0, "out_degree": 0,
            "votes_received": 0, "votes_given": 0}
    nodes = {code: {**node, **zero} for code, node in nodes.items()}
    for (source, target), edge in edges.items():
        nodes[source]["out_weight"] += edge.weight
        nodes[target]["in_weight"] += edge.weight
        nodes[source]["out_degree"] += 1
        nodes[target]["in_degree"] += 1
        nodes[source]["votes_given"] += edge.n_votes
        nodes[target]["votes_received"] += edge.n_votes
    return Network(nodes=nodes, edges=edges)


def ego_network(network: Network, country: str, mode: str) -> Network:
    """Keep only the edges incident to ``country`` (and the nodes they touch)."""
    edges = {
        (s, t): e
        for (s, t), e in network.edges.items()
        if (mode in ("in", "both") and t == country) or (mode in ("out", "both") and s == country)
    }
    keep = {country} | {s for s, _ in edges} | {t for _, t in edges}
    return with_edge_totals({c: n for c, n in network.nodes.items() if c in keep}, edges)


# ---------------------------------------------------------------------------
# Exporters
# ---------------------------------------------------------------------------

NODE_ATTRIBUTES = [
    ("code", "string"),
    ("role", "string"),
    ("years_finalist", "integer"),
    ("years_voting", "integer"),
    ("opportunities_in", "integer"),
    ("opportunities_out", "integer"),
    ("in_weight", "double"),
    ("out_weight", "double"),
    ("in_degree", "integer"),
    ("out_degree", "integer"),
    ("votes_received", "integer"),
    ("votes_given", "integer"),
    ("flag_url", "string"),
]
EDGE_ATTRIBUTES = [
    ("points", "double"),
    ("n_votes", "integer"),
    ("opportunities", "integer"),
    ("frequency", "double"),
    ("weight_mean", "double"),
    ("per_opportunity", "double"),
    ("first_year", "integer"),
    ("last_year", "integer"),
    ("years", "string"),
]
EDGE_WEIGHTS = ("sum", "mean", "per_opportunity", "frequency")


def fmt(value: object) -> str:
    """Format numbers without scientific notation or useless decimals."""
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.6f}".rstrip("0").rstrip(".")
    return str(value)


def edge_values(edge: EdgeStats, weight_column: str) -> dict[str, object]:
    years = sorted(edge.years)
    return {
        "weight": {
            "sum": edge.weight,
            "mean": edge.weight_mean,
            "per_opportunity": edge.per_opportunity,
            "frequency": edge.frequency,
        }[weight_column],
        "points": edge.weight,
        "n_votes": edge.n_votes,
        "opportunities": edge.opportunities,
        "frequency": edge.frequency,
        "weight_mean": edge.weight_mean,
        "per_opportunity": edge.per_opportunity,
        "first_year": years[0] if years else "",
        "last_year": years[-1] if years else "",
        "years": ",".join(map(str, years)),
    }


def sorted_nodes(network: Network) -> list[dict[str, object]]:
    return sorted(network.nodes.values(), key=lambda n: (-n["in_weight"], str(n["label"])))


def sorted_edges(network: Network, weight_column: str) -> list[tuple[tuple[str, str], dict[str, object]]]:
    rows = [(pair, edge_values(e, weight_column)) for pair, e in network.edges.items()]
    return sorted(rows, key=lambda item: (-item[1]["weight"], item[0]))


def write_gexf(path: Path, network: Network, weight_column: str, description: str) -> None:
    """Write a GEXF 1.2 file (Gephi's native format)."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">',
        f'  <meta lastmodifieddate="{today}">',
        "    <creator>Eurovision SNA project</creator>",
        f"    <description>{escape(description)}</description>",
        "  </meta>",
        '  <graph mode="static" defaultedgetype="directed">',
    ]
    for cls, attributes in (("node", NODE_ATTRIBUTES), ("edge", EDGE_ATTRIBUTES)):
        lines.append(f'    <attributes class="{cls}" mode="static">')
        for name, kind in attributes:
            lines.append(f"      <attribute id={quoteattr(name)} title={quoteattr(name)} type={quoteattr(kind)}/>")
        lines.append("    </attributes>")

    nodes = sorted_nodes(network)
    lines.append(f'    <nodes count="{len(nodes)}">')
    for node in nodes:
        lines.append(f"      <node id={quoteattr(node['id'])} label={quoteattr(node['label'])}>")
        lines.append("        <attvalues>")
        for name, _ in NODE_ATTRIBUTES:
            lines.append(f"          <attvalue for={quoteattr(name)} value={quoteattr(fmt(node[name]))}/>")
        lines.append("        </attvalues>")
        lines.append("      </node>")
    lines.append("    </nodes>")

    edges = sorted_edges(network, weight_column)
    lines.append(f'    <edges count="{len(edges)}">')
    for edge_id, ((source, target), values) in enumerate(edges):
        lines.append(
            f'      <edge id="{edge_id}" source={quoteattr(source)} target={quoteattr(target)} '
            f"weight={quoteattr(fmt(values['weight']))}>"
        )
        lines.append("        <attvalues>")
        for name, _ in EDGE_ATTRIBUTES:
            lines.append(f"          <attvalue for={quoteattr(name)} value={quoteattr(fmt(values[name]))}/>")
        lines.append("        </attvalues>")
        lines.append("      </edge>")
    lines.append("    </edges>")
    lines += ["  </graph>", "</gexf>"]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_csv(path: Path, header: list[str], rows: list[list[object]], encoding: str = "utf-8") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding=encoding, newline="") as stream:
        writer = csv.writer(stream)
        writer.writerow(header)
        writer.writerows(rows)


def write_graph_files(base: Path, network: Network, weight_column: str, description: str) -> Path:
    """Write ``base.gexf``, ``base_nodes.csv`` and ``base_edges.csv``."""
    base.parent.mkdir(parents=True, exist_ok=True)
    gexf = base.with_name(base.name + ".gexf")
    write_gexf(gexf, network, weight_column, description)
    node_columns = [name for name, _ in NODE_ATTRIBUTES]
    write_csv(
        base.with_name(base.name + "_nodes.csv"),
        ["Id", "Label", *node_columns],
        [[n["id"], n["label"], *(fmt(n[c]) for c in node_columns)] for n in sorted_nodes(network)],
    )
    edge_columns = [name for name, _ in EDGE_ATTRIBUTES]
    write_csv(
        base.with_name(base.name + "_edges.csv"),
        ["Source", "Target", "Type", "Weight", *edge_columns],
        [
            [s, t, "Directed", fmt(v["weight"]), *(fmt(v[c]) for c in edge_columns)]
            for (s, t), v in sorted_edges(network, weight_column)
        ],
    )
    return gexf


def write_matrices(output_dir: Path, editions: list[Edition], layers: tuple[str, ...]) -> int:
    """Write matrices and tables in the same format as build_eurovision_data.py.

    Empty cell = impossible vote; 0 = possible vote without points.
    Returns the number of opportunities written to votes_master.csv.
    """
    master_rows = []
    voting_years: defaultdict[str, set[int]] = defaultdict(set)
    finalist_years: defaultdict[str, set[int]] = defaultdict(set)
    for edition in editions:
        for country in edition.voters:
            voting_years[country].add(edition.year)
        for country in edition.finalists:
            finalist_years[country].add(edition.year)
        countries = edition.countries()
        for layer in layers:
            rows = []
            for source in countries:
                row: list[object] = [source]
                for target in countries:
                    if source in edition.voters and target in edition.finalists and source != target:
                        points = edition.points(layer, source, target)
                        row.append(points)
                        master_rows.append((edition.year, layer, source, target, points))
                    else:
                        row.append("")
                rows.append(row)
            write_csv(
                output_dir / "matrices" / f"{edition.year}_{layer}.csv",
                ["country", *countries], rows, encoding="utf-8-sig",
            )

    countries = sorted(set(voting_years) | set(finalist_years))
    write_csv(
        output_dir / "tables" / "votes_master.csv",
        ["year", "layer", "source", "target", "points"], master_rows, encoding="utf-8-sig",
    )
    write_csv(
        output_dir / "tables" / "nodes.csv",
        ["country", "years_voting", "years_finalist", "voting_years", "finalist_years"],
        [
            (
                c,
                len(voting_years[c]),
                len(finalist_years[c]),
                ";".join(map(str, sorted(voting_years[c]))),
                ";".join(map(str, sorted(finalist_years[c]))),
            )
            for c in countries
        ],
        encoding="utf-8-sig",
    )
    return len(master_rows)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build the Eurovision jury/televote vote networks and export GEXF/CSV for Gephi.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--data-dir", type=Path, default=DEFAULT_DATA_DIR,
                        help="Dataset 'data' directory or repository root (default: dataset/data).")
    parser.add_argument("--from", dest="year_from", type=int, default=2016, help="First edition (default: 2016).")
    parser.add_argument("--to", dest="year_to", type=int, default=2026, help="Last edition (default: 2026).")
    parser.add_argument("--year", type=int, help="Single edition; sets both --from and --to.")
    parser.add_argument("--score", default="both",
                        help="Layer: both (jury and public, default), jury, public/tele, total (jury + public).")
    parser.add_argument("--aggregate", action="store_true",
                        help="One network over the whole year range instead of one per edition.")
    parser.add_argument("--finalists-only", action="store_true",
                        help="Keep only finalists as voters (sub-network used for reciprocity/triads).")
    parser.add_argument("--min-points", type=int, default=1,
                        help="Dichotomisation: an award becomes an edge only if points >= N (default: 1).")
    parser.add_argument("--edge-weight", choices=EDGE_WEIGHTS, default="sum",
                        help="Value of the Gephi 'weight': total points (sum), points per award (mean), "
                             "points per opportunity (per_opportunity) or share of opportunities "
                             "with points (frequency). Default: sum.")
    target = parser.add_mutually_exclusive_group()
    target.add_argument("--country", metavar="CODE", help="Ego network around this country (e.g. IT).")
    target.add_argument("--all-countries", action="store_true",
                        help="One ego network per country, aggregated over the range.")
    parser.add_argument("--ego-mode", choices=["in", "out", "both"], default="in",
                        help="Ego network: votes received (in), given (out) or both. Default: in.")
    parser.add_argument("--matrices", action="store_true",
                        help="Also write processed_data/ (matrices + tables) like build_eurovision_data.py.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Default: output/.")
    parser.add_argument("--name", help="Name of the output sub-directory or base file name.")
    parser.add_argument("--list-countries", action="store_true", help="Print the country codes and exit.")
    return parser.parse_args(argv)


def variant_suffix(args: argparse.Namespace) -> str:
    parts = []
    if args.finalists_only:
        parts.append("finalists")
    if args.min_points > 1:
        parts.append(f"min{args.min_points}")
    if args.country:
        parts.append(f"ego-{args.country}-{args.ego_mode}")
    return "".join(f"_{p}" for p in parts)


def describe(args: argparse.Namespace, layer: str, years: list[int]) -> str:
    span = str(years[0]) if len(years) == 1 else f"{years[0]}-{years[-1]}"
    text = (
        f"Eurovision Grand Final vote network, {span}, layer={layer}, weight={args.edge_weight}, "
        f"min_points={args.min_points}, finalists_only={args.finalists_only}. "
        "Edges go from the voting country to the country receiving points; WLD excluded."
    )
    if args.country:
        text += f" Ego network of {args.country} (mode={args.ego_mode})."
    return text


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    data_dir = resolve_data_dir(args.data_dir)
    names = load_country_names(data_dir)

    if args.list_countries:
        for code, name in sorted(names.items(), key=lambda item: item[1]):
            print(f"{code:8s} {name}")
        return 0

    layers = SCORE_ALIASES.get(args.score.lower())
    if layers is None:
        print(f"[error] unknown score '{args.score}': use both, jury, public or total.", file=sys.stderr)
        return 2
    if args.year is not None:
        args.year_from = args.year_to = args.year
    if args.year_from > args.year_to:
        print("[error] --from must be <= --to", file=sys.stderr)
        return 2
    if args.country:
        args.country = args.country.upper()
    if args.all_countries:
        args.aggregate = True

    years, skipped = select_years(data_dir, args.year_from, args.year_to)
    if not years:
        print(f"[error] no Grand Final between {args.year_from} and {args.year_to} "
              f"(jury/public split starts in {FIRST_YEAR}).", file=sys.stderr)
        return 1
    try:
        editions = [read_edition(data_dir, year) for year in years]
    except (KeyError, ValueError, TypeError, OSError) as exc:
        print(f"[error] dataset validation failed: {exc}", file=sys.stderr)
        return 1

    print(f"Editions : {', '.join(map(str, years))}" + (f" (skipped: {', '.join(map(str, skipped))})" if skipped else ""))
    print(f"Layers   : {', '.join(layers)}")
    print("Validated: ballots complete, 58 points per voter, no self-votes; WLD excluded.")

    if args.country and not any(args.country in e.voters | e.finalists for e in editions):
        print(f"[error] {args.country} never voted in the selected editions.", file=sys.stderr)
        return 1

    if args.matrices:
        matrices_dir = args.output_dir / "processed_data"
        n = write_matrices(matrices_dir, editions, layers)
        countries = set().union(*(e.voters | e.finalists for e in editions))
        print(f"Matrices : {len(editions) * len(layers)} in {matrices_dir} "
              f"({n} eligible national votes, {len(countries)} countries)")

    suffix = variant_suffix(args)

    if args.all_countries:
        batch = args.output_dir / (args.name or "per-country")
        rows = []
        for layer in layers:
            full = build_network(editions, layer, args.min_points, args.finalists_only, names)
            for code in sorted(full.nodes):
                ego = ego_network(full, code, args.ego_mode)
                gexf = write_graph_files(batch / layer / code, ego, args.edge_weight,
                                         describe(args, layer, years) + f" Ego network of {code} (mode={args.ego_mode}).")
                points = sum(e.weight for e in ego.edges.values())
                rows.append([layer, code, names.get(code, code), args.ego_mode,
                             len(ego.nodes), len(ego.edges), fmt(points), gexf.relative_to(batch)])
        write_csv(batch / "index.csv",
                  ["layer", "code", "label", "ego_mode", "nodes", "edges", "points", "gexf"], rows)
        print(f"Ego nets : {len(rows)} in {batch} (index.csv)")
        return 0

    groups = [years] if args.aggregate else [[y] for y in years]
    batch = args.output_dir if args.aggregate else args.output_dir / (args.name or "per-year")
    index = []
    for group in groups:
        selected = [e for e in editions if e.year in group]
        span = str(group[0]) if len(group) == 1 else f"{group[0]}-{group[-1]}"
        for layer in layers:
            network = build_network(selected, layer, args.min_points, args.finalists_only, names)
            if args.country:
                network = ego_network(network, args.country, args.ego_mode)
            base = f"{args.name}_{layer}" if (args.aggregate and args.name) else f"{span}_{layer}{suffix}"
            gexf = write_graph_files(batch / base, network, args.edge_weight, describe(args, layer, group))
            top = max(network.nodes.values(), key=lambda n: n["in_weight"])
            points = sum(e.weight for e in network.edges.values())
            index.append([span, layer, len(network.nodes), len(network.edges),
                          fmt(points), top["label"], fmt(top["in_weight"]), gexf.relative_to(batch)])

    if not args.aggregate:
        write_csv(batch / f"index{suffix}.csv",
                  ["year", "layer", "nodes", "edges", "points", "top_country", "top_points", "gexf"], index)
    print(f"Graphs   : {len(index)} in {batch}")
    for span, layer, n_nodes, n_edges, points, top, top_points, _ in index:
        print(f"  {span:9s} {layer:6s} {n_nodes:3d} nodes {n_edges:4d} edges "
              f"{points:>6s} points  top: {top} ({top_points})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
