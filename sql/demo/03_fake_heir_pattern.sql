-- The Keesara pattern: heirs added without a death record, then a quick sale.
select s.parcel_id, h.registered_on as heirs_added, s.registered_on as sold, s.registered_on - h.registered_on as days_between,
       cardinality(h.to_parties) as heirs, s.amount_inr
from titlivo.title_events s
join titlivo.title_events h on h.parcel_id = s.parcel_id and h.event_type = 'succession'
 and s.registered_on between h.registered_on and h.registered_on + 180 and s.from_parties && h.to_parties
where s.event_type = 'sale' and h.basis_ref is null
order by days_between;
