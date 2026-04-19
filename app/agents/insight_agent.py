from app.llm.gemini_client import generate_text

def generate_insight(user_query: str, data: list):

    if not data:
        return "No data found."

    prompt = f"""
You are a business data analyst.

User asked:
{user_query}

Data:
{data}

Give a short, clear summary of the result.
Mention key insights like top product, trends.
Do NOT mention SQL.
-There should not be any kind of ** of extra spaces extra lines in the response.
"""

    response = generate_text(prompt)

    if not response or response.strip() == "":
        return "Top results generated successfully."

    return response.strip()