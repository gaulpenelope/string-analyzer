from fastapi import FastAPI, HTTPException, Path, Query, Request, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
import hashlib
from datetime import datetime, timezone
import sqlite3
import json
import re

DB_PATH = "strings.db"

app = FastAPI(title="String Analyzer Service")


# ---------------------------
# DB helpers (simple sqlite)
# ---------------------------
def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS strings (
        id TEXT PRIMARY KEY,
        value TEXT NOT NULL,
        properties TEXT NOT NULL,
        created_at TEXT NOT NULL
    )
    """)
    conn.commit()
    conn.close()

def db_insert(id_: str, value: str, properties: dict, created_at: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("INSERT INTO strings (id, value, properties, created_at) VALUES (?, ?, ?, ?)",
                  (id_, value, json.dumps(properties), created_at))
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        raise
    conn.close()

def db_get_by_id(id_: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, value, properties, created_at FROM strings WHERE id = ?", (id_,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "value": row[1], "properties": json.loads(row[2]), "created_at": row[3]}

def db_get_by_value(value: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, value, properties, created_at FROM strings WHERE value = ?", (value,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    return {"id": row[0], "value": row[1], "properties": json.loads(row[2]), "created_at": row[3]}

def db_delete_by_id(id_: str):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM strings WHERE id = ?", (id_,))
    changes = c.rowcount
    conn.commit()
    conn.close()
    return changes

def db_query_all():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, value, properties, created_at FROM strings")
    rows = c.fetchall()
    conn.close()
    return [{"id": r[0], "value": r[1], "properties": json.loads(r[2]), "created_at": r[3]} for r in rows]

# initialization
init_db()


# ---------------------------
# Pydantic models
# ---------------------------
class CreateStringRequest(BaseModel):
    value: Any = Field(..., description="string to analyze")

class StringProperties(BaseModel):
    length: int
    is_palindrome: bool
    unique_characters: int
    word_count: int
    sha256_hash: str
    character_frequency_map: Dict[str, int]

class StringResponse(BaseModel):
    id: str
    value: str
    properties: StringProperties
    created_at: str


# ---------------------------
# Utilities: analysis
# ---------------------------
def compute_sha256(s: str) -> str:
    return hashlib.sha256(s.encode('utf-8')).hexdigest()

def analyze_string(s: str) -> dict:
    length = len(s)
    # palindrome: case-insensitive check
    is_palindrome = s.lower() == s.lower()[::-1]
    unique_characters = len(set(s))
    word_count = len(s.split())
    sha = compute_sha256(s)
    freq = {}
    for ch in s:
        freq[ch] = freq.get(ch, 0) + 1
    return {
        "length": length,
        "is_palindrome": is_palindrome,
        "unique_characters": unique_characters,
        "word_count": word_count,
        "sha256_hash": sha,
        "character_frequency_map": freq
    }


# ---------------------------
# Endpoint: Create / Analyze
# ---------------------------
@app.post("/strings", status_code=status.HTTP_201_CREATED, response_model=StringResponse)
def create_string(req: CreateStringRequest):
    if "value" not in req.__dict__:
        raise HTTPException(status_code=400, detail='Missing "value" field')
    value = req.value
    if not isinstance(value, str):
        raise HTTPException(status_code=422, detail='"value" must be a string')
    props = analyze_string(value)
    id_ = props["sha256_hash"]

    # check duplicate
    existing = db_get_by_id(id_)
    if existing:
        raise HTTPException(status_code=409, detail="String already exists in the system")

    created_at = datetime.now(timezone.utc).isoformat()
    try:
        db_insert(id_, value, props, created_at)
    except Exception:
        raise HTTPException(status_code=500, detail="Failed to persist string")

    return {"id": id_, "value": value, "properties": props, "created_at": created_at}


# ---------------------------
# Endpoint: Get specific
# ---------------------------
def is_sha256_hex(s: str) -> bool:
    return bool(re.fullmatch(r"[A-Fa-f0-9]{64}", s))

@app.get("/strings/{string_value}", response_model=StringResponse)
def get_string(string_value: str = Path(..., description="raw string or sha256 id")):
    # attempt to treat param as sha256 id first
    if is_sha256_hex(string_value):
        item = db_get_by_id(string_value)
        if not item:
            raise HTTPException(status_code=404, detail="String does not exist in the system")
        return item
    # else treat as raw string (URL-decoded by framework)
    item = db_get_by_value(string_value)
    if not item:
        raise HTTPException(status_code=404, detail="String does not exist in the system")
    return item


# ---------------------------
# Endpoint: Delete
# ---------------------------
@app.delete("/strings/{string_value}", status_code=status.HTTP_204_NO_CONTENT)
def delete_string(string_value: str = Path(..., description="raw string or sha256 id")):
    if is_sha256_hex(string_value):
        changes = db_delete_by_id(string_value)
        if changes == 0:
            raise HTTPException(status_code=404, detail="String does not exist in the system")
        return
    item = db_get_by_value(string_value)
    if not item:
        raise HTTPException(status_code=404, detail="String does not exist in the system")
    changes = db_delete_by_id(item["id"])
    if changes == 0:
        raise HTTPException(status_code=404, detail="String does not exist in the system")
    return


# ---------------------------
# Endpoint: Get All with filtering
# ---------------------------
@app.get("/strings")
def list_strings(
    is_palindrome: Optional[bool] = Query(None),
    min_length: Optional[int] = Query(None, ge=0),
    max_length: Optional[int] = Query(None, ge=0),
    word_count: Optional[int] = Query(None, ge=0),
    contains_character: Optional[str] = Query(None, min_length=1, max_length=1)
):
    # fetch all and apply filters in Python (sqlite could do it too)
    all_items = db_query_all()
    def matches(item):
        p = item["properties"]
        if is_palindrome is not None and p["is_palindrome"] != is_palindrome:
            return False
        if min_length is not None and p["length"] < min_length:
            return False
        if max_length is not None and p["length"] > max_length:
            return False
        if word_count is not None and p["word_count"] != word_count:
            return False
        if contains_character is not None:
            if contains_character not in p["character_frequency_map"]:
                return False
        return True
    data = [i for i in all_items if matches(i)]
    return {"data": data, "count": len(data), "filters_applied": {
        "is_palindrome": is_palindrome,
        "min_length": min_length,
        "max_length": max_length,
        "word_count": word_count,
        "contains_character": contains_character
    }}


# ---------------------------
# Endpoint: Natural-language filtering
# ---------------------------
def parse_nl_query(q: str) -> dict:
    """
    Very small-rule-based parser that aims to cover the example queries.
    Returns dict of parsed filters or raises ValueError if cannot parse.
    Recognized:
      - "all single word palindromic strings" -> word_count=1, is_palindrome=True
      - "strings longer than N characters" or "longer than N" -> min_length = N+1
      - "palindromic strings that contain the first vowel" -> is_palindrome=True, contains_character='a'
      - "strings containing the letter z" -> contains_character='z'
      - "palindromic strings" -> is_palindrome=True
      - "single word strings" -> word_count=1
    """
    ql = q.strip().lower()
    filters = {}
    # single word & palindromic
    if "single word" in ql or "single-word" in ql:
        filters["word_count"] = 1
    if "palindrom" in ql:
        filters["is_palindrome"] = True
    # longer than N characters
    m = re.search(r"longer than (\d+)", ql)
    if m:
        n = int(m.group(1))
        filters["min_length"] = n+1
    m2 = re.search(r"longer than (\d+) characters", ql)
    if m2:
        n = int(m2.group(1))
        filters["min_length"] = n+1
    # containing the letter X
    m3 = re.search(r"containing the letter (\w)", ql)
    if m3:
        filters["contains_character"] = m3.group(1)
    # containing character z
    if "containing the letter z" in ql or "contain the letter z" in ql or "containing z" in ql:
        filters["contains_character"] = "z"
    # "contain the first vowel" heuristic -> 'a'
    if "first vowel" in ql:
        filters["contains_character"] = "a"
    # "strings containing the letter <char>" (generic)
    m4 = re.search(r"containing the letter (\w)", ql)
    if m4:
        filters["contains_character"] = m4.group(1)
    if not filters:
        raise ValueError("Unable to parse natural language query")
    return filters

@app.get("/strings/filter-by-natural-language")
def filter_by_nl(query: str = Query(..., description="natural language query")):
    try:
        parsed = parse_nl_query(query)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    # transform parsed to actual query params for list_strings
    # Validate potential conflicting filters (example: min_length > max_length)
    # For simplicity, use the list_strings function internal matching
    # apply filters to all items
    all_items = db_query_all()
    def matches(item):
        p = item["properties"]
        if "is_palindrome" in parsed and p["is_palindrome"] != parsed["is_palindrome"]:
            return False
        if "min_length" in parsed and p["length"] < parsed["min_length"]:
            return False
        if "max_length" in parsed and p["length"] > parsed["max_length"]:
            return False
        if "word_count" in parsed and p["word_count"] != parsed["word_count"]:
            return False
        if "contains_character" in parsed and parsed["contains_character"] not in p["character_frequency_map"]:
            return False
        return True

    data = [i for i in all_items if matches(i)]
    return {
        "data": data,
        "count": len(data),
        "interpreted_query": {
            "original": query,
            "parsed_filters": parsed
        }
    }
