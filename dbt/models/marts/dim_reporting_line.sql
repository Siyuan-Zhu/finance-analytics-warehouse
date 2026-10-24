select reporting_line_key, line_name, section_key, section_label, section_order, line_order, sign
from {{ ref('reporting_lines') }}
