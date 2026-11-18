#!/usr/bin/env python3
"""RQ3: prestige and cross-group (bridging) voting in Eurovision finals.

Run from the RQ3 directory:
    python src/analyze_rq3.py

Requires numpy, networkx and matplotlib. Reads, without modifying them:
  * the 20 annual matrices (default: ../RQ1/processed_data/matrices; the same
    matrices are produced by build_eurovision_data.py and by
    scripts/build_graph.py --matrices);
  * the country attribute table (default:
    ../RQ2/processed_data/tables/country_attributes_rq2.csv), of which only the
    UN M49 subregion and the Eurovision cultural block are used;
  * the RQ2 consensus partition (default:
    ../RQ2/results/rq2/rq2_consensus_labels.csv), i.e. the average-linkage
    consensus of 200 Louvain runs, with the firmness of every membership.

Three kinds of groups are used: region and block are fixed external labels;
community is the RQ2 consensus partition. The communities are derived from the
same votes, so their home bias is high by construction (circular): they are
used to locate bridges and to compare the layers, not as an independent test.

Matrix convention: W[i, j] = points from voter i to finalist j; empty cell =
impossible vote, 0 = possible vote without points.

What is computed for each of the 20 networks (10 editions x jury/public):

1. Prestige of every finalist (course measures: in-degree, PageRank with
   alpha = 0.85, authority score of HITS):
     in_degree, in_strength, points_per_opportunity = in_strength / number of
     voters that could vote for it, vote_share = in_degree / opportunities,
     PageRank, authority. Hub score of every voter = how much it votes for the
     finalists that receive consensus. Betweenness on the finalists-only
     network with distance = 1 / points (exploratory: the networks are dense).

2. Concentration of prestige among finalists: Gini of in-strength, share of
   the points taken by the top three, Herfindahl index. Compared with a null
   model of uniform random ballots that respects the rules (each voter gives
   1-8, 10, 12 to ten eligible finalists).

3. Bridging with groups (region, block, RQ2 community). For every finalist j:
     home_share   = share of its points coming from voters of its own group;
     home_expected = share of its eligible voters that belong to its group,
                     i.e. the value expected if votes ignored the groups;
     home_excess  = home_share - home_expected;
     participation = 1 - sum_g (points from group g / points)^2, the
                     participation coefficient of the incoming points, divided
                     by its value under random voting (1 - sum_g (eligible
                     voters in g / eligible voters)^2). Values near 1 mean
                     support spread across groups as voters are; lower values
                     mean bloc-based support.

4. Jury vs public: exact paired sign-flip test over the ten editions
   (2^10 configurations) on the network-level statistics, with Holm and
   Benjamini-Hochberg corrections.

   Per network, Spearman correlations between prestige (points per
   opportunity) and participation, between the participation measured on
   regions and on communities, and between the firmness of a country's RQ2
   community membership and its participation (low firmness = the country sits
   between communities).

5. Country aggregates over the editions in which a country was a finalist.

Results are exploratory: the editions are not independent samples and the
statistics were chosen without a pre-registered plan.
"""
from __future__ import annotations

import argparse
import csv
import itertools
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np

YEARS = (2016, 2017, 2018, 2019, 2021, 2022, 2023, 2024, 2025, 2026)
LAYERS = ("jury", "public")
BALLOT = np.array((1, 2, 3, 4, 5, 6, 7, 8, 10, 12), dtype=float)
VALID = {0, 1, 2, 3, 4, 5, 6, 7, 8, 10, 12}
GROUPS = ("region", "block", "community")
MIN_VOTERS = 5  # sensitivity threshold on the in-degree of a finalist
COLORS = {"jury": "#246b91", "public": "#cf7135"}
LABELS = {"jury": "Jury", "public": "Public"}

SCRIPT_DIR = Path(__file__).resolve().parent
ROOT = SCRIPT_DIR.parent if SCRIPT_DIR.name.lower() == "src" else SCRIPT_DIR
DEFAULT_MATRICES = ROOT.parent / "RQ1" / "processed_data" / "matrices"
DEFAULT_ATTRIBUTES = ROOT.parent / "RQ2" / "processed_data" / "tables" / "country_attributes_rq2.csv"
DEFAULT_COMMUNITIES = ROOT.parent / "RQ2" / "results" / "rq2" / "rq2_consensus_labels.csv"
RESULTS = ROOT / "results" / "rq3"
FIGURES = ROOT / "figures" / "rq3"


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------


