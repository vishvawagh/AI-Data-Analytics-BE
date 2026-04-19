import json
import re
from datetime import datetime
from typing import Any, Optional

from app.db.database import get_connection


NUMBER_WORDS = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
    "six": 6,
    "seven": 7,
    "eight": 8,
    "nine": 9,
    "ten": 10,
    "eleven": 11,
    "twelve": 12,
    "thirteen": 13,
    "fourteen": 14,
    "fifteen": 15,
    "sixteen": 16,
    "seventeen": 17,
    "eighteen": 18,
    "nineteen": 19,
    "twenty": 20,
}
TOP_LIMIT_PATTERN = re.compile(
    r"\b(top|first)\s+(\d+|one|two|three|four|five|six|seven|eight|nine|ten|"
    r"eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|"
    r"nineteen|twenty)\b",
    re.IGNORECASE,
)
SQL_LIMIT_PATTERN = re.compile(r"\blimit\s+\d+\s*(?:;)?\s*$", re.IGNORECASE)
CITY_FALLBACK_PATTERN = re.compile(
    r"\b(?:from|in|at)\s+([A-Za-z][A-Za-z .'-]*?)"
    r"(?=\s+(?:for|by|with|where|and|top|sales|stores|store|products|product|"
    r"revenue|quantity)\b|$)",
    re.IGNORECASE,
)
SQL_CITY_PATTERN = re.compile(
    r"(\b(?:stores\.)?city\s*(?:=|like)\s*)(?:'([^']|'')*'|\"([^\"]|\"\")*\")",
    re.IGNORECASE,
)


def ensure_query_cache_table():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS query_answer_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            access_scope TEXT NOT NULL,
            query_template TEXT NOT NULL,
            query_text TEXT NOT NULL,
            date_from TEXT,
            date_to TEXT,
            sql TEXT,
            answer TEXT NOT NULL,
            data_json TEXT NOT NULL,
            chart_json TEXT,
            hit_count INTEGER NOT NULL DEFAULT 1,
            cache_hits INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            last_used_at TEXT NOT NULL,
            UNIQUE(access_scope, query_template, date_from, date_to)
        )
        """
    )
    cursor.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_query_answer_cache_top
        ON query_answer_cache (access_scope, hit_count DESC, last_used_at DESC)
        """
    )

    conn.commit()
    conn.close()


def get_access_scope(user: dict) -> str:
    role = (user.get("role") or "").lower()
    if role == "admin":
        return "admin"
    return (user.get("department") or "general").lower()


def clean_query_text(query: str) -> str:
    text = query or ""
    text = re.sub(r"\s+", " ", text).strip(" ,.-")
    return text or (query or "").strip()


def normalize_query_template(query: str) -> str:
    normalized = clean_query_text(query).lower()
    normalized = re.sub(r"[^a-z0-9]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def get_known_cities() -> list[str]:
    conn = get_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "SELECT DISTINCT city FROM stores WHERE city IS NOT NULL AND TRIM(city) != ''"
        )
        cities = [row["city"] for row in cursor.fetchall()]
    except Exception:
        cities = []
    finally:
        conn.close()

    return sorted(cities, key=len, reverse=True)


def extract_city_value(query: str) -> Optional[str]:
    text = clean_query_text(query)
    lowered_text = text.lower()

    for city in get_known_cities():
        if re.search(rf"\b{re.escape(city.lower())}\b", lowered_text):
            return city

    match = CITY_FALLBACK_PATTERN.search(text)
    if not match:
        return None

    city = match.group(1).strip(" ,.-")
    return city or None


def normalize_city_template(query: str) -> Optional[str]:
    city = extract_city_value(query)
    if not city:
        return None

    normalized = clean_query_text(query).lower()
    normalized = re.sub(re.escape(city.lower()), "__city__", normalized, count=1)
    normalized = re.sub(r"[^a-z0-9_]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def extract_top_limit(query: str) -> Optional[int]:
    match = TOP_LIMIT_PATTERN.search(query or "")
    if not match:
        return None

    raw_limit = match.group(2).lower()
    limit = int(raw_limit) if raw_limit.isdigit() else NUMBER_WORDS.get(raw_limit)

    if not limit or limit < 1:
        return None

    return min(limit, 100)


def normalize_top_limit_template(query: str) -> Optional[str]:
    if not extract_top_limit(query):
        return None

    normalized = clean_query_text(query).lower()
    normalized = TOP_LIMIT_PATTERN.sub(r"\1 __limit__", normalized)
    normalized = re.sub(r"[^a-z0-9_]+", " ", normalized)
    return re.sub(r"\s+", " ", normalized).strip()


def apply_sql_limit(sql: str, limit: int) -> str:
    base_sql = (sql or "").strip().rstrip(";")
    if not base_sql:
        return ""

    limited_sql = SQL_LIMIT_PATTERN.sub(f"LIMIT {limit}", base_sql)
    if limited_sql == base_sql:
        limited_sql = f"{base_sql} LIMIT {limit}"

    return limited_sql


def apply_sql_city(sql: str, city: str) -> str:
    safe_city = (city or "").strip().replace("'", "''")
    if not safe_city:
        return ""

    return SQL_CITY_PATTERN.sub(
        lambda match: (
            f"{match.group(1)}'%{safe_city}%'"
            if "like" in match.group(1).lower()
            else f"{match.group(1)}'{safe_city}'"
        ),
        sql or "",
        count=1,
    )


def _decode_json(value: Optional[str], fallback: Any):
    if not value:
        return fallback
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return fallback


def _row_to_response(row) -> dict:
    return {
        "answer": row["answer"],
        "data": _decode_json(row["data_json"], []),
        "chart": _decode_json(row["chart_json"], None),
        "cached": True,
        "cache_hit_count": row["hit_count"],
    }


def get_cached_answer(query: str, user: dict) -> Optional[dict]:
    ensure_query_cache_table()

    scope = get_access_scope(user)
    template = normalize_query_template(query)

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM query_answer_cache
        WHERE access_scope = ?
          AND query_template = ?
          AND date_from IS NULL
          AND date_to IS NULL
        """,
        (scope, template),
    )
    row = cursor.fetchone()

    if not row:
        conn.close()
        return None

    now = datetime.utcnow().isoformat()
    cursor.execute(
        """
        UPDATE query_answer_cache
        SET hit_count = hit_count + 1,
            cache_hits = cache_hits + 1,
            last_used_at = ?
        WHERE id = ?
        """,
        (now, row["id"]),
    )
    conn.commit()

    cursor.execute("SELECT * FROM query_answer_cache WHERE id = ?", (row["id"],))
    updated_row = cursor.fetchone()
    conn.close()

    return _row_to_response(updated_row)


def find_dynamic_top_query(query: str, user: dict) -> Optional[dict]:
    ensure_query_cache_table()

    requested_limit = extract_top_limit(query)
    requested_template = normalize_top_limit_template(query)
    if not requested_limit or not requested_template:
        return None

    scope = get_access_scope(user)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM query_answer_cache
        WHERE access_scope = ?
          AND sql IS NOT NULL
          AND date_from IS NULL
          AND date_to IS NULL
        ORDER BY last_used_at DESC
        """,
        (scope,),
    )
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        cached_template = normalize_top_limit_template(row["query_text"])
        if cached_template == requested_template:
            return {
                "source_id": row["id"],
                "source_query": row["query_text"],
                "sql": apply_sql_limit(row["sql"], requested_limit),
                "limit": requested_limit,
            }

    return None


