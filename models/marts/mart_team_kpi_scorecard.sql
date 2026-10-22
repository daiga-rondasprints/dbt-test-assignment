with team_views as (

    select unnest(['CEO', 'Finance', 'Merchandising', 'Store Operations', 'Sales Ops']) as team_view

),

annual_metrics as (

    select * from {{ ref('mart_annual_sales') }}

),

store_cost_scenarios as (

    select
        year,
        sum(gross_profit_less_direct_cost_annual_scenario) as annual_scenario,
        sum(gross_profit_less_direct_cost_monthly_scenario) as monthly_scenario
    from {{ ref('mart_store_performance') }}
    where store_key != -1
    group by year

),

global_scorecard as (

    select
        annual.year,
        team.team_view,
        metric.metric_code,
        metric.metric_value,
        metric.metric_unit,
        metric.metric_basis,
        metric.formula
    from annual_metrics as annual
    cross join team_views as team
    cross join lateral (
        values
            ('net_sales', annual.net_sales, 'USD', 'global',
                'sum(signed quantity * unit_price)'),
            ('gross_profit_standard', annual.gross_profit, 'USD', 'global',
                'net sales - standard cost of sales on cost-covered rows; standard cost adjusted by pack_size'),
            ('gross_margin_standard', annual.gross_margin_pct, 'ratio', 'global',
                'standard gross profit / standard-cost-covered net sales'),
            ('net_sales_yoy_change', annual.net_sales_yoy_change, 'USD', 'global',
                'this calendar year net sales - prior calendar year net sales'),
            ('net_sales_yoy_pct', annual.net_sales_yoy_pct, 'ratio', 'global',
                'net sales YoY change / prior calendar year net sales')
    ) as metric(metric_code, metric_value, metric_unit, metric_basis, formula)

),

finance_scorecard as (

    select
        annual.year,
        'Finance' as team_view,
        metric.metric_code,
        metric.metric_value,
        metric.metric_unit,
        metric.metric_basis,
        metric.formula
    from annual_metrics as annual
    left join store_cost_scenarios as store_costs
        on annual.year = store_costs.year
    cross join lateral (
        values
            ('gross_profit_landed_sensitivity', annual.landed_gross_profit, 'USD', 'landed_cost_sensitivity',
                'sum(quantity * (unit_price - landed_unit_cost)); alternate cost basis pending Finance/AP reconciliation'),
            ('gross_margin_landed_sensitivity', annual.landed_gross_margin_pct, 'ratio', 'landed_cost_sensitivity',
                'landed gross profit / net sales'),
            ('gross_profit_standard_unadjusted_sensitivity', annual.gross_profit_standard_unadjusted, 'USD', 'pack_size_sensitivity',
                'sum(quantity * (unit_price - standard_unit_cost)); interprets standard cost at source quantity grain without dividing by pack_size'),
            ('gross_margin_standard_unadjusted_sensitivity', annual.gross_margin_standard_unadjusted_pct, 'ratio', 'pack_size_sensitivity',
                'unadjusted standard gross profit / standard-cost-covered net sales'),
            ('standard_cost_coverage', annual.standard_cost_coverage_pct, 'ratio', 'quality',
                'standard-costed event rows / all event rows'),
            ('gross_profit_less_store_cost_annual_scenario',
                store_costs.annual_scenario, 'USD', 'opex_period_sensitivity',
                'sum(store gross profit - source direct cost interpreted as annual)'),
            ('gross_profit_less_store_cost_monthly_scenario',
                store_costs.monthly_scenario, 'USD', 'opex_period_sensitivity',
                'sum(store gross profit - 12 * source direct cost interpreted as monthly)')
    ) as metric(metric_code, metric_value, metric_unit, metric_basis, formula)

),

