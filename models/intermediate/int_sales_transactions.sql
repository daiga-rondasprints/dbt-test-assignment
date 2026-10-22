with source_versions as (

    select * from {{ ref('int_transaction_versions') }}

)

select
    transaction_id,
    source_row_fingerprint,
    transaction_date,
    quantity,
    unit_price,
    unit_cost,
    standard_unit_cost,
    landed_unit_cost,
    pack_size,
    product_id,
    case
        when product_id is null or product_id = 99901 then -1
        else product_id
    end as product_key,
    product_name_on_transaction,
    product_name_catalog,
    product_category,
    store_id,
    case
        when store_id is null or store_id = 99901 then -1
        else store_id
    end as store_key,
    store_name,
    state_code,
    state,
    region_name,
    store_type,
    store_sqft,
    direct_store_operating_costs,
    source_system,
    ingested_at,
    duplicate_source_row_count,
    quantity < 0 as is_return_or_adjustment
from source_versions
where source_version_rank = 1