def find_dynamic_city_query(query: str, user: dict) -> Optional[dict]:
    ensure_query_cache_table()

    requested_city = extract_city_value(query)
    requested_template = normalize_city_template(query)
    if not requested_city or not requested_template:
        return None

    scope = get_access_scope(user)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM query_answer_cache
        WHERE access_scope = ?
          AND sql IS NOT NULL
          AND date_from IS NULL
          AND date_to IS NULL
        ORDER BY last_used_at DESC
        """,
        (scope,),
    )
    rows = cursor.fetchall()
    conn.close()

    for row in rows:
        cached_template = normalize_city_template(row["query_text"])
        if cached_template != requested_template:
            continue

        city_sql = apply_sql_city(row["sql"], requested_city)
        if city_sql and city_sql != row["sql"]:
            return {
                "source_id": row["id"],
                "source_query": row["query_text"],
                "sql": city_sql,
                "city": requested_city,
            }

    return None


def save_query_answer(
    query: str,
    user: dict,
    answer: str,
    data: list,
    chart: Optional[dict],
    sql: str,
):
    ensure_query_cache_table()

    scope = get_access_scope(user)
    template = normalize_query_template(query)
    query_text = clean_query_text(query)
    now = datetime.utcnow().isoformat()

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT id
        FROM query_answer_cache
        WHERE access_scope = ?
          AND query_template = ?
          AND date_from IS NULL
          AND date_to IS NULL
        """,
        (scope, template),
    )
    row = cursor.fetchone()

    payload = (
        query_text,
        sql,
        answer,
        json.dumps(data or []),
        json.dumps(chart) if chart else None,
        now,
        now,
    )

    if row:
        cursor.execute(
            """
            UPDATE query_answer_cache
            SET query_text = ?,
                sql = ?,
                answer = ?,
                data_json = ?,
                chart_json = ?,
                hit_count = hit_count + 1,
                updated_at = ?,
                last_used_at = ?
            WHERE id = ?
            """,
            (*payload, row["id"]),
        )
    else:
        cursor.execute(
            """
            INSERT INTO query_answer_cache (
                access_scope, query_template, query_text, date_from, date_to,
                sql, answer, data_json, chart_json, hit_count, cache_hits,
                created_at, updated_at, last_used_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, 0, ?, ?, ?)
            """,
            (
                scope,
                template,
                query_text,
                None,
                None,
                sql,
                answer,
                json.dumps(data or []),
                json.dumps(chart) if chart else None,
                now,
                now,
                now,
            ),
        )

    conn.commit()
    conn.close()


def get_top_cached_queries(user: dict, limit: int = 20) -> list[dict]:
    ensure_query_cache_table()

    scope = get_access_scope(user)
    safe_limit = max(1, min(limit, 20))

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        SELECT *
        FROM query_answer_cache
        WHERE access_scope = ?
          AND date_from IS NULL
          AND date_to IS NULL
        ORDER BY last_used_at DESC
        """,
        (scope,),
    )
    rows = cursor.fetchall()
    conn.close()

    grouped = {}
    for row in rows:
        template = row["query_template"]
        item = grouped.setdefault(
            template,
            {
                "query": row["query_text"],
                "hit_count": 0,
                "cache_hits": 0,
                "last_used_at": row["last_used_at"],
            },
        )
        item["hit_count"] += row["hit_count"]
        item["cache_hits"] += row["cache_hits"]

        if row["last_used_at"] > item["last_used_at"]:
            item["query"] = row["query_text"]
            item["last_used_at"] = row["last_used_at"]

    top_queries = sorted(
        grouped.values(),
        key=lambda item: item["last_used_at"],
        reverse=True,
    )
    return top_queries[:safe_limit]


def clear_cached_queries(user: dict) -> int:
    ensure_query_cache_table()

    scope = get_access_scope(user)
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        "DELETE FROM query_answer_cache WHERE access_scope = ?",
        (scope,),
    )
    deleted_count = cursor.rowcount
    conn.commit()
    conn.close()

    return deleted_count
