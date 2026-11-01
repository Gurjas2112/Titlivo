-- F12 Heir-impersonation transfer: a sale by parties added through a succession entry within the
-- previous 180 days, where that succession has no death or succession record behind it.
select s.parcel_id,
       jsonb_build_object('succession', jsonb_build_object('mutation_no', h.mutation_no, 'registered_on', h.registered_on,
                                                           'basis_ref', h.basis_ref, 'heirs_added', cardinality(h.to_parties)),
                          'sale', jsonb_build_object('mutation_no', s.mutation_no, 'registered_on', s.registered_on, 'doc_no', s.doc_no),
                          'days_between', s.registered_on - h.registered_on) as evidence,
       s.source_record_id
from titlivo.title_events s
join titlivo.title_events h
  on h.parcel_id = s.parcel_id and h.event_type = 'succession'
 and h.registered_on <= s.registered_on and s.registered_on - h.registered_on <= 180
 and s.from_parties && h.to_parties
where s.event_type = 'sale'
  and (h.basis_ref is null or btrim(h.basis_ref) = '')
  and (%(parcel_id)s::text is null or s.parcel_id = %(parcel_id)s::text)
