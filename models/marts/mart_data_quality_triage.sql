{{ config(materialized='table') }}

with source_rows as (

    select * from {{ ref('int_transaction_versions') }}

),

source_row_issues as (

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        source_version_rank,
        version_disposition,
        'source_row' as issue_scope,
        'DUPLICATE_TRANSACTION_ID' as issue_code,
        'review' as severity,
        'Older source version of a colliding transaction ID, moved to triage; the latest ingested_at version is in the fact.' as issue_details
    from source_rows
    where version_disposition = 'triage_duplicate_version'

    union all

    select
        source_row_fingerprint,
        transaction_id,
        product_id,
        store_id,
        source_system,
        ingested_at,
        cast(null as bigint),
        cast(null as varchar),
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
        cast(null as bigint),
        cast(null as varchar),
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
        cast(null as bigint),
        cast(null as varchar),
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
        cast(null as bigint),
        cast(null as varchar),
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
        or count(distinct pack_size) > 1

),

product_issues as (

    select
        cast(null as varchar) as source_row_fingerprint,
        cast(null as integer) as transaction_id,
        product_id,
        cast(null as integer) as store_id,
        cast(null as varchar) as source_system,
        cast(null as timestamp) as ingested_at,
        cast(null as bigint) as source_version_rank,
        cast(null as varchar) as version_disposition,
        'product' as issue_scope,
        'CONFLICTING_PRODUCT_ATTRIBUTES' as issue_code,
        'review' as severity,
        'Product name, category, or pack size varies across source rows; dimension selects the modal profile.' as issue_details
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
        cast(null as bigint) as source_version_rank,
        cast(null as varchar) as version_disposition,
        'store' as issue_scope,
        'CONFLICTING_STORE_ATTRIBUTES' as issue_code,
        'review' as severity,
        'Store attributes vary across source rows; dimension selects the modal profile and derives region from state code.' as issue_details
    from store_conflicts

    union all

    select
        cast(null as varchar) as source_row_fingerprint,
        cast(null as integer) as transaction_id,
        cast(null as integer) as product_id,
        store_id,
        cast(null as varchar) as source_system,
        cast(null as timestamp) as ingested_at,
        cast(null as bigint) as source_version_rank,
        cast(null as varchar) as version_disposition,
        'store' as issue_scope,
        'INVALID_STORE_SQUARE_FOOTAGE' as issue_code,
        'review' as severity,
        'Store square footage is missing or non-positive; area productivity is not calculated for this store.' as issue_details
    from source_rows
    where store_id is not null
      and store_id != 99901
      and (store_sqft is null or store_sqft <= 0)
    group by store_id

)

select * from source_row_issues
union all
select * from product_issues
union all
select * from store_issues
