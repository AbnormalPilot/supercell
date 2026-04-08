"""Tests for the FastAPI server endpoints."""

import sys
import os

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.app import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


# ---------------------------------------------------------------------------
# Health / Metadata / Schema
# ---------------------------------------------------------------------------
class TestHealthEndpoint:
    def test_returns_200(self, client):
        r = client.get("/health")
        assert r.status_code == 200

    def test_returns_healthy(self, client):
        data = client.get("/health").json()
        assert data["status"] == "healthy"


class TestMetadataEndpoint:
    def test_returns_200(self, client):
        r = client.get("/metadata")
        assert r.status_code == 200

    def test_contains_required_fields(self, client):
        data = client.get("/metadata").json()
        assert "name" in data
        assert "description" in data
        assert "version" in data

    def test_name_is_supercell(self, client):
        data = client.get("/metadata").json()
        assert "supercell" in data["name"]


class TestSchemaEndpoint:
    def test_returns_200(self, client):
        r = client.get("/schema")
        assert r.status_code == 200

    def test_contains_all_schemas(self, client):
        data = client.get("/schema").json()
        assert "action" in data
        assert "observation" in data
        assert "state" in data

    def test_action_schema_has_flight_index(self, client):
        data = client.get("/schema").json()
        props = data["action"].get("properties", {})
        assert "flight_index" in props

    def test_observation_schema_has_flights(self, client):
        data = client.get("/schema").json()
        props = data["observation"].get("properties", {})
        assert "flights" in props
        assert "weather" in props


class TestTasksEndpoint:
    @staticmethod
    def _task_list(payload):
        return payload if isinstance(payload, list) else payload["tasks"]

    def test_returns_200(self, client):
        r = client.get("/tasks")
        assert r.status_code == 200

    def test_returns_three_tasks(self, client):
        data = client.get("/tasks").json()
        tasks = self._task_list(data)
        assert len(tasks) == 3

    def test_task_ids(self, client):
        data = client.get("/tasks").json()
        tasks = self._task_list(data)
        ids = {t["task_id"] for t in tasks}
        assert ids == {"easy", "medium", "hard"}


# ---------------------------------------------------------------------------
# Reset endpoint
# ---------------------------------------------------------------------------
class TestResetEndpoint:
    def test_returns_200(self, client):
        r = client.post("/reset", json={"episode_id": "easy"})
        assert r.status_code == 200

    def test_returns_observation(self, client):
        data = client.post("/reset", json={"episode_id": "easy"}).json()
        assert "observation" in data
        assert "done" in data
        assert data["done"] is False

    def test_observation_has_flights(self, client):
        data = client.post("/reset", json={"episode_id": "easy"}).json()
        obs = data["observation"]
        assert len(obs["flights"]) == 4

    def test_medium_task(self, client):
        data = client.post("/reset", json={"episode_id": "medium"}).json()
        assert len(data["observation"]["flights"]) == 7

    def test_hard_task(self, client):
        data = client.post("/reset", json={"episode_id": "hard"}).json()
        assert len(data["observation"]["flights"]) == 12

    def test_default_task(self, client):
        data = client.post("/reset", json={}).json()
        assert data["observation"]["task_id"] == "easy"

    def test_with_seed(self, client):
        data = client.post("/reset", json={"episode_id": "easy", "seed": 42}).json()
        assert data["observation"]["task_id"] == "easy"


# ---------------------------------------------------------------------------
# Step endpoint
# ---------------------------------------------------------------------------
class TestStepEndpoint:
    def test_step_without_reset_returns_400(self, client):
        # Fresh app — no reset called
        r = client.post("/step", json={"action": {"flight_index": 0}})
        assert r.status_code == 400

    def test_step_returns_200(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        r = client.post("/step", json={"action": {"flight_index": 0}})
        assert r.status_code == 200

    def test_step_returns_observation(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        data = client.post("/step", json={"action": {"flight_index": 0}}).json()
        assert "observation" in data
        assert "reward" in data
        assert "done" in data

    def test_step_reward_numeric(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        data = client.post("/step", json={"action": {"flight_index": 0}}).json()
        assert isinstance(data["reward"], (int, float))

    def test_step_reduces_flight_count(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        data = client.post("/step", json={"action": {"flight_index": 0}}).json()
        assert len(data["observation"]["flights"]) == 3

    def test_invalid_action_schema(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        r = client.post("/step", json={"action": {"wrong_field": 0}})
        assert r.status_code == 422

    def test_invalid_action_index(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        data = client.post("/step", json={"action": {"flight_index": 99}}).json()
        assert data["reward"] == -5.0

    def test_full_episode(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        done = False
        steps = 0
        while not done and steps < 20:
            data = client.post("/step", json={"action": {"flight_index": 0}}).json()
            done = data["done"] or data["observation"].get("done", False)
            steps += 1
        assert done


# ---------------------------------------------------------------------------
# State endpoint
# ---------------------------------------------------------------------------
class TestStateEndpoint:
    def test_state_without_reset_returns_400(self, client):
        r = client.get("/state")
        assert r.status_code == 400

    def test_state_returns_200(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        r = client.get("/state")
        assert r.status_code == 200

    def test_state_fields(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        data = client.get("/state").json()
        assert "step_count" in data
        assert "task_id" in data
        assert "landed_safely" in data
        assert "crashed" in data
        assert "episode_reward" in data
        assert "landing_log" in data
        assert "crash_log" in data

    def test_state_updates_after_step(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        s1 = client.get("/state").json()
        assert s1["step_count"] == 0

        client.post("/step", json={"action": {"flight_index": 0}})
        s2 = client.get("/state").json()
        assert s2["step_count"] == 1
        assert s2["landed_safely"] == 1


# ---------------------------------------------------------------------------
# Grade endpoint
# ---------------------------------------------------------------------------
class TestGradeEndpoint:
    def test_grade_without_reset_returns_400(self, client):
        r = client.post("/grade")
        assert r.status_code == 400

    def test_grade_returns_200(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        r = client.post("/grade")
        assert r.status_code == 200

    def test_grade_fields(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        client.post("/step", json={"action": {"flight_index": 0}})
        data = client.post("/grade").json()
        assert "task_id" in data
        assert "score" in data
        assert "landing_log" in data
        assert "crash_log" in data
        assert "steps_used" in data
        assert "episode_reward" in data

    def test_grade_score_in_range(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        for _ in range(10):
            r = client.post("/step", json={"action": {"flight_index": 0}})
            if r.json()["done"]:
                break
        data = client.post("/grade").json()
        assert 0.0 <= data["score"] <= 1.0

    def test_grade_after_optimal_play(self, client):
        client.post("/reset", json={"episode_id": "easy"})
        # Optimal: MAYDAY first (index 1), PAN_PAN second, then normals
        client.post("/step", json={"action": {"flight_index": 1}})
        client.post("/step", json={"action": {"flight_index": 1}})
        client.post("/step", json={"action": {"flight_index": 0}})
        client.post("/step", json={"action": {"flight_index": 0}})
        data = client.post("/grade").json()
        assert data["score"] >= 0.9


# ---------------------------------------------------------------------------
# OpenAPI docs
# ---------------------------------------------------------------------------
class TestOpenAPI:
    def test_openapi_json(self, client):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert "info" in data
        assert data["info"]["title"] == "SUPERCELL"

    def test_docs_page(self, client):
        r = client.get("/docs")
        assert r.status_code == 200