def save_csv(path: Path, columns: list[str], rows: list) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(columns)
        writer.writerows(rows)


def read_matrix(path: Path) -> tuple[list[str], np.ndarray, np.ndarray]:
    """Return countries, points W and the eligibility mask, with ballot checks."""
    if not path.is_file():
        raise FileNotFoundError(f"Matrix not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.reader(handle))
    header = rows[0]
    if header[0] != "country":
        raise ValueError(f"Unexpected header in {path.name}")
    countries = header[1:]
    if [r[0] for r in rows[1:]] != countries:
        raise ValueError(f"Row and column labels differ in {path.name}")
    n = len(countries)
    W = np.zeros((n, n))
    eligible = np.zeros((n, n), dtype=bool)
    for i, row in enumerate(rows[1:]):
        for j, raw in enumerate(row[1:]):
            if raw.strip() == "":
                continue
            points = int(raw)
            if points not in VALID or i == j:
                raise ValueError(f"Invalid vote {countries[i]}->{countries[j]} in {path.name}")
            eligible[i, j] = True
            W[i, j] = points
        if not np.array_equal(np.sort(W[i, W[i] > 0]), BALLOT):
            raise ValueError(f"Incomplete ballot of {countries[i]} in {path.name}")
    return countries, W, eligible


def load_attributes(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        raise FileNotFoundError(f"Attribute table not found: {path}")
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return {
            row["country"].strip(): {"region": row["region"].strip(), "block": row["eurovision_block"].strip()}
            for row in csv.DictReader(handle)
        }


def load_communities(path: Path) -> dict[tuple[int, str], dict[str, tuple[str, float]]]:
    """RQ2 consensus partition (full networks): (year, layer) -> country -> (community, firmness)."""
    if not path.is_file():
        raise FileNotFoundError(
            f"RQ2 consensus labels not found: {path} (run RQ2/src/analyze_rq2_consensus.py)"
        )
    out: dict = {}
    with path.open(encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["scope"] != "all":
                continue
            out.setdefault((int(row["year"]), row["layer"]), {})[row["country"]] = (
                row["community"], float(row["mean_co_assignment_within"])
            )
    return out


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------


def gini(values: np.ndarray) -> float:
    x = np.sort(np.asarray(values, dtype=float))
    n = len(x)
    if n == 0 or x.sum() == 0:
        return float("nan")
    return float((2 * np.arange(1, n + 1) - n - 1) @ x / (n * x.sum()))


def concentration(in_strength: np.ndarray) -> dict[str, float]:
    """Concentration of the points received by the finalists."""
    share = in_strength / in_strength.sum()
    return {
        "gini": gini(in_strength),
        "top3_share": float(np.sort(share)[-3:].sum()),
        "hhi": float((share ** 2).sum()),
    }


def group_matrix(countries: list[str], attributes, key: str) -> np.ndarray:
    """One-hot matrix country x group for a fixed attribute."""
    values = [attributes[c][key] for c in countries]
    groups = sorted(set(values))
    M = np.zeros((len(countries), len(groups)))
    for i, value in enumerate(values):
        M[i, groups.index(value)] = 1.0
    return M


def bridging(W: np.ndarray, eligible: np.ndarray, G: np.ndarray, finalists: np.ndarray) -> dict[str, np.ndarray]:
    """Home bias and participation of the points received by each finalist.

    G is the one-hot group matrix. Points from group g to finalist j are
    (G.T @ W)[g, j]; eligible voters of group g for j are (G.T @ eligible)[g, j].
    """
    points_from = G.T @ W  # groups x countries
    voters_from = G.T @ eligible.astype(float)
    total = points_from.sum(axis=0)
    eligible_total = voters_from.sum(axis=0)
    own = np.argmax(G, axis=1)  # group index of every country
    idx = np.arange(len(own))

    with np.errstate(divide="ignore", invalid="ignore"):
        home_share = points_from[own, idx] / total
        home_expected = voters_from[own, idx] / eligible_total
        part = 1 - ((points_from / total) ** 2).sum(axis=0)
        part_expected = 1 - ((voters_from / eligible_total) ** 2).sum(axis=0)
        part_ratio = part / part_expected
    mask = finalists & (total > 0)
    nan = np.full(len(own), np.nan)
    return {
        "home_share": np.where(mask, home_share, nan),
        "home_expected": np.where(mask, home_expected, nan),
        "home_excess": np.where(mask, home_share - home_expected, nan),
        "participation": np.where(mask, part, nan),
        "participation_ratio": np.where(mask, part_ratio, nan),
    }


def network_statistics(W, eligible, finalists, groups) -> dict[str, float]:
    """Statistics compared with the null model and between layers."""
    in_strength = W.sum(axis=0)[finalists]
    prestige = in_strength / eligible.sum(axis=0)[finalists]
    stats = concentration(in_strength)
    for key, G in groups.items():
        b = bridging(W, eligible, G, finalists)
        stats[f"home_excess_{key}"] = float(np.nanmean(b["home_excess"]))
        stats[f"participation_ratio_{key}"] = float(np.nanmean(b["participation_ratio"]))
        # Do the most voted finalists draw on more groups? Part of this is
        # mechanical (more points = a larger sample of voters), hence the null.
        stats[f"spearman_prestige_participation_{key}"] = spearman(
            prestige, b["participation_ratio"][finalists]
        )
    # Sensitivity: drop finalists voted by fewer than MIN_VOTERS countries, whose
    # bridging measures rest on one or two ballots. Same rule in the null.
    enough = (W > 0).sum(axis=0)[finalists] >= MIN_VOTERS
    b = bridging(W, eligible, groups["region"], finalists)
    stats["home_excess_region_min5"] = float(np.nanmean(b["home_excess"][finalists][enough]))
    stats["participation_ratio_region_min5"] = float(np.nanmean(b["participation_ratio"][finalists][enough]))
    stats["spearman_prestige_participation_region_min5"] = spearman(
        prestige[enough], b["participation_ratio"][finalists][enough]
    )
    return stats


def random_ballots(eligible: np.ndarray, sims: int, rng: np.random.Generator) -> np.ndarray:
    """Uniform rule-compliant ballots: every voter scores ten random eligible finalists.

    Random keys are drawn for every cell, ineligible cells are pushed to the
    end, and the ten smallest keys get the points in random order.
    """
    n = len(eligible)
    voters = np.flatnonzero(eligible.any(axis=1))
    keys = rng.random((sims, len(voters), n))
    keys[:, ~eligible[voters]] = np.inf
    chosen = np.argsort(keys, axis=2)[:, :, :10]
    W = np.zeros((sims, n, n))
    s_idx = np.arange(sims)[:, None, None]
    v_idx = voters[None, :, None]
    W[s_idx, v_idx, chosen] = BALLOT  # chosen is already in random order
    return W


def pagerank(W: np.ndarray, alpha: float = 0.85, tol: float = 1e-12) -> np.ndarray:
    """Weighted PageRank by power iteration (numpy only, no scipy).

    Every voter spreads its centrality in proportion to the points it gives
    (W[i, j] / out-strength of i); countries that do not vote (none in these
    data, but handled) spread it uniformly. Normalised to sum to one.
    """
    n = len(W)
    out = W.sum(axis=1)
    P = np.divide(W, out[:, None], out=np.full_like(W, 1.0 / n), where=out[:, None] > 0)
    x = np.full(n, 1.0 / n)
    for _ in range(10_000):
        new = alpha * x @ P + (1 - alpha) / n
        if np.abs(new - x).sum() < tol:
            break
        x = new
    return new / new.sum()


def hits(W: np.ndarray, tol: float = 1e-12) -> tuple[np.ndarray, np.ndarray]:
    """Weighted HITS: authority = W^T hub, hub = W authority (each sums to one)."""
    a = np.ones(len(W))
    for _ in range(10_000):
        h = W @ a
        h /= h.sum()
        new = W.T @ h
        new /= new.sum()
        if np.abs(new - a).sum() < tol:
            break
        a = new
    return h, new


def centralities(W: np.ndarray, countries: list[str], finalists: np.ndarray) -> dict[str, dict[str, float]]:
    pr = pagerank(W)
    hub, auth = hits(W)
    graph = nx.DiGraph()
    graph.add_nodes_from(countries)
    for i, j in zip(*np.nonzero(W)):
        graph.add_edge(countries[i], countries[j], weight=float(W[i, j]))
    pagerank_d = dict(zip(countries, pr))
    hubs = dict(zip(countries, hub))
    authorities = dict(zip(countries, auth))

    fin = [c for c, f in zip(countries, finalists) if f]
    sub = graph.subgraph(fin).copy()
    for _, _, data in sub.edges(data=True):
        data["distance"] = 1.0 / data["weight"]
    betweenness = nx.betweenness_centrality(sub, weight="distance", normalized=True)
    return {"pagerank": pagerank_d, "authority": authorities, "hub": hubs, "betweenness": betweenness}


def spearman(x, y) -> float:
    """Spearman correlation with average ranks; pairs with a missing value are dropped."""
    x, y = np.asarray(x, float), np.asarray(y, float)
    keep = np.isfinite(x) & np.isfinite(y)
    x, y = x[keep], y[keep]
    if len(x) < 3:
        return float("nan")
    rx = np.argsort(np.argsort(x)).astype(float)
    ry = np.argsort(np.argsort(y)).astype(float)
    # Average ranks for ties.
    for values, ranks in ((x, rx), (y, ry)):
        for v in np.unique(values):
            tie = values == v
            ranks[tie] = ranks[tie].mean()
    return float(np.corrcoef(rx, ry)[0, 1])


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def mc_test(observed: float, null: np.ndarray) -> list[float]:
    null = null[np.isfinite(null)]
    mean = float(null.mean())
    high = (1 + int((null >= observed).sum())) / (len(null) + 1)
    low = (1 + int((null <= observed).sum())) / (len(null) + 1)
    two = (1 + int((np.abs(null - mean) >= abs(observed - mean) - 1e-12).sum())) / (len(null) + 1)
    return [observed, mean, float(null.std(ddof=1)), float(np.quantile(null, .025)),
            float(np.quantile(null, .975)), high, low, two]


def sign_flip_test(jury: list[float], public: list[float]) -> tuple[float, float]:
    """Exact paired test over the editions: swap the two layers within a year."""
    d = np.asarray(public) - np.asarray(jury)
    observed = float(d.mean())
    stats = np.array([np.mean(d * np.array(s)) for s in itertools.product((1, -1), repeat=len(d))])
    return observed, float((np.abs(stats) >= abs(observed) - 1e-12).mean())


def holm(p: list[float]) -> list[float]:
    order = np.argsort(p)
    out, running = [0.0] * len(p), 0.0
    for rank, i in enumerate(order):
        running = max(running, min(1.0, (len(p) - rank) * p[i]))
        out[i] = running
    return out


def benjamini_hochberg(p: list[float]) -> list[float]:
    order = np.argsort(p)[::-1]
    out, running = [0.0] * len(p), 1.0
    for rank, i in enumerate(order):
        running = min(running, min(1.0, p[i] * len(p) / (len(p) - rank)))
        out[i] = running
    return out


# ---------------------------------------------------------------------------
# Figures
# ---------------------------------------------------------------------------


def plot_concentration(network_rows: list[dict], null_rows: dict) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.5))
    for ax, key, title in ((axes[0], "gini", "Gini of points received"),
                           (axes[1], "top3_share", "Share of points to the top three")):
        for layer in LAYERS:
            obs = [r[key] for r in network_rows if r["layer"] == layer]
            ax.plot(YEARS, obs, "o-", color=COLORS[layer], label=f"{LABELS[layer]} observed")
        lo = [null_rows[y, "jury", key][3] for y in YEARS]
        hi = [null_rows[y, "jury", key][4] for y in YEARS]
        ax.fill_between(YEARS, lo, hi, color="#999999", alpha=.25, label="Random ballots, 95% range")
        ax.set_title(title)
        ax.set_xticks(YEARS[::2])
        ax.grid(alpha=.2)
    axes[0].legend(frameon=False, fontsize=8)
    fig.suptitle("RQ3 - How concentrated is prestige among the finalists?")
    fig.tight_layout()
    fig.savefig(FIGURES / "rq3_concentration.png", dpi=180)
    plt.close(fig)


def plot_prestige_scatter(aggregate: list[dict]) -> None:
    rows = [r for r in aggregate if r["finals"] >= 3]
    x = [r["points_per_opportunity_jury"] for r in rows]
    y = [r["points_per_opportunity_public"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 7.5))
    ax.scatter(x, y, s=[25 * r["finals"] for r in rows], color="#5a7d9a", alpha=.7, edgecolor="white")
    for r, xi, yi in zip(rows, x, y):
        ax.annotate(r["country"], (xi, yi), fontsize=8, ha="center", va="center")
    top = max(max(x), max(y)) * 1.05
    ax.plot([0, top], [0, top], "--", color="#888888", lw=1)
    ax.set_xlim(0, top)
    ax.set_ylim(0, top)
    ax.set_xlabel("Jury: mean points per voter that could vote for it")
    ax.set_ylabel("Public: mean points per voter that could vote for it")
    ax.set_title("RQ3 - Jury vs public prestige (finalists at least 3 times, size = finals)")
    ax.grid(alpha=.2)
    fig.tight_layout()
    fig.savefig(FIGURES / "rq3_jury_vs_public_prestige.png", dpi=180)
    plt.close(fig)


def plot_bridging(network_rows: list[dict], aggregate: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(14, 5))
    for layer in LAYERS:
        axes[0].plot(YEARS, [r["home_excess_region"] for r in network_rows if r["layer"] == layer],
                     "o-", color=COLORS[layer], label=LABELS[layer])
    axes[0].axhline(0, color="#888888", lw=1, ls="--")
    axes[0].set_title("Mean home bias of finalists (own subregion, observed - expected)")
    axes[0].set_xticks(YEARS[::2])
    axes[0].grid(alpha=.2)
    axes[0].legend(frameon=False)

    rows = sorted((r for r in aggregate if r["finals"] >= 3), key=lambda r: r["home_excess_region_public"])
    pos = np.arange(len(rows))
    axes[1].barh(pos - .2, [r["home_excess_region_jury"] for r in rows], .4, color=COLORS["jury"], label="Jury")
    axes[1].barh(pos + .2, [r["home_excess_region_public"] for r in rows], .4, color=COLORS["public"], label="Public")
    axes[1].set_yticks(pos, [r["country"] for r in rows], fontsize=7)
    axes[1].axvline(0, color="#888888", lw=1)
    axes[1].set_title("Home bias by country (finalists at least 3 times)")
    axes[1].legend(frameon=False, fontsize=8)
    axes[1].grid(axis="x", alpha=.2)
    fig.suptitle("RQ3 - Is prestige bloc-based or spread across Europe?")
    fig.tight_layout()
    fig.savefig(FIGURES / "rq3_home_bias.png", dpi=180)
    plt.close(fig)


def plot_prestige_participation(country_rows: list[dict]) -> None:
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for ax, layer in zip(axes, LAYERS):
        rows = [r for r in country_rows if r["layer"] == layer and r["finalist"]
                and r["participation_ratio_region"] != "" and np.isfinite(r["participation_ratio_region"])]
        x = [r["points_per_opportunity"] for r in rows]
        y = [r["participation_ratio_region"] for r in rows]
        ax.scatter(x, y, s=14, color=COLORS[layer], alpha=.55, edgecolor="none")
        ax.axhline(1, color="#888888", lw=1, ls="--")
        ax.set_title(f"{LABELS[layer]} (one dot = finalist in one edition)")
        ax.set_xlabel("Prestige: points per voter that could vote for it")
        ax.grid(alpha=.2)
    axes[0].set_ylabel("Participation ratio over subregions (1 = spread like the voters)")
    fig.suptitle("RQ3 - Do the most voted finalists draw support from more subregions?")
    fig.tight_layout()
    fig.savefig(FIGURES / "rq3_prestige_vs_participation.png", dpi=180)
    plt.close(fig)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="RQ3: prestige and bridging")
    parser.add_argument("--matrices", type=Path, default=DEFAULT_MATRICES)
    parser.add_argument("--attributes", type=Path, default=DEFAULT_ATTRIBUTES)
    parser.add_argument("--communities", type=Path, default=DEFAULT_COMMUNITIES,
                        help="RQ2 consensus labels (rq2_consensus_labels.csv)")
    parser.add_argument("--simulations", type=int, default=2000, help="Random-ballot null samples per network")
    parser.add_argument("--seed", type=int, default=2026)
    args = parser.parse_args()
    rng = np.random.default_rng(args.seed)
    attributes = load_attributes(args.attributes)
    communities = load_communities(args.communities)

    country_rows, network_rows, null_out = [], [], []
    null_rows: dict = {}
    per_country: dict = {}
    in_strength_by: dict = {}

    for year in YEARS:
        for layer in LAYERS:
            countries, W, eligible = read_matrix(args.matrices / f"{year}_{layer}.csv")
            missing = [c for c in countries if c not in attributes]
            if missing:
                raise ValueError(f"Countries without attributes: {missing}")
            finalists = eligible.any(axis=0)
            voters = eligible.any(axis=1)
            partition = communities.get((year, layer), {})
            missing = [c for c in countries if c not in partition]
            if missing:
                raise ValueError(f"{year} {layer}: countries without an RQ2 community: {missing}")
            labels = {c: {**attributes[c], "community": partition[c][0]} for c in countries}
            firmness = np.array([partition[c][1] for c in countries])
            groups = {key: group_matrix(countries, labels, key) for key in GROUPS}

            in_strength = W.sum(axis=0)
            in_degree = (W > 0).sum(axis=0)
            opportunities = eligible.sum(axis=0)
            cent = centralities(W, countries, finalists)
            bridge = {key: bridging(W, eligible, groups[key], finalists) for key in GROUPS}
            in_strength_by[year, layer] = dict(zip(countries, in_strength))

            fin_names = [c for c, f in zip(countries, finalists) if f]
            for i, c in enumerate(countries):
                row = {
                    "year": year, "layer": layer, "country": c,
                    "finalist": int(finalists[i]), "voter": int(voters[i]),
                    "in_degree": int(in_degree[i]) if finalists[i] else "",
                    "in_strength": float(in_strength[i]) if finalists[i] else "",
                    "opportunities": int(opportunities[i]) if finalists[i] else "",
                    "points_per_opportunity": float(in_strength[i] / opportunities[i]) if finalists[i] else "",
                    "vote_share": float(in_degree[i] / opportunities[i]) if finalists[i] else "",
                    "pagerank": cent["pagerank"][c],
                    "authority": cent["authority"][c],
                    "hub": cent["hub"][c] if voters[i] else "",
                    "betweenness_finalists": cent["betweenness"].get(c, ""),
                    "community": partition[c][0],
                    "community_firmness": float(firmness[i]),
                }
                for key in GROUPS:
                    for name, values in bridge[key].items():
                        row[f"{name}_{key}"] = float(values[i]) if finalists[i] else ""
                country_rows.append(row)
                if finalists[i]:
                    per_country.setdefault((c, layer), []).append(row)

            fin_strength = [in_strength_by[year, layer][c] for c in fin_names]
            stats = network_statistics(W, eligible, finalists, groups)
            part = {key: bridge[key]["participation_ratio"][finalists] for key in GROUPS}
            stats.update({
                "year": year, "layer": layer, "finalists": int(finalists.sum()), "voters": int(voters.sum()),
                "communities": len(set(partition[c][0] for c in countries)),
                "spearman_participation_region_community": spearman(part["region"], part["community"]),
                "spearman_firmness_participation_community": spearman(firmness[finalists], part["community"]),
                "spearman_pagerank_in_strength": spearman([cent["pagerank"][c] for c in fin_names], fin_strength),
                "spearman_authority_in_strength": spearman([cent["authority"][c] for c in fin_names], fin_strength),
                "top_country": fin_names[int(np.argmax(fin_strength))],
            })
            network_rows.append(stats)

            # Null model: uniform rule-compliant ballots on the same opportunities.
            sims = random_ballots(eligible, args.simulations, rng)
            keys = [k for k in stats if k in ("gini", "top3_share", "hhi")
                    or k.startswith(("home_excess_", "participation_ratio_", "spearman_prestige_participation_"))]
            values = {k: np.empty(args.simulations) for k in keys}
            for s in range(args.simulations):
                sim_stats = network_statistics(sims[s], eligible, finalists, groups)
                for k in keys:
                    values[k][s] = sim_stats[k]
            for k in keys:
                result = mc_test(stats[k], values[k])
                null_rows[year, layer, k] = result
                null_out.append([year, layer, k] + result)
        print(f"{year}: jury and public analysed ({args.simulations} random-ballot samples each)", flush=True)

    # Agreement between jury and public on who is prestigious.
    for year in YEARS:
        fin = [r["country"] for r in country_rows if r["year"] == year and r["layer"] == "jury" and r["finalist"]]
        rho = spearman([in_strength_by[year, "jury"][c] for c in fin], [in_strength_by[year, "public"][c] for c in fin])
        for r in network_rows:
            if r["year"] == year:
                r["spearman_jury_public_in_strength"] = rho

    # Jury vs public, paired over the editions.
    tested = ["gini", "top3_share", "hhi", "home_excess_region", "home_excess_block",
              "home_excess_community", "participation_ratio_region", "participation_ratio_block",
              "participation_ratio_community", "spearman_prestige_participation_region",
              "home_excess_region_min5", "spearman_prestige_participation_region_min5"]
    diffs = []
    for key in tested:
        jury = [r[key] for r in network_rows if r["layer"] == "jury"]
        public = [r[key] for r in network_rows if r["layer"] == "public"]
        observed, p = sign_flip_test(jury, public)
        diffs.append([key, float(np.mean(jury)), float(np.mean(public)), observed,
                      sum(pb > jb for jb, pb in zip(jury, public)), p])
    p_raw = [d[-1] for d in diffs]
    diffs = [d + [h, b] for d, h, b in zip(diffs, holm(p_raw), benjamini_hochberg(p_raw))]

    # Country aggregates over the editions in which the country was a finalist.
    aggregate = []
    for c in sorted({c for c, _ in per_country}):
        row = {"country": c, "finals": len(per_country.get((c, "jury"), []))}
        for layer in LAYERS:
            rows = per_country.get((c, layer), [])
            for k in ("points_per_opportunity", "vote_share", "pagerank", "home_share_region",
                      "home_expected_region", "home_excess_region", "participation_ratio_region",
                      "home_excess_block", "participation_ratio_block", "home_excess_community",
                      "participation_ratio_community", "community_firmness"):
                vals = [r[k] for r in rows if r[k] != ""]
                row[f"{k}_{layer}"] = float(np.nanmean(vals)) if vals else float("nan")
        row["prestige_gap_public_minus_jury"] = row["points_per_opportunity_public"] - row["points_per_opportunity_jury"]
        aggregate.append(row)
    aggregate.sort(key=lambda r: -(r["points_per_opportunity_jury"] + r["points_per_opportunity_public"]))

    RESULTS.mkdir(parents=True, exist_ok=True)
    FIGURES.mkdir(parents=True, exist_ok=True)
    save_csv(RESULTS / "rq3_country_year.csv", list(country_rows[0]), [list(r.values()) for r in country_rows])
    net_cols = ["year", "layer", "finalists", "voters", "top_country", "gini", "top3_share", "hhi",
                "home_excess_region", "home_excess_block", "participation_ratio_region",
                "participation_ratio_block", "communities", "home_excess_community",
                "participation_ratio_community", "spearman_prestige_participation_region",
                "spearman_prestige_participation_community", "spearman_participation_region_community",
                "spearman_firmness_participation_community", "home_excess_region_min5",
                "participation_ratio_region_min5", "spearman_prestige_participation_region_min5",
                "spearman_pagerank_in_strength",
                "spearman_authority_in_strength", "spearman_jury_public_in_strength"]
    save_csv(RESULTS / "rq3_network_summary.csv", net_cols, [[r[c] for c in net_cols] for r in network_rows])
    save_csv(RESULTS / "rq3_null_model.csv",
             ["year", "layer", "statistic", "observed", "null_mean", "null_sd", "null_q025", "null_q975",
              "p_high", "p_low", "p_two_sided"], null_out)
    save_csv(RESULTS / "rq3_layer_differences.csv",
             ["statistic", "mean_jury", "mean_public", "public_minus_jury", "years_public_higher",
              "p_exact", "p_holm", "p_fdr"], diffs)
    save_csv(RESULTS / "rq3_country_aggregate.csv", list(aggregate[0]), [list(r.values()) for r in aggregate])

    plot_concentration(network_rows, null_rows)
    plot_prestige_scatter(aggregate)
    plot_bridging(network_rows, aggregate)
    plot_prestige_participation(country_rows)

    print(f"Results: {RESULTS}")
    print(f"Figures: {FIGURES}")
    print("Exploratory analysis; community home bias is circular (communities come from the same votes).")


if __name__ == "__main__":
    try:
        main()
    except (FileNotFoundError, ValueError, OSError, nx.NetworkXException) as exc:
        raise SystemExit(f"RQ3 analysis failed: {exc}") from exc
