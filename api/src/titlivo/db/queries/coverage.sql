-- Coverage per state: villages, parcels, flagged parcels.
select v.state_code, v.state, count(distinct v.id) as villages, count(p.id) as parcels,
       count(distinct f.parcel_id) as flagged_parcels
from titlivo.villages v
left join titlivo.parcels p on p.village_id = v.id
left join titlivo.parcel_flags f on f.parcel_id = p.id
group by v.state_code, v.state
order by v.state_code desc
