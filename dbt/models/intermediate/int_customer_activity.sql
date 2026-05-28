/*
  int_customer_activity.sql
  ──────────────────────────────────────────────────────────────────────────────
  Intermediate model: per-user trading activity summary.

  Joins filled trades with users and transaction fees to produce a
  rich activity profile used by mart_customer_activity.
*/

with trades as (

    select * from {{ ref('stg_trades') }}
    where status = 'filled'

),

users as (

    select * from {{ ref('stg_users') }}

),

transactions as (

    select
        user_id,
        sum(fee)                                        as total_fees_paid,
        sum(case when transaction_type = 'deposit'
                 then amount else 0 end)               as total_deposits,
        count(case when transaction_type = 'trade_settlement'
                   then 1 end)                         as total_settlements
    from {{ ref('stg_transactions') }}
    group by user_id

),

activity as (

    select
        t.user_id,
        u.name,
        u.email,
        u.country,
        u.account_type,
        u.risk_profile,

        -- Trade metrics
        count(distinct t.trade_id)                     as total_trades,
        count(case when t.trade_type = 'buy'  then 1 end) as total_buys,
        count(case when t.trade_type = 'sell' then 1 end) as total_sells,
        count(distinct t.instrument_id)                as distinct_instruments,

        -- Value metrics
        sum(t.notional_value)                          as total_notional,
        sum(case when t.trade_type = 'buy'
                 then t.notional_value else 0 end)     as total_bought_value,
        sum(case when t.trade_type = 'sell'
                 then t.notional_value else 0 end)     as total_sold_value,
        avg(t.notional_value)                          as avg_trade_size,

        -- Timeline
        min(t.traded_at)                               as first_trade_at,
        max(t.traded_at)                               as last_trade_at

    from trades t
    inner join users u on t.user_id = u.user_id
    group by 1, 2, 3, 4, 5, 6

),

final as (

    select
        a.*,
        coalesce(tx.total_fees_paid, 0)                as total_fees_paid,
        coalesce(tx.total_deposits, 0)                 as total_deposits,
        coalesce(tx.total_settlements, 0)              as total_settlements,

        -- Estimated net P&L direction (sell - buy notional)
        a.total_sold_value - a.total_bought_value      as net_pnl_estimate,

        -- Days active (inclusive)
        cast(a.last_trade_at as date)
            - cast(a.first_trade_at as date)           as trading_days_span

    from activity a
    left join transactions tx on a.user_id = tx.user_id

)

select * from final
