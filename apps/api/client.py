"""Lightweight HTTP client for the ATC-Triage-v1 environment server."""

from __future__ import annotations

import httpx

from models import ATCAction, ATCObservation, ATCState


class ATCClient:
    """Synchronous client that talks to the ATC environment server over HTTP."""

    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=30.0)

    def health(self) -> dict:
        r = self._http.get("/health")
        r.raise_for_status()
        return r.json()

    def metadata(self) -> dict:
        r = self._http.get("/metadata")
        r.raise_for_status()
        return r.json()

    def tasks(self) -> list[dict]:
        r = self._http.get("/tasks")
        r.raise_for_status()
        payload = r.json()
        return payload if isinstance(payload, list) else payload["tasks"]

    def reset(self, task_id: str = "easy", seed: int | None = None) -> dict:
        payload: dict = {"episode_id": task_id}
        if seed is not None:
            payload["seed"] = seed
        r = self._http.post("/reset", json=payload)
        r.raise_for_status()
        return r.json()

    def step(self, flight_index: int) -> dict:
        r = self._http.post("/step", json={"action": {"flight_index": flight_index}})
        r.raise_for_status()
        return r.json()

    def state(self) -> dict:
        r = self._http.get("/state")
        r.raise_for_status()
        return r.json()

    def grade(self) -> dict:
        r = self._http.post("/grade")
        r.raise_for_status()
        return r.json()

    def close(self):
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
