def detect_chart(query: str, data: list):

    if not data:
        return None

    keys = list(data[0].keys())

    # Find numeric column
    numeric = None
    for k in keys:
        if isinstance(data[0][k], (int, float)):
            numeric = k

    # Find text column
    text = None
    for k in keys:
        if isinstance(data[0][k], str):
            text = k

    chart_type = "bar"

    if "distribution" in query.lower():
        chart_type = "pie"
    elif "trend" in query.lower() or "over time" in query.lower():
        chart_type = "line"

    return {
        "x": text,
        "y": numeric,
        "type": chart_type
    }