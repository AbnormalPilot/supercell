"""Validator-oriented contract tests for submission checks."""

import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from server.app import create_app


def _tasks_payload(client: TestClient) -> dict:
    res = client.get("/tasks")
    assert res.status_code == 200
    data = res.json()
    if isinstance(data, list):
        return {"tasks": data, "count": len(data)}
    assert isinstance(data, dict)
    assert "tasks" in data
    assert isinstance(data["tasks"], list)
    return data


def test_reset_accepts_empty_body() -> None:
    client = TestClient(create_app())
    res = client.post("/reset")
    assert res.status_code == 200
    body = res.json()
    assert "observation" in body
    assert body["observation"]["task_id"] == "easy"


def test_tasks_wrapper_has_count_and_three_tasks() -> None:
    client = TestClient(create_app())
    data = _tasks_payload(client)
    assert data["count"] == 3
    assert len(data["tasks"]) == 3


def test_tasks_have_unique_expected_ids() -> None:
    client = TestClient(create_app())
    tasks = _tasks_payload(client)["tasks"]
    ids = {t["task_id"] for t in tasks}
    assert ids == {"easy", "medium", "hard"}


def test_each_task_declares_grader() -> None:
    client = TestClient(create_app())
    tasks = _tasks_payload(client)["tasks"]
    for task in tasks:
        assert task["has_grader"] is True
        assert task["grader"]["type"] == "deterministic"
        assert task["grader"]["endpoint"] == "/grade"


def test_graders_endpoint_lists_three_graders() -> None:
    client = TestClient(create_app())
    res = client.get("/graders")
    assert res.status_code == 200
    data = res.json()
    assert data["count"] == 3
    assert len(data["graders"]) == 3


def test_grade_works_for_all_tasks() -> None:
    client = TestClient(create_app())
    for task_id in ("easy", "medium", "hard"):
        rr = client.post("/reset", json={"episode_id": task_id})
        assert rr.status_code == 200
        gr = client.post("/grade")
        assert gr.status_code == 200
        data = gr.json()
        assert data["task_id"] == task_id
        assert 0.0 <= data["score"] <= 1.0

