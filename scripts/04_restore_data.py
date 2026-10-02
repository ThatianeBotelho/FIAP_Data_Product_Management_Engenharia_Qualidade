from pathlib import Path
import duckdb


DB_PATH = Path("data/analytics.duckdb")

if not DB_PATH.exists():
    print("[ERROR] data/analytics.duckdb não encontrado.")
    raise SystemExit(1)


con = duckdb.connect(str(DB_PATH))

required_backups = ["orders_clean", "order_items_clean", "customers_clean"]
for table in required_backups:
    exists = con.execute(
        """
        select count(*)
        from information_schema.tables
        where table_schema = 'raw' and table_name = ?
        """,
        [table],
    ).fetchone()[0]

    if exists == 0:
        print(f"[ERROR] Backup raw.{table} não encontrado.")
        print("Execute novamente: python scripts/01_prepare_olist.py")
        con.close()
        raise SystemExit(1)


con.execute("delete from raw.orders")
con.execute("insert into raw.orders select * from raw.orders_clean")

con.execute("delete from raw.order_items")
con.execute("insert into raw.order_items select * from raw.order_items_clean")

con.execute("delete from raw.customers")
con.execute("insert into raw.customers select * from raw.customers_clean")

invalid_status = con.execute("""
select count(*)
from raw.orders
where order_status = 'CORRUPTED_STATUS'
""").fetchone()[0]

negative_price = con.execute("""
select count(*)
from raw.order_items
where price < 0
""").fetchone()[0]

print("=" * 72)
print("RESTAURAÇÃO CONCLUÍDA")
print("=" * 72)
print(f"Status corrompidos restantes: {invalid_status}")
print(f"Preços negativos restantes:   {negative_price}")
print()
print("Execute novamente:")
print("dbt build --profiles-dir .")

con.close()