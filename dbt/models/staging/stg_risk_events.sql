/*
  stg_risk_events.sql
  ──────────────────────────────────────────────────────────────────────────────
  Staging layer for compliance and risk monitoring events.
  trade_id is nullable – some events are not linked to a specific trade.
*/

with source as (

    select * from {{ source('trading_raw', 'raw_risk_events') }}

),

staged as (

    select
        event_id,
        user_id,
        nullif(trim(trade_id), '')                      as trade_id,   -- nullable
        lower(trim(event_type))                         as event_type,
        lower(trim(severity))                           as severity,
        cast(event_timestamp as timestamp)              as event_occurred_at,
        trim(description)                               as description

    from source
    where event_id is not null

)

select * from staged
