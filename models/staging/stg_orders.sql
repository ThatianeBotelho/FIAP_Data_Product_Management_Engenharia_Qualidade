select
    cast(order_id as varchar) as order_id,
    cast(customer_id as varchar) as source_customer_id,
    cast(order_status as varchar) as order_status,
    cast(order_purchase_timestamp as timestamp) as order_purchase_timestamp
from {{ source('olist_raw', 'orders') }}