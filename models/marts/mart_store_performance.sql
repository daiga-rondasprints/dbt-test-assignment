with annual_store as (

    select
        extract(year from sales.transaction_date)::integer as year,
        store.store_key,
        store.store_name,
        store.region_name,
        store.state_code,
        store.direct_store_operating_costs,
        sum(sales.net_sales) as net_sales,
        sum(sales.quantity) as net_units_sold,
        sum(case when sales.gross_profit is not null then sales.gross_profit end) as gross_profit,
        sum(case when sales.gross_profit is not null then sales.net_sales end) as standard_costed_net_sales,
        sum(sales.landed_gross_profit) as landed_gross_profit,
        count(*) as transaction_count,
        sum(case when sales.is_return_or_adjustment then 1 else 0 end) as return_or_adjustment_count
    from {{ ref('fct_sales') }} as sales
    inner join {{ ref('dim_store') }} as store
        on sales.store_key = store.store_key
    group by 1, 2, 3, 4, 5, 6

),

with_scenarios as (

    select
        *,
        gross_profit / nullif(standard_costed_net_sales, 0) as gross_margin_pct,
        case
            when direct_store_operating_costs is not null
                then gross_profit - direct_store_operating_costs
            else null
        end as gross_profit_less_direct_cost_annual_scenario,
        case
            when direct_store_operating_costs is not null
                then gross_profit - (direct_store_operating_costs * 12)
            else null
        end as gross_profit_less_direct_cost_monthly_scenario,
        net_sales - lag(net_sales) over (partition by store_key order by year) as net_sales_yoy_change,
        net_sales / nullif(lag(net_sales) over (partition by store_key order by year), 0) - 1 as net_sales_yoy_pct,
        gross_profit - lag(gross_profit) over (partition by store_key order by year) as gross_profit_yoy_change,
        gross_profit / nullif(lag(gross_profit) over (partition by store_key order by year), 0) - 1 as gross_profit_yoy_pct
    from annual_store

)

select * from with_scenarios
