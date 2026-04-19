from app.agents.sql_agent import generate_sql_query
from app.agents.validator_agent import validate_sql
from app.agents.execution_agent import run_query
from app.agents.insight_agent import generate_insight
from app.core.guardrails import validate_query
from app.db.query_cache import (
    clear_cached_queries,
    find_dynamic_city_query,
    find_dynamic_top_query,
    get_cached_answer,
    get_top_cached_queries,
    save_query_answer,
)


DEPARTMENT_RULES = {
    "sales": ["sales", "revenue", "quantity", "store"],
    "product": ["product", "category", "price", "launch"],
    "store": ["store", "city", "country"],
}


def is_query_allowed(query: str, department: str):
    query = query.lower()
    allowed_keywords = DEPARTMENT_RULES.get(department, [])

    return any(word in query for word in allowed_keywords)


def detect_chart(query: str, data: list):
    if not data:
        return None

    keys = list(data[0].keys())

    numeric = None
    text = None

    for key in keys:
        if isinstance(data[0][key], (int, float)):
            numeric = key
        else:
            text = key

    if not numeric or not text:
        return None

    chart_type = "bar"

    q = query.lower()
    if "distribution" in q:
        chart_type = "pie"
    elif "trend" in q or "over time" in q:
        chart_type = "line"

    return {
        "x": text,
        "y": numeric,
        "type": chart_type,
    }


def generate_dynamic_cache_answer(user_query: str, data: list, limit: int):
    if not data:
        return "No relevant data found for your query. Try refining your question."

    count = len(data)
    row_word = "result" if count == 1 else "results"
    preview = []

    for row in data[: min(count, 3)]:
        values = [f"{key}: {value}" for key, value in row.items()]
        preview.append("; ".join(values))

    summary = " | ".join(preview)
    if count > 3:
        summary = f"{summary} | ..."

    return f"Showing top {count} of requested {limit} {row_word} for '{user_query}'. {summary}"


def generate_city_cache_answer(user_query: str, data: list, city: str):
    if not data:
        return "No relevant data found for your query. Try refining your question."

    count = len(data)
    row_word = "result" if count == 1 else "results"
    preview = []

    for row in data[: min(count, 3)]:
        values = [f"{key}: {value}" for key, value in row.items()]
        preview.append("; ".join(values))

    summary = " | ".join(preview)
    if count > 3:
        summary = f"{summary} | ..."

    return f"Showing {count} {row_word} for {city} from cached query pattern. {summary}"


def process_query(user_query: str, user: dict):
    dept = user.get("department", "").lower()
    is_admin = user.get("role", "").lower() == "admin"

    if not is_admin and not is_query_allowed(user_query, dept):
        return {
            "answer": f"Please ask questions related to your department ({dept}).",
            "data": [],
            "chart": None,
            "cached": False,
        }

    if not validate_query(user_query):
        return {
            "answer": "I do not have permission to answer this. Please ask a data-related question.",
            "data": [],
            "chart": None,
            "cached": False,
        }

    cached_answer = get_cached_answer(user_query, user)
    if cached_answer:
        return cached_answer

    dynamic_top_query = find_dynamic_top_query(user_query, user)
    if dynamic_top_query and validate_sql(dynamic_top_query["sql"]):
        data = run_query(dynamic_top_query["sql"])

        if not data or all(v is None for row in data for v in row.values()):
            return {
                "answer": "No relevant data found for your query. Try refining your question.",
                "data": [],
                "chart": None,
                "cached": True,
                "cache_hit_count": 1,
            }

        insight = generate_dynamic_cache_answer(
            user_query,
            data,
            dynamic_top_query["limit"],
        )
        chart = detect_chart(user_query, data)

        save_query_answer(
            user_query,
            user,
            insight,
            data,
            chart,
            dynamic_top_query["sql"],
        )

        return {
            "answer": insight,
            "data": data,
            "chart": chart,
            "cached": True,
            "cache_hit_count": 1,
            "dynamic_cache": True,
        }

    dynamic_city_query = find_dynamic_city_query(user_query, user)
    if dynamic_city_query and validate_sql(dynamic_city_query["sql"]):
        data = run_query(dynamic_city_query["sql"])

        if not data or all(v is None for row in data for v in row.values()):
            return {
                "answer": "No relevant data found for your query. Try refining your question.",
                "data": [],
                "chart": None,
                "cached": True,
                "cache_hit_count": 1,
            }

        insight = generate_city_cache_answer(
            user_query,
            data,
            dynamic_city_query["city"],
        )
        chart = detect_chart(user_query, data)

        save_query_answer(
            user_query,
            user,
            insight,
            data,
            chart,
            dynamic_city_query["sql"],
        )

        return {
            "answer": insight,
            "data": data,
            "chart": chart,
            "cached": True,
            "cache_hit_count": 1,
            "dynamic_cache": True,
        }

    sql = generate_sql_query(user_query)

    if not validate_sql(sql):
        return {"error": "Unsafe SQL", "cached": False}

    data = run_query(sql)

    if not data or all(v is None for row in data for v in row.values()):
        return {
            "answer": "No relevant data found for your query. Try refining your question.",
            "data": [],
            "chart": None,
            "cached": False,
        }

    insight = generate_insight(user_query, data)
    chart = detect_chart(user_query, data)

    save_query_answer(
        user_query,
        user,
        insight,
        data,
        chart,
        sql,
    )

    return {
        "answer": insight,
        "data": data,
        "chart": chart,
        "cached": False,
        "cache_hit_count": 1,
    }


def top_queries(user: dict, limit: int = 20):
    return get_top_cached_queries(user, limit)


def clear_top_queries(user: dict):
    return clear_cached_queries(user)
