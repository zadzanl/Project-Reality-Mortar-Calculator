import json

from calculator import server


def make_fake_map(tmp_path, monkeypatch):
    map_dir = tmp_path / "fake_map"
    flow_dir = map_dir / "flow" / "gpm_cq_32" / "team1"
    flow_dir.mkdir(parents=True)
    (map_dir / "metadata.json").write_text("{}\n", encoding="ascii")
    (map_dir / "flow" / "gpm_cq_32" / "race_times.json").write_text(
        json.dumps({"format_version": "1.0"}) + "\n", encoding="ascii")
    payload = bytes(range(16))
    (flow_dir / "infantry.bin").write_bytes(payload)
    monkeypatch.setattr(server, "PROCESSED_MAPS_DIR", tmp_path)
    return map_dir, payload


def test_index_returns_html():
    server.app.config["TESTING"] = True
    rv = server.app.test_client().get("/")
    assert rv.status_code == 200
    assert "text/html" in rv.content_type


def test_static_file_served():
    server.app.config["TESTING"] = True
    rv = server.app.test_client().get("/static/css/styles.css")
    assert rv.status_code == 200
    assert "text/css" in rv.content_type or "text/plain" in rv.content_type


def test_maps_list_endpoint():
    server.app.config["TESTING"] = True
    rv = server.app.test_client().get("/maps/list")
    assert rv.status_code in (200, 404)


def test_serve_map_data_404(tmp_path, monkeypatch):
    make_fake_map(tmp_path, monkeypatch)
    rv = server.app.test_client().get("/maps/this_map_does_not_exist/metadata.json")
    assert rv.status_code == 404


def test_nested_flow_file_bytes_and_alias(tmp_path, monkeypatch):
    _, payload = make_fake_map(tmp_path, monkeypatch)
    client = server.app.test_client()
    for prefix in ("/maps", "/processed_maps"):
        rv = client.get(prefix + "/fake_map/flow/gpm_cq_32/team1/infantry.bin")
        assert rv.status_code == 200
        assert rv.data == payload
        assert len(rv.data) == 16


def test_nested_json_and_single_segment_file(tmp_path, monkeypatch):
    map_dir, _ = make_fake_map(tmp_path, monkeypatch)
    client = server.app.test_client()
    rv = client.get("/maps/fake_map/flow/gpm_cq_32/race_times.json")
    assert rv.status_code == 200
    assert rv.data == (map_dir / "flow" / "gpm_cq_32" / "race_times.json").read_bytes()
    assert "application/json" in rv.content_type
    rv = client.get("/maps/fake_map/metadata.json")
    assert rv.status_code == 200


def test_nested_path_traversal_is_rejected(tmp_path, monkeypatch):
    make_fake_map(tmp_path, monkeypatch)
    attempts = {
        "raw parent": "/maps/fake_map/flow/../metadata.json",
        "encoded parent": "/maps/fake_map/flow/%2e%2e/metadata.json",
        "empty component": "/maps/fake_map/flow//gpm_cq_32/race_times.json",
        "bare dot": "/maps/fake_map/flow/./gpm_cq_32/race_times.json",
        "drive-shaped": "/maps/fake_map/C%3A/metadata.json",
        "UNC-shaped": "/maps/fake_map/%5C%5Cserver/metadata.json",
        "backslash traversal": "/maps/fake_map/flow/..%5Cmetadata.json",
    }
    client = server.app.test_client()
    for name, path in attempts.items():
        rv = client.get(path)
        assert rv.status_code in (404, 403), name
        assert rv.data not in (b"{}\n", bytes(range(16)))
