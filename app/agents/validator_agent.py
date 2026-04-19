def validate_sql(sql: str):
    sql = sql.lower()

    blocked = ["delete", "update", "insert", "drop"]

    if any(word in sql for word in blocked):
        return False

    if not sql.strip().startswith("select"):
        return False

    return True