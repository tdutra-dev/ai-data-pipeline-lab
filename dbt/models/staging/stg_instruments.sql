/*
  stg_instruments.sql
  ──────────────────────────────────────────────────────────────────────────────
  Staging layer for tradeable financial instruments.
*/

with source as (

    select * from {{ source('trading_raw', 'raw_instruments') }}

),

staged as (

    select
        instrument_id,
        upper(trim(symbol))                             as symbol,
        trim(name)                                      as instrument_name,
        lower(trim(instrument_type))                    as instrument_type,
        upper(trim(currency))                           as currency

    from source
    where instrument_id is not null

)

select * from staged
