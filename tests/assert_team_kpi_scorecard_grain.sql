select year, team_view, metric_code
from {{ ref('mart_team_kpi_scorecard') }}
group by year, team_view, metric_code
having count(*) > 1
