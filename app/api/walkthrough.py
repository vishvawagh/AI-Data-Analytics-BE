from fastapi import APIRouter, Depends
from app.api.auth import get_current_user
from app.db.database import get_connection
import sqlite3

router = APIRouter(prefix="/walkthrough")

# Role-based table access (from the extra folder config)
ROLE_TABLE_ACCESS = {
    "admin": {"category", "products", "sales", "stores", "warranty"},
    "sales": {"category", "products", "sales", "stores"},
    "creativity": {"category", "products", "sales", "warranty"}
}

# Group fields configuration
GROUP_FIELDS = [
    {
        "id": "product",
        "label": "Product",
        "expr": "p.product_name",
        "alias": "product_name",
        "required_tables": {"sales", "products"},
    },
    {
        "id": "category",
        "label": "Category",
        "expr": "c.category_name",
        "alias": "category_name",
        "required_tables": {"sales", "products", "category"},
    },
    {
        "id": "city",
        "label": "City",
        "expr": "st.city",
        "alias": "city",
        "required_tables": {"sales", "stores"},
    },
    {
        "id": "country",
        "label": "Country",
        "expr": "st.country",
        "alias": "country",
        "required_tables": {"sales", "stores"},
    },
    {
        "id": "store",
        "label": "Store",
        "expr": "st.store_name",
        "alias": "store_name",
        "required_tables": {"sales", "stores"},
    },
    {
        "id": "sale_date",
        "label": "Sale Date",
        "expr": "s.sale_date",
        "alias": "sale_date",
        "required_tables": {"sales"},
    },
    {
        "id": "sale_month",
        "label": "Sale Month",
        "expr": "strftime('%Y-%m', s.sale_date)",
        "alias": "sale_month",
        "required_tables": {"sales"},
    },
]

# Measure fields configuration
MEASURE_FIELDS = [
    {
        "id": "quantity",
        "label": "Sales Quantity",
        "expr": "s.quantity",
        "alias": "sales_quantity",
        "type": "numeric",
        "required_tables": {"sales"},
    },
    {
        "id": "price",
        "label": "Unit Price",
        "expr": "p.price",
        "alias": "unit_price",
        "type": "numeric",
        "required_tables": {"sales", "products"},
    },
    {
        "id": "revenue",
        "label": "Revenue (Quantity x Price)",
        "expr": "(s.quantity * p.price)",
        "alias": "revenue",
        "type": "numeric",
        "required_tables": {"sales", "products"},
    },
    {
        "id": "sales_rows",
        "label": "Sales Rows",
        "expr": "s.sale_id",
        "alias": "sales_rows",
        "type": "text",
        "required_tables": {"sales"},
    },
    {
        "id": "claims",
        "label": "Warranty Claims",
        "expr": "w.claim_id",
        "alias": "warranty_claims",
        "type": "text",
        "required_tables": {"sales", "warranty"},
    },
]

AGG_FUNCTIONS = ["NONE", "SUM", "AVG", "COUNT", "MAX", "MIN"]
RANKING_MODES = ["Top", "Bottom", "Full table"]

def get_accessible_group_fields(role: str):
    allowed_tables = ROLE_TABLE_ACCESS[role]
    return [item for item in GROUP_FIELDS if item["required_tables"].issubset(allowed_tables)]

def get_accessible_measure_fields(role: str, agg_function: str):
    allowed_tables = ROLE_TABLE_ACCESS[role]
    visible = []
    for item in MEASURE_FIELDS:
        if not item["required_tables"].issubset(allowed_tables):
            continue
        if agg_function in {"SUM", "AVG"} and item["type"] != "numeric":
            continue
        visible.append(item)
    return visible

def _build_join_sql(required_tables: set[str]):
    joins = []
    if "products" in required_tables or "category" in required_tables:
        joins.append("JOIN products p ON s.product_id = p.product_id")
    if "category" in required_tables:
        joins.append("JOIN category c ON p.category_id = c.category_id")
    if "stores" in required_tables:
        joins.append("JOIN stores st ON s.store_id = st.store_id")
    if "warranty" in required_tables:
        joins.append("LEFT JOIN warranty w ON s.sale_id = w.sale_id")
    return "\n".join(joins)

def _measure_expr_with_agg(agg_function: str, measure_expr: str):
    if agg_function == "NONE":
        return measure_expr
    if agg_function == "COUNT":
        return f"COUNT({measure_expr})"
    if agg_function == "SUM":
        return f"SUM({measure_expr})"
    if agg_function == "AVG":
        return f"ROUND(AVG({measure_expr}), 2)"
    if agg_function == "MAX":
        return f"MAX({measure_expr})"
    if agg_function == "MIN":
        return f"MIN({measure_expr})"
    raise ValueError("Unsupported aggregate function.")

