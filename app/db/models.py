from app.db.database import get_connection

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    # ================= USERS (RBAC) =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE,
        password TEXT,
        department TEXT
    )
    """)

    # ================= CATEGORY =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS category (
        category_id TEXT PRIMARY KEY,   -- ✅ FIXED
        category_name TEXT
    )
    """)

    # ================= PRODUCTS =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS products (
        product_id TEXT PRIMARY KEY,    -- ✅ FIXED
        product_name TEXT,
        category_id TEXT,               -- ✅ FIXED
        launch_date TEXT,
        price REAL,
        FOREIGN KEY (category_id) REFERENCES category(category_id)
    )
    """)

    # ================= STORES =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS stores (
        store_id TEXT PRIMARY KEY,      -- ✅ FIXED
        store_name TEXT,
        city TEXT,
        country TEXT
    )
    """)

    # ================= SALES =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS sales (
        sale_id TEXT PRIMARY KEY,       -- ✅ FIXED
        sale_date TEXT,
        store_id TEXT,                  -- ✅ FIXED
        product_id TEXT,                -- ✅ FIXED
        quantity INTEGER,
        FOREIGN KEY (store_id) REFERENCES stores(store_id),
        FOREIGN KEY (product_id) REFERENCES products(product_id)
    )
    """)

    # ================= WARRANTY =================
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS warranty (
        claim_id TEXT PRIMARY KEY,      -- ✅ FIXED
        claim_date TEXT,
        sale_id TEXT,                  -- ✅ FIXED
        repair_status TEXT,
        FOREIGN KEY (sale_id) REFERENCES sales(sale_id)
    )
    """)

    # ================= QUERY ANSWER CACHE =================
    cursor.execute("""
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
    """)

    cursor.execute("""
    CREATE INDEX IF NOT EXISTS idx_query_answer_cache_top
    ON query_answer_cache (access_scope, hit_count DESC, last_used_at DESC)
    """)

    conn.commit()
    conn.close()
