{#
  generate_schema_name.sql
  ──────────────────────────────────────────────────────────────────────────────
  Override dbt's default schema naming so that the model config
    +schema: staging
  produces the schema "staging" rather than "{target.schema}_staging".

  This keeps the warehouse clean and human-readable:
    trading.staging.*
    trading.intermediate.*
    trading.marts.*
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema | trim }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
