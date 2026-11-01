-- Search parcels by survey number, owner name (any script, via name_key trigrams) or village name.
-- Params: q_survey (ASCII digits), q_key (name_key of the query), q_text (raw lower-case), lim
with hits as (
    select p.id, 3.0 as score from titlivo.parcels p
    where %(q_survey)s <> '' and (p.survey_no = %(q_survey)s or p.survey_no like %(q_survey)s || '/%%')
    union all
    select h.parcel_id, 1.0 + similarity(pt.name_key, %(q_key)s)
    from titlivo.parties pt join titlivo.holdings h on h.party_id = pt.id
    where %(q_key)s <> '' and (pt.name_key %% %(q_key)s or pt.name_key like '%%' || %(q_key)s || '%%')
    union all
    select p.id, 0.8 from titlivo.parcels p join titlivo.villages v on v.id = p.village_id
    where %(q_text)s <> '' and (lower(v.name) like '%%' || %(q_text)s || '%%' or v.name_local like '%%' || %(q_text)s || '%%')
)
select p.id, p.survey_no, p.state_code, v.name as village, v.name_local as village_local, v.district,
       max(h.score) as score,
       coalesce((select max(case f.severity when 'high' then 3 when 'medium' then 2 else 1 end)
                 from titlivo.parcel_flags f where f.parcel_id = p.id), 0) as max_severity,
       (select count(*) from titlivo.parcel_flags f where f.parcel_id = p.id) as flag_count
from hits h
join titlivo.parcels p on p.id = h.id
join titlivo.villages v on v.id = p.village_id
group by p.id, v.id
order by score desc, p.survey_no
limit %(lim)s