def _validate_role_access(role: str, required_tables: set[str]):
    allowed_tables = ROLE_TABLE_ACCESS[role]
    unauthorized = required_tables - allowed_tables
    if unauthorized:
        raise ValueError(
            f"Unauthorized table access for role '{role}': {', '.join(sorted(unauthorized))}"
        )

def build_analytics_query(
    role: str,
    group_field_ids: list[str],
    agg_function: str,
    measure_field_ids: list[str],
    start_date: str,
    end_date: str,
    cities: list[str],
    categories: list[str],
    products: list[str],
    countries: list[str],
    ranking_mode: str,
    limit_n: int,
):
    if agg_function not in AGG_FUNCTIONS:
        raise ValueError("Invalid aggregate function.")
    if ranking_mode not in RANKING_MODES:
        raise ValueError("Invalid ranking mode.")
    if not measure_field_ids:
        raise ValueError("Choose at least one measure.")

    group_fields = [item for item in GROUP_FIELDS if item["id"] in group_field_ids]
    measure_fields = [item for item in MEASURE_FIELDS if item["id"] in measure_field_ids]

    required_tables = {"sales"}
    for field in group_fields + measure_fields:
        required_tables.update(field["required_tables"])

    where_clauses = []
    params = []

    if start_date and end_date:
        where_clauses.append("s.sale_date BETWEEN ? AND ?")
        params.extend([start_date, end_date])

    if cities:
        required_tables.update({"sales", "stores"})
        placeholders = ", ".join(["?"] * len(cities))
        where_clauses.append(f"st.city IN ({placeholders})")
        params.extend(cities)

    if countries:
        required_tables.update({"sales", "stores"})
        placeholders = ", ".join(["?"] * len(countries))
        where_clauses.append(f"st.country IN ({placeholders})")
        params.extend(countries)

    if categories:
        required_tables.update({"sales", "products", "category"})
        placeholders = ", ".join(["?"] * len(categories))
        where_clauses.append(f"c.category_name IN ({placeholders})")
        params.extend(categories)

    if products:
        required_tables.update({"sales", "products"})
        placeholders = ", ".join(["?"] * len(products))
        where_clauses.append(f"p.product_name IN ({placeholders})")
        params.extend(products)

    # If category is selected but product filter is empty, include product in output automatically.
    if categories and not products and "category" in group_field_ids and "product" not in group_field_ids:
        product_field = next(item for item in GROUP_FIELDS if item["id"] == "product")
        group_fields.append(product_field)
        required_tables.update(product_field["required_tables"])

    _validate_role_access(role, required_tables)

    select_parts = []
    group_exprs = []
    group_aliases = []
    for field in group_fields:
        select_parts.append(f"{field['expr']} AS {field['alias']}")
        group_exprs.append(field["expr"])
        group_aliases.append(field["alias"])

    metric_aliases = []
    for measure in measure_fields:
        metric_expr = _measure_expr_with_agg(agg_function, measure["expr"])
        alias = measure["alias"] if agg_function == "NONE" else f"{agg_function.lower()}_{measure['alias']}"
        select_parts.append(f"{metric_expr} AS {alias}")
        metric_aliases.append(alias)

    join_sql = _build_join_sql(required_tables)
    sql = "SELECT\n    " + ",\n    ".join(select_parts) + "\nFROM sales s\n"
    if join_sql:
        sql += join_sql + "\n"
    if where_clauses:
        sql += "WHERE " + " AND ".join(where_clauses) + "\n"

    if agg_function != "NONE" and group_exprs:
        sql += "GROUP BY " + ", ".join(group_exprs) + "\n"

    order_metric = metric_aliases[0]
    if ranking_mode == "Top":
        sql += f"ORDER BY {order_metric} DESC\nLIMIT ?"
        params.append(int(limit_n))
    elif ranking_mode == "Bottom":
        sql += f"ORDER BY {order_metric} ASC\nLIMIT ?"
        params.append(int(limit_n))
    else:
        if group_aliases:
            sql += f"ORDER BY {group_aliases[0]} ASC"
        else:
            sql += f"ORDER BY {order_metric} DESC"

    return {
        "sql": sql,
        "params": params,
        "group_aliases": group_aliases,
        "metric_aliases": metric_aliases,
        "metric_label": (
            "Raw measures"
            if agg_function == "NONE"
            else f"{agg_function} of selected measures"
        ),
    }

