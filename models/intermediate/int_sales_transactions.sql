with source_versions as (

    select
        *,
        count(*) over (partition by transaction_id) as source_version_count,
        row_number() over (
            partition by transaction_id
            order by
                ingested_at desc nulls last,
                case source_system
                    when 'POS' then 3
                    when 'ERP' then 2
                    when 'Manual' then 1
                    else 0
                end desc,
                standard_unit_cost desc nulls last,
                unit_cost desc nulls last
        ) as version_rank
    from {{ ref('stg_consolidated_transactions') }}

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
    source_version_count as duplicate_source_row_count,
    quantity < 0 as is_return_or_adjustment
from source_versions
where version_rank = 1
