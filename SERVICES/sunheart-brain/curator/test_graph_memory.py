from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).with_name("graph_memory.py")
SPEC = importlib.util.spec_from_file_location("graph_memory_test_module", MODULE_PATH)
assert SPEC and SPEC.loader
graph_memory = importlib.util.module_from_spec(SPEC)
sys.modules["graph_memory_test_module"] = graph_memory
SPEC.loader.exec_module(graph_memory)


def _contact(idx: int, handle: str, topic_signal: str, *, stage: str = "spark", name: str = "") -> dict:
    return {
        "id": idx,
        "pool": "warm" if idx < 4 else "adjacent",
        "handle": handle,
        "platform": "telegram",
        "source": "fixture",
        "topic_signal": topic_signal,
        "metadata": {"name": name or handle.title(), "stage": stage, "interests": [topic_signal]},
    }


class GraphMemoryTest(unittest.TestCase):
    def setUp(self) -> None:
        self.contacts = [
            _contact(1, "josh", "regenerative cities", stage="awaken", name="Josh"),
            _contact(2, "cheyenne", "regenerative cities and community design", stage="activate", name="Cheyenne"),
            _contact(3, "atlas", "coaching offers", stage="build"),
            _contact(4, "halley", "creative practice", stage="spark"),
            _contact(5, "sierra", "regenerative cities", stage="contribute"),
            _contact(6, "delaney", "retreat design", stage="activate"),
            _contact(7, "mira", "somatic practice", stage="awaken"),
            _contact(8, "noah", "open source tools", stage="build"),
            _contact(9, "kai", "cooperative finance", stage="contribute"),
            _contact(10, "lena", "education commons", stage="spark"),
        ]
        self.becoming = [
            {"person_id": "person:telegram:josh", "stage": "awaken"},
            {"person_id": "person:telegram:cheyenne", "stage": "activate"},
            {"person_id": "person:telegram:sierra", "stage": "contribute"},
        ]

    def test_indexes_ten_contacts_with_stage_and_topic_edges(self) -> None:
        graph = graph_memory.build_contact_graph(self.contacts, self.becoming)

        person_nodes = [node for node in graph.nodes if node.node_type == "person"]
        stage_edges = [edge for edge in graph.edges if edge.relation == "AT_STAGE"]
        interest_edges = [edge for edge in graph.edges if edge.relation == "INTERESTED_IN"]

        self.assertEqual(len(person_nodes), 10)
        self.assertGreaterEqual(len(stage_edges), 10)
        self.assertGreaterEqual(len(interest_edges), 10)
        self.assertIn(
            ("topic", "topic:regenerative-cities"),
            {(node.node_type, node.node_key) for node in graph.nodes},
        )

    def test_regenerative_cities_query_returns_josh_and_related_contacts(self) -> None:
        graph = graph_memory.build_contact_graph(self.contacts, self.becoming)

        results = graph_memory.query_connected_people(graph, "who is connected to regenerative cities?")
        labels = [result.label for result in results]

        self.assertIn("Josh", labels)
        self.assertIn("Cheyenne", labels)
        self.assertIn("Sierra", labels)
        self.assertEqual(results[0].distance, 1)
        stages = {result.label: result.stage for result in results}
        self.assertEqual(stages["Josh"], "awaken")
        self.assertEqual(stages["Cheyenne"], "activate")

    def test_relationships_are_stable_after_graph_rehydration(self) -> None:
        graph = graph_memory.build_contact_graph(self.contacts, self.becoming)
        node_rows = [node.__dict__ for node in graph.nodes]
        edge_rows = [edge.__dict__ for edge in graph.edges]
        rehydrated = graph_memory.GraphBuild(
            nodes=tuple(graph_memory.GraphNode(**row) for row in node_rows),
            edges=tuple(graph_memory.GraphEdge(**row) for row in edge_rows),
        )

        original = graph_memory.query_connected_people(graph, "regenerative cities")
        after = graph_memory.query_connected_people(rehydrated, "regenerative cities")

        self.assertEqual([item.person_key for item in original], [item.person_key for item in after])
        self.assertEqual([item.via for item in original], [item.via for item in after])

    def test_topic_extraction_handles_metadata_lists_and_text_splits(self) -> None:
        row = {
            "id": 11,
            "handle": "river",
            "platform": "github",
            "topic_signal": "Regenerative City / Cooperative Finance",
            "metadata": {"interests": ["public goods", "regenerative cities"]},
        }

        topics = graph_memory.extract_topics(row)

        self.assertIn("regenerative-cities", topics)
        self.assertIn("cooperative-finance", topics)
        self.assertIn("public-goods", topics)


if __name__ == "__main__":
    unittest.main()
