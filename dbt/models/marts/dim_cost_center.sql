select cost_center_code, cost_center_name, kind
from {{ ref('cost_centers') }}
