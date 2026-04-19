def validate_query(query: str):
    q = query.lower()

    allowed_keywords = [
        "sales", "product", "store", "quantity",
        "revenue", "top", "count", "sum"
    ]

    return any(word in q for word in allowed_keywords)

def validate_sql(sql: str):
    sql = sql.lower()

    # Block dangerous operations
    blocked = ["delete", "update", "insert", "drop"]

    if any(b in sql for b in blocked):
        return False

    return True