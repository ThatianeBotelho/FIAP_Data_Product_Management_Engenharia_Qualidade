from pathlib import Path
import duckdb


DB_PATH = Path("data/analytics.duckdb")

if not DB_PATH.exists():
    print("[ERROR] data/analytics.duckdb não encontrado.")
    print("Execute primeiro: python scripts/01_prepare_olist.py")
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


# Torna a simulação idempotente: sempre parte do estado canônico.
con.execute("delete from raw.orders")
con.execute("insert into raw.orders select * from raw.orders_clean")
con.execute("delete from raw.order_items")
con.execute("insert into raw.order_items select * from raw.order_items_clean")
con.execute("delete from raw.customers")
con.execute("insert into raw.customers select * from raw.customers_clean")

target_order = con.execute("""
select order_id
from raw.orders
where order_status = 'delivered'
order by order_id
limit 1
""").fetchone()

target_item = con.execute("""
select order_id, order_item_id, product_id
from raw.order_items
order by order_id, order_item_id
limit 1
""").fetchone()

if target_order is None or target_item is None:
    print("[ERROR] Não foi possível selecionar registros para a simulação.")
    con.close()
    raise SystemExit(1)


con.execute(
    "update raw.orders set order_status = 'CORRUPTED_STATUS' where order_id = ?",
    [target_order[0]],
)

con.execute(
    """
    update raw.order_items
    set price = -999.50
    where order_id = ?
      and order_item_id = ?
    """,
    [target_item[0], target_item[1]],
)

print("=" * 72)
print("DADOS CORROMPIDOS INJETADOS PARA O EXPERIMENTO")
print("=" * 72)
print(f"[CORRUPÇÃO 1] order_id={target_order[0]}")
print("               order_status='CORRUPTED_STATUS'")
print()
print(
    f"[CORRUPÇÃO 2] order_id={target_item[0]} | "
    f"order_item_id={target_item[1]} | product_id={target_item[2]}"
)
print("               price=-999.50")
print()
print("Agora execute:")
print("dbt build --profiles-dir .")
print()
print("Resultado esperado:")
print("- testes da camada Staging falham;")
print("- o Mart downstream não é reconstruído;")
print("- a esteira é bloqueada antes de publicar a nova versão.")

con.close()