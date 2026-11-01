-- One canonical schema, three native formats: the same question answered for every state.
select v.state, sr.record_type, p.native_area || ' ' || p.native_unit as as_written, round(p.area_m2) as area_m2,
       p.tenure_class, sr.native ->> (case sr.record_type when 'mh_712' then 'भूमापन क्रमांक'
                                                         when 'ka_rtc' then 'ಸರ್ವೆ ನಂಬರ್' else 'સર્વે નંબર' end) as survey_as_written,
       p.survey_no as survey_canonical
from titlivo.parcels p
join titlivo.villages v on v.id = p.village_id
join titlivo.source_records sr on sr.id = p.source_record_id
where p.survey_no in ('214/2', '214', '312')
order by v.state;
