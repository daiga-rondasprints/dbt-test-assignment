with annual as (

    select
        date.calendar_year as year,
        sum(net_sales) as net_sales,
        sum(quantity) as net_units_sold,
        sum(pack_equivalent_quantity_if_quantity_is_eaches) as net_pack_equivalents_scenario,
        sum(net_sales) / nullif(sum(quantity), 0) as average_selling_price,
        sum(net_sales) / nullif(sum(pack_equivalent_quantity_if_quantity_is_eaches), 0) as average_sales_per_pack_equivalent_scenario,
        sum(standard_cost_of_sales) as standard_cost_of_sales,
        sum(case when gross_profit is not null then gross_profit end) as gross_profit,
        sum(case when gross_profit is not null then net_sales end) as standard_costed_net_sales,
        sum(standard_cost_of_sales_unadjusted) as standard_cost_of_sales_unadjusted,
        sum(gross_profit_standard_unadjusted) as gross_profit_standard_unadjusted,
        sum(landed_gross_profit) as landed_gross_profit,
        sum(net_sales) as landed_costed_net_sales,
        count(*) as transaction_count,
        sum(case when is_return_or_adjustment then 1 else 0 end) as return_or_adjustment_count,
        sum(case when product_key = -1 then net_sales else 0 end) as unknown_product_net_sales,
        sum(case when store_key = -1 then net_sales else 0 end) as unknown_store_net_sales,
        sum(case when gross_profit is not null then 1 else 0 end)::double / count(*) as standard_cost_coverage_pct
    from {{ ref('fct_sales') }} as sales
    inner join {{ ref('dim_date') }} as date
        on sales.date_key = date.date_key
    group by 1

),

with_rates as (

    select
        *,
        gross_profit / nullif(standard_costed_net_sales, 0) as gross_margin_pct,
        gross_profit_standard_unadjusted / nullif(standard_costed_net_sales, 0) as gross_margin_standard_unadjusted_pct,
        landed_gross_profit / nullif(landed_costed_net_sales, 0) as landed_gross_margin_pct,
        net_sales - lag(net_sales) over (order by year) as net_sales_yoy_change,
        net_sales / nullif(lag(net_sales) over (order by year), 0) - 1 as net_sales_yoy_pct,
        gross_profit - lag(gross_profit) over (order by year) as gross_profit_yoy_change,
        gross_profit / nullif(lag(gross_profit) over (order by year), 0) - 1 as gross_profit_yoy_pct
    from annual

)

select * from with_rates
