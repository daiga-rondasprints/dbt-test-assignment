select
    'event fact does not equal the number of selected source versions' as failure_reason
where
    (select count(*) from {{ ref('fct_sales') }})
    !=
    (select count(*)
     from {{ ref('int_transaction_versions') }}
     where version_disposition = 'selected_for_fact')

union all

select
    'source version audit does not partition source rows into selected/excluded rows' as failure_reason
where
    (select count(*) from {{ ref('int_transaction_versions') }})
    !=
    (select count(*) from {{ ref('fct_sales') }})
    +
    (select count(*)
     from {{ ref('int_transaction_versions') }}
     where version_disposition = 'triage_duplicate_version')
