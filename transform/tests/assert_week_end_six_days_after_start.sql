-- Each week ends exactly 6 days after it starts. Returns weeks that don't.
select *
from {{ ref('dim_fiscal_week') }}
where date_diff('day', week_start_date, week_end_date) <> 6