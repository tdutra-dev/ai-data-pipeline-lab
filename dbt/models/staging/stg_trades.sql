/*
  stg_trades.sql
  ──────────────────────────────────────────────────────────────────────────────
  Staging layer for raw trade orders.
  Responsibilities:
    • Rename columns to snake_case business vocabulary
    • Lowercase + trim categoricals (trade_type, status)
    • Cast to proper types
    • Derive notional_value (quantity × price)
    • Exclude rows with null primary key (defensive guard)
*/

with source as (

    select * from {{ source('trading_raw', 'raw_trades') }}

),

staged as (

    select
        trade_id,
        user_id,
        instrument_id,

        lower(trim(trade_type))                         as trade_type,
        cast(quantity        as numeric(18, 8))         as quantity,
        cast(price           as numeric(18, 8))         as price,
        cast(quantity as numeric(18, 8))
            * cast(price as numeric(18, 8))             as notional_value,

        cast(trade_timestamp as timestamp)              as traded_at,
        lower(trim(status))                             as status

    from source
    where trade_id is not null

)

select * from staged
