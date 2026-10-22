with monthly as (

    select
        date_trunc('month', transaction_date)::date as month_start,
        sum(net_sales) as net_sales,
        sum(quantity) as net_units_sold,
        sum(net_sales) / nullif(sum(quantity), 0) as average_selling_price,
        sum(case when gross_profit is not null then gross_profit end) as gross_profit,
        sum(case when gross_profit is not null then net_sales end) as standard_costed_net_sales,
        sum(landed_gross_profit) as landed_gross_profit,
        sum(net_sales) as landed_costed_net_sales,
        count(*) as transaction_count,
        sum(case when is_return_or_adjustment then 1 else 0 end) as return_or_adjustment_count
    from {{ ref('fct_sales') }}
    group by 1

),

with_rates as (

    select
        *,
        gross_profit / nullif(standard_costed_net_sales, 0) as gross_margin_pct,
        landed_gross_profit / nullif(landed_costed_net_sales, 0) as landed_gross_margin_pct,
        net_sales - lag(net_sales, 12) over (order by month_start) as net_sales_yoy_change,
        net_sales / nullif(lag(net_sales, 12) over (order by month_start), 0) - 1 as net_sales_yoy_pct
    from monthly

)

select * from with_rates
