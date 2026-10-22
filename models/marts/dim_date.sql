with date_spine as (

    select
        unnest(
            generate_series(
                date_trunc('year', min(transaction_date))::date,
                (date_trunc('year', max(transaction_date)) + interval '1 year' - interval '1 day')::date,
                interval '1 day'
            )
        )::date as date_day
    from {{ ref('stg_consolidated_transactions') }}

)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_key,
    date_day,
    extract(year from date_day)::integer as calendar_year,
    extract(quarter from date_day)::integer as calendar_quarter,
    extract(month from date_day)::integer as month_number,
    strftime(date_day, '%B') as month_name,
    strftime(date_day, '%Y-%m') as year_month,
    extract(day from date_day)::integer as day_of_month,
    extract(dow from date_day)::integer as day_of_week,
    strftime(date_day, '%A') as day_name,
    extract(doy from date_day)::integer as day_of_year,
    date_trunc('month', date_day)::date as month_start,
    date_trunc('quarter', date_day)::date as quarter_start,
    date_trunc('year', date_day)::date as year_start,
    extract(month from date_day) in (1, 2, 3) as is_q1,
    extract(month from date_day) in (4, 5, 6) as is_q2,
    extract(month from date_day) in (7, 8, 9) as is_q3,
    extract(month from date_day) in (10, 11, 12) as is_q4
from date_spine
