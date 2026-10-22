select 'product' as dimension_name
where not exists (
    select 1
    from {{ ref('dim_product') }}
    where product_key = -1 and is_unknown
)

union all

select 'store' as dimension_name
where not exists (
    select 1
    from {{ ref('dim_store') }}
    where store_key = -1 and is_unknown
)
