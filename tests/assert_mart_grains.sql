select 'mart_product_performance' as model_name, year, product_key::varchar as entity_key
from {{ ref('mart_product_performance') }}
group by year, product_key
having count(*) > 1

union all

select 'mart_region_performance' as model_name, year, region_name as entity_key
from {{ ref('mart_region_performance') }}
group by year, region_name
having count(*) > 1

union all

select 'mart_store_performance' as model_name, year, store_key::varchar as entity_key
from {{ ref('mart_store_performance') }}
group by year, store_key
having count(*) > 1
