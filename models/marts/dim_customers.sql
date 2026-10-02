select
    customer_id,
    min(customer_city) as customer_city,
    min(customer_state) as customer_state
from {{ ref('stg_customers') }}
group by customer_id