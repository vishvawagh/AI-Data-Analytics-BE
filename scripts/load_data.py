import csv
from app.db.database import get_connection
import os

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../"))
DATA_DIR = os.path.join(BASE_DIR, "data")


# ================= CATEGORY =================
def load_category():
    conn = get_connection()
    cursor = conn.cursor()

    with open(os.path.join(DATA_DIR, "categories.csv"), newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO category (category_id, category_name)
                VALUES (?, ?)
            """, (
                row["category_id"],
                row["category_name"]
            ))

    conn.commit()
    conn.close()


# ================= PRODUCTS =================
def load_products():
    conn = get_connection()
    cursor = conn.cursor()

    with open(os.path.join(DATA_DIR, "products.csv"), newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO products (product_id, product_name, category_id, launch_date, price)
                VALUES (?, ?, ?, ?, ?)
            """, (
                (row["product_id"],       # ✅ FIXED
                row["product_name"],
                row["category_id"],
                row["launch_date"],
                row["price"])
            ))

    conn.commit()
    conn.close()


# ================= STORES =================
def load_stores():
    conn = get_connection()
    cursor = conn.cursor()

    with open(os.path.join(DATA_DIR, "stores.csv"), newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO stores (store_id, store_name, city, country)
                VALUES (?, ?, ?, ?)
            """, (
                row["store_id"],        # ✅ FIXED
                row["store_name"],
                row["city"],
                row["country"]
            ))

    conn.commit()
    conn.close()


# ================= SALES =================
def load_sales():
    conn = get_connection()
    cursor = conn.cursor()

    with open(os.path.join(DATA_DIR, "sales.csv"), newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO sales (sale_id, sale_date, store_id, product_id, quantity)
                VALUES (?, ?, ?, ?, ?)
            """, (
                row["sale_id"],        # ✅ FIXED
                row["sale_date"],
                row["store_id"],
                row["product_id"],     # ✅ MUST MATCH products
                row["quantity"]
            ))

    conn.commit()
    conn.close()


# ================= WARRANTY =================
def load_warranty():
    conn = get_connection()
    cursor = conn.cursor()

    with open(os.path.join(DATA_DIR, "warranty.csv"), newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            cursor.execute("""
                INSERT INTO warranty (claim_id, claim_date, sale_id, repair_status)
                VALUES (?, ?, ?, ?)
            """, (
                row["claim_id"],       # ✅ FIXED
                row["claim_date"],
                row["sale_id"],
                row["repair_status"]
            ))

    conn.commit()
    conn.close()


# ================= RUN ALL =================
if __name__ == "__main__":
    load_category()
    load_products()
    load_stores()
    load_sales()
    load_warranty()

    print("All data loaded successfully")