-- Chain of title (spec §6.2): walk each parcel's events in registration order, carrying the set of
-- recorded holders forward. A transfer is consistent only if every transferor was a holder at the
-- time; otherwise the chain is broken (flag F01). GPA and mutation entries do not change holders.
-- Params: %(parcel_id)s (text or NULL for all parcels)
with recursive ev as (
    select e.*, row_number() over (partition by e.parcel_id order by e.registered_on, e.seq) as rn
    from titlivo.title_events e
    where (%(parcel_id)s::text is null or e.parcel_id = %(parcel_id)s::text)
),
chain as (
    select ev.parcel_id, ev.rn, ev.id, ev.seq, ev.event_type, ev.native_term, ev.registered_on,
           ev.from_parties, ev.to_parties, ev.doc_no, ev.amount_inr, ev.mutation_no, ev.mutation_status,
           ev.basis_ref, ev.source_record_id, ev.injected,
           '{}'::text[] as holders_before,
           ev.to_parties as holders_after,
           (ev.event_type = 'grant' or cardinality(ev.from_parties) = 0) as consistent
    from ev
    where ev.rn = 1
    union all
    select n.parcel_id, n.rn, n.id, n.seq, n.event_type, n.native_term, n.registered_on,
           n.from_parties, n.to_parties, n.doc_no, n.amount_inr, n.mutation_no, n.mutation_status,
           n.basis_ref, n.source_record_id, n.injected,
           c.holders_after,
           case
               when n.event_type in ('sale', 'gift', 'succession', 'partition') then
                   array(select x from unnest(c.holders_after) as x where x <> all (n.from_parties)
                         union
                         select y from unnest(n.to_parties) as y)
               when n.event_type = 'grant' then n.to_parties
               else c.holders_after
           end,
           case
               when n.event_type in ('sale', 'gift', 'succession', 'partition') then n.from_parties <@ c.holders_after
               else true
           end
    from chain c
    join ev n on n.parcel_id = c.parcel_id and n.rn = c.rn + 1
)
select parcel_id, rn as position, id as event_id, seq, event_type, native_term, registered_on,
       from_parties, to_parties, holders_before, holders_after, consistent,
       doc_no, amount_inr, mutation_no, mutation_status, basis_ref, source_record_id, injected,
       registered_on - lag(registered_on) over (partition by parcel_id order by rn) as gap_days
from chain
order by parcel_id, rn
