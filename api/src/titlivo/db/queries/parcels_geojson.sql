-- Every parcel as a GeoJSON feature with its worst flag severity (map layer). No names.
select jsonb_build_object(
    'type', 'FeatureCollection',
    'features', coalesce(jsonb_agg(jsonb_build_object(
        'type', 'Feature',
        'id', p.id,
        'geometry', st_asgeojson(p.geom, 6)::jsonb,
        'properties', jsonb_build_object(
            'id', p.id, 'survey_no', p.survey_no, 'state_code', p.state_code, 'village', v.name,
            'flag_count', coalesce(f.n, 0), 'max_severity', coalesce(f.sev, 0),
            'flags', coalesce(f.ids, '[]'::jsonb))
    )), '[]'::jsonb)) as fc
from titlivo.parcels p
join titlivo.villages v on v.id = p.village_id
left join (
    select parcel_id, count(*) as n, jsonb_agg(distinct flag_id) as ids,
           max(case severity when 'high' then 3 when 'medium' then 2 else 1 end) as sev
    from titlivo.parcel_flags group by parcel_id
) f on f.parcel_id = p.id
