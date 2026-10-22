with ranked_versions as (

    select
        *,
        count(*) over (partition by transaction_id) as duplicate_source_row_count,
        row_number() over (
            partition by transaction_id
            order by
                ingested_at desc nulls last,
                case source_system
                    when 'POS' then 3
                    when 'ERP' then 2
                    when 'Manual' then 1
                    else 0
                end desc,
                standard_unit_cost desc nulls last,
                unit_cost desc nulls last,
                source_row_fingerprint
        ) as source_version_rank
    from {{ ref('stg_consolidated_transactions') }}

)

select
    *,
    case
        when source_version_rank = 1 then 'selected_for_fact'
        else 'triage_duplicate_version'
    end as version_disposition
from ranked_versions
