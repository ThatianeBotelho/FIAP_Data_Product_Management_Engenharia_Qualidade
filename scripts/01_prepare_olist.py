from pathlib import Path
import duckdb


RAW_DIR = Path("data/raw")
DB_PATH = Path("data/analytics.duckdb")

FILES = {
    "orders": RAW_DIR / "olist_orders_dataset.csv",
    "order_items": RAW_DIR / "olist_order_items_dataset.csv",
    "customers": RAW_DIR / "olist_customers_dataset.csv",
}


missing = [str(path) for path in FILES.values() if not path.exists()]

if missing:
    print("[ERROR] Arquivos Olist não encontrados:")
    for path in missing:
        print(f" - {path}")
    print()
    print("Baixe o dataset Brazilian E-Commerce Public Dataset by Olist")
    print("e coloque os três CSVs em data/raw/.")
    raise SystemExit(1)


DB_PATH.parent.mkdir(parents=True, exist_ok=True)

print("=" * 72)
print("PREPARANDO FONTES OLIST NO DUCKDB")
print("=" * 72)

con = duckdb.connect(str(DB_PATH))
con.execute("create schema if not exists raw")

con.execute(f"""
create or replace table raw.orders as
select
    cast(order_id as varchar) as order_id,
    cast(customer_id as varchar) as customer_id,
    cast(order_status as varchar) as order_status,
    cast(order_purchase_timestamp as timestamp) as order_purchase_timestamp
from read_csv_auto(
    '{FILES["orders"].as_posix()}',
    header = true
)
""")

con.execute(f"""
create or replace table raw.order_items as
select
    cast(order_id as varchar) as order_id,
    cast(order_item_id as integer) as order_item_id,
    cast(product_id as varchar) as product_id,
    cast(price as decimal(18, 2)) as price,
    cast(freight_value as decimal(18, 2)) as freight_value
from read_csv_auto(
    '{FILES["order_items"].as_posix()}',
    header = true
)
""")

con.execute(f"""
create or replace table raw.customers as
select
    cast(customer_id as varchar) as customer_id,
    cast(customer_unique_id as varchar) as customer_unique_id,
    cast(customer_city as varchar) as customer_city,
    cast(customer_state as varchar) as customer_state
from read_csv_auto(
    '{FILES["customers"].as_posix()}',
    header = true
)
""")

# Backups canônicos para o experimento de Circuit Breaker.
con.execute("create or replace table raw.orders_clean as select * from raw.orders")
con.execute("create or replace table raw.order_items_clean as select * from raw.order_items")
con.execute("create or replace table raw.customers_clean as select * from raw.customers")

summary = con.execute("""
select
    (select count(*) from raw.orders) as orders,
    (select count(*) from raw.order_items) as order_items,
    (select count(*) from raw.customers) as customers
""").fetchone()

print(f"[OK] raw.orders:      {summary[0]:,} linhas")
print(f"[OK] raw.order_items: {summary[1]:,} linhas")
print(f"[OK] raw.customers:   {summary[2]:,} linhas")
print(f"[OK] Banco criado: {DB_PATH}")
print("[OK] Backups canônicos criados para restauração do experimento.")

con.close()
print("=" * 72)