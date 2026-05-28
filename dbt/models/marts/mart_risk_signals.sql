/*
  mart_risk_signals.sql
  ──────────────────────────────────────────────────────────────────────────────
  Final mart: aggregated risk signals per user.

  Consumed by:
    • Compliance dashboard
    • Automated risk alerts
    • AI insights layer (risk explanation, escalation recommendations)

  Materialised as TABLE for fast query performance.
*/

with risk_events as (

    select * from {{ ref('stg_risk_events') }}

),

users as (

    select * from {{ ref('stg_users') }}

),

trades_summary as (

    -- Provide context: user's total trading notional
    select
        user_id,
        round(sum(notional_value), 2)                  as total_notional,
        count(*)                                       as total_trades
    from {{ ref('stg_trades') }}
    where status = 'filled'
    group by user_id

),

risk_agg as (

    select
        re.user_id,
        u.name,
        u.country,
        u.account_type,
        u.risk_profile,

        -- Event counts by severity
        count(*)                                       as total_risk_events,
        count(case when re.severity = 'high'   then 1 end) as high_severity_events,
        count(case when re.severity = 'medium' then 1 end) as medium_severity_events,
        count(case when re.severity = 'low'    then 1 end) as low_severity_events,

        -- Event type breakdown
        count(distinct re.event_type)                  as distinct_event_types,
        count(case when re.event_type = 'compliance_flag'     then 1 end) as compliance_flags,
        count(case when re.event_type = 'large_position'      then 1 end) as large_position_flags,
        count(case when re.event_type = 'rapid_trading'       then 1 end) as rapid_trading_flags,
        count(case when re.event_type = 'concentration_risk'  then 1 end) as concentration_risk_flags,

        -- Timeline
        min(re.event_occurred_at)                      as first_risk_event_at,
        max(re.event_occurred_at)                      as last_risk_event_at

    from risk_events re
    inner join users u on re.user_id = u.user_id
    group by 1, 2, 3, 4, 5

),

final as (

    select
        ra.*,
        coalesce(ts.total_notional, 0)                 as user_total_notional,
        coalesce(ts.total_trades, 0)                   as user_total_trades,

        -- Computed risk tier (deterministic scoring)
        case
            when ra.high_severity_events >= 3
              or ra.compliance_flags >= 2              then 'critical'
            when ra.high_severity_events >= 1          then 'elevated'
            when ra.medium_severity_events >= 3        then 'moderate'
            else                                            'low'
        end                                            as risk_tier,

        -- Risk score 0-100
        least(100,
            ra.high_severity_events   * 25 +
            ra.medium_severity_events * 10 +
            ra.low_severity_events    *  3 +
            ra.compliance_flags       * 20
        )                                              as risk_score,

        current_timestamp                              as refreshed_at

    from risk_agg ra
    left join trades_summary ts on ra.user_id = ts.user_id

)

select * from final
