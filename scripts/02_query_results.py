from pathlib import Path
import duckdb


DB_PATH = Path("data/analytics.duckdb")

if not DB_PATH.exists():
    print("[ERROR] data/analytics.duckdb não encontrado.")
    print("Execute primeiro: python scripts/01_prepare_olist.py")
    raise SystemExit(1)


con = duckdb.connect(str(DB_PATH), read_only=True)

table_exists = con.execute("""
select count(*)
from information_schema.tables
where table_schema = 'main'
  and table_name = 'fct_retail_sales'
""").fetchone()[0]

if table_exists == 0:
    print("[ERROR] fct_retail_sales ainda não existe.")
    print("Execute: dbt build --profiles-dir .")
    con.close()
    raise SystemExit(1)


summary = con.execute("""
select
    count(*) as sales_lines,
    count(distinct order_id) as orders,
    count(distinct customer_id) as customers,
    sum(quantity) as units,
    round(sum(sales_amount), 2) as sales_amount
from main.fct_retail_sales
""").fetchdf()

status = con.execute("""
select
    order_status,
    count(*) as sales_lines,
    round(sum(sales_amount), 2) as sales_amount
from main.fct_retail_sales
group by order_status
order by sales_amount desc
""").fetchdf()

sample = con.execute("""
select *
from main.fct_retail_sales
order by sale_date, order_id, product_id
limit 10
""").fetchdf()

print("=" * 72)
print("RESUMO DO DATA PRODUCT")
print("=" * 72)
print(summary.to_string(index=False))

print()
print("VENDAS POR STATUS")
print(status.to_string(index=False))

print()
print("AMOSTRA")
print(sample.to_string(index=False))

con.close()