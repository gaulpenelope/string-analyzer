import pytest
from httpx import AsyncClient
from app.main import app, DB_PATH
import os
import sqlite3
import json
import hashlib

# ensure a fresh DB for tests
@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    db_file = tmp_path / "strings_test.db"
    monkeypatch.setenv("TEST_DB", str(db_file))
    # monkeypatch DB_PATH inside module
    import importlib
    m = importlib.import_module("app.main")
    m.DB_PATH = str(db_file)
    m.init_db()
    yield

@pytest.mark.asyncio
async def test_create_get_delete():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # create
        resp = await ac.post("/strings", json={"value": "level"})
        assert resp.status_code == 201
        data = resp.json()
        assert data["value"] == "level"
        assert data["properties"]["is_palindrome"] == True
        sha = data["id"]

        # duplicate -> 409
        resp2 = await ac.post("/strings", json={"value": "level"})
        assert resp2.status_code == 409

        # get by value
        resp3 = await ac.get("/strings/level")
        assert resp3.status_code == 200
        assert resp3.json()["id"] == sha

        # get by id
        resp4 = await ac.get(f"/strings/{sha}")
        assert resp4.status_code == 200

        # delete by value
        resp5 = await ac.delete("/strings/level")
        assert resp5.status_code == 204

        # get after delete -> 404
        resp6 = await ac.get("/strings/level")
        assert resp6.status_code == 404

@pytest.mark.asyncio
async def test_list_and_filters():
    async with AsyncClient(app=app, base_url="http://test") as ac:
        await ac.post("/strings", json={"value": "racecar"})
        await ac.post("/strings", json={"value": "hello world"})
        await ac.post("/strings", json={"value": "a"})
        await ac.post("/strings", json={"value": "noon"})

        resp = await ac.get("/strings", params={"is_palindrome": "true"})
        assert resp.status_code == 200
        assert resp.json()["count"] >= 2

        resp2 = await ac.get("/strings", params={"min_length": 5, "max_length": 10})
        assert resp2.status_code == 200

        # NL filter
        resp3 = await ac.get("/strings/filter-by-natural-language", params={"query": "all single word palindromic strings"})
        assert resp3.status_code == 200
        js = resp3.json()
        assert js["interpreted_query"]["parsed_filters"]["word_count"] == 1
        assert js["interpreted_query"]["parsed_filters"]["is_palindrome"] == True
