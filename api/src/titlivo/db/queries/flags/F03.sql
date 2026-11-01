-- F03 Pending litigation recorded against the parcel.
select l.parcel_id,
       jsonb_build_object('case_no', l.case_no, 'court', l.court, 'status', l.status, 'filed_on', l.filed_on) as evidence,
       l.source_record_id
from titlivo.litigation l
where l.status in ('pending', 'stay')
  and (%(parcel_id)s::text is null or l.parcel_id = %(parcel_id)s::text)
