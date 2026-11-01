-- F11 Double sale: the same transferor conveys the parcel twice without reacquiring it in between.
select distinct on (a.parcel_id, b.id) a.parcel_id,
       jsonb_build_object('first_sale', jsonb_build_object('mutation_no', a.mutation_no, 'registered_on', a.registered_on, 'doc_no', a.doc_no),
                          'second_sale', jsonb_build_object('mutation_no', b.mutation_no, 'registered_on', b.registered_on, 'doc_no', b.doc_no),
                          'common_transferors', (select count(*) from unnest(a.from_parties) x where x = any (b.from_parties))) as evidence,
       b.source_record_id
from titlivo.title_events a
join titlivo.title_events b
  on b.parcel_id = a.parcel_id and b.event_type = 'sale' and a.event_type = 'sale'
 and (b.registered_on, b.seq) > (a.registered_on, a.seq)
 and a.from_parties && b.from_parties
where (%(parcel_id)s::text is null or a.parcel_id = %(parcel_id)s::text)
  and not exists (
      select 1 from titlivo.title_events m
      where m.parcel_id = a.parcel_id
        and (m.registered_on, m.seq) > (a.registered_on, a.seq)
        and (m.registered_on, m.seq) < (b.registered_on, b.seq)
        and m.to_parties && b.from_parties
  )
order by a.parcel_id, b.id, a.registered_on desc
