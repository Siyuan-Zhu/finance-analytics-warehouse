{# Vendor name -> matching key: lower case, "&" as "and", punctuation removed, a leading "the" and trailing company
   suffixes (inc, llc, ltd, co ...) dropped. Edge spaces are trimmed before the prefix and suffixes are looked for, so
   "Foo Inc " and " The Foo Co." still match "Foo". The suffix pattern is applied twice so "Foo Co Inc" loses both. #}
{% macro normalize_vendor(column) -%}
    trim(
        regexp_replace(
            regexp_replace(
                regexp_replace(
                    trim(regexp_replace(
                        lower(replace(replace({{ column }}, '&', ' and '), '.', '')),
                        '[^a-z0-9]+', ' ', 'g')),
                    '^the ', ''),
                ' (inc|incorporated|llc|llp|lp|ltd|limited|co|corp|corporation|company)$', ''),
            ' (inc|incorporated|llc|llp|lp|ltd|limited|co|corp|corporation|company)$', '')
    )
{%- endmacro %}
