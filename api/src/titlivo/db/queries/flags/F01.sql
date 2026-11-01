-- F01 Break in chain of title: a transfer whose transferors were not all recorded holders.
-- The title_chain placeholder below is replaced with db/queries/title_chain.sql by services/flags.py.
select t.parcel_id,
       jsonb_build_object('mutation_no', t.mutation_no, 'event_type', t.event_type, 'registered_on', t.registered_on,
                          'doc_no', t.doc_no, 'transferors', cardinality(t.from_parties),
                          'transferors_not_holders', (select count(*) from unnest(t.from_parties) x where x <> all (t.holders_before))) as evidence,
       t.source_record_id
from ({{title_chain}}) t
where not t.consistent
