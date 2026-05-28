/*
  mart_customer_activity.sql
  ──────────────────────────────────────────────────────────────────────────────
  Final mart: comprehensive customer trading activity.

  This table is the primary output consumed by:
    • Business intelligence dashboards
    • Client-facing reports
    • AI insights layer (anomaly detection, segmentation)

  Materialised as TABLE for fast query performance.
*/

with activity as (

    select * from {{ ref('int_customer_activity') }}

),

risk_count as (

    -- Enrich with number of risk events per user
    select
        user_id,
        count(*)                                        as total_risk_events,
        count(case when severity = 'high'   then 1 end) as high_risk_events,
        count(case when severity = 'medium' then 1 end) as medium_risk_events
    from {{ ref('stg_risk_events') }}
    group by user_id

),

final as (

    select
        -- Identity
        a.user_id,
        a.name,
        a.country,
        a.account_type,
        a.risk_profile,

        -- Trade summary
        a.total_trades,
        a.total_buys,
        a.total_sells,
        a.distinct_instruments,

        -- Financial metrics
        round(a.total_notional, 2)                     as total_notional,
        round(a.total_bought_value, 2)                 as total_bought_value,
        round(a.total_sold_value, 2)                   as total_sold_value,
        round(a.avg_trade_size, 2)                     as avg_trade_size,
        round(a.net_pnl_estimate, 2)                   as net_pnl_estimate,

        -- Cost
        round(a.total_fees_paid, 2)                    as total_fees_paid,
        round(a.total_deposits, 2)                     as total_deposits,

        -- Timeline
        a.first_trade_at,
        a.last_trade_at,
        a.trading_days_span,

        -- Risk overlay
        coalesce(r.total_risk_events, 0)               as total_risk_events,
        coalesce(r.high_risk_events,  0)               as high_risk_events,
        coalesce(r.medium_risk_events, 0)              as medium_risk_events,

        -- Derived segment
        case
            when a.total_notional >= 400000            then 'whale'
            when a.total_notional >= 100000            then 'high_value'
            when a.total_notional >= 30000             then 'active'
            else                                            'light'
        end                                            as customer_segment,

        current_timestamp                              as refreshed_at

    from activity a
    left join risk_count r on a.user_id = r.user_id

)

select * from final
