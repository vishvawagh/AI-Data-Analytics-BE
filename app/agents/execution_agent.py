from app.db.query_executor import execute_sql

def run_query(sql: str):
    return execute_sql(sql)