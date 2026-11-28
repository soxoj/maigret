"""Keep extracted list values attached to the profiles they came from."""

import json

import pytest

from maigret.report import _build_maigret_graph, save_graph_report, save_neo4j_report
from maigret.result import MaigretCheckResult, MaigretCheckStatus
from maigret.sites import MaigretDatabase, MaigretSite


def make_results(profiles, serialized):
    rows = []
    for username, site_name, values in profiles:
        url = f"https://profiles.example/{username}"
        ids = {
            key: repr(value) if serialized else value for key, value in values.items()
        }
        status = MaigretCheckResult(
            username, site_name, url, MaigretCheckStatus.CLAIMED, ids_data=ids
        )
        rows.append(
            (username, "username", {site_name: {"status": status, "url_user": url}})
        )
    return rows


@pytest.mark.parametrize("serialized", [False, True])
def test_distinct_profile_lists_do_not_share_a_collection(serialized):
    alice_links = ["https://alice.example", "https://shared.example"]
    bob_links = ["https://bob.example", "https://shared.example"]
    rows = make_results(
        [
            ("alice", "Profiles", {"links": alice_links}),
            ("bob", "Profiles", {"links": bob_links}),
        ],
        serialized,
    )
    graph = _build_maigret_graph(rows, MaigretDatabase())
    alice_collection = f"links: {alice_links}"
    bob_collection = f"links: {bob_links}"
    alice_account = "account: https://profiles.example/alice"
    bob_account = "account: https://profiles.example/bob"

    assert graph.has_edge(alice_account, alice_collection)
    assert graph.has_edge(bob_account, bob_collection)
    assert not graph.has_edge(alice_account, bob_collection)
    assert not graph.has_edge(bob_account, alice_collection)
    assert graph.has_edge(alice_collection, "links: https://alice.example")
    assert not graph.has_edge(alice_collection, "links: https://bob.example")
    assert graph.has_edge(bob_collection, "links: https://bob.example")
    assert not graph.has_edge(bob_collection, "links: https://alice.example")
    assert graph.has_edge(alice_collection, "links: https://shared.example")
    assert graph.has_edge(bob_collection, "links: https://shared.example")
    assert "links: Profiles" not in graph


@pytest.mark.parametrize("serialized", [False, True])
def test_identical_lists_share_values_without_changing_their_source(serialized):
    links = ["https://shared.example"]
    rows = make_results(
        [("alice", "First", {"links": links}), ("bob", "Second", {"links": links})],
        serialized,
    )
    graph = _build_maigret_graph(rows, MaigretDatabase())
    collection = f"links: {links}"
    value = "links: https://shared.example"
    assert graph.has_edge("account: https://profiles.example/alice", collection)
    assert graph.has_edge("account: https://profiles.example/bob", collection)
    assert graph.has_edge(collection, value)
    assert list(graph).count(value) == 1
    assert graph.nodes[value]["title"] == "<b>links</b><br>https://shared.example"


@pytest.mark.parametrize("serialized", [False, True])
def test_list_items_keep_their_field_and_derived_identifiers(serialized):
    rows = make_results(
        [
            (
                "alice",
                "Profiles",
                {
                    "links": ["https://target.example/bob"],
                    "aliases": [1234, True, {"source": "api"}],
                },
            )
        ],
        serialized,
    )
    db = MaigretDatabase().update_site(
        MaigretSite("Target", {"url": "https://target.example/{username}"})
    )
    graph = _build_maigret_graph(rows, db)
    assert graph.has_edge("links: https://target.example/bob", "username: bob")
    for value in ["1234", "True", "{'source': 'api'}"]:
        assert f"aliases: {value}" in graph
    assert "https://target.example/bob: Profiles" not in graph


@pytest.mark.parametrize("output", ["html", "cypher"])
def test_graph_exports_preserve_distinct_extracted_lists(tmp_path, output):
    rows = make_results(
        [
            ("alice", "Profiles", {"links": ["https://alice.example"]}),
            ("bob", "Profiles", {"links": ["https://bob.example"]}),
        ],
        True,
    )
    filename = tmp_path / f"report.{output}"
    writer = save_graph_report if output == "html" else save_neo4j_report
    writer(str(filename), rows, MaigretDatabase())
    text = filename.read_text(encoding="utf-8")
    assert "links: Profiles" not in text
    if output == "html":
        # The embedded data, not just the graph builder, must retain both lists.
        start = text.index("nodes = new vis.DataSet(") + len("nodes = new vis.DataSet(")
        nodes, _ = json.JSONDecoder().raw_decode(text[start:])
        names = {node["id"] for node in nodes}
        assert "links: ['https://alice.example']" in names
        assert "links: ['https://bob.example']" in names
    else:
        assert "links: https://alice.example" in text
        assert "links: https://bob.example" in text
