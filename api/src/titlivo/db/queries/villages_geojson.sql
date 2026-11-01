-- Village outlines (map layer).
select jsonb_build_object('type', 'FeatureCollection', 'features', jsonb_agg(jsonb_build_object(
    'type', 'Feature', 'id', v.id, 'geometry', st_asgeojson(v.geom, 6)::jsonb,
    'properties', jsonb_build_object('id', v.id, 'name', v.name, 'name_local', v.name_local, 'state_code', v.state_code,
        'parcels', (select count(*) from titlivo.parcels p where p.village_id = v.id))))) as fc
from titlivo.villages v
