def get_schema_context():
    return """
Tables:
- products(product_id, product_name, category_id, launch_date, price)
- sales(sale_id, sale_date, store_id, product_id, quantity)
- stores(store_id, store_name, city, country)
- category(category_id, category_name)
- warranty(claim_id, claim_date, sale_id, repair_status)
"""