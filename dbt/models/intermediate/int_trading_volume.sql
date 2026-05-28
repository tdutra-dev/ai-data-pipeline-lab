/*
  int_trading_volume.sql
  ──────────────────────────────────────────────────────────────────────────────
  Intermediate model: daily trading volume per instrument.

  Joins filled trades with instrument metadata and aggregates by
  calendar day. Produces the building block for volume-based analytics
  and anomaly detection.
*/

with trades as (

    select * from {{ ref('stg_trades') }}
    where status = 'filled'

),

instruments as (

    select * from {{ ref('stg_instruments') }}

),

volume_by_day as (

    select
        cast(t.traded_at as date)                           as trade_date,
        t.instrument_id,
        i.symbol,
        i.instrument_name,
        i.instrument_type,
        i.currency,

        -- Trade counts
        count(*)                                            as total_trades,
        count(case when t.trade_type = 'buy'  then 1 end)  as buy_count,
        count(case when t.trade_type = 'sell' then 1 end)  as sell_count,

        -- Volume metrics
        sum(t.quantity)                                     as total_quantity,
        sum(case when t.trade_type = 'buy'
                 then t.quantity else 0 end)               as bought_quantity,
        sum(case when t.trade_type = 'sell'
                 then t.quantity else 0 end)               as sold_quantity,

        -- Notional value
        sum(t.notional_value)                              as total_notional,
        avg(t.price)                                       as avg_price,
        min(t.price)                                       as min_price,
        max(t.price)                                       as max_price

    from trades t
    inner join instruments i on t.instrument_id = i.instrument_id
    group by 1, 2, 3, 4, 5, 6

)

select * from volume_by_day
