-- F16 Sale while mortgaged: a sale registered while an encumbrance was active (no release before the sale).
select s.parcel_id,
       jsonb_build_object('sale', jsonb_build_object('mutation_no', s.mutation_no, 'registered_on', s.registered_on, 'doc_no', s.doc_no),
                          'mortgage', jsonb_build_object('lender', e.lender, 'amount_inr', e.amount_inr,
                                                         'created_on', e.created_on, 'released_on', e.released_on)) as evidence,
       s.source_record_id
from titlivo.title_events s
join titlivo.encumbrances e
  on e.parcel_id = s.parcel_id
 and s.registered_on > e.created_on
 and (e.released_on is null or s.registered_on < e.released_on)
where s.event_type = 'sale'
  and (%(parcel_id)s::text is null or s.parcel_id = %(parcel_id)s::text)
