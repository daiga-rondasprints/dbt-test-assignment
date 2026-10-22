-- Every colliding transaction ID contributes exactly one row to duplicate triage (the older version),
-- and that row is never the version selected into the fact.
with triage as (
    select transaction_id, version_disposition
    from {{ ref('mart_data_quality_triage') }}
    where issue_code = 'DUPLICATE_TRANSACTION_ID'
)
select 'selected_version_in_triage' as failure, count(*) as n
from triage where version_disposition <> 'triage_duplicate_version'
having count(*) > 0
union all
select 'triage_rows_vs_excluded_versions', count(*)
from triage
having count(*) <> (select count(*) from {{ ref('int_transaction_versions') }} where version_disposition = 'triage_duplicate_version')
