
import re
from app.llm.gemini_client import generate_sql
from app.llm.prompts import get_sql_prompt
from app.rag.retriever import retrieve_schema

def clean_sql(sql: str) -> str:
    """
    Clean LLM output to extract pure SQL
    """

    if not sql:
        return ""

    # Remove markdown blocks like ```sql ... ```
    sql = re.sub(r"```sql", "", sql, flags=re.IGNORECASE)
    sql = re.sub(r"```", "", sql)

    # Remove leading/trailing whitespace
    sql = sql.strip()

    return sql



def generate_sql_query(user_query: str):
    
    # 🔥 RAG retrieval
    schema_context = retrieve_schema(user_query)
    print(f"Retrieved Schema Context: {schema_context}")

    prompt = f"""
You are an expert SQL generator.

Relevant Schema:
{schema_context}

Rules:
- Use only given schema
- Generate valid SQL
- Return only SQL

User Query:
{user_query}
"""

    sql = generate_sql(prompt)

    return clean_sql(sql)