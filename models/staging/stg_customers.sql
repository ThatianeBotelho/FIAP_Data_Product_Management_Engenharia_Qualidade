select
    cast(customer_id as varchar) as source_customer_id,
    cast(customer_unique_id as varchar) as customer_id,
    cast(customer_city as varchar) as customer_city,
    cast(customer_state as varchar) as customer_state
from {{ source('olist_raw', 'customers') }}