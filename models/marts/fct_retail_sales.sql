with sales_base as (

    select
        cast(o.order_purchase_timestamp as date) as sale_date,
        oi.order_id,
        c.customer_id,
        oi.product_id,
        oi.price,
        o.order_status
    from {{ ref('stg_order_items') }} oi
    inner join {{ ref('stg_orders') }} o
        on oi.order_id = o.order_id
    inner join {{ ref('stg_customers') }} c
        on o.source_customer_id = c.source_customer_id

),

aggregated as (

    select
        sale_date,
        order_id,
        customer_id,
        product_id,
        cast(count(*) as integer) as quantity,
        cast(sum(price) as decimal(18, 2)) as sales_amount,
        order_status
    from sales_base
    group by
        sale_date,
        order_id,
        customer_id,
        product_id,
        order_status

)

select
    cast(order_id || '-' || product_id as varchar) as sales_line_id,
    sale_date,
    cast(order_id as varchar) as order_id,
    cast(customer_id as varchar) as customer_id,
    cast(product_id as varchar) as product_id,
    quantity,
    sales_amount,
    cast(order_status as varchar) as order_status
from aggregated