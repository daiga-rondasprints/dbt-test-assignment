with store_attribute_counts as (

    select
        store_id as store_key,
        store_name,
        state_code,
        state,
        store_type,
        store_sqft,
        direct_store_operating_costs,
        region_name,
        count(*) as observed_rows
    from {{ ref('int_sales_transactions') }}
    where store_id is not null
      and store_id != 99901
    group by 1, 2, 3, 4, 5, 6, 7, 8

),

ranked_attributes as (

    select
        *,
        row_number() over (
            partition by store_key
            order by observed_rows desc, store_name, state_code, region_name
        ) as attribute_rank
    from store_attribute_counts

),

selected_stores as (

    select *
    from ranked_attributes
    where attribute_rank = 1

),

known_stores as (

    select
        store_key,
        store_name,
        state_code,
        state,
        store_type,
        store_sqft,
        direct_store_operating_costs,
        case
            when state_code in ('CT', 'ME', 'MA', 'NH', 'RI', 'VT', 'NJ', 'NY', 'PA') then 'Northeast'
            when state_code in ('IL', 'IN', 'MI', 'OH', 'WI', 'IA', 'KS', 'MN', 'MO', 'NE', 'ND', 'SD') then 'Midwest'
            when state_code in ('DE', 'FL', 'GA', 'MD', 'NC', 'SC', 'VA', 'WV', 'AL', 'KY', 'MS', 'TN', 'AR', 'LA', 'OK', 'TX', 'DC') then 'South'
            when state_code in ('AK', 'CA', 'CO', 'HI', 'ID', 'MT', 'NV', 'OR', 'UT', 'WA', 'WY') then 'West'
            else coalesce(region_name, 'Unknown')
        end as region_name
    from selected_stores

)

select
    store_key,
    store_name,
    state_code,
    state,
    region_name,
    store_type,
    store_sqft,
    direct_store_operating_costs,
    false as is_unknown
from known_stores

union all

select
    -1 as store_key,
    'Unknown / unassigned' as store_name,
    null as state_code,
    null as state,
    'Unknown' as region_name,
    null as store_type,
    null as store_sqft,
    null as direct_store_operating_costs,
    true as is_unknown
