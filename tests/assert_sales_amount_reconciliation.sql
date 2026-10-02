-- Regra de negócio:
-- sales_amount e quantity publicados no Mart devem reconciliar com os itens upstream
-- no mesmo grão de Pedido + Produto.
--
-- Em um teste singular do dbt, zero linhas = PASS.

with expected as (

    select
        order_id,
        product_id,
        cast(count(*) as integer) as expected_quantity,
        cast(sum(price) as decimal(18, 2)) as expected_sales_amount
    from {{ ref('stg_order_items') }}
    group by order_id, product_id

),

published as (

    select
        order_id,
        product_id,
        quantity,
        sales_amount
    from {{ ref('fct_retail_sales') }}

)

select
    coalesce(e.order_id, p.order_id) as order_id,
    coalesce(e.product_id, p.product_id) as product_id,
    e.expected_quantity,
    p.quantity as published_quantity,
    e.expected_sales_amount,
    p.sales_amount as published_sales_amount
from expected e
full outer join published p
    on e.order_id = p.order_id
   and e.product_id = p.product_id
where
    e.order_id is null
    or p.order_id is null
    or e.expected_quantity <> p.quantity
    or abs(
        cast(e.expected_sales_amount as double)
        - cast(p.sales_amount as double)
    ) > 0.01