"""Tests of the dashboard tool adapters against in-process fake servers.

They prove the requests each adapter sends and how it reads the answers;
none of Grafana, Metabase, Superset or Power BI was available live.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))

from fake_json_server import FakeJsonServer  # noqa: E402

from ai_platform.common.visualization_tool.dashboard_support import DashboardToolError  # noqa: E402
from ai_platform.common.visualization_tool.grafana_adapter import GrafanaAdapter  # noqa: E402
from ai_platform.common.visualization_tool.metabase_adapter import MetabaseAdapter  # noqa: E402
from ai_platform.common.visualization_tool.powerbi_adapter import PowerBIAdapter  # noqa: E402
from ai_platform.common.visualization_tool.superset_adapter import SupersetAdapter  # noqa: E402
from ai_platform.common.visualization_tool.tableau_adapter import TableauAdapter  # noqa: E402

DATA = {"x": ["r1", "r2"], "series": {"qwen": [2.1, 1.8], "bielik": [3.0, 2.4]}}


def test_grafana_csv_panel():
    with FakeJsonServer({("POST", "/api/dashboards/db"):
                         {"status": "success", "uid": "u1", "url": "/d/u1/latency"}}) as server:
        grafana = GrafanaAdapter()
        grafana.connect({"url": server.url, "token": "t", "folder_uid": "f"})
        url = grafana.create_dashboard(DATA, title="Latency", plot_type="bar")
    request = server.requests[0]
    assert request["headers"]["authorization"] == "Bearer t"
    panel = request["body"]["dashboard"]["panels"][0]
    assert panel["type"] == "barchart"
    assert panel["targets"][0]["csvContent"] == "x,qwen,bielik\nr1,2.1,3.0\nr2,1.8,2.4"
    assert request["body"]["folderUid"] == "f" and request["body"]["overwrite"] is True
    assert url == server.url + "/d/u1/latency"


def test_metabase_session_login_and_cards():
    routes = {
        ("POST", "/api/session"): {"id": "sess"},
        ("POST", "/api/dashboard"): {"id": 7},
        ("POST", "/api/card"): {"id": 42},
        ("PUT", "/api/dashboard/7"): {"id": 7},
    }
    with FakeJsonServer(routes) as server:
        metabase = MetabaseAdapter()
        metabase.connect({"url": server.url, "username": "u", "password": "p"})
        url = metabase.create_dashboard({"questions": [
            {"name": "Latency", "sql": "SELECT 1", "database_id": 1, "display": "line"}]})
    card = server.requests[2]
    assert card["headers"]["x-metabase-session"] == "sess"
    assert card["body"]["dataset_query"]["native"]["query"] == "SELECT 1"
    assert server.requests[3]["body"]["dashcards"][0]["card_id"] == 42
    assert url == f"{server.url}/dashboard/7"


def test_metabase_needs_credentials(monkeypatch):
    monkeypatch.delenv("METABASE_API_KEY", raising=False)
    with FakeJsonServer({}) as server:
        with pytest.raises(DashboardToolError, match="api_key"):
            MetabaseAdapter().connect({"url": server.url})


def test_superset_login_csrf_and_charts():
    def login(_m, _p, body, _h):
        assert body["provider"] == "db"
        return 200, {"access_token": "jwt"}

    routes = {("POST", "/api/v1/security/login"): login,
              ("GET", "/api/v1/security/csrf_token/"): {"result": "csrf"},
              ("POST", "/api/v1/dashboard/"): (201, {"id": 5}),
              ("PUT", "/api/v1/chart/3"): {"id": 3}}
    with FakeJsonServer(routes) as server:
        superset = SupersetAdapter()
        superset.connect({"url": server.url, "username": "admin", "password": "x"})
        url = superset.create_dashboard({"chart_ids": [3]}, title="Bench")
    created = server.requests[2]
    assert created["headers"]["authorization"] == "Bearer jwt"
    assert created["headers"]["x-csrftoken"] == "csrf"
    assert created["body"]["dashboard_title"] == "Bench"
    assert server.requests[3]["body"] == {"dashboards": [5]}
    assert url.endswith("/superset/dashboard/5/")


def test_powerbi_push_dataset_and_dashboard():
    routes = {("POST", "/groups/g/datasets?defaultRetentionPolicy=basicFIFO"): {"id": "ds"},
              ("POST", "/groups/g/datasets/ds/tables/data/rows"): {},
              ("POST", "/groups/g/dashboards"): {"id": "db", "webUrl": "https://app/x"}}
    with FakeJsonServer(routes) as server:
        powerbi = PowerBIAdapter()
        powerbi.connect({"url": server.url, "access_token": "aad", "group_id": "g"})
        assert powerbi.create_dashboard(DATA, title="Bench") == "https://app/x"
    rows = server.requests[1]["body"]["rows"]
    assert len(rows) == 4 and rows[0] == {"x": "r1", "y": 2.1, "series": "qwen"}
    assert server.requests[0]["body"]["defaultMode"] == "Push"


def test_tableau_refuses():
    with pytest.raises(NotImplementedError, match="GrafanaAdapter"):
        TableauAdapter().create_dashboard(DATA)
