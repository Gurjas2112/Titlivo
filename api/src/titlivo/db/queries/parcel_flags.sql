-- Cached flags for one parcel (recomputed by the rules on every change). Params: parcel_id
select flag_id, severity, evidence, source_record_id
from titlivo.parcel_flags where parcel_id = %(parcel_id)s
order by case severity when 'high' then 0 when 'medium' then 1 else 2 end, flag_id
