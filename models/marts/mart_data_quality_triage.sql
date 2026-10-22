{{ config(materialized='table') }}

with source_rows as (

    select * from {{ ref('stg_consolidated_transactions') }}

),

duplicate_ids as (

    select transaction_id
    from source_rows
    group by transaction_id
    having count(*) > 1

),

source_row_issues as (

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        'source_row' as issue_scope,
        'DUPLICATE_TRANSACTION_ID' as issue_code,
        'review' as severity,
        'Multiple source rows share this ID; the latest ingested version is selected in the fact.' as issue_details
    from source_rows
    where transaction_id in (select transaction_id from duplicate_ids)

    union all

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        'source_row',
        'UNKNOWN_PRODUCT_KEY',
        'review',
        'Product ID is missing or uses source placeholder 99901; fact is retained under the Unknown product member.'
    from source_rows
    where product_id is null or product_id = 99901

    union all

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        'source_row',
        'UNKNOWN_STORE_KEY',
        'review',
        'Store ID is missing or uses source placeholder 99901; fact is retained under the Unknown store member.'
    from source_rows
    where store_id is null or store_id = 99901

    union all

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        'source_row',
        'MISSING_STANDARD_COST',
        'review',
        'Standard cost is missing; net sales remain reported, while standard-cost gross profit is null for this row.'
    from source_rows
    where standard_unit_cost is null

    union all

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        'source_row',
        'NEGATIVE_QUANTITY_REVIEW',
        'information',
        'Signed negative quantity is retained as a return or adjustment; reason and original sale are not provided.'
    from source_rows
    where quantity < 0

),

product_conflicts as (

    select product_id
    from source_rows
    where product_id is not null
      and product_id != 99901
    group by product_id
    having count(distinct product_name_catalog) > 1
        or count(distinct product_name_on_transaction) > 1
        or count(distinct product_category) > 1

),

product_issues as (

    select
        cast(null as varchar) as source_row_fingerprint,
        cast(null as integer) as transaction_id,
        product_id,
        cast(null as integer) as store_id,
        cast(null as varchar) as source_system,
        cast(null as timestamp) as ingested_at,
        'product' as issue_scope,
        'CONFLICTING_PRODUCT_ATTRIBUTES' as issue_code,
        'review' as severity,
        'Product name or category varies across source rows; dimension selects the modal profile.' as issue_details
    from product_conflicts

),

store_conflicts as (

    select store_id
    from source_rows
    where store_id is not null
      and store_id != 99901
    group by store_id
    having count(distinct store_name) > 1
        or count(distinct state_code) > 1
        or count(distinct state) > 1
        or count(distinct region_name) > 1
        or count(distinct store_type) > 1
        or count(distinct store_sqft) > 1
        or count(distinct direct_store_operating_costs) > 1

),

store_issues as (

    select
        cast(null as varchar) as source_row_fingerprint,
        cast(null as integer) as transaction_id,
        cast(null as integer) as product_id,
        store_id,
        cast(null as varchar) as source_system,
        cast(null as timestamp) as ingested_at,
        'store' as issue_scope,
        'CONFLICTING_STORE_ATTRIBUTES' as issue_code,
        'review' as severity,
        'Store attributes vary across source rows; dimension selects the modal profile and derives region from state code.' as issue_details
    from store_conflicts

)

select * from source_row_issues
union all
select * from product_issues
union all
select * from store_issues
