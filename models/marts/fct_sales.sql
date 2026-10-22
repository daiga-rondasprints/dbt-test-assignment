with transactions as (

    select * from {{ ref('int_sales_transactions') }}

),

extended as (

    select
        transaction_id,
        transaction_date,
        cast(strftime(transaction_date, '%Y%m%d') as integer) as date_key,
        product_key,
        store_key,
        quantity,
        unit_price,
        pack_size,
        quantity / nullif(pack_size, 0) as pack_equivalent_quantity_if_quantity_is_eaches,
        unit_cost,
        standard_unit_cost,
        landed_unit_cost,
        case
            when standard_unit_cost is not null and pack_size > 0
                then standard_unit_cost / pack_size
            else null
        end as standard_cost_per_selling_unit,
        source_system,
        ingested_at,
        duplicate_source_row_count,
        is_return_or_adjustment,
        quantity * unit_price as net_sales,
        case
            when standard_unit_cost is not null and pack_size > 0
                then quantity * standard_unit_cost / pack_size
            else null
        end as standard_cost_of_sales,
        case
            when standard_unit_cost is not null and pack_size > 0
                then quantity * (unit_price - standard_unit_cost / pack_size)
            else null
        end as gross_profit,
        case
            when standard_unit_cost is not null
                then quantity * standard_unit_cost
            else null
        end as standard_cost_of_sales_unadjusted,
        case
            when standard_unit_cost is not null
                then quantity * (unit_price - standard_unit_cost)
            else null
        end as gross_profit_standard_unadjusted,
        quantity * landed_unit_cost as landed_cost_of_sales,
        quantity * (unit_price - landed_unit_cost) as landed_gross_profit,
        unit_price as selling_price_per_unit
    from transactions

)

select * from extended
