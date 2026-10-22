select
    'staging row count differs from the current source extract' as failure_reason
where
    (select count(*) from {{ ref('stg_consolidated_transactions') }})
    !=
    (select count(*) from {{ source('raw', 'consolidated_transactions') }})
