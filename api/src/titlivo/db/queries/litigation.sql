-- Court cases recorded against a parcel. Params: parcel_id
select id, case_no, court, status, filed_on, source_record_id
from titlivo.litigation where parcel_id = %(parcel_id)s
order by filed_on desc
