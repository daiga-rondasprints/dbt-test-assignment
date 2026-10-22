with product_attribute_counts as (

    select
        product_id as product_key,
        coalesce(nullif(trim(product_name_catalog), ''), nullif(trim(product_name_on_transaction), '')) as product_name,
        product_category,
        pack_size,
        count(*) as observed_rows
    from {{ ref('int_sales_transactions') }}
    where product_id is not null
      and product_id != 99901
    group by 1, 2, 3, 4

),

ranked_attributes as (

    select
        *,
        row_number() over (
            partition by product_key
            order by observed_rows desc, product_name, product_category
        ) as attribute_rank
    from product_attribute_counts

),

known_products as (

    select
        product_key,
        product_name,
        product_category,
        pack_size
    from ranked_attributes
    where attribute_rank = 1

)

select
    product_key,
    product_name,
    product_category,
    pack_size,
    false as is_unknown
from known_products

union all

select
    -1 as product_key,
    'Unknown / unassigned' as product_name,
    'Unknown' as product_category,
    null::integer as pack_size,
    true as is_unknown
