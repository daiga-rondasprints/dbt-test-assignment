with annual_region as (

    select
        date.calendar_year as year,
        store.region_name,
        sum(sales.net_sales) as net_sales,
        sum(sales.quantity) as net_units_sold,
        sum(sales.pack_equivalent_quantity_if_quantity_is_eaches) as net_pack_equivalents_scenario,
        sum(sales.standard_cost_of_sales) as standard_cost_of_sales,
        sum(case when sales.gross_profit is not null then sales.gross_profit end) as gross_profit,
        sum(case when sales.gross_profit is not null then sales.net_sales end) as standard_costed_net_sales,
        sum(sales.standard_cost_of_sales_unadjusted) as standard_cost_of_sales_unadjusted,
        sum(sales.gross_profit_standard_unadjusted) as gross_profit_standard_unadjusted,
        sum(sales.landed_gross_profit) as landed_gross_profit,
        count(*) as transaction_count,
        sum(case when sales.is_return_or_adjustment then 1 else 0 end) as return_or_adjustment_count
    from {{ ref('fct_sales') }} as sales
    inner join {{ ref('dim_date') }} as date
        on sales.date_key = date.date_key
    inner join {{ ref('dim_store') }} as store
        on sales.store_key = store.store_key
    group by 1, 2

),

with_rates as (

    select
        *,
        gross_profit / nullif(standard_costed_net_sales, 0) as gross_margin_pct,
        gross_profit_standard_unadjusted / nullif(standard_costed_net_sales, 0) as gross_margin_standard_unadjusted_pct,
        net_sales - lag(net_sales) over (partition by region_name order by year) as net_sales_yoy_change,
        net_sales / nullif(lag(net_sales) over (partition by region_name order by year), 0) - 1 as net_sales_yoy_pct,
        gross_profit - lag(gross_profit) over (partition by region_name order by year) as gross_profit_yoy_change,
        gross_profit / nullif(lag(gross_profit) over (partition by region_name order by year), 0) - 1 as gross_profit_yoy_pct
    from annual_region

)

select * from with_rates
