"""Thin HTTP client that talks to the FastAPI backend."""
from __future__ import annotations
import os
import httpx
from typing import Optional, Any

API_BASE = os.environ.get("API_BASE_URL", "http://localhost:8000")
TIMEOUT = 120.0


def _client() -> httpx.Client:
    return httpx.Client(base_url=API_BASE, timeout=TIMEOUT)


def health() -> dict:
    with _client() as c:
        return c.get("/health").json()


def get_plan_info() -> Optional[dict]:
    with _client() as c:
        r = c.get("/plan/current")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


def get_sections() -> list:
    with _client() as c:
        r = c.get("/plan/sections")
        if r.status_code == 404:
            return []
        return r.json().get("sections", [])


def get_options(section: Optional[str] = None) -> list:
    with _client() as c:
        params = {"section": section} if section else {}
        r = c.get("/plan/options", params=params)
        if r.status_code == 404:
            return []
        return r.json().get("options", [])


def get_option_detail(section: str, option_no: int) -> Optional[dict]:
    with _client() as c:
        r = c.get(f"/plan/options/{section}/{option_no}")
        if r.status_code == 404:
            return None
        return r.json()


def get_parsed_items() -> list:
    with _client() as c:
        r = c.get("/plan/parsed-items")
        if r.status_code == 404:
            return []
        return r.json().get("items", [])


def upload_plan(file_bytes: bytes, filename: str) -> dict:
    with _client() as c:
        r = c.post(
            "/plan/upload",
            files={"file": (filename, file_bytes, "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        )
        return {"status_code": r.status_code, "data": r.json()}


def download_template() -> bytes:
    with _client() as c:
        r = c.get("/plan/template")
        r.raise_for_status()
        return r.content


def download_workbook() -> bytes:
    with _client() as c:
        r = c.get("/workbook/download")
        r.raise_for_status()
        return r.content


def send_message(message: str, session_id: str = "default", date_override: Optional[str] = None) -> dict:
    with _client() as c:
        payload: dict = {"message": message, "session_id": session_id}
        if date_override:
            payload["date_override"] = date_override
        r = c.post("/assistant/message", json=payload)
        r.raise_for_status()
        return r.json()


def get_daily_tracking(date: str) -> Optional[dict]:
    with _client() as c:
        r = c.get(f"/tracking/day/{date}")
        if r.status_code == 404:
            return None
        r.raise_for_status()
        return r.json()


def get_events(date: Optional[str] = None) -> list:
    with _client() as c:
        params = {"date": date} if date else {}
        r = c.get("/tracking/events", params=params)
        if r.status_code == 404:
            return []
        return r.json().get("events", [])


def patch_event(event_id: str, patch: dict) -> dict:
    with _client() as c:
        r = c.patch(f"/tracking/events/{event_id}", json=patch)
        r.raise_for_status()
        return r.json()


def delete_event(event_id: str) -> dict:
    with _client() as c:
        r = c.delete(f"/tracking/events/{event_id}")
        r.raise_for_status()
        return r.json()


def reparse_options() -> dict:
    with _client() as c:
        r = c.post("/plan/parse-options")
        r.raise_for_status()
        return r.json()


def get_calorie_goal() -> int | None:
    with _client() as c:
        r = c.get("/plan/calorie-goal")
        if r.status_code != 200:
            return None
        return r.json().get("calorie_goal")


def set_calorie_goal(goal: int) -> dict:
    with _client() as c:
        r = c.put("/plan/calorie-goal", json={"calorie_goal": goal})
        r.raise_for_status()
        return r.json()
