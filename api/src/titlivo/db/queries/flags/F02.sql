-- F02 Mortgage or charge without a recorded release.
select e.parcel_id,
       jsonb_build_object('lender', e.lender, 'amount_inr', e.amount_inr, 'created_on', e.created_on,
                          'mutation_no', e.mutation_no, 'kind', e.kind) as evidence,
       e.source_record_id
from titlivo.encumbrances e
where e.status = 'active'
  and (%(parcel_id)s::text is null or e.parcel_id = %(parcel_id)s::text)
