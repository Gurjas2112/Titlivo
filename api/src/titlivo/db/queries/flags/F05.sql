-- F05 Restricted tenure: transfer needs prior sanction (MH Class II, KA PTCL grant, GJ new tenure).
select p.id as parcel_id,
       jsonb_build_object('tenure_class', p.tenure_class) as evidence,
       p.source_record_id
from titlivo.parcels p
where p.tenure_class = any (%(restricted)s::text[])
  and (%(parcel_id)s::text is null or p.id = %(parcel_id)s::text)