merchandising_scorecard as (

    select
        product.year,
        'Merchandising' as team_view,
        metric.metric_code,
        metric.metric_value,
        metric.metric_unit,
        metric.metric_basis,
        metric.formula
    from (
        select
            year,
            sum(net_units_sold) as net_selling_units,
            sum(net_pack_equivalents_scenario) as pack_equivalents,
            sum(net_sales) as net_sales,
            sum(gross_profit) as gross_profit,
            sum(standard_costed_net_sales) as costed_net_sales,
            sum(net_sales_yoy_change) as product_sales_yoy_change
        from {{ ref('mart_product_performance') }}
        group by year
    ) as product
    cross join lateral (
        values
            ('net_selling_units', product.net_selling_units, 'selling_units', 'global',
                'sum signed transaction quantity'),
            ('pack_equivalents_if_quantity_is_eaches', product.pack_equivalents, 'pack_equivalents', 'pack_size_sensitivity',
                'sum(signed quantity / pack_size); only if source quantity counts eaches'),
            ('sales_per_pack_equivalent_if_quantity_is_eaches',
                product.net_sales / nullif(product.pack_equivalents, 0), 'USD_per_pack_equivalent', 'pack_size_sensitivity',
                'global net sales / pack equivalents only if source quantity counts eaches')
    ) as metric(metric_code, metric_value, metric_unit, metric_basis, formula)

),

store_operations_scorecard as (

    select
        area.year,
        'Store Operations' as team_view,
        metric.metric_code,
        metric.metric_value,
        metric.metric_unit,
        metric.metric_basis,
        metric.formula
    from (
        select
            year,
            sum(case when store_sqft > 0 then net_sales else 0 end) as area_covered_net_sales,
            sum(case when store_sqft > 0 then gross_profit else 0 end) as area_covered_gross_profit,
            sum(case when store_sqft > 0 then standard_cost_of_sales else 0 end) as area_covered_cost_of_sales,
            sum(case when store_sqft > 0 then store_sqft else 0 end) as area_covered_sqft,
            count(distinct store_key) filter (where store_sqft > 0) as area_covered_stores
        from {{ ref('mart_store_performance') }}
        where store_key != -1
        group by year
    ) as area
    cross join (
        select count(*) as known_stores
        from {{ ref('dim_store') }}
        where not is_unknown
    ) as store_dimension
    cross join lateral (
        values
            ('net_sales_per_sqft', area.area_covered_net_sales / nullif(area.area_covered_sqft, 0), 'USD_per_sqft', 'global',
                'net sales from stores with valid area / sum modal store square footage'),
            ('gross_profit_per_sqft', area.area_covered_gross_profit / nullif(area.area_covered_sqft, 0), 'USD_per_sqft', 'global',
                'standard gross profit from stores with valid area / sum modal store square footage'),
            ('standard_cost_per_sqft', area.area_covered_cost_of_sales / nullif(area.area_covered_sqft, 0), 'USD_per_sqft', 'global',
                'standard cost of sales from stores with valid area / sum modal store square footage'),
            ('store_area_coverage', area.area_covered_stores::double / nullif(store_dimension.known_stores, 0), 'ratio', 'quality',
                'stores with sales and positive square footage / all known stores')
    ) as metric(metric_code, metric_value, metric_unit, metric_basis, formula)

),

sales_ops_scorecard as (

    select
        annual.year,
        'Sales Ops' as team_view,
        metric.metric_code,
        metric.metric_value,
        metric.metric_unit,
        metric.metric_basis,
        metric.formula
    from annual_metrics as annual
    cross join lateral (
        values
            ('average_net_sales_per_event', annual.net_sales / nullif(annual.transaction_count, 0), 'USD_per_event', 'global',
                'net sales / selected event count'),
            ('return_adjustment_line_rate', annual.return_or_adjustment_count::double / nullif(annual.transaction_count, 0), 'ratio', 'global',
                'negative-quantity event lines / selected event count')
    ) as metric(metric_code, metric_value, metric_unit, metric_basis, formula)

)

select * from global_scorecard
union all
select * from finance_scorecard
union all
select * from merchandising_scorecard
union all
select * from store_operations_scorecard
union all
select * from sales_ops_scorecard
