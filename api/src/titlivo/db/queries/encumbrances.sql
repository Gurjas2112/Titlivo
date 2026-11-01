-- Encumbrances on a parcel, newest first. Params: parcel_id
select id, kind, native_term, lender, amount_inr, created_on, released_on, status, mutation_no, source_record_id, injected
from titlivo.encumbrances where parcel_id = %(parcel_id)s
order by created_on desc
