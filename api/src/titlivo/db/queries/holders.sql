-- Current recorded holders of a parcel. Params: parcel_id
select pt.id, pt.name, pt.name_local, h.share
from titlivo.holdings h join titlivo.parties pt on pt.id = h.party_id
where h.parcel_id = %(parcel_id)s
order by pt.name
