"""Vendor relationship graph for procurement collusion detection.

Builds a bipartite graph (authorities ↔ vendors) and scores edges
for unusual patterns: monopoly bidders, rotating winners, shell clusters.
"""

from __future__ import annotations

from dataclasses import dataclass, field

import networkx as nx
import pandas as pd
import structlog

log = structlog.get_logger(__name__)


@dataclass
class VendorGraphStats:
    """Summary statistics computed from the vendor network."""

    node_count: int
    edge_count: int
    monopoly_vendors: list[str] = field(default_factory=list)
    high_centrality_vendors: list[tuple[str, float]] = field(default_factory=list)
    suspected_clusters: list[list[str]] = field(default_factory=list)


class VendorNetworkAnalyser:
    """Build and analyse the vendor–authority procurement network.

    Uses NetworkX for graph construction and community detection.
    """

    def __init__(self) -> None:
        self._graph: nx.Graph = nx.Graph()

    def build(self, df: pd.DataFrame) -> None:
        """Construct the bipartite graph from a tenders DataFrame.

        Expects columns: reference, contracting_authority, vendor_name, amount_mad.
        Vendor information must be joined from a separate awards table.
        """
        self._graph.clear()
        for _, row in df.iterrows():
            authority = f"auth:{row['contracting_authority']}"
            vendor = f"vendor:{row.get('vendor_name', 'unknown')}"
            self._graph.add_node(authority, node_type="authority")
            self._graph.add_node(vendor, node_type="vendor")
            if self._graph.has_edge(authority, vendor):
                self._graph[authority][vendor]["weight"] += 1
                self._graph[authority][vendor]["total_mad"] += float(
                    row.get("estimated_amount_mad") or 0
                )
            else:
                self._graph.add_edge(
                    authority,
                    vendor,
                    weight=1,
                    total_mad=float(row.get("estimated_amount_mad") or 0),
                )
        log.info(
            "vendor_graph_built",
            nodes=self._graph.number_of_nodes(),
            edges=self._graph.number_of_edges(),
        )

    def analyse(self) -> VendorGraphStats:
        """Compute network statistics and flag suspicious patterns.

        Returns a :class:`VendorGraphStats` summary.
        """
        vendor_nodes = [n for n, d in self._graph.nodes(data=True) if d.get("node_type") == "vendor"]

        # Monopoly: vendor wins >80% of an authority's contracts
        monopoly: list[str] = []
        for node in vendor_nodes:
            neighbors = list(self._graph.neighbors(node))
            for auth in neighbors:
                auth_degree = self._graph.degree(auth)
                edge_weight = self._graph[auth][node]["weight"]
                if auth_degree > 0 and edge_weight / auth_degree > 0.8:
                    monopoly.append(node)
                    break

        # Centrality: top vendors by betweenness centrality
        centrality = nx.betweenness_centrality(self._graph, normalized=True)
        top_vendors = sorted(
            [(n, s) for n, s in centrality.items() if n.startswith("vendor:")],
            key=lambda x: x[1],
            reverse=True,
        )[:10]

        # Community detection for cluster analysis
        communities = list(nx.community.greedy_modularity_communities(self._graph))
        suspected = [
            [n for n in c if n.startswith("vendor:")]
            for c in communities
            if len([n for n in c if n.startswith("vendor:")]) >= 3
        ][:5]

        stats = VendorGraphStats(
            node_count=self._graph.number_of_nodes(),
            edge_count=self._graph.number_of_edges(),
            monopoly_vendors=monopoly,
            high_centrality_vendors=top_vendors,
            suspected_clusters=suspected,
        )
        log.info(
            "vendor_analysis_complete",
            monopolies=len(monopoly),
            clusters=len(suspected),
        )
        return stats
