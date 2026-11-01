-- Sale price per hectare by decade and state (storytelling with data; synthetic prices).
select v.state, (extract(year from t.registered_on)::int / 10) * 10 as decade,
       round(avg(t.amount_inr / (p.area_m2 / 10000))) as avg_inr_per_ha, count(*) as sales
from titlivo.title_events t
join titlivo.parcels p on p.id = t.parcel_id
join titlivo.villages v on v.id = p.village_id
where t.event_type = 'sale' and t.amount_inr is not null
group by v.state, decade
order by v.state, decade;
