-- Parcels with an unreleased mortgage AND two or more transfers in the last three years:
-- the ones a lender should look at first.
select p.id, p.survey_no, v.name as village, e.lender, e.amount_inr, count(t.*) as transfers_3y
from titlivo.encumbrances e
join titlivo.parcels p on p.id = e.parcel_id
join titlivo.villages v on v.id = p.village_id
left join titlivo.title_events t
  on t.parcel_id = p.id and t.event_type in ('sale', 'gift') and t.registered_on > current_date - interval '3 years'
where e.status = 'active'
group by p.id, v.name, e.lender, e.amount_inr
order by transfers_3y desc, e.amount_inr desc;
