-- How many parcels carry each red flag, per state? (the "where is the risk" slide)
select v.state, f.flag_id, count(distinct f.parcel_id) as parcels
from titlivo.parcel_flags f
join titlivo.parcels p on p.id = f.parcel_id
join titlivo.villages v on v.id = p.village_id
group by v.state, f.flag_id
order by v.state, f.flag_id;
