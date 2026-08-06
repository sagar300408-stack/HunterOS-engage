"""
Tests for BusinessIntentTaxonomyGraph DAG topology, multi-parent paths, and reachability.
"""

import pytest

from app.domain.intents.classification.models import (
    BusinessDomain,
    IntentCategory,
)
from app.domain.intents.classification.taxonomy.graph import (
    BusinessIntentTaxonomyGraph,
)
from app.domain.intents.classification.taxonomy.models import (
    TaxonomyEdge,
    TaxonomyNode,
)


def test_taxonomy_graph_initialization_and_reachability():
    graph = BusinessIntentTaxonomyGraph()

    # Verify roots
    roots = graph.get_root_nodes()
    root_ids = {r.node_id for r in roots}
    assert "commercial" in root_ids
    assert "operational" in root_ids
    assert "relationship" in root_ids
    assert "information" in root_ids

    # Find paths for discount discussion (which has multi-parent DAG structure)
    paths = graph.get_all_paths_to_root("commercial.negotiation.discount_discussion")
    assert len(paths) >= 1
    primary_path = graph.find_primary_path("commercial.negotiation.discount_discussion")
    assert "commercial" in primary_path
    assert "discount_discussion" in primary_path


def test_taxonomy_graph_multi_parent_resolution():
    graph = BusinessIntentTaxonomyGraph()

    # Add custom multi-parent node
    special_node = TaxonomyNode(
        node_id="special.hybrid_inquiry",
        category=IntentCategory.COMMERCIAL,
        display_name="Hybrid Inquiry",
        business_domain=BusinessDomain.CROSS_INDUSTRY,
    )
    graph.add_node(special_node)

    # Edge from commercial
    graph.add_edge("commercial", "special.hybrid_inquiry", relation="parent_of")
    # Edge from information
    graph.add_edge("information", "special.hybrid_inquiry", relation="parent_of")

    paths = graph.get_all_paths_to_root("special.hybrid_inquiry")
    assert len(paths) == 2
    path_strs = [p.path_str for p in paths]
    assert "commercial > special.hybrid_inquiry" in path_strs
    assert "information > special.hybrid_inquiry" in path_strs


def test_taxonomy_graph_cycle_detection():
    graph = BusinessIntentTaxonomyGraph()

    node_a = TaxonomyNode(node_id="cycle.a", category=IntentCategory.COMMERCIAL, display_name="A")
    node_b = TaxonomyNode(node_id="cycle.b", category=IntentCategory.COMMERCIAL, display_name="B")
    graph.add_node(node_a)
    graph.add_node(node_b)

    graph.add_edge("cycle.a", "cycle.b")

    # Attempting to add edge B -> A should raise ValueError for cycle
    with pytest.raises(ValueError, match="creates a cycle"):
        graph.add_edge("cycle.b", "cycle.a")


def test_taxonomy_graph_export():
    graph = BusinessIntentTaxonomyGraph()
    export_data = graph.export_graph()

    assert export_data["total_nodes"] >= 4
    assert export_data["total_edges"] >= 4
    assert "nodes" in export_data
    assert "edges" in export_data
