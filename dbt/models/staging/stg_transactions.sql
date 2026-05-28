/*
  stg_transactions.sql
  ──────────────────────────────────────────────────────────────────────────────
  Staging layer for financial transactions.
  Includes both trade settlements and direct deposits/withdrawals.
  trade_id is nullable (deposits have no associated trade).
*/

with source as (

    select * from {{ source('trading_raw', 'raw_transactions') }}

),

staged as (

    select
        transaction_id,
        user_id,
        nullif(trim(trade_id), '')                      as trade_id,   -- nullable
        cast(amount as numeric(18, 2))                  as amount,
        cast(fee    as numeric(18, 2))                  as fee,
        lower(trim(transaction_type))                   as transaction_type,
        cast(transaction_timestamp as timestamp)        as transacted_at

    from source
    where transaction_id is not null

)

select * from staged
