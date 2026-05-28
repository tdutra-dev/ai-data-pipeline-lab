/*
  stg_users.sql
  ──────────────────────────────────────────────────────────────────────────────
  Staging layer for platform users.
  Responsibilities:
    • Lowercase + trim categoricals
    • Cast timestamps
    • Exclude rows with null primary key
*/

with source as (

    select * from {{ source('trading_raw', 'raw_users') }}

),

staged as (

    select
        user_id,
        trim(name)                                      as name,
        lower(trim(email))                              as email,
        upper(trim(country))                            as country,
        lower(trim(account_type))                       as account_type,
        lower(trim(risk_profile))                       as risk_profile,
        cast(created_at as timestamp)                   as created_at

    from source
    where user_id is not null

)

select * from staged