@router.get("/cities")
def get_cities(user=Depends(get_current_user)):
    if "stores" not in ROLE_TABLE_ACCESS[user["role"]]:
        return {"cities": []}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT st.city AS city
        FROM stores st
        WHERE st.city IS NOT NULL AND TRIM(st.city) <> ''
        ORDER BY st.city
    """)
    rows = cursor.fetchall()
    return {"cities": [row["city"] for row in rows]}

@router.get("/countries")
def get_countries(user=Depends(get_current_user)):
    if "stores" not in ROLE_TABLE_ACCESS[user["role"]]:
        return {"countries": []}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT st.country AS country
        FROM stores st
        WHERE st.country IS NOT NULL AND TRIM(st.country) <> ''
        ORDER BY st.country
    """)
    rows = cursor.fetchall()
    return {"countries": [row["country"] for row in rows]}

@router.get("/categories")
def get_categories(user=Depends(get_current_user)):
    if "category" not in ROLE_TABLE_ACCESS[user["role"]]:
        return {"categories": []}

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT DISTINCT c.category_name AS category_name
        FROM category c
        WHERE c.category_name IS NOT NULL AND TRIM(c.category_name) <> ''
        ORDER BY c.category_name
    """)
    rows = cursor.fetchall()
    return {"categories": [row["category_name"] for row in rows]}

@router.get("/products")
def get_products(categories: str = "", user=Depends(get_current_user)):
    if "products" not in ROLE_TABLE_ACCESS[user["role"]]:
        return {"products": []}

    conn = get_connection()
    cursor = conn.cursor()

    if categories:
        category_list = [cat.strip() for cat in categories.split(",") if cat.strip()]
        if category_list:
            placeholders = ", ".join(["?"] * len(category_list))
            cursor.execute(f"""
                SELECT DISTINCT p.product_name AS product_name
                FROM products p
                JOIN category c ON p.category_id = c.category_id
                WHERE c.category_name IN ({placeholders})
                  AND p.product_name IS NOT NULL
                  AND TRIM(p.product_name) <> ''
                ORDER BY p.product_name
            """, category_list)
        else:
            cursor.execute("""
                SELECT DISTINCT p.product_name AS product_name
                FROM products p
                WHERE p.product_name IS NOT NULL AND TRIM(p.product_name) <> ''
                ORDER BY p.product_name
            """)
    else:
        cursor.execute("""
            SELECT DISTINCT p.product_name AS product_name
            FROM products p
            WHERE p.product_name IS NOT NULL AND TRIM(p.product_name) <> ''
            ORDER BY p.product_name
        """)

    rows = cursor.fetchall()
    return {"products": [row["product_name"] for row in rows]}

@router.get("/date-bounds")
def get_date_bounds(user=Depends(get_current_user)):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT MIN(sale_date) AS min_date, MAX(sale_date) AS max_date FROM sales")
    row = cursor.fetchone()
    return {
        "min": row["min_date"] or "",
        "max": row["max_date"] or ""
    }

@router.get("/fields")
def get_fields(role: str, agg_function: str = "SUM", user=Depends(get_current_user)):
    # Ensure user can only access their own role's fields
    if user["role"] != role:
        return {"group_fields": [], "measure_fields": []}

    group_fields = get_accessible_group_fields(role)
    measure_fields = get_accessible_measure_fields(role, agg_function)

    return {
        "group_fields": group_fields,
        "measure_fields": measure_fields
    }

@router.post("/analytics")
def run_analytics(data: dict, user=Depends(get_current_user)):
    # Ensure user can only run analytics for their own role
    if user["role"] != data.get("role"):
        raise ValueError("Role mismatch")

    query_data = build_analytics_query(
        role=data["role"],
        group_field_ids=data["group_field_ids"],
        agg_function=data["agg_function"],
        measure_field_ids=data["measure_field_ids"],
        start_date=data["start_date"],
        end_date=data["end_date"],
        cities=data["cities"],
        categories=data["categories"],
        products=data["products"],
        countries=data["countries"],
        ranking_mode=data["ranking_mode"],
        limit_n=data["limit_n"],
    )

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(query_data["sql"], query_data["params"])
    columns = [col[0] for col in cursor.description] if cursor.description else []
    rows = cursor.fetchall()

    # Convert rows to dict format
    data_rows = [dict(row) for row in rows]

    return {
        "data": data_rows,
        "truncated": False,  # For now, not implementing truncation
        "group_aliases": query_data["group_aliases"],
        "metric_aliases": query_data["metric_aliases"],
        "metric_label": query_data["metric_label"]
    }